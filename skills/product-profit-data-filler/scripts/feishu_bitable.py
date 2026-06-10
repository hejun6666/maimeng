"""Small stdlib Feishu Bitable client and probe CLI."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://open.feishu.cn/open-apis"


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def parse_bitable_url(url):
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    app_match = re.search(r"/base/([A-Za-z0-9]+)", parsed.path)
    if not app_match:
        raise ValueError("Feishu Bitable link must contain /base/<app_token>")
    return {
        "app_token": app_match.group(1),
        "table_id": (query.get("table") or query.get("table_id") or [None])[0],
        "view_id": (query.get("view") or query.get("view_id") or [None])[0],
    }


def extract_file_tokens(value):
    tokens = []
    if isinstance(value, list):
        for item in value:
            tokens.extend(extract_file_tokens(item))
    elif isinstance(value, dict):
        token = value.get("file_token") or value.get("fileToken")
        if token:
            tokens.append(token)
        for child in value.values():
            if isinstance(child, (list, dict)):
                tokens.extend(extract_file_tokens(child))
    return tokens


def _redact(text, secrets=()):
    text = str(text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", text)
    for secret in secrets:
        if secret:
            text = text.replace(str(secret), "<redacted>")
    return text


def _known_secrets(*extra):
    names = ["FEISHU_APP_ID", "FEISHU_APP_SECRET"]
    return [value for value in [*(os.environ.get(name) for name in names), *extra] if value]


def _decode_json(payload):
    if not payload:
        return {}
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _feishu_error(status, payload=None, fallback=None, secrets=()):
    data = _decode_json(payload or b"")
    code = data.get("code", "")
    msg = data.get("msg") or data.get("message") or fallback or "request failed"
    request_id = data.get("request_id") or data.get("requestId") or data.get("log_id") or ""
    parts = [f"Feishu API error status={status}"]
    if code != "":
        parts.append(f"code={code}")
    if msg:
        parts.append(f"msg={_redact(msg, secrets)}")
    if request_id:
        parts.append(f"request_id={_redact(request_id, secrets)}")
    return RuntimeError(" ".join(parts))


def verify_readable_product_image(client, records, field_map):
    image_meta = field_map.get("product_image")
    if not image_meta:
        raise RuntimeError("Probe failed: product_image field is not mapped")
    image_field = image_meta["field_name"]
    last_error = None
    for record in records:
        for token in extract_file_tokens(record.get("fields", {}).get(image_field)):
            try:
                client.download_media(token)
                return token
            except RuntimeError as exc:
                last_error = str(exc)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"Probe failed: No readable product image attachment found in sampled records{detail}")


class FeishuClient:
    def __init__(self, token=None):
        self.token = token or self.get_tenant_access_token()

    def get_tenant_access_token(self):
        app_id = os.environ["FEISHU_APP_ID"]
        app_secret = os.environ["FEISHU_APP_SECRET"]
        body = {"app_id": app_id, "app_secret": app_secret}
        req = urllib.request.Request(
            API + "/auth/v3/tenant_access_token/internal",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json; charset=utf-8")
        secrets = _known_secrets(app_id, app_secret)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            raise _feishu_error(exc.code, exc.read(), exc.reason, secrets) from None
        except urllib.error.URLError as exc:
            raise _feishu_error("network", fallback=exc.reason, secrets=secrets) from None
        result = _decode_json(payload)
        if result.get("code") != 0:
            raise _feishu_error(200, payload, secrets=secrets)
        return result["tenant_access_token"]

    def request(self, method, path, body=None, params=None, raw=False):
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        if body is not None:
            req.add_header("Content-Type", "application/json; charset=utf-8")
        secrets = _known_secrets(self.token)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            raise _feishu_error(exc.code, exc.read(), exc.reason, secrets) from None
        except urllib.error.URLError as exc:
            raise _feishu_error("network", fallback=exc.reason, secrets=secrets) from None
        if raw:
            return payload
        result = _decode_json(payload)
        if result.get("code") != 0:
            raise _feishu_error(200, payload, secrets=secrets)
        return result.get("data", {})

    def _list_paginated(self, path, page_size=100):
        items = []
        page_token = None
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            data = self.request("GET", path, params=params)
            items.extend(data.get("items", []))
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token")
            if not page_token:
                return items

    def list_tables(self, app_token):
        return self._list_paginated(f"/bitable/v1/apps/{app_token}/tables")

    def list_fields(self, app_token, table_id):
        return self._list_paginated(f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields")

    def list_records(self, app_token, table_id, page_size=100):
        return self._list_paginated(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            page_size=page_size,
        )

    def list_records_sample(self, app_token, table_id, page_size=20, max_pages=1, max_records=None):
        items = []
        page_token = None
        for _ in range(max_pages):
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            data = self.request(
                "GET",
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                params=params,
            )
            items.extend(data.get("items", []))
            if max_records is not None and len(items) >= max_records:
                return items[:max_records]
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token")
            if not page_token:
                return items
        return items

    def download_media(self, file_token):
        return self.request("GET", f"/drive/v1/medias/{file_token}/download", raw=True)

    def batch_update_records(self, app_token, table_id, records):
        body = {"records": records}
        return self.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
            body=body,
        )


def cmd_probe(args):
    from field_mapping import build_field_map

    load_env_file(args.env)
    info = parse_bitable_url(args.url)
    client = FeishuClient()
    tables = client.list_tables(info["app_token"])
    if not tables and not info["table_id"]:
        raise RuntimeError("No tables found and URL did not include a table id")
    table_id = info["table_id"] or tables[0]["table_id"]
    fields = client.list_fields(info["app_token"], table_id)
    records = client.list_records_sample(
        info["app_token"],
        table_id,
        page_size=args.sample_size,
        max_pages=args.max_pages,
        max_records=args.sample_size,
    )
    mapping = build_field_map(fields)
    verify_readable_product_image(client, records, mapping)
    out = {
        "link": info,
        "table_id": table_id,
        "tables": tables,
        "fields": fields,
        "field_map": mapping,
        "sample_record_count": len(records),
        "readable_product_image": True,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)


def build_parser():
    parser = argparse.ArgumentParser(description="Feishu Bitable product-profit helper")
    parser.add_argument("--env", default=".env", help="path to local env file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="read Bitable metadata and sample records")
    probe.add_argument("--url", required=True, help="Feishu Bitable URL containing /base/<app_token>")
    probe.add_argument("--out", help="optional JSON output path")
    probe.add_argument("--sample-size", type=int, default=20, help="maximum records to sample")
    probe.add_argument("--max-pages", type=int, default=1, help="maximum record pages to read")
    probe.set_defaults(func=cmd_probe)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])

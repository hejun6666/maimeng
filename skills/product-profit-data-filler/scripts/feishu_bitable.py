"""Small stdlib Feishu Bitable client and probe CLI."""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://open.feishu.cn/open-apis"
MAX_UPDATE_BATCH_SIZE = 500
TARGET_ROLES = [
    "purchase_price_gbp",
    "package_dimensions",
    "package_weight",
    "product_attribute",
    "selling_price_gbp",
]


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


def is_blank(value):
    if value in (None, "", [], {}):
        return True
    return isinstance(value, str) and value.strip() == ""


def plan_records(records, field_map):
    image_field = field_map["product_image"]["field_name"]
    target_names = [field_map[role]["field_name"] for role in TARGET_ROLES if role in field_map]
    planned = []
    for record in records:
        fields = record.get("fields", {})
        image_tokens = extract_file_tokens(fields.get(image_field))
        if not image_tokens:
            continue
        if target_names and not any(is_blank(fields.get(name)) for name in target_names):
            continue
        planned.append(
            {
                "record_id": record["record_id"],
                "image_tokens": image_tokens,
                "fields": fields,
            }
        )
    return planned


def shape_update_record(record_id, field_map, values):
    fields = {}
    for role, value in values.items():
        meta = field_map.get(role)
        if meta is not None and value is not None:
            fields[meta["field_name"]] = value
    return {"record_id": record_id, "fields": fields}


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


def _write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _selected_table_id(info, tables):
    if info["table_id"]:
        return info["table_id"]
    if tables:
        return tables[0]["table_id"]
    raise RuntimeError("No tables found and URL did not include a table id")


def _safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "record")).strip("._")
    return cleaned or "record"


def _image_extension(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


def _chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def validate_update_records(records):
    if not isinstance(records, list):
        raise ValueError("Updates JSON must be a list of Feishu update records")
    allowed_keys = {"record_id", "fields"}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Update record at index {index} must be an object")
        unknown_keys = set(record) - allowed_keys
        if unknown_keys:
            raise ValueError(f"Update record at index {index} has unknown keys: {sorted(unknown_keys)}")
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"Update record at index {index} must have a non-empty string record_id")
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise ValueError(f"Update record at index {index} must have a non-empty fields object")


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
        _write_json(args.out, out)


def cmd_plan(args):
    from field_mapping import build_field_map

    load_env_file(args.env)
    info = parse_bitable_url(args.url)
    client = FeishuClient()
    tables = client.list_tables(info["app_token"])
    table_id = _selected_table_id(info, tables)
    fields = client.list_fields(info["app_token"], table_id)
    records = client.list_records(info["app_token"], table_id)
    mapping = build_field_map(fields)
    planned = plan_records(records, mapping)
    out = {
        "link": info,
        "table_id": table_id,
        "field_map": mapping,
        "record_count": len(planned),
        "records": planned,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    _write_json(args.out, out)


def _plan_records_from_payload(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    raise ValueError("Plan JSON must be a list or an object with a records list")


def cmd_download_images(args):
    load_env_file(args.env)
    parse_bitable_url(args.url)
    plan_payload = _read_json(args.plan)
    records = _plan_records_from_payload(plan_payload)
    client = FeishuClient()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = []
    for record in records:
        record_id = record["record_id"]
        for token_index, file_token in enumerate(record.get("image_tokens", [])):
            data = client.download_media(file_token)
            filename = f"{_safe_name(record_id)}_{token_index}{_image_extension(data)}"
            path = out_dir / filename
            path.write_bytes(data)
            metadata.append(
                {
                    "record_id": record_id,
                    "token_index": token_index,
                    "file_token": file_token,
                    "path": str(path),
                    "filename": filename,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    metadata_path = out_dir / "metadata.json"
    _write_json(metadata_path, metadata)
    print(json.dumps({"downloaded": len(metadata), "metadata": str(metadata_path)}, ensure_ascii=False, indent=2))


def cmd_update_records(args):
    load_env_file(args.env)
    info = parse_bitable_url(args.url)
    updates = _read_json(args.updates)
    validate_update_records(updates)
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.batch_size > MAX_UPDATE_BATCH_SIZE:
        raise ValueError(f"--batch-size must be at most {MAX_UPDATE_BATCH_SIZE}")
    client = FeishuClient()
    tables = [] if info["table_id"] else client.list_tables(info["app_token"])
    table_id = _selected_table_id(info, tables)
    total = 0
    for batch in _chunks(updates, args.batch_size):
        if not batch:
            continue
        client.batch_update_records(info["app_token"], table_id, batch)
        total += len(batch)
    print(json.dumps({"updated": total, "batches": (total + args.batch_size - 1) // args.batch_size}, indent=2))


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

    plan = subparsers.add_parser("plan", help="plan records with images and blank target fields")
    plan.add_argument("--url", required=True, help="Feishu Bitable URL containing /base/<app_token>")
    plan.add_argument("--out", required=True, help="JSON plan output path")
    plan.set_defaults(func=cmd_plan)

    download = subparsers.add_parser("download-images", help="download planned product images")
    download.add_argument("--url", required=True, help="Feishu Bitable URL containing /base/<app_token>")
    download.add_argument("--plan", required=True, help="JSON plan from the plan command")
    download.add_argument("--out-dir", required=True, help="directory for downloaded images")
    download.set_defaults(func=cmd_download_images)

    update = subparsers.add_parser("update-records", help="batch update Feishu Bitable records")
    update.add_argument("--url", required=True, help="Feishu Bitable URL containing /base/<app_token>")
    update.add_argument("--updates", required=True, help="JSON list of Feishu update records")
    update.add_argument("--batch-size", type=int, default=100, help="maximum records per batch update")
    update.set_defaults(func=cmd_update_records)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])

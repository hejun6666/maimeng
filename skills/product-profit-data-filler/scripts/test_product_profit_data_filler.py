from pathlib import Path
import io
import json
import re
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_REFERENCES = [
    "field-mapping.md",
    "feishu-bitable-workflow.md",
    "1688-data-rules.md",
    "amazon-uk-price-rules.md",
]
TASK1_DOCS = [
    ROOT / "SKILL.md",
    *(ROOT / "references" / name for name in REQUIRED_REFERENCES),
]
MOJIBAKE_MARKERS = [
    "澶氱淮琛ㄦ牸",
    "鍥剧墖",
    "閲囪喘浠",
    "閫夊搧",
    "婢舵",
    "闁插",
    "閸",
    "鈧",
    "銆",
    "拢",
]
SECRET_VALUE_RE = re.compile(
    r"(cli_[A-Za-z0-9_-]{12,}|[A-Za-z0-9_-]{32,}|FEISHU_APP_(?:ID|SECRET)\s*=\s*['\"]?[^<\s][^'\"]+)",
)


def read(path):
    return path.read_text(encoding="utf-8")


def skill_description():
    text = read(ROOT / "SKILL.md")
    match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    if not match:
        raise AssertionError("SKILL.md missing description frontmatter")
    return match.group(1)


class SkillContractTest(unittest.TestCase):
    def test_skill_mentions_bitable_and_amazon_uk(self):
        text = read(ROOT / "SKILL.md")
        self.assertIn("Feishu Bitable", text)
        self.assertIn("amazon.co.uk", text)
        self.assertIn("9.17", text)
        self.assertIn("FEISHU_APP_ID", text)
        self.assertIn("FEISHU_APP_SECRET", text)

    def test_skill_description_is_under_1024_chars(self):
        self.assertLess(len(skill_description()), 1024)

    def test_required_references_exist_one_level_deep(self):
        refs = ROOT / "references"
        for name in REQUIRED_REFERENCES:
            path = refs / name
            self.assertTrue(path.exists(), name)
            self.assertEqual(path.parent, refs, name)
            self.assertFalse((refs / name / name).exists(), name)

    def test_no_obvious_mojibake_artifacts(self):
        for path in TASK1_DOCS:
            text = read(path)
            for marker in MOJIBAKE_MARKERS:
                self.assertNotIn(marker, text, f"{path.name}: {marker}")

    def test_no_secret_looking_literal_values(self):
        for path in TASK1_DOCS:
            text = read(path)
            self.assertIsNone(SECRET_VALUE_RE.search(text), path.name)

    def test_no_hard_requirement_to_run_missing_scripts(self):
        for path in [ROOT / "SKILL.md", ROOT / "references" / "feishu-bitable-workflow.md"]:
            text = read(path)
            self.assertNotIn("python ", text, path.name)
            self.assertNotIn("scripts/feishu_bitable.py", text, path.name)
            self.assertIn("once the Task 2 helper script is available", text)


class FeishuBitableHelpersTest(unittest.TestCase):
    def test_parse_bitable_url(self):
        from feishu_bitable import parse_bitable_url

        result = parse_bitable_url("https://x.feishu.cn/base/appABC123?table=tbl456&view=vew789")

        self.assertEqual(result["app_token"], "appABC123")
        self.assertEqual(result["table_id"], "tbl456")
        self.assertEqual(result["view_id"], "vew789")

    def test_map_fields(self):
        from field_mapping import build_field_map

        fields = [
            {"field_id": "fld_img", "field_name": "产品图片", "type": 17},
            {"field_id": "fld_cost", "field_name": "采购价", "type": 2},
            {"field_id": "fld_sale", "field_name": "英国售价", "type": 2},
        ]

        result = build_field_map(fields)

        self.assertEqual(result["product_image"]["field_id"], "fld_img")
        self.assertEqual(result["purchase_price_gbp"]["field_id"], "fld_cost")
        self.assertEqual(result["selling_price_gbp"]["field_id"], "fld_sale")

    def test_extract_file_tokens(self):
        from feishu_bitable import extract_file_tokens

        value = [{"file_token": "boxcn123", "name": "a.png"}, {"token": "ignored"}]

        self.assertEqual(extract_file_tokens(value), ["boxcn123"])


class FeishuBitableClientTest(unittest.TestCase):
    def test_list_records_sample_stops_at_page_limit(self):
        from feishu_bitable import FeishuClient

        client = FeishuClient(token="test-token")
        calls = []

        def fake_request(method, path, params=None, **kwargs):
            calls.append(params.copy())
            return {
                "items": [{"record_id": f"rec{len(calls)}"}],
                "has_more": True,
                "page_token": f"page-{len(calls)}",
            }

        client.request = fake_request

        records = client.list_records_sample("appABC123", "tbl456", page_size=2, max_pages=2)

        self.assertEqual([record["record_id"] for record in records], ["rec1", "rec2"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], {"page_size": 2})
        self.assertEqual(calls[1], {"page_size": 2, "page_token": "page-1"})

    def test_verify_readable_product_image_downloads_one_token(self):
        from feishu_bitable import verify_readable_product_image

        class FakeClient:
            def __init__(self):
                self.downloaded = []

            def download_media(self, file_token):
                self.downloaded.append(file_token)
                return b"image-bytes"

        client = FakeClient()
        records = [{"fields": {"产品图片": [{"file_token": "boxcn123"}]}}]
        field_map = {"product_image": {"field_name": "产品图片"}}

        token = verify_readable_product_image(client, records, field_map)

        self.assertEqual(token, "boxcn123")
        self.assertEqual(client.downloaded, ["boxcn123"])

    def test_verify_readable_product_image_requires_readable_token(self):
        from feishu_bitable import verify_readable_product_image

        class FakeClient:
            def download_media(self, file_token):
                raise RuntimeError("Feishu API error status=403 code=999 msg=Forbidden request_id=req-1")

        records = [{"fields": {"产品图片": [{"file_token": "boxcn123"}]}}]
        field_map = {"product_image": {"field_name": "产品图片"}}

        with self.assertRaisesRegex(RuntimeError, "No readable product image attachment"):
            verify_readable_product_image(FakeClient(), records, field_map)

    def test_nonzero_feishu_code_is_sanitized(self):
        from feishu_bitable import FeishuClient

        body = {
            "code": 999,
            "msg": "bad app secret secret-value Bearer raw-token",
            "request_id": "req-abc",
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(body).encode("utf-8")

        with patch.dict("os.environ", {"FEISHU_APP_ID": "app-id", "FEISHU_APP_SECRET": "secret-value"}):
            with patch("urllib.request.urlopen", return_value=FakeResponse()):
                with self.assertRaises(RuntimeError) as raised:
                    FeishuClient().get_tenant_access_token()

        message = str(raised.exception)
        self.assertIn("status=200", message)
        self.assertIn("code=999", message)
        self.assertIn("request_id=req-abc", message)
        self.assertNotIn("secret-value", message)
        self.assertNotIn("raw-token", message)

    def test_http_error_body_is_sanitized(self):
        from feishu_bitable import FeishuClient

        body = {
            "code": 1254003,
            "msg": "Bearer raw-token cannot read secret-value",
            "request_id": "req-http",
        }
        error = urllib.error.HTTPError(
            "https://open.feishu.cn/open-apis/test",
            403,
            "Forbidden",
            {},
            io.BytesIO(json.dumps(body).encode("utf-8")),
        )
        client = FeishuClient(token="raw-token")

        with patch.dict("os.environ", {"FEISHU_APP_SECRET": "secret-value"}):
            with patch("urllib.request.urlopen", side_effect=error):
                with self.assertRaises(RuntimeError) as raised:
                    client.request("GET", "/test")

        message = str(raised.exception)
        self.assertIn("status=403", message)
        self.assertIn("code=1254003", message)
        self.assertIn("request_id=req-http", message)
        self.assertNotIn("secret-value", message)
        self.assertNotIn("raw-token", message)


class BitablePlanTest(unittest.TestCase):
    def test_plan_records_with_missing_fields(self):
        from feishu_bitable import plan_records

        field_map = {
            "product_image": {"field_name": "产品图片"},
            "purchase_price_gbp": {"field_name": "采购价"},
            "package_dimensions": {"field_name": "包装尺寸"},
        }
        records = [
            {
                "record_id": "rec1",
                "fields": {
                    "产品图片": [{"file_token": "img1"}],
                    "采购价": None,
                    "包装尺寸": "",
                },
            },
            {
                "record_id": "rec2",
                "fields": {
                    "产品图片": [],
                    "采购价": None,
                },
            },
            {
                "record_id": "rec3",
                "fields": {
                    "产品图片": [{"file_token": "img3"}],
                    "采购价": 2.5,
                    "包装尺寸": "45 x 32 x 18 cm",
                },
            },
        ]

        plan = plan_records(records, field_map)

        self.assertEqual([record["record_id"] for record in plan], ["rec1"])
        self.assertEqual(plan[0]["image_tokens"], ["img1"])

    def test_shape_update_uses_field_names(self):
        from feishu_bitable import shape_update_record

        values = {"purchase_price_gbp": 2.5, "status": "已补齐", "ignored": "skip"}
        field_map = {
            "purchase_price_gbp": {"field_name": "采购价"},
            "status": {"field_name": "状态"},
        }

        self.assertEqual(
            shape_update_record("rec1", field_map, values),
            {"record_id": "rec1", "fields": {"采购价": 2.5, "状态": "已补齐"}},
        )


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import tempfile
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

    def test_update_records_rejects_malformed_payloads_before_write(self):
        from feishu_bitable import cmd_update_records

        malformed_payloads = [
            ["not-a-record"],
            [{"record_id": "", "fields": {"status": "filled"}}],
            [{"record_id": "rec1", "fields": {}}],
            [{"record_id": "rec1", "fields": {"status": "filled"}, "extra": True}],
        ]

        with tempfile.TemporaryDirectory() as tmp:
            for index, payload in enumerate(malformed_payloads):
                updates = Path(tmp) / f"updates-{index}.json"
                updates.write_text(json.dumps(payload), encoding="utf-8")
                args = argparse.Namespace(
                    env=str(Path(tmp) / "missing.env"),
                    url="https://x.feishu.cn/base/appABC123?table=tbl456",
                    updates=str(updates),
                    batch_size=100,
                )

                with patch("feishu_bitable.FeishuClient") as client_cls:
                    with self.assertRaises(ValueError):
                        cmd_update_records(args)

                client_cls.assert_not_called()

    def test_update_records_rejects_oversized_batch_before_write(self):
        from feishu_bitable import cmd_update_records

        with tempfile.TemporaryDirectory() as tmp:
            updates = Path(tmp) / "updates.json"
            updates.write_text(
                json.dumps([{"record_id": "rec1", "fields": {"status": "filled"}}]),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                env=str(Path(tmp) / "missing.env"),
                url="https://x.feishu.cn/base/appABC123?table=tbl456",
                updates=str(updates),
                batch_size=501,
            )

            with patch("feishu_bitable.FeishuClient") as client_cls:
                with self.assertRaises(ValueError):
                    cmd_update_records(args)

            client_cls.assert_not_called()

    def test_download_images_writes_token_and_sha256_metadata(self):
        from feishu_bitable import cmd_download_images

        image_bytes = b"\x89PNG\r\n\x1a\nimage-data"

        class FakeClient:
            def download_media(self, file_token):
                return image_bytes

        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            out_dir = Path(tmp) / "images"
            plan.write_text(
                json.dumps({"records": [{"record_id": "rec/1", "image_tokens": ["boxcn123"]}]}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                env=str(Path(tmp) / "missing.env"),
                url="https://x.feishu.cn/base/appABC123?table=tbl456",
                plan=str(plan),
                out_dir=str(out_dir),
            )

            with patch("feishu_bitable.FeishuClient", return_value=FakeClient()):
                with patch("builtins.print"):
                    cmd_download_images(args)

            metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
            downloaded = out_dir / metadata[0]["filename"]
            downloaded_bytes = downloaded.read_bytes()

        self.assertEqual(metadata[0]["record_id"], "rec/1")
        self.assertEqual(metadata[0]["file_token"], "boxcn123")
        self.assertEqual(metadata[0]["sha256"], hashlib.sha256(image_bytes).hexdigest())
        self.assertEqual(metadata[0]["byte_count"], len(image_bytes))
        self.assertEqual(metadata[0]["filename"], "rec_1_0.png")
        self.assertEqual(downloaded_bytes, image_bytes)


class ProductExtractionTest(unittest.TestCase):
    def test_parse_1688_text(self):
        from scrape_1688_product import parse_1688_text

        text = "浠锋牸 楼22.90 鍖呰灏哄 450脳320脳180mm 姣涢噸 850g"

        result = parse_1688_text(text)

        self.assertEqual(result["price_cny"], "22.90")
        self.assertEqual(result["package_dimensions"], "45.00 x 32.00 x 18.00 cm")
        self.assertEqual(result["package_weight"], "0.85 kg")

    def test_parse_amazon_uk_prices(self):
        from scrape_amazon_uk_prices import parse_prices_from_text

        result = parse_prices_from_text("拢16.99 拢26.99 拢28.99")

        self.assertEqual(result["selected_price"], "26.99")
        self.assertEqual(result["marketplace"], "amazon.co.uk")

    def test_parse_prices_ignores_bare_non_price_numbers(self):
        from select_competitor_price import money, parse_prices

        result = parse_prices(["Rated 4.6 stars from 1,234 reviews; item size 45 x 32 x 18 cm"])

        self.assertEqual([money(price) for price in result], [])

    def test_parse_prices_accepts_explicit_comma_delimited_numbers(self):
        from select_competitor_price import money, parse_prices

        result = parse_prices(["16.99,26.99,28.99"])

        self.assertEqual([money(price) for price in result], ["16.99", "26.99", "28.99"])

    def test_parse_amazon_split_price_markup(self):
        from scrape_amazon_uk_prices import parse_prices_from_text

        html = """
        <span class="a-price">
          <span class="a-price-symbol">&pound;</span>
          <span class="a-price-whole">16</span>
          <span class="a-price-fraction">99</span>
        </span>
        """

        result = parse_prices_from_text(html)

        self.assertEqual(result["prices"], ["16.99"])
        self.assertEqual(result["selected_price"], "16.99")

    def test_parse_amazon_no_price_returns_empty_result(self):
        from scrape_amazon_uk_prices import parse_prices_from_text

        result = parse_prices_from_text("Rated 4.6 stars from 1,234 reviews")

        self.assertEqual(result["prices"], [])
        self.assertIsNone(result["selected_price"])

    def test_package_dimensions_prefer_package_label(self):
        from normalize_package_data import extract

        result = extract("item dimensions 10 x 20 x 30 cm; package size 450 x 320 x 180 mm")

        self.assertEqual(result["package_dimensions"]["text"], "45.00 x 32.00 x 18.00 cm")


class BatchRunnerTest(unittest.TestCase):
    def test_cny_to_gbp(self):
        from run_batch import cny_to_gbp

        self.assertEqual(cny_to_gbp("22.90"), 2.50)

    def test_evidence_line(self):
        from run_batch import build_evidence

        evidence = build_evidence("rec1", {"price_cny": "22.90"}, {"selected_price": "26.99"})

        self.assertEqual(evidence["record_id"], "rec1")
        self.assertEqual(evidence["purchase_price_gbp"], 2.5)
        self.assertEqual(evidence["selling_price_gbp"], 26.99)

    def test_load_plan_accepts_utf8_bom_json(self):
        from run_batch import load_plan

        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            plan.write_text('{"records": [{"record_id": "rec1"}]}', encoding="utf-8-sig")

            result = load_plan(plan)

        self.assertEqual(result["records"][0]["record_id"], "rec1")

    def test_build_update_without_field_map_has_no_internal_role_fields(self):
        from run_batch import build_update

        evidence = {
            "purchase_price_gbp": 2.5,
            "package_dimensions": "45.00 x 32.00 x 18.00 cm",
            "status": "filled",
        }

        self.assertEqual(build_update("rec1", {}, evidence), {"record_id": "rec1", "fields": {}})

    def test_row_failure_writes_evidence_and_continues(self):
        from run_batch import run_batch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            image_dir.mkdir()
            plan = root / "plan.json"
            evidence = root / "evidence.jsonl"
            updates = root / "updates.json"
            plan.write_text(
                json.dumps(
                    {
                        "field_map": {"purchase_price_gbp": {"field_name": "Purchase GBP"}},
                        "records": [{"record_id": "rec-bad"}, {"record_id": "rec-good"}],
                    }
                ),
                encoding="utf-8",
            )
            (image_dir / "rec-bad.1688.json").write_text("{bad json", encoding="utf-8")
            (image_dir / "rec-good.1688.json").write_text(json.dumps({"price_cny": "22.90"}), encoding="utf-8")
            (image_dir / "rec-good.amazon.json").write_text(json.dumps({"selected_price": "26.99"}), encoding="utf-8")

            result = run_batch(plan, image_dir, updates, evidence, batch_size=20)
            lines = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines()]
            state = json.loads((root / "run-state.json").read_text(encoding="utf-8"))

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual([line["record_id"] for line in lines], ["rec-bad", "rec-good"])
        self.assertEqual(lines[0]["status"], "error")
        self.assertIn("error", lines[0])
        self.assertIn("extraction_files", lines[0])
        self.assertEqual(
            lines[0]["extraction_files"],
            {
                "1688": {"path": str(image_dir / "rec-bad.1688.json"), "exists": True},
                "amazon": {"path": str(image_dir / "rec-bad.amazon.json"), "exists": False},
            },
        )
        self.assertEqual(lines[1]["purchase_price_gbp"], 2.5)
        self.assertEqual(
            lines[1]["extraction_files"],
            {
                "1688": {"path": str(image_dir / "rec-good.1688.json"), "exists": True},
                "amazon": {"path": str(image_dir / "rec-good.amazon.json"), "exists": True},
            },
        )
        self.assertEqual(state["processed"], 2)
        self.assertEqual(state["failed"], 1)

    def test_missing_record_id_failure_uses_standard_extraction_file_shape(self):
        from run_batch import run_batch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            image_dir.mkdir()
            plan = root / "plan.json"
            evidence = root / "evidence.jsonl"
            updates = root / "updates.json"
            plan.write_text(json.dumps({"records": [{"fields": {}}]}), encoding="utf-8")

            result = run_batch(plan, image_dir, updates, evidence, batch_size=20)
            lines = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["failed"], 1)
        self.assertEqual(lines[0]["status"], "error")
        self.assertEqual(
            lines[0]["extraction_files"],
            {
                "1688": {"path": str(image_dir / "record.1688.json"), "exists": False},
                "amazon": {"path": str(image_dir / "record.amazon.json"), "exists": False},
            },
        )


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import re
import unittest

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


if __name__ == "__main__":
    unittest.main()

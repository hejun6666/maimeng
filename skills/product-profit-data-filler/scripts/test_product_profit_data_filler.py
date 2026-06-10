from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillContractTest(unittest.TestCase):
    def test_skill_mentions_bitable_and_amazon_uk(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Feishu Bitable", text)
        self.assertIn("amazon.co.uk", text)
        self.assertIn("9.17", text)
        self.assertIn("FEISHU_APP_ID", text)
        self.assertIn("FEISHU_APP_SECRET", text)

    def test_required_references_exist(self):
        refs = ROOT / "references"
        for name in [
            "field-mapping.md",
            "feishu-bitable-workflow.md",
            "1688-data-rules.md",
            "amazon-uk-price-rules.md",
        ]:
            self.assertTrue((refs / name).exists(), name)


if __name__ == "__main__":
    unittest.main()

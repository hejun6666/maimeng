import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class SkillTextTest(unittest.TestCase):
    def test_browser_use_cleanup_rule_is_explicit(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("browser-use close --all", skill_text)
        self.assertIn("browser-use close --all", workflow_text)
        self.assertIn("open-source browser-use sessions", skill_text)

    def test_customer_service_inquiry_is_mandatory_before_final_export(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")
        openai_yaml = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("Customer-service inquiry is mandatory", skill_text)
        self.assertIn("筛选候选供应商不等于完成询价", skill_text)
        self.assertIn("Do not export a final procurement table before inquiry messages are sent", skill_text)
        self.assertIn("Do not put 1688 search-result URLs in the final `链接` column", workflow_text)
        self.assertIn("s.1688.com/selloffer/offer_search", workflow_text)
        self.assertIn("一家一家打开客服发送询价", openai_yaml)
        self.assertIn("不能只筛选就导出最终表", openai_yaml)

    def test_chat_must_send_product_context_and_wait_for_real_replies(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")
        openai_yaml = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("Send product context before inquiry text", skill_text)
        self.assertIn("先发送商品卡片/商品链接，再发送询价话术", skill_text)
        self.assertIn("Wait for real customer-service replies", skill_text)
        self.assertIn("Do not treat product-page price, shop page text, or existing page information as a customer-service reply", skill_text)
        self.assertIn("No reply means `待回复`", skill_text)
        self.assertIn("product card/link prompt", workflow_text)
        self.assertIn("wait for a real new customer-service message", workflow_text)
        self.assertIn("页面已有信息不能冒充客服回复", openai_yaml)

    def test_inquiry_uses_default_wording_without_start_confirmation(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")
        openai_yaml = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("Use the default inquiry strategy without asking for wording approval", skill_text)
        self.assertIn("Do not stop to ask \"话术可以吗\" or \"确认开始吗\"", skill_text)
        self.assertIn("Do not stop for start approval or per-supplier approval", workflow_text)
        self.assertIn("逐家模拟人工操作", skill_text)
        self.assertIn("Do not batch-send", workflow_text)
        self.assertIn("不要先问我确认话术", openai_yaml)
        self.assertNotIn("让我确认一次询价策略", openai_yaml)

    def test_partial_replies_and_external_contact_are_followed_up(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("incomplete reply", skill_text)
        self.assertIn("请直接在1688这里发就可以", skill_text)
        self.assertIn("报价图片", skill_text)
        self.assertIn("page MOQ", skill_text)
        self.assertIn("contact details privately", workflow_text)
        self.assertIn("price table image", workflow_text)

    def test_quantity_and_spec_questions_use_context_before_stopping(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("先按100套报价", skill_text)
        self.assertIn("就按刚才这个链接里的款式", skill_text)
        self.assertIn("100套", workflow_text)
        self.assertIn("same product link", workflow_text)

    def test_efficiency_memory_and_excel_rules_are_explicit(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")
        openai_yaml = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("7-9 suppliers", skill_text)
        self.assertIn("候选池", skill_text)
        self.assertIn("send pass", workflow_text)
        self.assertIn("reply collection pass", workflow_text)
        self.assertIn("reuse one chat page", workflow_text)
        self.assertIn("do not open a new chat window for every supplier", workflow_text)
        self.assertIn("product card/link send button above the input box", workflow_text)
        self.assertIn("only ask the user in Codex chat", skill_text)
        self.assertIn("only the screenshot columns", skill_text)
        self.assertIn("7-9家", openai_yaml)
        self.assertIn("cleanup-plan --apply", skill_text)
        self.assertIn("Tab cleanup is a required checkpoint", workflow_text)
        self.assertIn("--new-tab", workflow_text)
        self.assertIn("heartbeat", skill_text)
        self.assertIn("cron", skill_text)
        self.assertIn("heartbeat", workflow_text)
        self.assertIn("cron", workflow_text)
        self.assertIn("do not create a daily `cron` by default", skill_text)
        self.assertIn("Keep the heartbeat finite", workflow_text)
        self.assertIn("超时未回复/暂不跟进", workflow_text)

    def test_fast_cdp_helper_is_documented_as_safe_speed_fallback(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("scripts/1688_fast_inquiry.py", skill_text)
        self.assertIn("direct CDP/Playwright speed helper", skill_text)
        self.assertIn("dry-run-send-plan", workflow_text)
        self.assertIn("cleanup-plan", workflow_text)
        self.assertIn("--allow-send", workflow_text)
        self.assertIn("do not pause just to ask the user to approve the default wording", workflow_text)
        self.assertIn("attach a `heartbeat` automation to the current thread", skill_text)
        self.assertIn("standalone recurring sourcing/monitoring jobs", workflow_text)

    def test_reply_decision_helper_is_documented_for_hard_reply_cases(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("scripts/inquiry_reply_rules.py", skill_text)
        self.assertIn("deterministic reply decision helper", skill_text)
        self.assertIn("已回复但缺字段", workflow_text)
        self.assertIn("要求外部联系", workflow_text)
        self.assertIn("需识别报价图", workflow_text)
        self.assertIn("安全暂停", workflow_text)

    def test_real_world_speed_failures_are_documented(self):
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("def_cbu_web_im_core", workflow_text)
        self.assertIn("chat-state", workflow_text)
        self.assertIn("open-chat", workflow_text)
        self.assertIn("--message-file", workflow_text)
        self.assertIn("Do not pipe inline Chinese Python or JavaScript through PowerShell", workflow_text)
        self.assertIn("two keyword attempts", workflow_text)
        self.assertIn("switch away from keyword search", workflow_text)

    def test_1688_keyword_url_encoding_is_documented(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("search-url", skill_text)
        self.assertIn("GBK/GB18030", skill_text)
        self.assertIn("Do not hand-build `keywords=`", workflow_text)
        self.assertIn("mojibake", workflow_text)

    def test_real_send_checks_active_contact_and_avoids_duplicate_followups(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("active chat contact", skill_text)
        self.assertIn("active_contact_mismatch", skill_text)
        self.assertIn("--seller-login-id", workflow_text)
        self.assertIn("do not rely on `--offer-id` alone", workflow_text)
        self.assertIn("Do not repeat the same inquiry or full missing-field follow-up", workflow_text)
        self.assertIn("ask only the exact missing item", workflow_text)

    def test_incomplete_exports_and_page_only_values_are_not_final_table(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("--allow-in-progress", skill_text)
        self.assertIn("in-progress", skill_text)
        self.assertIn("Page-only values", skill_text)
        self.assertIn("customer-service-confirmed values only", workflow_text)
        self.assertIn("Page-only values must stay in remarks", workflow_text)
        self.assertIn("未税报价（非含税价，开票/税点见原话）", skill_text)
        self.assertIn("未税价", workflow_text)

    def test_chat_switch_failure_must_not_be_treated_as_completion(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        workflow_text = (SKILL_DIR / "references" / "1688-web-workflow.md").read_text(encoding="utf-8")

        self.assertIn("尚未选择联系人", skill_text)
        self.assertIn("chat-switch failure", skill_text)
        self.assertIn("Retry opening the direct Web IM URL", workflow_text)
        self.assertIn("mark only that supplier as `回查异常/待回复`", workflow_text)


if __name__ == "__main__":
    unittest.main()

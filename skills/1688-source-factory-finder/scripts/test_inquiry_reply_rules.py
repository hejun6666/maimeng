import unittest

import inquiry_reply_rules as rules


class InquiryReplyRulesTest(unittest.TestCase):
    def test_short_or_polite_reply_is_incomplete_and_gets_followup(self):
        decision = rules.decide_reply("有货，稍等")

        self.assertEqual(decision.status, "已回复但缺字段")
        self.assertEqual(decision.action, "follow_up")
        self.assertFalse(decision.ask_user)
        self.assertIn("含税报价", decision.message)
        self.assertIn("起订量", decision.message)
        self.assertIn("样品费", decision.message)

    def test_does_not_repeat_full_missing_field_followup_when_already_asked(self):
        history = "我：麻烦再发一下这款的含税报价、起订量、交期、样品费和打样货期；如果有阶梯价也一起发下，谢谢。"

        decision = rules.decide_reply("好的", rules.ReplyContext(chat_history=history))

        self.assertEqual(decision.status, "已回复但缺字段")
        self.assertEqual(decision.action, "avoid_duplicate_followup")
        self.assertEqual(decision.message, "")
        self.assertIn("已经追问过完整报价字段", decision.stop_reason)

    def test_external_contact_request_stays_on_1688_without_asking_user(self):
        decision = rules.decide_reply("这个要加微信发报价单")

        self.assertEqual(decision.status, "要求外部联系")
        self.assertEqual(decision.action, "reply_keep_on_1688")
        self.assertFalse(decision.ask_user)
        self.assertIn("直接在1688这里发", decision.message)

    def test_quantity_question_uses_default_quantity(self):
        decision = rules.decide_reply("你们要多少套？", rules.ReplyContext(default_quantity="100套"))

        self.assertEqual(decision.status, "已追问")
        self.assertEqual(decision.action, "reply_quantity")
        self.assertFalse(decision.ask_user)
        self.assertIn("先按100套报价", decision.message)

    def test_quantity_question_uses_page_moq_when_no_default_quantity(self):
        decision = rules.decide_reply("采购数量多少？", rules.ReplyContext(page_moq="50件"))

        self.assertEqual(decision.action, "reply_quantity")
        self.assertIn("先按页面起订量报价", decision.message)

    def test_quantity_question_asks_user_only_without_basis(self):
        decision = rules.decide_reply("这个你要多少？")

        self.assertEqual(decision.status, "需用户确认数量")
        self.assertEqual(decision.action, "ask_user")
        self.assertTrue(decision.ask_user)
        self.assertIn("数量", decision.message)

    def test_spec_question_uses_product_context_when_clear(self):
        decision = rules.decide_reply("要哪个颜色和尺寸？", rules.ReplyContext(product_context_clear=True))

        self.assertEqual(decision.status, "已追问")
        self.assertEqual(decision.action, "reply_spec_from_context")
        self.assertFalse(decision.ask_user)
        self.assertIn("就按刚才这个链接里的款式", decision.message)

    def test_spec_question_asks_user_when_context_is_ambiguous(self):
        decision = rules.decide_reply("你要哪个型号？")

        self.assertEqual(decision.status, "需用户确认规格")
        self.assertEqual(decision.action, "ask_user")
        self.assertTrue(decision.ask_user)
        self.assertIn("规格", decision.message)

    def test_quote_image_requires_visual_extraction_not_no_useful_reply(self):
        decision = rules.decide_reply("报价在图片里，你看下", rules.ReplyContext(has_quote_image=True))

        self.assertEqual(decision.status, "需识别报价图")
        self.assertEqual(decision.action, "extract_visual_quote")
        self.assertFalse(decision.ask_user)
        self.assertIn("截图/OCR", decision.message)

    def test_order_or_payment_request_is_safety_stop(self):
        decision = rules.decide_reply("你先拍下付款，我们再安排")

        self.assertEqual(decision.status, "安全暂停")
        self.assertEqual(decision.action, "stop")
        self.assertTrue(decision.ask_user)
        self.assertIn("下单或付款", decision.stop_reason)

    def test_no_new_customer_reply_stays_pending(self):
        decision = rules.decide_reply("页面展示：100件起订", rules.ReplyContext(has_new_customer_reply=False))

        self.assertEqual(decision.status, "待回复")
        self.assertEqual(decision.action, "wait")
        self.assertFalse(decision.ask_user)
        self.assertEqual(decision.message, "")

    def test_complete_quote_can_be_recorded(self):
        decision = rules.decide_reply("100件起订，含税价12元，交期7天，样品费50元，打样3天")

        self.assertEqual(decision.status, "已拿到报价")
        self.assertEqual(decision.action, "record_quote")
        self.assertFalse(decision.ask_user)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import importlib.util


SCRIPT_PATH = Path(__file__).with_name("1688_fast_inquiry.py")
SPEC = importlib.util.spec_from_file_location("fast_inquiry", SCRIPT_PATH)
fast = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fast)


class FastInquiryHelperTest(unittest.TestCase):
    def test_normalize_cdp_url_defaults_and_accepts_common_inputs(self):
        self.assertEqual(fast.normalize_cdp_url(None), "http://127.0.0.1:9222")
        self.assertEqual(fast.normalize_cdp_url("9223"), "http://127.0.0.1:9223")
        self.assertEqual(fast.normalize_cdp_url("127.0.0.1:9224"), "http://127.0.0.1:9224")
        self.assertEqual(fast.normalize_cdp_url("http://127.0.0.1:9222/json/list"), "http://127.0.0.1:9222")
        self.assertEqual(fast.normalize_cdp_url("http://127.0.0.1:9222/"), "http://127.0.0.1:9222")

    def test_classify_1688_tabs(self):
        samples = {
            "https://air.1688.com/app/ocms-fusion-components-1688/def_cbu_web_im/index.html#/": "chat",
            "https://detail.1688.com/offer/853601682276.html": "product",
            "https://s.1688.com/selloffer/offer_search.htm?keywords=x": "search",
            "https://maimeng.1688.com/page/offerlist.htm": "shop",
            "https://www.1688.com/": "1688",
            "https://example.com/": "other",
            "about:blank": "other",
        }

        for url, expected in samples.items():
            with self.subTest(url=url):
                self.assertEqual(fast.classify_url(url), expected)

    def test_tab_from_target_keeps_only_needed_fields(self):
        target = {
            "id": "ABC",
            "title": "婴儿围栏 - 1688",
            "url": "https://detail.1688.com/offer/1.html",
            "type": "page",
            "webSocketDebuggerUrl": "ws://example",
        }

        tab = fast.tab_from_target(target)

        self.assertEqual(tab.id, "ABC")
        self.assertEqual(tab.title, "婴儿围栏 - 1688")
        self.assertEqual(tab.kind, "product")
        self.assertEqual(tab.url, "https://detail.1688.com/offer/1.html")

    def test_cleanup_plan_keeps_one_search_one_chat_and_non_1688_tabs(self):
        tabs = [
            fast.TabInfo("chat-new", "chat", "https://air.1688.com/app/im", "chat"),
            fast.TabInfo("chat-old", "chat", "https://air.1688.com/app/im?old=1", "chat"),
            fast.TabInfo("search", "search", "https://s.1688.com/selloffer/offer_search.htm", "search"),
            fast.TabInfo("product-1", "item", "https://detail.1688.com/offer/1.html", "product"),
            fast.TabInfo("product-2", "item", "https://detail.1688.com/offer/2.html", "product"),
            fast.TabInfo("feishu", "chat", "https://scn5kjniodza.feishu.cn/wiki/x", "other"),
        ]

        plan = fast.build_cleanup_plan(tabs)

        kept = {item.tab.id for item in plan if item.action == "keep"}
        closed = {item.tab.id for item in plan if item.action == "close"}
        self.assertEqual(kept, {"chat-new", "search", "feishu"})
        self.assertEqual(closed, {"chat-old", "product-1", "product-2"})
        self.assertTrue(all(item.tab.id != "feishu" for item in plan if item.action == "close"))

    def test_build_inquiry_plan_defaults_to_dry_run(self):
        candidates = [
            {
                "shop_name": "宁波某厂",
                "product_url": "https://detail.1688.com/offer/1.html",
                "product_name": "婴儿围栏",
            }
        ]

        actions = fast.build_inquiry_plan(candidates, default_quantity="100套")

        self.assertEqual(actions[0].action, "open_product")
        self.assertEqual(actions[1].action, "send_product_context")
        self.assertEqual(actions[2].action, "send_inquiry_text")
        self.assertIn("婴儿围栏", actions[2].text)
        self.assertIn("先按100套", actions[2].text)
        self.assertFalse(any(action.will_send for action in actions))

    def test_build_inquiry_plan_allow_send_marks_only_real_send_actions(self):
        actions = fast.build_inquiry_plan(
            [
                {
                    "shop_name": "宁波某厂",
                    "product_url": "https://detail.1688.com/offer/1.html",
                    "product_name": "婴儿围栏",
                }
            ],
            allow_send=True,
        )

        will_send_actions = [action.action for action in actions if action.will_send]
        self.assertEqual(will_send_actions, ["send_product_context", "send_inquiry_text"])

    def test_build_chat_url_uses_offer_login_id_and_offer_context(self):
        url = fast.build_chat_url("匠心客科教工厂", "633516066121")

        self.assertIn("def_cbu_web_im/index.html", url)
        self.assertIn("offerId=633516066121", url)
        self.assertIn("touid=cnalichn%E5%8C%A0%E5%BF%83%E5%AE%A2%E7%A7%91%E6%95%99%E5%B7%A5%E5%8E%82", url)
        self.assertIn("sourceValue=", url)
        self.assertIn("%22targetLoginId%22%3A%22%E5%8C%A0%E5%BF%83%E5%AE%A2%E7%A7%91%E6%95%99%E5%B7%A5%E5%8E%82%22", url)

    def test_open_chat_reuses_existing_chat_tab_by_default(self):
        async def fake_navigate(target, url, timeout=10.0):
            return {"result": {"frameId": "frame-1"}}

        target = {"id": "chat-1", "url": "https://air.1688.com/app/im", "webSocketDebuggerUrl": "ws://chat"}
        with mock.patch.object(fast, "find_chat_target", return_value=target), mock.patch.object(
            fast, "navigate_cdp_target", side_effect=fake_navigate
        ) as navigate, mock.patch.object(fast, "activate_cdp_tab") as activate, mock.patch.object(
            fast, "open_cdp_tab"
        ) as open_tab:
            result = fast.open_or_reuse_chat_tab("http://127.0.0.1:9222", "https://air.1688.com/app/new-chat")

        self.assertEqual(result["mode"], "reuse-existing-chat")
        navigate.assert_called_once()
        activate.assert_called_once_with("http://127.0.0.1:9222", "chat-1", timeout=5.0)
        open_tab.assert_not_called()

    def test_open_chat_opens_new_tab_only_when_no_chat_exists(self):
        with mock.patch.object(fast, "find_chat_target", side_effect=RuntimeError("No chat")), mock.patch.object(
            fast, "open_cdp_tab", return_value={"id": "new-chat"}
        ) as open_tab:
            result = fast.open_or_reuse_chat_tab("http://127.0.0.1:9222", "https://air.1688.com/app/new-chat")

        self.assertEqual(result["mode"], "new-tab")
        open_tab.assert_called_once()

    def test_keyword_search_should_switch_when_results_are_empty_or_irrelevant(self):
        empty_body = "哎呦喂，这里空空如也～ 您还可以：写下您的采购需求"
        irrelevant_body = "没有相关商品，推荐试试搜这些：不锈钢公司门牌 旗帜 定制阁楼"
        relevant_body = "自制水精灵手工小制作科学实验diy实验安全级STEM教具益智玩具 义乌市智匠教学仪器设备有限公司"

        self.assertTrue(fast.should_switch_keyword_strategy(empty_body, ["水精灵", "水宝宝"]))
        self.assertTrue(fast.should_switch_keyword_strategy(irrelevant_body, ["水精灵", "水宝宝"]))
        self.assertFalse(fast.should_switch_keyword_strategy(relevant_body, ["水精灵", "水宝宝"]))

    def test_build_1688_search_url_uses_1688_legacy_keyword_encoding(self):
        url = fast.build_1688_search_url("双头马克笔 套装")

        self.assertEqual(
            url,
            "https://s.1688.com/selloffer/offer_search.htm?keywords=%CB%AB%CD%B7%C2%ED%BF%CB%B1%CA%20%CC%D7%D7%B0",
        )
        self.assertNotIn("%E5%8F%8C", url)

    def test_cli_search_url_outputs_legacy_encoded_keyword_url(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "search-url",
                "--keyword",
                "双头马克笔 套装",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["keyword"], "双头马克笔 套装")
        self.assertIn("%CB%AB%CD%B7%C2%ED%BF%CB%B1%CA", payload["search_url"])
        self.assertNotIn("%E5%8F%8C", payload["search_url"])

    def test_chat_core_state_script_targets_iframe_and_uses_unicode_escapes(self):
        script = fast.chat_core_state_script()

        self.assertIn("def_cbu_web_im_core", script)
        self.assertIn("[contenteditable=", script)
        self.assertIn("\\u53d1\\u9001\\u94fe\\u63a5", script)
        self.assertNotIn("发送链接", script)
        self.assertNotIn("请输入消息", script)

    def test_send_chat_message_script_prefers_real_button_for_send(self):
        script = fast.send_chat_message_script("你好", send_product_link=True)

        self.assertIn("clickablePriority", script)
        self.assertIn("tagName === 'BUTTON'", script)
        self.assertIn("sendCandidates.sort", script)

    def test_send_chat_message_script_refuses_without_product_link_button(self):
        script = fast.send_chat_message_script("你好", send_product_link=True)

        self.assertIn("product_link_button_not_found", script)
        self.assertIn("if (!productLinkButton)", script)

    def test_send_chat_message_script_checks_active_supplier_when_provided(self):
        script = fast.send_chat_message_script("你好", send_product_link=True, expected_seller_login_id="义乌市平筹电子商务商行")

        self.assertIn("expectedSellerLoginId", script)
        self.assertIn("active_contact_mismatch", script)
        self.assertIn("义乌市平筹电子商务商行", script)

    def test_send_current_chat_refuses_without_allow_send(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "send-current-chat",
                "--message",
                "测试消息，不能真的发送",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--allow-send", result.stderr)

    def test_send_current_chat_accepts_utf8_message_file_for_chinese_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            message_path = Path(tmp) / "message.txt"
            message_path.write_text("你好，测试中文不要走 PowerShell 管道", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "send-current-chat",
                    "--message-file",
                    str(message_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--allow-send", result.stderr)

    def test_send_current_chat_requires_seller_login_id_when_allow_send_is_used(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "send-current-chat",
                "--message",
                "测试消息，不能没有目标供应商就发送",
                "--allow-send",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--seller-login-id", result.stderr)

    def test_cli_dry_run_plan_does_not_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "candidates.json"
            input_path.write_text(
                json.dumps(
                    {
                        "suppliers": [
                            {
                                "shop_name": "义乌某厂",
                                "product_url": "https://detail.1688.com/offer/2.html",
                                "product_name": "收纳盒",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "dry-run-send-plan",
                    "--input",
                    str(input_path),
                    "--default-quantity",
                    "100套",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertFalse(any(action["will_send"] for action in payload["actions"]))
        self.assertIn("收纳盒", payload["actions"][2]["text"])


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import factory_inquiry_export as exporter


class FactoryInquiryExportTest(unittest.TestCase):
    def sample_suppliers(self):
        return [
            {
                "shop_name": "宁波某母婴用品厂",
                "product_url": "https://detail.1688.com/offer/123.html",
                "product_image": "C:/tmp/baby-fence.jpg",
                "product_name": "婴儿围栏",
                "benchmark_url": "https://example.com/benchmark",
                "is_super_factory": True,
                "years_on_1688": "8年",
                "main_category": "母婴用品",
                "match_level": "高",
                "moq": "100件",
                "tax_included_price": "100件: 32元；500件: 29元",
                "lead_time": "7天",
                "remarks": "出厂价28元；打样费300元；打样货期一周左右；下大货退样品费",
                "sample_owner": "雷艳艳",
                "progress": "已拿到报价",
                "direct_factory": "客服称工厂直供",
                "inquiry_sent": True,
                "message_sent": "你好，这款婴儿围栏有现货吗？",
                "reply_summary": "已回复MOQ和阶梯价",
                "codex_judgement": "优先跟进",
                "next_action": "追问包装和打样",
            }
        ]

    def test_normalize_rows_uses_company_table_columns_only(self):
        rows = exporter.normalize_rows(self.sample_suppliers())

        self.assertEqual(len(exporter.FIELDS), 12)
        self.assertEqual(len(rows[0]), 12)
        self.assertEqual(rows[0][0], "1")
        self.assertEqual(rows[0][1], "C:/tmp/baby-fence.jpg")
        self.assertEqual(rows[0][2], "婴儿围栏")
        self.assertEqual(rows[0][4], "宁波某母婴用品厂")
        self.assertEqual(rows[0][11], "已拿到报价")
        self.assertTrue(any("报价含税价" in label for _key, label in exporter.FIELDS))
        self.assertFalse(any("Codex判断" in label for _key, label in exporter.FIELDS))

    def test_page_only_values_do_not_fill_quote_or_moq_columns(self):
        rows = exporter.normalize_rows(
            [
                {
                    "shop_name": "页面价供应商",
                    "product_name": "鸡舍门",
                    "tax_included_price": "待客服确认；页面显示194元",
                    "moq": "页面显示1件起批",
                    "lead_time": "待回复",
                    "remarks": "未客服确认",
                    "progress": "已发询价，待回复",
                }
            ]
        )

        self.assertEqual(rows[0][5], "待客服确认")
        self.assertEqual(rows[0][6], "待客服确认")
        self.assertEqual(rows[0][7], "待回复")
        self.assertIn("页面显示194元", rows[0][9])
        self.assertIn("页面显示1件起批", rows[0][9])

    def test_untaxed_customer_service_quote_is_kept_but_labeled(self):
        rows = exporter.normalize_rows(
            [
                {
                    "shop_name": "未税价供应商",
                    "product_name": "鸡舍门",
                    "tax_included_price": "客服报未税阶梯价：100台164元、300台161元；开票加13%",
                    "moq": "客服阶梯从100台起；页面显示5台起批",
                    "lead_time": "待回复",
                    "remarks": "客服确认源头工厂",
                    "progress": "已拿到阶梯价，待交期/样品信息",
                }
            ]
        )

        self.assertEqual(
            rows[0][5],
            "未税报价（非含税价，开票/税点见原话）：客服报未税阶梯价：100台164元、300台161元；开票加13%",
        )
        self.assertEqual(rows[0][6], "客服阶梯从100台起")
        self.assertIn("页面起订量信息：页面显示5台起批", rows[0][9])

    def test_final_export_rejects_incomplete_inquiry_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            output_path = Path(tmp) / "suppliers.xlsx"
            input_path.write_text(
                json.dumps(
                    {
                        "suppliers": [
                            {
                                "shop_name": "未完成供应商",
                                "product_name": "鸡舍门",
                                "tax_included_price": "待客服确认；页面显示194元",
                                "moq": "页面显示1件起批",
                                "lead_time": "待回复",
                                "progress": "已发询价，回查异常/待回复",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "不能导出最终表"):
                exporter.export(input_path, output_path)

    def test_final_export_allows_closed_no_reply_rows_when_some_supplier_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            output_path = Path(tmp) / "suppliers.xlsx"
            suppliers = self.sample_suppliers()
            suppliers.append(
                {
                    "shop_name": "未回复供应商",
                    "product_name": "鸡舍门",
                    "tax_included_price": "未回复",
                    "moq": "未回复",
                    "lead_time": "未回复",
                    "remarks": "已完成3轮回查，仍未回复",
                    "progress": "超时未回复/暂不跟进",
                }
            )
            input_path.write_text(json.dumps({"suppliers": suppliers}, ensure_ascii=False), encoding="utf-8")

            exporter.export(input_path, output_path)

            self.assertTrue(output_path.exists())

    def test_final_export_rejects_when_all_suppliers_closed_without_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            output_path = Path(tmp) / "suppliers.xlsx"
            input_path.write_text(
                json.dumps(
                    {
                        "suppliers": [
                            {
                                "shop_name": "未回复供应商",
                                "product_name": "鸡舍门",
                                "tax_included_price": "未回复",
                                "moq": "未回复",
                                "lead_time": "未回复",
                                "progress": "超时未回复/暂不跟进",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "还没有拿到任何完整报价供应商"):
                exporter.export(input_path, output_path)

    def test_in_progress_export_requires_in_progress_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            bad_output = Path(tmp) / "suppliers.xlsx"
            good_output = Path(tmp) / "suppliers-in-progress.xlsx"
            input_path.write_text(
                json.dumps(
                    {
                        "suppliers": [
                            {
                                "shop_name": "未完成供应商",
                                "product_name": "鸡舍门",
                                "tax_included_price": "待客服确认；页面显示194元",
                                "moq": "页面显示1件起批",
                                "lead_time": "待回复",
                                "progress": "已发询价，待回复",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "文件名必须标明"):
                exporter.export(input_path, bad_output, allow_in_progress=True)

            exporter.export(input_path, good_output, allow_in_progress=True)

            self.assertTrue(good_output.exists())

    def test_company_procurement_columns_are_the_only_columns(self):
        labels = [label for _key, label in exporter.FIELDS]

        self.assertEqual(
            labels,
            [
                "序号",
                "产品图片",
                "产品品名",
                "产品对标链接",
                "供应商",
                "报价含税价",
                "起订量",
                "交期",
                "链接",
                "备注",
                "样品负责人",
                "进度",
            ],
        )

    def test_csv_output_has_utf8_bom_for_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            output_path = Path(tmp) / "suppliers.csv"
            input_path.write_text(json.dumps({"suppliers": self.sample_suppliers()}, ensure_ascii=False), encoding="utf-8")

            exporter.export(input_path, output_path)

            raw = output_path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            text = raw.decode("utf-8-sig")
            self.assertIn("宁波某母婴用品厂", text)
            self.assertIn("进度", text)
            self.assertNotIn("Codex判断", text)
            self.assertNotIn("跟进建议", text)

    def test_xlsx_output_contains_sheet_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            output_path = Path(tmp) / "suppliers.xlsx"
            input_path.write_text(json.dumps(self.sample_suppliers(), ensure_ascii=False), encoding="utf-8")

            exporter.export(input_path, output_path)

            with zipfile.ZipFile(output_path) as workbook:
                names = set(workbook.namelist())
                self.assertIn("xl/worksheets/sheet1.xml", names)
                sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertIn("宁波某母婴用品厂", sheet)
                self.assertIn("1688", sheet)
                self.assertNotIn("Codex判断", sheet)

    def test_cli_exports_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "suppliers.json"
            output_path = Path(tmp) / "suppliers.csv"
            input_path.write_text(json.dumps(self.sample_suppliers(), ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("factory_inquiry_export.py")),
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.exists())
            self.assertIn("已导出", result.stdout)


if __name__ == "__main__":
    unittest.main()

import json
import math
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from replenishment_calculator import (
    ReplenishmentInput,
    calculate_batch_replenishment,
    calculate_replenishment,
    format_batch_csv,
    round_order_quantity,
    season_multiplier,
)
from lingxing_capture import extract_known_numbers_from_text, parse_sales_triplet


class SeasonMultiplierTests(unittest.TestCase):
    def test_uses_peak_month_multiplier_for_promoted_skus(self):
        self.assertEqual(season_multiplier(month=10, is_promoted=True), 2.0)
        self.assertEqual(season_multiplier(month=11, is_promoted=True), 2.0)
        self.assertEqual(season_multiplier(month=12, is_promoted=True), 4.0)

    def test_uses_peak_month_multiplier_for_non_promoted_skus(self):
        self.assertEqual(season_multiplier(month=10, is_promoted=False), 1.5)
        self.assertEqual(season_multiplier(month=11, is_promoted=False), 1.5)
        self.assertEqual(season_multiplier(month=12, is_promoted=False), 2.25)

    def test_manual_multiplier_overrides_calendar_defaults(self):
        self.assertEqual(
            season_multiplier(month=7, is_promoted=False, manual_multiplier=1.8),
            1.8,
        )

    def test_unknown_promoted_status_does_not_apply_peak_multiplier(self):
        self.assertEqual(season_multiplier(month=12, is_promoted=None), 1.0)


class RoundingTests(unittest.TestCase):
    def test_rounds_up_to_case_pack_and_moq(self):
        self.assertEqual(round_order_quantity(37, moq=50, case_pack=12), 60)
        self.assertEqual(round_order_quantity(121, moq=50, case_pack=24), 144)

    def test_zero_shortage_stays_zero(self):
        self.assertEqual(round_order_quantity(0, moq=50, case_pack=12), 0)


class ReplenishmentCalculationTests(unittest.TestCase):
    def test_example_sku_uses_sales_stock_lead_time_and_weekly_cadence(self):
        result = calculate_replenishment(
            ReplenishmentInput(
                sku="FL-DE12GB-A",
                site="US",
                month=6,
                sales_30=70,
                fba_total=100,
                awd_available_inbound_total=0,
                is_promoted=False,
                sales_stability="stable",
                replenishment_cadence="weekly",
                production_days=15,
                freight_prep_days=3,
                transit_days=37,
            )
        )

        self.assertEqual(result["lead_time_days"], 55)
        self.assertEqual(result["reorder_threshold_days"], 55)
        self.assertEqual(result["risk_level"], "reorder")
        self.assertEqual(result["steady_replenishment_days"], 7)
        self.assertEqual(result["steady_replenishment_qty"], 17)
        self.assertTrue(math.isclose(result["forecast_daily_sales"], 70 / 30))
        self.assertTrue(math.isclose(result["current_stock_days"], 100 / (70 / 30)))


class BatchReplenishmentCalculationTests(unittest.TestCase):
    def test_calculates_each_listing_row_in_batch(self):
        rows = [
            {
                "sku": "FL-DE12GB-A",
                "site": "US",
                "title": "Dragon Egg",
                "sales_30": 70,
                "fba_total": 100,
                "awd_available_inbound_total": 0,
                "is_promoted": False,
                "sales_stability": "stable",
            },
            {
                "sku": "FL-BL-CRYS-12G",
                "site": "CA",
                "title": "Crystal Egg",
                "sales_30": 0,
                "fba_total": 20,
                "awd_available_inbound_total": 0,
            },
        ]

        results = calculate_batch_replenishment(rows)

        self.assertEqual([item["sku"] for item in results], ["FL-DE12GB-A", "FL-BL-CRYS-12G"])
        self.assertEqual(results[0]["title"], "Dragon Egg")
        self.assertEqual(results[0]["steady_replenishment_qty"], 17)
        self.assertEqual(results[1]["risk_level"], "needs_manual_review")

    def test_formats_batch_results_as_csv_for_excel(self):
        results = calculate_batch_replenishment(
            [
                {
                    "sku": "FL-DE12GB-A",
                    "site": "US",
                    "title": "Dragon Egg",
                    "sales_30": 70,
                    "fba_total": 100,
                    "fba_sellable": 80,
                    "awd_available_inbound_total": 5,
                    "is_promoted": False,
                    "sales_stability": "stable",
                }
            ]
        )

        csv_text = format_batch_csv(results)

        self.assertIn("SKU,品名,站点/店铺,近30天销量,日均销量,FBA总库存,FBA可售,AWD库存,海外库存合计,库存可撑天数,风险等级,每周补货参考量,工厂下单建议量,需要人工确认的问题", csv_text)
        self.assertIn("FL-DE12GB-A,Dragon Egg,US,70,2.33,100,80,5,105,45.0,reorder,17,105,", csv_text)

    def test_cli_accepts_json_list_and_outputs_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "batch.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "sku": "FL-DE12GB-A",
                            "site": "US",
                            "title": "Dragon Egg",
                            "sales_30": 70,
                            "fba_total": 100,
                            "awd_available_inbound_total": 0,
                            "is_promoted": False,
                            "sales_stability": "stable",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("replenishment_calculator.py")),
                    "--input",
                    str(input_path),
                    "--format",
                    "csv",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("SKU,品名,站点/店铺", proc.stdout)
        self.assertIn("FL-DE12GB-A,Dragon Egg,US", proc.stdout)

    def test_cli_accepts_utf8_bom_json_from_powershell(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "batch-bom.json"
            input_path.write_text(
                json.dumps([{"sku": "BOM-SKU", "sales_30": 30}], ensure_ascii=False),
                encoding="utf-8-sig",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("replenishment_calculator.py")),
                    "--input",
                    str(input_path),
                    "--format",
                    "csv",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("BOM-SKU", proc.stdout)

    def test_december_promoted_sku_multiplies_sales_and_flags_critical_stock(self):
        result = calculate_replenishment(
            ReplenishmentInput(
                sku="HOT-SKU",
                site="US",
                month=12,
                sales_30=300,
                fba_total=80,
                awd_available_inbound_total=0,
                is_promoted=True,
                sales_stability="stable",
                replenishment_cadence="weekly",
            )
        )

        self.assertEqual(result["season_multiplier"], 4.0)
        self.assertEqual(result["forecast_daily_sales"], 40.0)
        self.assertEqual(result["current_stock_days"], 2.0)
        self.assertEqual(result["risk_level"], "critical")

    def test_overstock_is_reported_when_inventory_exceeds_max_days(self):
        result = calculate_replenishment(
            ReplenishmentInput(
                sku="SLOW-SKU",
                site="CA",
                month=6,
                sales_30=30,
                fba_total=120,
                awd_available_inbound_total=20,
                is_promoted=False,
                replenishment_cadence="monthly",
            )
        )

        self.assertEqual(result["risk_level"], "overstock")
        self.assertEqual(result["steady_replenishment_days"], 30)
        self.assertEqual(result["steady_replenishment_qty"], 30)
        self.assertEqual(result["recommended_factory_order_qty"], 0)

    def test_missing_promoted_status_is_reported_for_peak_months(self):
        result = calculate_replenishment(
            ReplenishmentInput(
                sku="UNKNOWN-PUSH",
                site="US",
                month=12,
                sales_30=300,
                fba_total=500,
                awd_available_inbound_total=0,
                is_promoted=None,
            )
        )

        self.assertEqual(result["season_multiplier"], 1.0)
        self.assertIn("is_promoted_or_manual_season_multiplier", result["missing_parameters"])

    def test_uses_current_month_when_month_not_provided(self):
        class FakeDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 10, 1)

        with patch("replenishment_calculator.date", FakeDate):
            result = calculate_replenishment(
                ReplenishmentInput(
                    sku="DEFAULT-MONTH",
                    site="US",
                    sales_30=30,
                    fba_total=30,
                    awd_available_inbound_total=0,
                    is_promoted=False,
                )
            )

        self.assertEqual(result["calculation_month"], 10)
        self.assertEqual(result["season_multiplier"], 1.5)

    def test_inbound_delay_does_not_affect_first_version_lead_time(self):
        result = calculate_replenishment(
            ReplenishmentInput(
                sku="NO-INBOUND-DELAY",
                site="US",
                month=6,
                sales_30=30,
                fba_total=30,
                awd_available_inbound_total=0,
                is_promoted=False,
                production_days=15,
                freight_prep_days=3,
                transit_days=37,
                inbound_delay_days=999,
            )
        )

        self.assertEqual(result["lead_time_days"], 55)


class LingxingTextParsingTests(unittest.TestCase):
    def test_parses_listing_sales_triplet(self):
        self.assertEqual(
            parse_sales_triplet("191 | 383 | 842"),
            {"sales_7": 191.0, "sales_14": 383.0, "sales_30": 842.0},
        )

    def test_extracts_known_inventory_numbers_from_visible_text(self):
        text = """
        FBA总库存
        800
        FBA可售
        760
        AWD可用+在途库存合计
        600
        """

        fields = extract_known_numbers_from_text(text)

        self.assertEqual(fields["fba_total"], 800.0)
        self.assertEqual(fields["fba_sellable"], 760.0)
        self.assertEqual(fields["awd_available_inbound_total"], 600.0)


if __name__ == "__main__":
    unittest.main()

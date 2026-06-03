#!/usr/bin/env python3
"""Replenishment calculator for Lingxing SKU planning.

The module is intentionally independent from browser automation so the business
rules can be tested and reused even when ERP extraction changes.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from dataclasses import asdict, dataclass, fields
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class ReplenishmentInput:
    sku: str = ""
    site: str = ""
    title: str = ""
    asin: str = ""
    owner: str = ""
    month: Optional[int] = None
    sales_7: Optional[float] = None
    sales_14: Optional[float] = None
    sales_30: Optional[float] = None
    fba_total: float = 0
    fba_sellable: Optional[float] = None
    awd_available_inbound_total: float = 0
    confirmed_inbound_qty: float = 0
    is_promoted: Optional[bool] = None
    manual_season_multiplier: Optional[float] = None
    sales_stability: str = "unknown"
    replenishment_cadence: str = "auto"
    production_days: int = 15
    freight_prep_days: int = 3
    transit_days: int = 37
    inbound_delay_days: int = 0
    safety_stock_days: int = 30
    max_stock_days: int = 90
    target_stock_days: int = 90
    reorder_threshold_days: Optional[int] = None
    moq: Optional[int] = None
    case_pack: Optional[int] = None


def _positive_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _positive_int(value: Any) -> Optional[int]:
    parsed = _positive_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _coerce_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "promoted", "main", "主推", "是"}:
        return True
    if normalized in {"0", "false", "no", "n", "not-promoted", "normal", "非主推", "否"}:
        return False
    return None


def season_multiplier(
    month: Optional[int],
    is_promoted: Optional[bool],
    manual_multiplier: Optional[float] = None,
) -> float:
    """Return the sales multiplier from the current company rule set."""
    manual = _positive_float(manual_multiplier)
    if manual and manual > 0:
        return manual

    if month in {10, 11, 12} and is_promoted is None:
        return 1.0
    if month in {10, 11}:
        return 2.0 if is_promoted else 1.5
    if month == 12:
        return 4.0 if is_promoted else 2.25
    return 1.0


def round_order_quantity(
    quantity: float,
    moq: Optional[int] = None,
    case_pack: Optional[int] = None,
) -> int:
    """Round an order quantity up to MOQ and case-pack constraints."""
    if quantity <= 0:
        return 0

    rounded = math.ceil(quantity)
    if moq and moq > 0:
        rounded = max(rounded, int(moq))
    if case_pack and case_pack > 0:
        rounded = int(math.ceil(rounded / case_pack) * case_pack)
    return rounded


def _daily_sales_basis(data: ReplenishmentInput) -> tuple[float, str]:
    sales_30 = _positive_float(data.sales_30)
    sales_14 = _positive_float(data.sales_14)
    sales_7 = _positive_float(data.sales_7)

    if sales_30 and sales_30 > 0:
        return sales_30 / 30, "30d"
    if sales_14 and sales_14 > 0:
        return sales_14 / 14, "14d"
    if sales_7 and sales_7 > 0:
        return sales_7 / 7, "7d"
    return 0.0, "missing"


def _resolve_cadence(data: ReplenishmentInput) -> tuple[str, int]:
    cadence = (data.replenishment_cadence or "auto").strip().lower()
    stability = (data.sales_stability or "unknown").strip().lower()

    if cadence in {"weekly", "week", "每周", "周"}:
        return "weekly", 7
    if cadence in {"monthly", "month", "每月", "月"}:
        return "monthly", 30
    if stability in {"stable", "稳定"}:
        return "weekly", 7
    return "monthly", 30


def _risk_level(current_days: Optional[float], data: ReplenishmentInput, threshold: int) -> str:
    if current_days is None:
        return "needs_manual_review"
    if current_days < data.safety_stock_days:
        return "critical"
    if current_days > data.max_stock_days:
        return "overstock"
    if current_days < threshold:
        return "reorder"
    return "safe"


def calculate_replenishment(data: ReplenishmentInput) -> Dict[str, Any]:
    base_daily_sales, sales_basis = _daily_sales_basis(data)
    calculation_month = data.month if data.month is not None else date.today().month
    multiplier = season_multiplier(
        month=calculation_month,
        is_promoted=data.is_promoted,
        manual_multiplier=data.manual_season_multiplier,
    )
    forecast_daily_sales = base_daily_sales * multiplier

    lead_time_days = (
        int(data.production_days)
        + int(data.freight_prep_days)
        + int(data.transit_days)
    )
    threshold = data.reorder_threshold_days or max(data.safety_stock_days, lead_time_days)

    overseas_inventory = float(data.fba_total or 0) + float(data.awd_available_inbound_total or 0)
    current_stock_days = (
        overseas_inventory / forecast_daily_sales if forecast_daily_sales > 0 else None
    )

    cadence, cadence_days = _resolve_cadence(data)
    steady_qty = round_order_quantity(forecast_daily_sales * cadence_days)

    target_inventory = forecast_daily_sales * data.target_stock_days
    raw_order_qty = max(
        0.0,
        target_inventory - overseas_inventory - float(data.confirmed_inbound_qty or 0),
    )
    recommended_order_qty = round_order_quantity(raw_order_qty, data.moq, data.case_pack)
    missing_parameters = []
    if (
        calculation_month in {10, 11, 12}
        and data.is_promoted is None
        and not _positive_float(data.manual_season_multiplier)
    ):
        missing_parameters.append("is_promoted_or_manual_season_multiplier")

    result: Dict[str, Any] = {
        "sku": data.sku,
        "site": data.site,
        "title": data.title,
        "asin": data.asin,
        "owner": data.owner,
        "input": asdict(data),
        "calculation_month": calculation_month,
        "sales_basis": sales_basis,
        "base_daily_sales": base_daily_sales,
        "season_multiplier": multiplier,
        "forecast_daily_sales": forecast_daily_sales,
        "lead_time_days": lead_time_days,
        "safety_stock_days": data.safety_stock_days,
        "reorder_threshold_days": threshold,
        "max_stock_days": data.max_stock_days,
        "target_stock_days": data.target_stock_days,
        "overseas_inventory": overseas_inventory,
        "current_stock_days": current_stock_days,
        "cadence": cadence,
        "steady_replenishment_days": cadence_days,
        "steady_replenishment_qty": steady_qty,
        "target_inventory": target_inventory,
        "raw_factory_order_qty": raw_order_qty,
        "recommended_factory_order_qty": recommended_order_qty,
        "risk_level": _risk_level(current_stock_days, data, threshold),
        "missing_parameters": missing_parameters,
    }
    return result


def calculate_batch_replenishment(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    results = []
    for row in rows:
        if isinstance(row, ReplenishmentInput):
            data = row
        else:
            data = input_from_mapping(row)
        results.append(calculate_replenishment(data))
    return results


def _fmt_number(value: Any, digits: int = 0) -> str:
    parsed = _positive_float(value)
    if parsed is None:
        return ""
    if digits == 0:
        return str(int(round(parsed)))
    return f"{parsed:.{digits}f}"


def format_batch_csv(results: list[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "SKU",
            "品名",
            "站点/店铺",
            "近30天销量",
            "日均销量",
            "FBA总库存",
            "FBA可售",
            "AWD库存",
            "海外库存合计",
            "库存可撑天数",
            "风险等级",
            "每周补货参考量",
            "工厂下单建议量",
            "需要人工确认的问题",
        ]
    )
    for result in results:
        raw_input = result.get("input", {})
        stock_days = result.get("current_stock_days")
        writer.writerow(
            [
                result.get("sku", ""),
                result.get("title", ""),
                result.get("site", ""),
                _fmt_number(raw_input.get("sales_30")),
                _fmt_number(result.get("base_daily_sales"), 2),
                _fmt_number(raw_input.get("fba_total")),
                _fmt_number(raw_input.get("fba_sellable")),
                _fmt_number(raw_input.get("awd_available_inbound_total")),
                _fmt_number(result.get("overseas_inventory")),
                "" if stock_days is None else f"{stock_days:.1f}",
                result.get("risk_level", ""),
                _fmt_number(result.get("steady_replenishment_qty")),
                _fmt_number(result.get("recommended_factory_order_qty")),
                "、".join(result.get("missing_parameters", [])),
            ]
        )
    return output.getvalue()


def format_chinese_report(result: Dict[str, Any]) -> str:
    stock_days = result["current_stock_days"]
    stock_days_text = "无法计算" if stock_days is None else f"{stock_days:.1f} 天"
    risk_text = {
        "critical": "警报：库存可撑天数偏低",
        "reorder": "需要补货：库存低于补货触发线",
        "safe": "暂时正常：库存处在可接受区间",
        "overstock": "压货风险：库存可撑天数偏高",
        "needs_manual_review": "需要人工判断：销量数据不足",
    }.get(result["risk_level"], result["risk_level"])

    lines = [
        f"SKU：{result['sku']}",
        f"站点/店铺：{result['site']}",
        "",
        "一、核心结论",
        f"- 风险判断：{risk_text}",
        f"- 当前海外库存可覆盖：{stock_days_text}",
        f"- 建议工厂下单量：{result['recommended_factory_order_qty']} 件",
        f"- {result['cadence']} 节奏下单次补货参考量：{result['steady_replenishment_qty']} 件",
        "",
        "二、计算依据",
        f"- 销量口径：{result['sales_basis']}",
        f"- 基础日均销量：{result['base_daily_sales']:.2f} 件/天",
        f"- 淡旺季/主推倍率：{result['season_multiplier']:.2f}",
        f"- 预测日均销量：{result['forecast_daily_sales']:.2f} 件/天",
        f"- 海外库存合计：{result['overseas_inventory']:.0f} 件",
        f"- 生产+货代+运输提前期：{result['lead_time_days']} 天",
    ]
    if result.get("missing_parameters"):
        lines.extend(
            [
                "",
                "三、需要人工确认的参数",
                "- " + "、".join(result["missing_parameters"]),
            ]
        )
    return "\n".join(lines)


def input_from_mapping(raw: Dict[str, Any]) -> ReplenishmentInput:
    names = {field.name for field in fields(ReplenishmentInput)}
    cleaned = {key: value for key, value in raw.items() if key in names}
    bool_value = _coerce_bool(cleaned.get("is_promoted"))
    if bool_value is not None:
        cleaned["is_promoted"] = bool_value
    return ReplenishmentInput(**cleaned)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calculate SKU replenishment advice.")
    parser.add_argument("--input", help="JSON file containing ReplenishmentInput fields")
    parser.add_argument("--format", choices=["json", "text", "csv"], default="json")
    parser.add_argument("--sku", default="")
    parser.add_argument("--site", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--asin", default="")
    parser.add_argument("--owner", default="")
    parser.add_argument("--month", type=int)
    parser.add_argument("--sales-7", type=float)
    parser.add_argument("--sales-14", type=float)
    parser.add_argument("--sales-30", type=float)
    parser.add_argument("--fba-total", type=float, default=0)
    parser.add_argument("--fba-sellable", type=float)
    parser.add_argument("--awd-total", type=float, default=0)
    parser.add_argument("--confirmed-inbound-qty", type=float, default=0)
    parser.add_argument("--is-promoted")
    parser.add_argument("--manual-season-multiplier", type=float)
    parser.add_argument("--sales-stability", default="unknown")
    parser.add_argument("--replenishment-cadence", default="auto")
    parser.add_argument("--production-days", type=int, default=15)
    parser.add_argument("--freight-prep-days", type=int, default=3)
    parser.add_argument("--transit-days", type=int, default=37)
    parser.add_argument("--inbound-delay-days", type=int, default=0)
    parser.add_argument("--safety-stock-days", type=int, default=30)
    parser.add_argument("--max-stock-days", type=int, default=90)
    parser.add_argument("--target-stock-days", type=int, default=90)
    parser.add_argument("--reorder-threshold-days", type=int)
    parser.add_argument("--moq", type=int)
    parser.add_argument("--case-pack", type=int)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.input:
        with open(args.input, "r", encoding="utf-8-sig") as handle:
            raw = json.load(handle)
        if isinstance(raw, list):
            results = calculate_batch_replenishment(raw)
            if args.format == "csv":
                print(format_batch_csv(results), end="")
            elif args.format == "text":
                print("\n\n---\n\n".join(format_chinese_report(result) for result in results))
            else:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        data = input_from_mapping(raw)
    else:
        data = ReplenishmentInput(
            sku=args.sku,
            site=args.site,
            title=args.title,
            asin=args.asin,
            owner=args.owner,
            month=args.month,
            sales_7=args.sales_7,
            sales_14=args.sales_14,
            sales_30=args.sales_30,
            fba_total=args.fba_total,
            fba_sellable=args.fba_sellable,
            awd_available_inbound_total=args.awd_total,
            confirmed_inbound_qty=args.confirmed_inbound_qty,
            is_promoted=_coerce_bool(args.is_promoted),
            manual_season_multiplier=args.manual_season_multiplier,
            sales_stability=args.sales_stability,
            replenishment_cadence=args.replenishment_cadence,
            production_days=args.production_days,
            freight_prep_days=args.freight_prep_days,
            transit_days=args.transit_days,
            inbound_delay_days=args.inbound_delay_days,
            safety_stock_days=args.safety_stock_days,
            max_stock_days=args.max_stock_days,
            target_stock_days=args.target_stock_days,
            reorder_threshold_days=args.reorder_threshold_days,
            moq=args.moq,
            case_pack=args.case_pack,
        )

    result = calculate_replenishment(data)
    if args.format == "csv":
        print(format_batch_csv([result]), end="")
    elif args.format == "text":
        print(format_chinese_report(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

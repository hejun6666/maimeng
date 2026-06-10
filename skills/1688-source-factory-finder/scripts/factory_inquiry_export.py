#!/usr/bin/env python3
"""Export 1688 supplier inquiry records to CSV or a minimal XLSX workbook."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape


FIELDS: list[tuple[str, str]] = [
    ("index", "序号"),
    ("product_image", "产品图片"),
    ("product_name", "产品品名"),
    ("benchmark_url", "产品对标链接"),
    ("shop_name", "供应商"),
    ("tax_included_price", "报价含税价"),
    ("moq", "起订量"),
    ("lead_time", "交期"),
    ("product_url", "链接"),
    ("remarks", "备注"),
    ("sample_owner", "样品负责人"),
    ("progress", "进度"),
]

ALIASES: dict[str, tuple[str, ...]] = {
    "product_image": ("image", "image_url", "product_image_url", "图片", "产品图"),
    "product_name": ("name", "title", "商品名", "产品品名"),
    "benchmark_url": ("benchmark_link", "reference_url", "comparison_url", "product_benchmark_url", "对标链接"),
    "shop_name": ("supplier", "supplier_name", "店铺名", "供应商"),
    "tax_included_price": ("price", "quoted_price", "tax_price", "报价", "报价含税价", "阶梯价"),
    "moq": ("minimum_order_quantity", "起订量", "MOQ"),
    "lead_time": ("delivery_time", "delivery_days", "交期"),
    "product_url": ("link", "url", "商品链接", "链接"),
    "remarks": ("note", "notes", "remark", "备注"),
    "sample_owner": ("owner", "sample_person", "样品负责人"),
    "progress": ("status", "stage", "进度"),
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_suppliers(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("suppliers", [])
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list or an object with a 'suppliers' list.")

    suppliers: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each supplier record must be a JSON object.")
        suppliers.append(item)
    return suppliers


def normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (list, tuple)):
        return "；".join(normalize_value(item) for item in value if item is not None)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def get_field_value(supplier: dict[str, Any], key: str) -> Any:
    if key in supplier:
        return supplier.get(key)
    for alias in ALIASES.get(key, ()):
        if alias in supplier:
            return supplier.get(alias)
    return None


def is_customer_service_value(value: str) -> bool:
    if "待客服确认" in value:
        return False
    return any(marker in value for marker in ("客服报", "客服确认", "客服阶梯", "已拿到报价", "含税价"))


def is_page_only_value(value: str) -> bool:
    page_only_markers = ("页面显示", "候选页显示", "聊天商品卡显示")
    return any(marker in value for marker in page_only_markers)


def is_untaxed_quote(value: str) -> bool:
    untaxed_markers = ("未税", "不含税")
    has_untaxed_marker = any(marker in value for marker in untaxed_markers)
    has_explicit_tax_included_price = any(marker in value for marker in ("含税价", "含税报价", "含税：", "含税:"))
    return has_untaxed_marker and not has_explicit_tax_included_price


def split_detail_segments(value: str) -> list[str]:
    return [segment.strip() for segment in value.replace(";", "；").split("；") if segment.strip()]


def strip_page_only_segments(value: str) -> str:
    kept = [segment for segment in split_detail_segments(value) if not is_page_only_value(segment)]
    return "；".join(kept)


def page_only_detail(value: str) -> str:
    details = [segment for segment in split_detail_segments(value) if is_page_only_value(segment)]
    return "；".join(details) if details else value


def format_untaxed_quote(value: str) -> str:
    if value.startswith("未税报价"):
        return value
    return f"未税报价（非含税价，开票/税点见原话）：{value}"


def sanitize_column_value(key: str, value: str) -> str:
    if key == "tax_included_price" and is_untaxed_quote(value):
        return format_untaxed_quote(value)
    if key in {"tax_included_price", "moq"}:
        if is_page_only_value(value):
            if is_customer_service_value(value):
                stripped = strip_page_only_segments(value)
                if stripped:
                    return stripped
            return "待客服确认"
    return value


def export_value(supplier: dict[str, Any], key: str) -> str:
    return sanitize_column_value(key, normalize_value(get_field_value(supplier, key)))


def normalize_rows(suppliers: Iterable[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for i, supplier in enumerate(suppliers, start=1):
        row: list[str] = []
        for key, _label in FIELDS:
            if key == "index":
                row.append(str(i))
            else:
                row.append(export_value(supplier, key))
        append_suppressed_details_to_remarks(row, supplier)
        rows.append(row)
    return rows


def append_suppressed_details_to_remarks(row: list[str], supplier: dict[str, Any]) -> None:
    remarks_index = 9
    details: list[str] = []

    raw_quote = normalize_value(get_field_value(supplier, "tax_included_price"))
    exported_quote = row[5]
    if raw_quote and exported_quote != raw_quote and is_page_only_value(raw_quote):
        details.append(f"页面价格信息：{page_only_detail(raw_quote)}")

    raw_moq = normalize_value(get_field_value(supplier, "moq"))
    exported_moq = row[6]
    if raw_moq and exported_moq != raw_moq and is_page_only_value(raw_moq):
        details.append(f"页面起订量信息：{page_only_detail(raw_moq)}")

    for detail in details:
        if detail and detail not in row[remarks_index]:
            row[remarks_index] = f"{row[remarks_index]}；{detail}" if row[remarks_index] else detail


def supplier_is_incomplete(supplier: dict[str, Any]) -> bool:
    if supplier_is_closed_without_quote(supplier):
        return False

    progress = export_value(supplier, "progress")
    price = export_value(supplier, "tax_included_price")
    moq = export_value(supplier, "moq")
    lead_time = export_value(supplier, "lead_time")
    remarks = export_value(supplier, "remarks")
    combined = f"{progress} {price} {moq} {lead_time} {remarks}"

    incomplete_markers = (
        "待回复",
        "待客服确认",
        "回查异常",
        "尚未选择联系人",
        "未发送",
        "未见首轮询价文本",
        "暂无报价",
        "暂无具体",
        "缺字段",
        "待报价",
        "待交期",
        "待样品",
        "已发询价",
        "已追问",
    )
    if any(marker in combined for marker in incomplete_markers):
        return True
    return not price or not moq or not lead_time


def supplier_is_closed_without_quote(supplier: dict[str, Any]) -> bool:
    progress = export_value(supplier, "progress")
    remarks = export_value(supplier, "remarks")
    combined = f"{progress} {remarks}"
    closed_markers = (
        "未回复/暂不跟进",
        "未回复，暂不跟进",
        "无回复/暂不跟进",
        "超时未回复",
        "长期未回复",
        "暂不跟进",
    )
    return any(marker in combined for marker in closed_markers)


def supplier_has_completed_reply(supplier: dict[str, Any]) -> bool:
    return not supplier_is_closed_without_quote(supplier) and not supplier_is_incomplete(supplier)


def output_name_marks_progress(path: Path) -> bool:
    stem = path.stem.lower()
    return any(marker in stem for marker in ("in-progress", "progress", "draft", "进行中", "草稿"))


def validate_export_readiness(suppliers: list[dict[str, Any]], output_path: Path, allow_in_progress: bool) -> None:
    incomplete_count = sum(1 for supplier in suppliers if supplier_is_incomplete(supplier))
    if not incomplete_count:
        if not any(supplier_has_completed_reply(supplier) for supplier in suppliers):
            raise ValueError("不能导出最终表：还没有拿到任何完整报价供应商。请继续回查，或导出 in-progress/draft。")
        return
    if not allow_in_progress:
        raise ValueError(
            f"不能导出最终表：{incomplete_count} 家供应商仍未完成询价/回查。"
            "请继续收回复，或使用 --allow-in-progress 并把文件名标明 in-progress/draft。"
        )
    if not output_name_marks_progress(output_path):
        raise ValueError("文件名必须标明 in-progress/draft/进行中/草稿，避免把未完成询价表当成最终结果。")


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([label for _key, label in FIELDS])
        writer.writerows(rows)


def col_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def sheet_xml(rows: list[list[str]]) -> str:
    all_rows = [[label for _key, label in FIELDS], *rows]
    xml_rows: list[str] = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells: list[str] = []
        for c_idx, value in enumerate(row, start=1):
            cell_ref = f"{col_name(c_idx)}{r_idx}"
            value_xml = escape(value)
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{value_xml}</t></is></c>')
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    column_widths = [8, 18, 22, 38, 24, 22, 14, 14, 38, 48, 16, 18]
    widths = "".join(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>' for i, width in enumerate(column_widths, start=1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<cols>{widths}</cols><sheetData>{''.join(xml_rows)}</sheetData>"
        "</worksheet>"
    )


def write_xlsx(path: Path, rows: list[list[str]]) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="1688供应商对比" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": sheet_xml(rows),
        "xl/styles.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            "</styleSheet>"
        ),
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:title>1688供应商对比</dc:title><dc:creator>Codex</dc:creator>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            "</cp:coreProperties>"
        ),
        "docProps/app.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Application>Codex</Application></Properties>"
        ),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content.encode("utf-8"))


def export(input_path: Path, output_path: Path, allow_in_progress: bool = False) -> None:
    suppliers = load_suppliers(input_path)
    validate_export_readiness(suppliers, output_path, allow_in_progress=allow_in_progress)
    rows = normalize_rows(suppliers)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    if suffix == ".csv":
        write_csv(output_path, rows)
    elif suffix == ".xlsx":
        write_xlsx(output_path, rows)
    else:
        raise ValueError("Output path must end with .csv or .xlsx")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export 1688 supplier inquiry records.")
    parser.add_argument("--input", required=True, type=Path, help="JSON list or object with suppliers list.")
    parser.add_argument("--output", required=True, type=Path, help="Output .xlsx or .csv path.")
    parser.add_argument(
        "--allow-in-progress",
        action="store_true",
        help="Allow exporting incomplete inquiry records only when the output filename marks in-progress/draft.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        export(args.input, args.output, allow_in_progress=args.allow_in_progress)
    except Exception as exc:
        print(f"导出失败: {exc}", file=sys.stderr)
        return 1
    print(f"已导出: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

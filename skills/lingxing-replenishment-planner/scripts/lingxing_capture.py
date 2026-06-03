#!/usr/bin/env python3
"""Technical fallback for best-effort Lingxing ERP data capture.

Normal colleagues should use the Lingxing web page opened inside Codex, not
this script. This script does not know company accounts or passwords. It
connects to a browser automation endpoint, opens Lingxing pages, tries to search
the SKU, scrolls dynamic tables horizontally, and returns visible text plus
parsed common fields.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

FBA_INVENTORY_URL = "https://erp.lingxing.com/erp/msupply/fbaInventory"
LISTING_URL = "https://erp.lingxing.com/erp/listing"

KNOWN_NUMBER_LABELS = {
    "fba_total": ["FBA总库存"],
    "fba_sellable": ["FBA可售", "FBA可用库存"],
    "awd_available_inbound_total": ["AWD可用+在途库存合计"],
    "fba_inbound_actual": ["FBA实际在途"],
    "fba_inbound_standard": ["FBA标发在途"],
    "fba_receiving": ["FBA入库中"],
}


def parse_number(value: str) -> Optional[float]:
    cleaned = value.replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def parse_sales_triplet(text: str) -> Dict[str, float]:
    """Parse Lingxing's 7|14|30 day sales cell."""
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*[|｜/]\s*(\d+(?:\.\d+)?)\s*[|｜/]\s*(\d+(?:\.\d+)?)",
        text,
    )
    if not match:
        return {}
    return {
        "sales_7": float(match.group(1)),
        "sales_14": float(match.group(2)),
        "sales_30": float(match.group(3)),
    }


def _first_number_after_label(text: str, label: str) -> Optional[float]:
    pattern = re.compile(re.escape(label) + r"[\s:：\n\r]*([,\d]+(?:\.\d+)?)", re.I)
    match = pattern.search(text)
    if match:
        return parse_number(match.group(1))

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        if label in line:
            for look_ahead in lines[idx + 1 : idx + 5]:
                parsed = parse_number(look_ahead)
                if parsed is not None:
                    return parsed
    return None


def extract_known_numbers_from_text(text: str) -> Dict[str, float]:
    fields: Dict[str, float] = {}
    for key, labels in KNOWN_NUMBER_LABELS.items():
        for label in labels:
            parsed = _first_number_after_label(text, label)
            if parsed is not None:
                fields[key] = parsed
                break
    fields.update(parse_sales_triplet(text))
    return fields


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "lingxing"


def _try_fill_search(page: Any, sku: str) -> None:
    if not sku:
        return
    selectors = [
        "input[placeholder*='SKU']",
        "input[placeholder*='MSKU']",
        "input[placeholder*='ASIN']",
        "input[placeholder*='品名']",
        "input[placeholder*='搜索']",
        "textarea[placeholder*='SKU']",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0 or not locator.is_visible(timeout=1000):
                continue
            locator.fill(sku, timeout=3000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2500)
            return
        except Exception:
            continue


def _scroll_and_collect_text(page: Any) -> List[str]:
    texts: List[str] = []
    for step in range(5):
        try:
            texts.append(page.locator("body").inner_text(timeout=8000))
        except Exception:
            pass
        try:
            page.evaluate(
                """
                (step) => {
                  const scrollers = Array.from(document.querySelectorAll('*'))
                    .filter(el => el.scrollWidth > el.clientWidth + 80);
                  for (const el of scrollers) {
                    el.scrollLeft = Math.floor((el.scrollWidth - el.clientWidth) * step / 4);
                  }
                }
                """,
                step,
            )
        except Exception:
            pass
        page.wait_for_timeout(900)
    return texts


def _open_collect_page(
    page: Any,
    url: str,
    sku: str,
    screenshot_dir: Path,
    name: str,
) -> Dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    _try_fill_search(page, sku)
    page.wait_for_timeout(3000)
    texts = _scroll_and_collect_text(page)
    combined_text = "\n".join(texts)
    screenshot_path = screenshot_dir / f"{_safe_filename(name)}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=False)
    except Exception:
        screenshot_path = Path("")
    return {
        "url": page.url,
        "title": page.title(),
        "text": combined_text,
        "parsed_fields": extract_known_numbers_from_text(combined_text),
        "screenshot": str(screenshot_path) if screenshot_path else "",
    }


def capture_lingxing(
    sku: str,
    cdp_url: str = "http://127.0.0.1:9222",
    screenshot_dir: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment specific
        raise RuntimeError("Python Playwright is required: python -m pip install playwright") from exc

    out_dir = Path(screenshot_dir) if screenshot_dir else Path(tempfile.mkdtemp(prefix="lingxing-capture-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        inventory = _open_collect_page(page, FBA_INVENTORY_URL, sku, out_dir, "fba_inventory")
        listing = _open_collect_page(page, LISTING_URL, sku, out_dir, "sales_listing")

        merged_fields: Dict[str, Any] = {}
        merged_fields.update(inventory.get("parsed_fields", {}))
        merged_fields.update(listing.get("parsed_fields", {}))

        return {
            "sku": sku,
            "cdp_url": cdp_url,
            "screenshot_dir": str(out_dir),
            "inventory": inventory,
            "listing": listing,
            "merged_fields": merged_fields,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Lingxing ERP visible data for one SKU.")
    parser.add_argument("--sku", required=True)
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--screenshot-dir")
    parser.add_argument("--out")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        result = capture_lingxing(
            sku=args.sku,
            cdp_url=args.cdp_url,
            screenshot_dir=args.screenshot_dir,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

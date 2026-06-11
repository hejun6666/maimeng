#!/usr/bin/env python3
"""Extract CNY price and package data from 1688 product text or HTML."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

from normalize_package_data import extract as extract_package


DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; CodexProductProfitDataFiller/1.0)"
PRICE_RE = re.compile(
    r"(?:¥|￥|CNY|RMB|价格|价钱|批发价|现货价|单价|起批价|采购价)\s*[:：]?\s*(?:¥|￥)?\s*"
    r"([0-9]+(?:\.[0-9]{1,2})?)",
    re.I,
)
ATTRIBUTE_RE = re.compile(
    r"(?:产品属性|商品属性|规格参数|产品参数|属性)\s*[:：]\s*(.{2,160}?)(?=\s*(?:价格|价钱|批发价|现货价|包装尺寸|包裹尺寸|外箱尺寸|毛重|重量|$))"
)


def money(value: str) -> str:
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def text_from_html(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def fetch_text(url: str, timeout: int = 30) -> str:
    """Fetch page text with Scrapling when installed, otherwise urllib."""
    try:
        from scrapling.fetchers import Fetcher  # type: ignore

        page = Fetcher.get(
            url,
            timeout=timeout,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        return str(page.text)
    except Exception:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")


def extract_product_attribute(text: str) -> str | None:
    match = ATTRIBUTE_RE.search(text)
    if not match:
        return None
    value = re.sub(r"\s+", " ", match.group(1)).strip(" ;；,，")
    return value or None


def parse_1688_text(text: str, url: str | None = None) -> dict[str, object]:
    normalized_text = text_from_html(text)
    price = None
    match = PRICE_RE.search(normalized_text)
    if match:
        price = money(match.group(1))

    package = extract_package(normalized_text)
    dimensions = package.get("package_dimensions")
    weight = package.get("package_weight")

    return {
        "price_cny": price,
        "package_dimensions": dimensions["text"] if dimensions else None,
        "package_weight": weight["text"] if weight else None,
        "product_attribute": extract_product_attribute(normalized_text),
        "url": url,
        "raw_text": normalized_text[:2000],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse 1688 product price and package data.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="1688 product URL to fetch.")
    source.add_argument("--text", help="Raw page/listing text to parse.")
    source.add_argument("--html", help="Raw page HTML to parse.")
    parser.add_argument("--timeout", type=int, default=30, help="Fetch timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    value = fetch_text(args.url, timeout=args.timeout) if args.url else (args.text or args.html or "")
    print(json.dumps(parse_1688_text(value, url=args.url), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

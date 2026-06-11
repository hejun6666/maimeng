#!/usr/bin/env python3
"""Extract observed GBP prices from Amazon UK text or HTML."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request

from select_competitor_price import choose_existing_middle, money, parse_prices


DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; CodexProductProfitDataFiller/1.0)"
MARKETPLACE = "amazon.co.uk"
GBP_RE = re.compile(r"(?:£|GBP)\s*([0-9]+(?:\.[0-9]{2})?)", re.I)
SPLIT_PRICE_RE = re.compile(
    r"<[^>]*class=[\"'][^\"']*a-price-symbol[^\"']*[\"'][^>]*>\s*(?:&pound;|£|GBP)?\s*</[^>]+>\s*"
    r"<[^>]*class=[\"'][^\"']*a-price-whole[^\"']*[\"'][^>]*>\s*([0-9,]+)\s*</[^>]+>\s*"
    r"(?:<[^>]*class=[\"'][^\"']*a-price-decimal[^\"']*[\"'][^>]*>.*?</[^>]+>\s*)?"
    r"<[^>]*class=[\"'][^\"']*a-price-fraction[^\"']*[\"'][^>]*>\s*([0-9]{2})\s*</[^>]+>",
    re.I | re.S,
)


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


def ensure_amazon_uk_url(url: str) -> None:
    host = urllib.parse.urlparse(url).netloc.lower()
    if not (host == MARKETPLACE or host.endswith("." + MARKETPLACE)):
        raise ValueError("Amazon UK parser only accepts amazon.co.uk URLs")


def split_markup_prices(text: str) -> list[str]:
    return [
        f"£{whole.replace(',', '')}.{fraction}"
        for whole, fraction in SPLIT_PRICE_RE.findall(text)
    ]


def parse_prices_from_text(text: str) -> dict[str, object]:
    normalized_text = text_from_html(text)
    split_prices = split_markup_prices(text)
    generic_prices = [] if split_prices else ["£" + value for value in GBP_RE.findall(normalized_text)]
    price_inputs = [" ".join(split_prices), *generic_prices]
    prices = parse_prices(price_inputs)
    selected = choose_existing_middle(prices) if prices else None
    return {
        "marketplace": MARKETPLACE,
        "prices": [money(price) for price in sorted(prices)],
        "selected_price": money(selected) if selected is not None else None,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse observed prices from Amazon UK text.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="amazon.co.uk URL to fetch.")
    source.add_argument("--text", help="Raw page/listing text to parse.")
    source.add_argument("--html", help="Raw page HTML to parse.")
    parser.add_argument("--timeout", type=int, default=30, help="Fetch timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.url:
        ensure_amazon_uk_url(args.url)
        value = fetch_text(args.url, timeout=args.timeout)
    else:
        value = args.text or args.html or ""
    print(json.dumps(parse_prices_from_text(value), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

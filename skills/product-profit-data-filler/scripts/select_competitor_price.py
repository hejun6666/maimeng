#!/usr/bin/env python3
"""Select a representative Amazon competitor price from visible candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP


CURRENCY_PRICE_RE = re.compile(
    r"(?:£|\$|€|¥|￥|GBP|USD|EUR|CNY|RMB)\s*([0-9]+(?:\.[0-9]{1,2})?)",
    re.I,
)
COMMA_NUMBERS_RE = re.compile(r"^\s*[0-9]+(?:\.[0-9]{1,2})?(?:\s*,\s*[0-9]+(?:\.[0-9]{1,2})?)+\s*$")
NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")


def parse_prices(parts: list[str]) -> list[Decimal]:
    text = " ".join(parts)
    if COMMA_NUMBERS_RE.match(text):
        return [Decimal(match.group(0)) for match in NUMBER_RE.finditer(text)]

    values: list[Decimal] = []
    for match in CURRENCY_PRICE_RE.finditer(text):
        value = Decimal(match.group(1))
        if value >= Decimal("1"):
            values.append(value)
    return values


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def choose_existing_middle(prices: list[Decimal]) -> Decimal:
    if not prices:
        raise ValueError("No valid prices found")
    ordered = sorted(prices)
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n // 2]
    lower = ordered[n // 2 - 1]
    upper = ordered[n // 2]
    numeric_mid = (lower + upper) / 2
    # Selling price should be an observed competitor price. When tied, choose the lower
    # middle price to avoid over-optimistic profit calculations.
    if abs(numeric_mid - lower) <= abs(upper - numeric_mid):
        return lower
    return upper


def main() -> int:
    parser = argparse.ArgumentParser(description="Choose a middle observed competitor price.")
    parser.add_argument("--prices", nargs="*", default=[], help="Price strings, e.g. '16.99, 26.99, 28.99'.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    parts = args.prices
    if not parts and not sys.stdin.isatty():
        parts = [sys.stdin.read()]

    prices = parse_prices(parts)
    selected = choose_existing_middle(prices)
    payload = {
        "prices": [money(p) for p in sorted(prices)],
        "selected_price": money(selected),
        "rule": "choose the middle observed price; if even count ties, choose lower middle",
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["selected_price"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

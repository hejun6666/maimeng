#!/usr/bin/env python3
"""Extract simple package dimensions and weight from listing text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP


DIM_RE = re.compile(
    r"(?P<a>[0-9]+(?:\.[0-9]+)?)\s*(?:cm|厘米|CM|公分)?\s*[xX×脳*]\s*"
    r"(?P<b>[0-9]+(?:\.[0-9]+)?)\s*(?:cm|厘米|CM|公分)?\s*[xX×脳*]\s*"
    r"(?P<c>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>cm|厘米|CM|公分|mm|毫米|MM|m|米)?"
)
WEIGHT_RE = re.compile(r"(?P<w>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>kg|KG|千克|公斤|g|G|克)")
PACKAGE_LABEL_RE = re.compile(r"(包装尺寸|包裹尺寸|外箱尺寸|package\s+size|packed\s+size)", re.I)


def q(value: Decimal, places: str = "0.01") -> str:
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def normalize_dim(value: Decimal, unit: str | None) -> Decimal:
    unit = (unit or "cm").lower()
    if unit in ("mm", "毫米"):
        return value / Decimal("10")
    if unit in ("m", "米"):
        return value * Decimal("100")
    return value


def normalize_weight(value: Decimal, unit: str) -> Decimal:
    unit = unit.lower()
    if unit in ("g", "克"):
        return value / Decimal("1000")
    return value


def build_dimension(match: re.Match[str]) -> dict[str, object]:
    unit = match.group("unit")
    dims = [
        normalize_dim(Decimal(match.group(k)), unit)
        for k in ("a", "b", "c")
    ]
    return {
        "cm": [q(v) for v in dims],
        "text": f"{q(dims[0])} x {q(dims[1])} x {q(dims[2])} cm",
    }


def choose_dimension_match(text: str) -> re.Match[str] | None:
    matches = list(DIM_RE.finditer(text))
    if not matches:
        return None
    for match in matches:
        before = text[max(0, match.start() - 80):match.start()]
        if PACKAGE_LABEL_RE.search(before):
            return match
    return matches[0]


def extract(text: str) -> dict[str, object]:
    dim = None
    weight = None

    dim_match = choose_dimension_match(text)
    if dim_match:
        dim = build_dimension(dim_match)

    weight_match = WEIGHT_RE.search(text)
    if weight_match:
        kg = normalize_weight(Decimal(weight_match.group("w")), weight_match.group("unit"))
        weight = {"kg": q(kg), "text": f"{q(kg)} kg"}

    return {
        "package_dimensions": dim,
        "package_weight": weight,
        "found_dimensions": dim is not None,
        "found_weight": weight is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize package dimensions and weight from text.")
    parser.add_argument("text", nargs="*", help="Raw listing/spec text. Reads stdin when omitted.")
    args = parser.parse_args()
    text = " ".join(args.text) if args.text else sys.stdin.read()
    print(json.dumps(extract(text), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Lightweight safety and similarity checks for generated Amazon copy."""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from typing import Any


RISKY_PATTERNS = {
    "absolute_safety": r"\b(100%\s+safe|completely safe|guaranteed safe|prevents injury|childproof)\b",
    "unsupported_certification": r"\b(FDA approved|CPC certified|UL listed|CE certified|BPA[- ]free|non[- ]toxic)\b",
    "medical_claim": r"\b(treats|cures|prevents disease|clinically proven|medical grade)\b",
    "superlative": r"\b(best|number\s*1|#1|top rated|guaranteed)\b",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def phrase_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def check_copy(payload: dict[str, Any]) -> dict[str, Any]:
    copy_text = payload.get("copy", "")
    competitor_texts = payload.get("competitorTexts", [])
    warnings: list[dict[str, Any]] = []

    for label, pattern in RISKY_PATTERNS.items():
        for match in re.finditer(pattern, copy_text, flags=re.I):
            warnings.append({
                "type": label,
                "text": match.group(0),
                "message": "Review this claim. Keep only if confirmed, otherwise tag as [待核实].",
            })

    for competitor in competitor_texts:
        competitor = str(competitor)
        if len(competitor) < 25:
            continue
        sim = phrase_similarity(copy_text, competitor)
        if sim >= 0.72:
            warnings.append({
                "type": "competitor_similarity",
                "score": round(sim, 3),
                "message": "Generated copy is too similar to competitor text. Rewrite structure and wording.",
            })

    repeated = re.findall(r"\b([a-zA-Z][a-zA-Z0-9-]{3,})\b", copy_text.lower())
    counts = {}
    for word in repeated:
        counts[word] = counts.get(word, 0) + 1
    stuffed = sorted((word, count) for word, count in counts.items() if count >= 8)
    for word, count in stuffed[:10]:
        warnings.append({
            "type": "keyword_repetition",
            "word": word,
            "count": count,
            "message": "Possible keyword stuffing. Reduce repetition if readability suffers.",
        })

    return {"warningCount": len(warnings), "warnings": warnings}


def main() -> None:
    if len(sys.argv) < 2:
        raw = sys.stdin.read().strip()
        if not raw:
            print("Usage: copy_safety_check.py '<JSON {copy, competitorTexts}>'", file=sys.stderr)
            print("   or: echo '<JSON>' | copy_safety_check.py", file=sys.stderr)
            sys.exit(1)
    else:
        raw = sys.argv[1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(check_copy(payload), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

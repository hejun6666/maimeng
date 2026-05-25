#!/usr/bin/env python3
"""Check whether Amazon copy is AI Shopping readable without making promises."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


PROHIBITED_PROMISES = [
    r"\bAI\s+recommended\b",
    r"\brecommended\s+by\s+Rufus\b",
    r"\bAlexa\s+recommended\b",
    r"\bRufus\s+optimized\b",
    r"\bGEO\s+guaranteed\b",
    r"\bguaranteed\s+(?:ranking|indexing|citation|visibility|recommendation)\b",
]

VAGUE_PHRASES = [
    r"\bpremium\s+quality\b",
    r"\bhigh\s+quality\b",
    r"\bperfect\s+(?:choice|gift|solution)\b",
    r"\bmust[- ]have\b",
    r"\bbest\s+(?:choice|gift|solution|quality)\b",
]

SIGNAL_TERMS = {
    "product_type": ["productType", "product", "category"],
    "audience": ["audience", "targetUser", "targetUsers"],
    "scenarios": ["scenarios", "useCases", "uses"],
    "attributes": ["features", "materials", "size", "capacity", "quantity", "compatibility", "accessories"],
}

ATTRIBUTE_MAP_ALIASES = {
    "product_type": {"producttype", "product_type", "product", "category", "type"},
    "audience": {"audience", "targetuser", "targetusers", "user", "users", "buyer", "buyers"},
    "scenarios": {"scenario", "scenarios", "usecase", "usecases", "uses", "occasions"},
}


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(normalize_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(normalize_text(item) for item in value.values())
    return re.sub(r"\s+", " ", str(value or "")).strip()


def word_tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) > 2}


def contains_phrase_or_tokens(copy_text: str, phrase: str) -> bool:
    phrase = normalize_text(phrase)
    if not phrase:
        return True
    copy_lower = copy_text.lower()
    phrase_lower = phrase.lower()
    if phrase_lower in copy_lower:
        return True
    tokens = word_tokens(phrase)
    if not tokens:
        return True
    copy_tokens = word_tokens(copy_text)
    return len(tokens & copy_tokens) / max(len(tokens), 1) >= 0.6


def listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[\n;|]+", value) if part.strip()]
    return []


def attribute_map_values(attribute_map: dict[str, Any], signal_name: str) -> list[str]:
    values: list[str] = []
    aliases = ATTRIBUTE_MAP_ALIASES.get(signal_name, set())
    for key, value in attribute_map.items():
        normalized_key = re.sub(r"[^a-z0-9]+", "", str(key).lower())
        if signal_name == "attributes" or normalized_key in aliases:
            if isinstance(value, list):
                values.extend(normalize_text(item) for item in value)
            elif value:
                values.append(normalize_text(value))
    return values


def check_question_coverage(copy_text: str, questions: list[str]) -> tuple[int, list[str]]:
    covered = 0
    missing: list[str] = []
    for question in questions:
        question_tokens = word_tokens(question)
        if not question_tokens:
            continue
        copy_tokens = word_tokens(copy_text)
        overlap = len(question_tokens & copy_tokens) / max(len(question_tokens), 1)
        if overlap >= 0.45:
            covered += 1
        else:
            missing.append(question)
    return covered, missing


def check_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = normalize_text(payload.get("title"))
    bullets = listify(payload.get("bullets"))
    description = normalize_text(payload.get("description"))
    backend = normalize_text(payload.get("backendSearchTerms") or payload.get("backend"))
    brief = payload.get("productBrief") if isinstance(payload.get("productBrief"), dict) else payload
    attribute_map = payload.get("attributeEntityMap") if isinstance(payload.get("attributeEntityMap"), dict) else {}
    copy_text = normalize_text([title, bullets, description, backend])

    warnings: list[dict[str, Any]] = []

    for pattern in PROHIBITED_PROMISES:
        for match in re.finditer(pattern, copy_text, flags=re.I):
            warnings.append({
                "type": "ai_promise_language",
                "text": match.group(0),
                "message": "Do not promise AI recommendation, ranking, indexing, visibility, or citation.",
            })

    for pattern in VAGUE_PHRASES:
        for match in re.finditer(pattern, copy_text, flags=re.I):
            warnings.append({
                "type": "vague_claim",
                "text": match.group(0),
                "message": "Replace vague quality language with a specific, verifiable attribute or benefit.",
            })

    if len(bullets) != 5:
        warnings.append({
            "type": "bullet_count",
            "message": "Expected exactly 5 bullet points for Amazon listing copy.",
        })

    for index, bullet in enumerate(bullets, start=1):
        if ":" not in bullet[:80]:
            warnings.append({
                "type": "missing_benefit_headline",
                "bullet": index,
                "message": "Bullet should start with a benefit-led mini headline ending with a colon.",
            })

    missing_signals: list[str] = []
    for signal_name, keys in SIGNAL_TERMS.items():
        values: list[str] = []
        for key in keys:
            value = brief.get(key) if isinstance(brief, dict) else None
            if isinstance(value, list):
                values.extend(normalize_text(item) for item in value)
            elif value:
                values.append(normalize_text(value))
        values.extend(attribute_map_values(attribute_map, signal_name))
        values = [value for value in values if value]
        if values and not any(contains_phrase_or_tokens(copy_text, value) for value in values[:6]):
            missing_signals.append(signal_name)

    for signal in missing_signals:
        warnings.append({
            "type": "missing_ai_readability_signal",
            "signal": signal,
            "message": "Known product signal is not clearly represented in the copy.",
        })

    questions = listify(payload.get("aiShoppingQuestions"))
    covered_questions, missing_questions = check_question_coverage(copy_text, questions)
    if questions and covered_questions < min(4, len(questions)):
        warnings.append({
            "type": "low_buyer_question_coverage",
            "covered": covered_questions,
            "total": len(questions),
            "missingExamples": missing_questions[:5],
            "message": "Copy should naturally answer more buyer questions for AI Shopping readiness.",
        })

    triggers = listify(payload.get("recommendationTriggers"))
    matched_triggers = [trigger for trigger in triggers if contains_phrase_or_tokens(copy_text, trigger)]
    if triggers and len(matched_triggers) < min(3, len(triggers)):
        warnings.append({
            "type": "low_recommendation_trigger_coverage",
            "matched": len(matched_triggers),
            "total": len(triggers),
            "message": "Copy should cover more buyer-intent, scenario, audience, or attribute trigger language naturally.",
        })

    score = max(0, 100 - len(warnings) * 8)
    return {
        "score": score,
        "warningCount": len(warnings),
        "coveredBuyerQuestions": covered_questions,
        "warnings": warnings,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raw = sys.stdin.read().strip()
        if not raw:
            print("Usage: ai_recommendation_check.py '<JSON payload>'", file=sys.stderr)
            print("   or: echo '<JSON>' | ai_recommendation_check.py", file=sys.stderr)
            sys.exit(1)
    else:
        raw = sys.argv[1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(check_payload(payload), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Prepare product-profit update payloads from offline extraction outputs."""

import argparse
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from feishu_bitable import shape_update_record

EXCHANGE_RATE = Decimal("9.17")
STATUS_FILLED = "\u5df2\u8865\u9f50"
STATUS_PARTIAL = "已补齐但缺字段"
REQUIRED_EVIDENCE_FIELDS = [
    "purchase_price_cny",
    "purchase_price_gbp",
    "package_dimensions",
    "package_weight",
    "product_attribute",
    "selling_price_gbp",
    "supplier_url",
]


def cny_to_gbp(price_cny):
    value = Decimal(str(price_cny)) / EXCHANGE_RATE
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_evidence(record_id, data_1688, amazon_data):
    evidence = {
        "record_id": record_id,
        "purchase_price_cny": data_1688.get("price_cny"),
        "purchase_price_gbp": cny_to_gbp(data_1688["price_cny"]) if data_1688.get("price_cny") else None,
        "package_dimensions": data_1688.get("package_dimensions"),
        "package_weight": data_1688.get("package_weight"),
        "product_attribute": data_1688.get("product_attribute"),
        "selling_price_gbp": float(amazon_data["selected_price"]) if amazon_data.get("selected_price") else None,
        "supplier_url": data_1688.get("url") or data_1688.get("supplier_url"),
        "amazon_url": amazon_data.get("url") or amazon_data.get("amazon_url"),
    }
    missing = missing_evidence_fields(evidence)
    evidence["missing_fields"] = missing
    evidence["status"] = STATUS_FILLED if not missing else STATUS_PARTIAL
    return evidence


def missing_evidence_fields(evidence):
    return [name for name in REQUIRED_EVIDENCE_FIELDS if evidence.get(name) in (None, "", [], {})]


def is_complete_evidence(evidence):
    return not missing_evidence_fields(evidence)


def safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "record")).strip("._")
    return cleaned or "record"


def read_json_if_present(path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_state(path, state):
    write_json(path, state)


def load_plan(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return {"records": payload, "field_map": {}}
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload
    raise ValueError("Plan JSON must be a list or an object with a records list")


def extraction_paths(image_dir, record_id):
    stem = safe_name(record_id)
    return {
        "1688": Path(image_dir) / f"{stem}.1688.json",
        "amazon": Path(image_dir) / f"{stem}.amazon.json",
    }


def values_from_evidence(evidence):
    return {
        "purchase_price_cny": evidence.get("purchase_price_cny"),
        "purchase_price_gbp": evidence.get("purchase_price_gbp"),
        "package_dimensions": evidence.get("package_dimensions"),
        "package_weight": evidence.get("package_weight"),
        "product_attribute": evidence.get("product_attribute"),
        "selling_price_gbp": evidence.get("selling_price_gbp"),
        "supplier_url": evidence.get("supplier_url"),
        "amazon_url": evidence.get("amazon_url"),
        "status": evidence.get("status"),
    }


def build_update(record_id, field_map, evidence, original_fields=None):
    values = values_from_evidence(evidence)
    return shape_update_record(record_id, field_map, values, original_fields=original_fields)


def has_essential_extraction_data(data_1688, amazon_data):
    return (
        isinstance(data_1688, dict)
        and bool(data_1688.get("price_cny"))
        and isinstance(amazon_data, dict)
        and bool(amazon_data.get("selected_price"))
    )


def load_previous_state(state_path):
    if not state_path.exists():
        return {"processed": 0, "succeeded": 0, "failed": 0, "errors": []}
    try:
        with state_path.open(encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"processed": 0, "succeeded": 0, "failed": 0, "errors": []}
    if not isinstance(state, dict):
        return {"processed": 0, "succeeded": 0, "failed": 0, "errors": []}
    return state


def extraction_file_context(paths):
    return {
        name: {
            "path": str(path),
            "exists": path.exists(),
        }
        for name, path in paths.items()
    }


def extraction_file_context_for_record(image_dir, record_id):
    return extraction_file_context(extraction_paths(image_dir, record_id))


def build_error_evidence(record_id, error, record=None, paths=None, index=None, extraction_files=None):
    return {
        "record_id": record_id,
        "status": "error",
        "error": str(error),
        "record_index": index,
        "record": record or {},
        "extraction_files": extraction_files if extraction_files is not None else extraction_file_context(paths or {}),
    }


def run_batch(plan_path, image_dir, out_updates, evidence_path, batch_size):
    if batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    image_root = Path(image_dir)
    if not image_root.exists() or not image_root.is_dir():
        raise ValueError("--image-dir must be an existing directory")

    plan = load_plan(plan_path)
    state_path = Path(evidence_path).parent / "run-state.json"
    previous_state = load_previous_state(state_path)
    start_index = min(int(previous_state.get("processed") or 0), len(plan["records"]))
    records = plan["records"][start_index : start_index + batch_size]
    field_map = plan.get("field_map") or {}
    updates = []
    state = {
        "processed": start_index,
        "succeeded": int(previous_state.get("succeeded") or 0),
        "failed": int(previous_state.get("failed") or 0),
        "errors": list(previous_state.get("errors") or []),
    }

    Path(evidence_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(evidence_path).open("w", encoding="utf-8") as evidence_file:
        for index, record in enumerate(records, start=start_index + 1):
            record_id = None
            paths = {}
            extraction_files = None
            try:
                if not isinstance(record, dict):
                    raise ValueError("planned record must be an object")
                record_id = record.get("record_id")
                extraction_files = extraction_file_context_for_record(image_root, record_id)
                paths = extraction_paths(image_root, record_id)
                if not record_id:
                    raise ValueError("planned record is missing record_id")
                data_1688 = read_json_if_present(paths["1688"])
                amazon_data = read_json_if_present(paths["amazon"])
                if not has_essential_extraction_data(data_1688, amazon_data):
                    raise ValueError(
                        "Missing essential extraction data: No usable extraction data found for record"
                    )
                evidence = build_evidence(record_id, data_1688, amazon_data)
                evidence["extraction_files"] = extraction_files
                original_fields = record.get("fields")
                if field_map and not isinstance(original_fields, dict):
                    raise ValueError("planned record is missing original fields; refusing blank-field writeback")
                evidence_file.write(json.dumps(evidence, ensure_ascii=False) + "\n")
                update = build_update(record_id, field_map, evidence, original_fields=original_fields or {})
                if update["fields"]:
                    updates.append(update)
                state["succeeded"] += 1
            except Exception as exc:  # Keep the batch moving when one row is bad.
                state["failed"] += 1
                if extraction_files is None:
                    extraction_files = extraction_file_context_for_record(image_root, record_id)
                error_evidence = build_error_evidence(
                    record_id,
                    exc,
                    record=record,
                    paths=paths,
                    index=index,
                    extraction_files=extraction_files,
                )
                evidence_file.write(json.dumps(error_evidence, ensure_ascii=False) + "\n")
                state["errors"].append({"record_id": record_id, "error": str(exc), "record_index": index})
            finally:
                state["processed"] = index
                write_state(state_path, state)

    write_json(out_updates, updates)
    return {"updates": len(updates), "evidence": str(evidence_path), "state": str(state_path), **state}


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare Feishu update JSON and evidence JSONL from a plan and offline extraction JSON. "
            "Per-record extraction files are optional and must live in --image-dir as "
            "<safe_record_id>.1688.json and <safe_record_id>.amazon.json; safe_record_id replaces "
            "non filename-safe characters with underscores, matching downloaded image stems."
        )
    )
    parser.add_argument("--url", help="Feishu Bitable URL kept for workflow symmetry; no live API calls are made")
    parser.add_argument("--plan", required=True, help="JSON plan from feishu_bitable.py plan")
    parser.add_argument("--image-dir", required=True, help="directory containing downloaded images and extraction JSON")
    parser.add_argument("--batch-size", type=int, default=20, help="maximum planned records to process")
    parser.add_argument("--out-updates", required=True, help="Feishu update-records JSON output path")
    parser.add_argument("--evidence", required=True, help="JSONL evidence output path")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = run_batch(args.plan, args.image_dir, args.out_updates, args.evidence, args.batch_size)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])

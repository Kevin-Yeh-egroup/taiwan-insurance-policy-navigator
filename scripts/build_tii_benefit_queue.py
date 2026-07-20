#!/usr/bin/env python3
"""Build a resumable, local-only queue for reviewed TII benefit extraction."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_PRIORITY = {
    "健康保險": 1,
    "傷害保險": 2,
    "傳統型壽險": 3,
    "傳統型年金": 4,
    "投資型壽險": 5,
    "投資型年金": 6,
    "汽車保險": 7,
    "火災保險": 8,
    "海上保險": 9,
    "意外保險": 10,
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def all_coverage_entries(record: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        entry for entry in record.get("coverage_entries") or [] if isinstance(entry, dict)
    ]
    for plan in record.get("plan_options") or []:
        if not isinstance(plan, dict):
            continue
        entries.extend(
            entry
            for entry in plan.get("coverage_entries") or []
            if isinstance(entry, dict)
        )
    return entries


def has_verified_benefits(record: dict[str, Any]) -> bool:
    for entry in all_coverage_entries(record):
        amount = entry.get("amount")
        has_amount = (
            isinstance(amount, (int, float))
            and not isinstance(amount, bool)
            and amount > 0
        )
        calculation_basis = entry.get("calculation_basis")
        has_percentage_formula = calculation_basis == "percentage_of_base" and any(
            isinstance(entry.get(field), (int, float))
            and not isinstance(entry.get(field), bool)
            and entry[field] > 0
            for field in ("rate", "rate_percent")
        )
        has_multiplier_formula = (
            calculation_basis == "table_multiplier"
            and isinstance(entry.get("multiplier"), (int, float))
            and not isinstance(entry.get("multiplier"), bool)
            and entry["multiplier"] > 0
        )
        if (
            entry.get("source") == "terms"
            and entry.get("source_ref")
            and (has_amount or has_percentage_formula or has_multiplier_formula)
        ):
            return True
    return False


def batch_catalog(plan_path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(plan_path)
    result = {}
    for item in payload.get("tii_manual_matrix_batches") or []:
        batch_id = str(item.get("id") or "")
        if not batch_id:
            continue
        result[batch_id] = {
            "batch_id": batch_id,
            "company_type": item.get("company_type") or "",
            "company_type_label": item.get("company_type_label") or "",
            "company": item.get("company_label") or "",
            "insurance_category": item.get("category_label") or "",
        }
    return result


def reviewed_keys(reviewed_dir: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for path in reviewed_dir.glob("*.json"):
        payload = read_json(path)
        batch_id = str(payload.get("batch_id") or path.stem)
        for record in payload.get("records") or []:
            product_id = str(record.get("product_id") or "")
            if product_id:
                keys.add((batch_id, product_id))
    return keys


def public_inventory(
    content_dir: Path,
) -> tuple[dict[str, dict[str, int]], set[tuple[str, str]]]:
    inventory: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "content_batches": 0,
            "records": 0,
            "records_with_documents": 0,
            "records_with_verified_benefits": 0,
        }
    )
    structured_keys: set[tuple[str, str]] = set()
    for path in sorted(content_dir.glob("tii-*.json")):
        batch_id = path.stem
        payload = read_json(path)
        records = [record for record in payload.get("records") or [] if isinstance(record, dict)]
        categories = {
            str(record.get("insurance_category") or "") for record in records
        }
        categories.discard("")
        category = next(iter(categories), "")
        stats = inventory[category]
        stats["content_batches"] += 1
        stats["records"] += len(records)
        for record in records:
            product_id = str(record.get("product_id") or "")
            if int(record.get("extracted_document_count") or 0) > 0:
                stats["records_with_documents"] += 1
            if product_id and has_verified_benefits(record):
                stats["records_with_verified_benefits"] += 1
                structured_keys.add((batch_id, product_id))
    return inventory, structured_keys


def build_queue(
    *,
    plan_path: Path,
    content_dir: Path,
    raw_dir: Path,
    candidates_path: Path,
    reviewed_dir: Path,
) -> dict[str, Any]:
    catalog = batch_catalog(plan_path)
    public_stats, structured_keys = public_inventory(content_dir)
    reviewed = reviewed_keys(reviewed_dir)
    candidates_payload = read_json(candidates_path)
    candidates = [
        item
        for item in candidates_payload.get("candidates") or []
        if isinstance(item, dict)
    ]

    category_batches: dict[str, list[str]] = defaultdict(list)
    for batch_id, item in catalog.items():
        category_batches[item["insurance_category"]].append(batch_id)

    candidate_keys_by_category: dict[str, set[tuple[str, str]]] = defaultdict(set)
    candidate_documents_by_category: dict[str, int] = defaultdict(int)
    candidate_templates_by_category: dict[str, set[str]] = defaultdict(set)
    queue_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    queued_product_keys: set[tuple[str, str]] = set()
    for item in candidates:
        category = str(item.get("insurance_category") or "")
        batch_id = str(item.get("batch_id") or "")
        product_id = str(item.get("product_id") or "")
        fingerprint = str(item.get("template_fingerprint") or "")
        if not category or not batch_id or not product_id or not fingerprint:
            continue
        key = (batch_id, product_id)
        if key in structured_keys or key in reviewed:
            continue
        candidate_keys_by_category[category].add(key)
        queued_product_keys.add(key)
        candidate_documents_by_category[category] += 1
        candidate_templates_by_category[category].add(fingerprint)
        queue_groups[(category, fingerprint)].append(item)

    categories = []
    for category in sorted(category_batches, key=lambda value: CATEGORY_PRIORITY.get(value, 99)):
        batches = category_batches[category]
        stats = public_stats.get(
            category,
            {
                "content_batches": 0,
                "records": 0,
                "records_with_documents": 0,
                "records_with_verified_benefits": 0,
            },
        )
        raw_batches = sum((raw_dir / f"{batch_id}-text.json").is_file() for batch_id in batches)
        reviewed_count = sum(batch_id == key[0] for key in reviewed for batch_id in batches)
        if not stats["content_batches"] and not raw_batches:
            status = "blocked_missing_documents"
        elif candidate_keys_by_category[category]:
            status = "ready_for_structuring"
        elif stats["records_with_verified_benefits"]:
            status = "partially_structured"
        else:
            status = "needs_candidate_rules"
        categories.append(
            {
                "insurance_category": category,
                "official_batch_count": len(batches),
                "content_batch_count": stats["content_batches"],
                "raw_text_batch_count": raw_batches,
                "record_count": stats["records"],
                "records_with_documents": stats["records_with_documents"],
                "records_with_verified_benefits": stats[
                    "records_with_verified_benefits"
                ],
                "reviewed_record_count": reviewed_count,
                "candidate_document_count": candidate_documents_by_category[category],
                "candidate_product_count": len(candidate_keys_by_category[category]),
                "candidate_template_count": len(candidate_templates_by_category[category]),
                "status": status,
            }
        )

    queue = []
    for (category, fingerprint), items in queue_groups.items():
        product_keys = {
            (str(item.get("batch_id") or ""), str(item.get("product_id") or ""))
            for item in items
        }
        batch_ids = sorted({key[0] for key in product_keys})
        sample_products = []
        for item in items:
            name = str(item.get("product_name") or "")
            if name and name not in sample_products:
                sample_products.append(name)
            if len(sample_products) >= 3:
                break
        queue.append(
            {
                "queue_id": f"{category}:{fingerprint}",
                "insurance_category": category,
                "template_fingerprint": fingerprint,
                "candidate_document_count": len(items),
                "candidate_product_count": len(product_keys),
                "batch_ids": batch_ids,
                "companies": sorted(
                    {str(item.get("company") or "") for item in items if item.get("company")}
                ),
                "sample_products": sample_products,
                "status": "pending_template_review",
                "dedupe_key": "batch_id + product_id",
            }
        )

    queue.sort(
        key=lambda item: (
            CATEGORY_PRIORITY.get(item["insurance_category"], 99),
            -item["candidate_product_count"],
            -item["candidate_document_count"],
            item["template_fingerprint"],
        )
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": {
            "official_batch_count": len(catalog),
            "category_count": len(category_batches),
            "candidate_document_count": sum(
                item["candidate_document_count"] for item in queue
            ),
            "candidate_product_count": len(queued_product_keys),
            "queue_group_count": len(queue),
        },
        "rules": {
            "version_key": "batch_id + product_id",
            "promotion_gate": (
                "Every promoted schedule must preserve source hashes and receive explicit "
                "review metadata. Keyword matches alone are not verified benefits."
            ),
            "public_safety": (
                "The queue is local-only. Public files may contain reviewed schedules and "
                "short evidence references, never full extracted terms text."
            ),
        },
        "categories": categories,
        "queue": queue,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "data" / "batch-plan.json")
    parser.add_argument(
        "--content-dir", type=Path, default=ROOT / "data" / "tii" / "document-content"
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=ROOT / "work" / "tii-document-text"
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=ROOT / "work" / "tii-benefit-candidates" / "all-life-v3.json",
    )
    parser.add_argument(
        "--reviewed-dir", type=Path, default=ROOT / "data" / "tii" / "reviewed-benefits"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "work" / "tii-benefit-candidates" / "structure-queue.json",
    )
    args = parser.parse_args()
    payload = build_queue(
        plan_path=args.plan,
        content_dir=args.content_dir,
        raw_dir=args.raw_dir,
        candidates_path=args.candidates,
        reviewed_dir=args.reviewed_dir,
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ok",
                **payload["scope"],
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

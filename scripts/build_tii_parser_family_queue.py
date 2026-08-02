#!/usr/bin/env python3
"""Group unresolved life products into exact-version parser work families."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from tii_workflow_guard import (
    IntegrationLock,
    atomic_write_json,
    canonical_integration_lock,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDS = ROOT / "work" / "tii-life-calculation-readiness" / "records.jsonl"
DEFAULT_OUTPUT = (
    ROOT / "work" / "tii-life-calculation-readiness" / "parser-family-queue.json"
)
DEFAULT_SOURCE_GAPS_DIR = ROOT / "work" / "tii-benefit-candidates"
TARGET_STATUS = "needs_parser_or_proposal"
WORK_TYPE_PRIORITY = {
    "benefit_parser": 1,
    "additional_terms_review": 2,
    "endorsement_review": 3,
    "source_text_recovery": 4,
}
INSURANCE_CATEGORY_PRIORITY = {
    "健康保險": 1,
    "傷害保險": 2,
    "傳統型壽險": 3,
    "投資型壽險": 4,
    "傳統型年金": 5,
    "投資型年金": 6,
}
REVISION_SUFFIX_PATTERNS = (
    re.compile(
        r"[（(]\s*第[^）)]{0,40}(?:次)?(?:部份|部分)?"
        r"(?:變更|修訂|改版)[^）)]*[）)]\s*$"
    ),
    re.compile(r"[（(]\s*第[^）)]{0,40}次[^）)]*[）)]\s*$"),
)


def normalize_family_name(value: str) -> str:
    name = unicodedata.normalize("NFKC", value or "").strip()
    previous = None
    while name and name != previous:
        previous = name
        for pattern in REVISION_SUFFIX_PATTERNS:
            name = pattern.sub("", name).strip()
    return " ".join(name.split())


def work_type_for_name(product_name: str) -> str:
    if "批註條款" in product_name:
        return "endorsement_review"
    if "附加條款" in product_name:
        return "additional_terms_review"
    return "benefit_parser"


def family_fingerprint(
    *,
    batch_id: str,
    insurance_category: str,
    work_type: str,
    family_name: str,
) -> str:
    canonical = json.dumps(
        {
            "batch_id": batch_id,
            "insurance_category": insurance_category,
            "work_type": work_type,
            "family_name": family_name,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def load_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if (
                isinstance(record, dict)
                and record.get("calculation_status") == TARGET_STATUS
            ):
                records.append(record)
    return records


def load_source_gaps(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    gaps: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.exists():
        return gaps
    for source_path in sorted(path.glob("*source-gaps.json")):
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        batch_id = str(payload.get("batch_id") or "")
        for gap in payload.get("gaps") or []:
            if not isinstance(gap, dict):
                continue
            product_id = str(gap.get("product_id") or "")
            if (
                batch_id
                and product_id
                and gap.get("status") == "source_pending"
            ):
                gaps[(batch_id, product_id)] = {
                    "reason_code": str(gap.get("reason_code") or ""),
                    "reason": str(gap.get("reason") or ""),
                    "next_action": str(gap.get("next_action") or ""),
                    "source_gap_path": str(source_path),
                }
    return gaps


def build_queue(
    records: list[dict[str, Any]],
    source_gaps: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_gaps = source_gaps or {}
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for record in records:
        batch_id = str(record.get("batch_id") or "")
        product_id = str(record.get("product_id") or "")
        insurance_category = str(record.get("insurance_category") or "")
        product_name = str(record.get("product_name") or "")
        family_name = normalize_family_name(product_name)
        if not batch_id or not product_id or not family_name:
            continue
        work_type = (
            "source_text_recovery"
            if (batch_id, product_id) in source_gaps
            else work_type_for_name(product_name)
        )
        grouped[(batch_id, insurance_category, work_type, family_name)].append(
            record
        )

    groups = []
    work_type_record_counts: Counter[str] = Counter()
    work_type_group_counts: Counter[str] = Counter()
    for (
        batch_id,
        insurance_category,
        work_type,
        family_name,
    ), family_records in grouped.items():
        family_records.sort(key=lambda item: str(item.get("product_id") or ""))
        product_ids = [
            str(record.get("product_id") or "") for record in family_records
        ]
        coverage_term_counts: Counter[str] = Counter()
        group_source_gaps = []
        for record in family_records:
            coverage_term_counts.update(
                str(term)
                for term in record.get("coverage_terms") or []
                if str(term)
            )
            source_gap = source_gaps.get(
                (
                    str(record.get("batch_id") or ""),
                    str(record.get("product_id") or ""),
                )
            )
            if source_gap:
                group_source_gaps.append(
                    {
                        "product_id": str(
                            record.get("product_id") or ""
                        ),
                        **source_gap,
                    }
                )
        fingerprint = family_fingerprint(
            batch_id=batch_id,
            insurance_category=insurance_category,
            work_type=work_type,
            family_name=family_name,
        )
        groups.append(
            {
                "queue_id": f"parser-family:{fingerprint}",
                "family_fingerprint": fingerprint,
                "work_type": work_type,
                "batch_id": batch_id,
                "insurance_category": insurance_category,
                "company": str(family_records[0].get("company") or ""),
                "family_name": family_name,
                "record_count": len(family_records),
                "product_ids": product_ids,
                "coverage_term_counts": dict(coverage_term_counts.most_common()),
                **(
                    {"source_gaps": group_source_gaps}
                    if group_source_gaps
                    else {}
                ),
                "sample_versions": [
                    {
                        "product_id": str(record.get("product_id") or ""),
                        "product_name": str(record.get("product_name") or ""),
                        "edition_label": str(record.get("edition_label") or ""),
                        "summary_path": str(record.get("summary_path") or ""),
                    }
                    for record in family_records[:5]
                ],
                "version_boundary": (
                    "This is a work-planning family only. Every proposal and "
                    "promotion must preserve exact source_batch_id + product_id "
                    "+ source document SHA-256."
                ),
                "next_action": (
                    "Implement one deterministic benefit parser and generate an "
                    "exact product slice."
                    if work_type == "benefit_parser"
                    else "Recover an exact machine-readable official source or "
                    "perform page-level OCR plus visual verification; do not "
                    "infer the schedule from adjacent product versions."
                    if work_type == "source_text_recovery"
                    else "Determine whether the terms change benefits, limits, "
                    "eligibility, or only administrative/investment mechanics; "
                    "link to the applicable base contract without inventing a "
                    "standalone payout."
                ),
            }
        )
        work_type_record_counts[work_type] += len(family_records)
        work_type_group_counts[work_type] += 1

    groups.sort(
        key=lambda item: (
            WORK_TYPE_PRIORITY[item["work_type"]],
            INSURANCE_CATEGORY_PRIORITY.get(
                item["insurance_category"],
                999,
            ),
            -item["record_count"],
            item["batch_id"],
            item["family_name"],
        )
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "target_status": TARGET_STATUS,
        "version_boundary": (
            "Groups accelerate parser design only. They never merge product "
            "versions and never authorize proposal approval or promotion."
        ),
        "record_count": sum(item["record_count"] for item in groups),
        "group_count": len(groups),
        "multi_version_group_count": sum(
            item["record_count"] >= 2 for item in groups
        ),
        "records_in_multi_version_groups": sum(
            item["record_count"] for item in groups if item["record_count"] >= 2
        ),
        "large_group_count": sum(item["record_count"] >= 10 for item in groups),
        "records_in_large_groups": sum(
            item["record_count"] for item in groups if item["record_count"] >= 10
        ),
        "work_type_record_counts": dict(work_type_record_counts),
        "work_type_group_counts": dict(work_type_group_counts),
        "groups": groups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--source-gaps-dir",
        type=Path,
        default=DEFAULT_SOURCE_GAPS_DIR,
    )
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    records_path = args.records if args.records.is_absolute() else ROOT / args.records
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    source_gaps_dir = (
        args.source_gaps_dir
        if args.source_gaps_dir.is_absolute()
        else ROOT / args.source_gaps_dir
    )
    with IntegrationLock(
        canonical_integration_lock(ROOT),
        purpose="build_tii_parser_family_queue",
        owner="build_tii_parser_family_queue.py",
    ):
        payload = build_queue(
            load_records(records_path),
            load_source_gaps(source_gaps_dir),
        )
        if args.limit is not None:
            payload["groups"] = payload["groups"][: max(args.limit, 0)]
            payload["output_group_count"] = len(payload["groups"])
        atomic_write_json(output_path, payload)
    print(
        json.dumps(
            {
                "status": "ok",
                "record_count": payload["record_count"],
                "group_count": payload["group_count"],
                "multi_version_group_count": payload[
                    "multi_version_group_count"
                ],
                "records_in_multi_version_groups": payload[
                    "records_in_multi_version_groups"
                ],
                "large_group_count": payload["large_group_count"],
                "records_in_large_groups": payload["records_in_large_groups"],
                "work_type_record_counts": payload["work_type_record_counts"],
                "output": str(output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

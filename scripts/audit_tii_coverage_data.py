#!/usr/bin/env python3
"""Audit TII records for verified benefit amounts and keyword-only summaries."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "tii-policy-results.json"
SUMMARY_DIR = ROOT / "data" / "tii" / "document-summaries"
TARGET_TERMS = ("給付項目", "保險範圍", "保險金", "住院", "手術", "醫療費用")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def coverage_terms(record: dict[str, Any]) -> set[str]:
    for item in record.get("reader_focus") or []:
        if isinstance(item, dict) and item.get("key") == "coverage":
            return {term for term in item.get("terms") or [] if isinstance(term, str)}
    return set()


def all_coverage_entries(record: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        entry
        for entry in record.get("coverage_entries") or []
        if isinstance(entry, dict)
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


def is_verified_entry(entry: dict[str, Any]) -> bool:
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
    has_policy_recorded_cap = (
        calculation_basis in {
            "reimbursement_with_cap",
            "percentage_of_actual_expense_with_cap",
        }
        and entry.get("basis") == "policy_recorded_limit"
        and (
            calculation_basis == "reimbursement_with_cap"
            or (
                isinstance(entry.get("rate_percent"), (int, float))
                and not isinstance(entry.get("rate_percent"), bool)
                and entry["rate_percent"] > 0
            )
        )
    )
    return (
        (
            has_amount
            or has_percentage_formula
            or has_multiplier_formula
            or has_policy_recorded_cap
        )
        and entry.get("source") == "terms"
        and bool(entry.get("source_ref"))
    )


def verified_field_flags(record: dict[str, Any]) -> dict[str, bool]:
    entries = [entry for entry in all_coverage_entries(record) if is_verified_entry(entry)]
    texts = [
        " ".join(
            str(entry.get(field) or "")
            for field in ("name", "note", "calculation_basis", "basis", "source_ref")
        )
        for entry in entries
    ]

    return {
        "給付項目": bool(entries),
        "保險範圍": bool(entries),
        "保險金": bool(entries),
        "住院": any("住院" in text for text in texts),
        "手術": any("手術" in text for text in texts),
        "醫療費用": any(
            "醫療" in text or "reimbursement" in text or "實支實付" in text
            for text in texts
        ),
    }


def build_audit() -> dict[str, Any]:
    master = read_json(MASTER_PATH)
    total_records = int(master.get("record_count") or 0)
    summary_paths = sorted(SUMMARY_DIR.glob("*.json"))

    summary_records = 0
    actual_present = {term: 0 for term in TARGET_TERMS}
    keyword_present = {term: 0 for term in TARGET_TERMS}
    records_with_verified_benefits = 0
    summaries_missing_all_terms = 0
    summaries_with_all_terms = 0

    for path in summary_paths:
        payload = read_json(path)
        records = payload.get("records") or []
        summary_records += len(records)

        for record in records:
            if not isinstance(record, dict):
                continue

            terms = coverage_terms(record)
            matched_terms = terms.intersection(TARGET_TERMS)
            for term in matched_terms:
                keyword_present[term] += 1
            if not matched_terms:
                summaries_missing_all_terms += 1
            if all(term in terms for term in TARGET_TERMS):
                summaries_with_all_terms += 1

            flags = verified_field_flags(record)
            if flags["給付項目"]:
                records_with_verified_benefits += 1
            for term, is_present in flags.items():
                if is_present:
                    actual_present[term] += 1

    if summary_records > total_records:
        raise ValueError(
            f"Summary records ({summary_records}) exceed master records ({total_records})."
        )

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "definitions": {
            "verified_benefit": (
                "A coverage entry with a numeric amount or a calculable terms formula, "
                "source=terms, and source_ref."
            ),
            "keyword_summary": (
                "An exact term in reader_focus.coverage.terms; this is not proof of an amount."
            ),
        },
        "scope": {
            "total_tii_records": total_records,
            "document_summary_records": summary_records,
            "records_without_document_summary": total_records - summary_records,
            "summary_files": len(summary_paths),
            "life_summary_files": sum(path.name.startswith("tii-life-") for path in summary_paths),
            "property_summary_files": sum(
                path.name.startswith("tii-property-") for path in summary_paths
            ),
        },
        "actual_structured_benefits": {
            "records_with_verified_benefits": records_with_verified_benefits,
            "records_without_verified_benefits": total_records - records_with_verified_benefits,
            "present_by_field": actual_present,
            "missing_by_field": {
                term: total_records - actual_present[term] for term in TARGET_TERMS
            },
        },
        "keyword_only_document_summaries": {
            "present_by_field_among_summaries": keyword_present,
            "missing_by_field_among_summaries": {
                term: summary_records - keyword_present[term] for term in TARGET_TERMS
            },
            "missing_by_field_across_all_tii_records": {
                term: total_records - keyword_present[term] for term in TARGET_TERMS
            },
            "summary_records_missing_all_six_terms": summaries_missing_all_terms,
            "summary_records_with_all_six_terms": summaries_with_all_terms,
        },
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON report. The report is always printed.",
    )
    args = parser.parse_args()

    audit = build_audit()
    rendered = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output:
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

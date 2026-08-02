#!/usr/bin/env python3
"""Audit whether TII life products can produce user-facing benefit numbers."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from tii_workflow_guard import (
    IntegrationLock,
    atomic_write_json,
    atomic_write_jsonl,
    atomic_write_text,
    canonical_integration_lock,
)


ROOT = Path(__file__).resolve().parents[1]
TAIPEI_TZ = timezone(timedelta(hours=8))

DEFAULT_RECORDS_ROOT = ROOT / "data" / "tii" / "records" / "life"
DEFAULT_SUMMARY_DIR = ROOT / "data" / "tii" / "document-summaries"
DEFAULT_REVIEWED_DIR = ROOT / "data" / "tii" / "reviewed-benefits"
DEFAULT_PROPOSALS_DIR = ROOT / "work" / "tii-benefit-proposals"
DEFAULT_QUEUE_DIR = ROOT / "work" / "tii-completion-queues"
DEFAULT_SOURCE_GAPS_DIR = ROOT / "work" / "tii-benefit-candidates"
DEFAULT_OUTPUT = ROOT / "docs" / "TII_LIFE_CALCULATION_READINESS.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "TII_LIFE_CALCULATION_READINESS.md"
DEFAULT_RECORDS_OUTPUT = ROOT / "work" / "tii-life-calculation-readiness" / "records.jsonl"
DEFAULT_GROUPS_OUTPUT = ROOT / "work" / "tii-life-calculation-readiness" / "groups.json"

USER_INPUT_SELECTION_TYPES = {
    "face_amount",
    "face_amount_plan",
    "fixed",
    "multi_unit",
    "paid_premium_factor_plan",
    "plan",
    "plan_unit",
    "unit",
}
POLICY_STATE_SELECTION_TYPES = {
    "account_value",
    "policy_state",
}
USER_CALCULABLE_BASES = {
    "fixed_amount",
    "percentage_of_base",
    "plan_schedule_lookup",
    "per_unit",
    "per_unit_per_day",
    "per_day",
    "reimbursement_with_cap",
    "percentage_of_actual_expense_with_cap",
    "table_multiplier",
    "tiered_or_stepped",
    "additional_benefit",
    "aggregate_cap",
    "annuity_face_amount_schedule",
}
POLICY_STATE_BASES = {
    "account_value",
    "account_value_annuity_factor",
    "annuity_amount_or_lump_sum",
    "greater_of",
    "maturity_policy_account_value",
    "net_amount_at_risk_plus_policy_account_value",
    "paid_premium_factor_account_value_formula",
    "policy_state_amount",
    "policy_value_component",
    "policy_value_plus_general_and_accidental_insurance_amount",
    "policy_value_plus_general_insurance_amount",
    "sum_policy_state_amounts",
    "death_or_funeral_greater_of",
    "policy_year_tiered_premium_or_face_amount",
    "policy_year_greater_of_face_reserve_premium_with_offset",
    "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset",
    "maturity_greater_of_face_and_premium_with_offset",
    "waiver",
}
POLICY_STATE_BASIS_VALUES = {
    "hospital_daily_amount",
    "policy_account_value",
    "policy_premium",
    "policy_recorded_limit",
}
DIRECT_AMOUNT_BASES = {
    "fixed_amount",
    "per_day",
    "per_unit",
    "per_unit_per_day",
    "additional_benefit",
}
CLAIM_SCENARIO_GAP_BASES = {
    "per_day": "days_not_applied_to_claim_total",
    "per_unit_per_day": "days_not_applied_to_claim_total",
    "reimbursement_with_cap": "actual_expense_not_applied_to_claim_total",
    "percentage_of_actual_expense_with_cap": "actual_expense_not_applied_to_claim_total",
    "tiered_or_stepped": "benefit_tier_selection_not_modeled",
}


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    return atomic_write_jsonl(path, rows)


def report_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def batch_sort_key(batch_id: str) -> tuple[str, int, str]:
    prefix, _, suffix = batch_id.rpartition("-")
    try:
        number = int(suffix)
    except ValueError:
        number = 999999
    return prefix, number, batch_id


def load_life_records(records_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(records_root.glob("*.json")):
        payload = read_json(path)
        shard = path.stem
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            batch_id = str(record.get("source_batch_id") or "")
            product_id = str(record.get("product_id") or "")
            if not batch_id or not product_id:
                continue
            records.append(
                {
                    **record,
                    "_record_shard": str(path.relative_to(ROOT)),
                    "_record_shard_id": shard,
                }
            )
    return records


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


def summary_terms(record: dict[str, Any]) -> list[str]:
    for focus in record.get("reader_focus") or []:
        if isinstance(focus, dict) and focus.get("key") == "coverage":
            return [
                str(term)
                for term in focus.get("terms") or []
                if isinstance(term, str) and term
            ]
    return []


def load_summary_index(summary_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    summary_index: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(summary_dir.glob("tii-life-*.json")):
        payload = read_json(path)
        batch_id = str(payload.get("batch_id") or path.stem)
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            product_id = str(record.get("product_id") or "")
            if not product_id:
                continue
            summary_index[(batch_id, product_id)] = {
                "summary_path": str(path.relative_to(ROOT)),
                "coverage_terms": summary_terms(record),
                "coverage_tags": record.get("coverage_tags") or [],
            }
    return summary_index


def load_reviewed_index(reviewed_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    reviewed: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(reviewed_dir.glob("tii-life-*.json")):
        payload = read_json(path)
        batch_id = str(payload.get("batch_id") or path.stem)
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            product_id = str(record.get("product_id") or "")
            if product_id:
                reviewed[(batch_id, product_id)] = {**record, "_reviewed_path": str(path.relative_to(ROOT))}
    return reviewed


def load_proposal_index(proposals_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    proposals: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(proposals_dir.glob("tii-life-*.json")):
        try:
            payload = read_json(path)
        except Exception:
            continue
        batch_id = str(payload.get("batch_id") or path.stem)
        for proposal in payload.get("proposals") or []:
            if not isinstance(proposal, dict):
                continue
            product_id = str(proposal.get("product_id") or "")
            if not product_id:
                continue
            candidates = [
                candidate
                for candidate in proposal.get("candidates") or []
                if isinstance(candidate, dict)
            ]
            indexed = {
                "proposal_path": report_path(path),
                "status": str(proposal.get("status") or ""),
                "candidate_count": int(proposal.get("candidate_count") or len(candidates)),
                "generated_at": str(payload.get("generated_at") or ""),
                "extractor_version": str(payload.get("extractor_version") or ""),
                "parser_ids": sorted(
                    {
                        str(candidate.get("parser_id") or "")
                        for candidate in candidates
                        if candidate.get("parser_id")
                    }
                ),
                "source_files": sorted(
                    {
                        str(candidate.get("source_file") or "")
                        for candidate in candidates
                        if candidate.get("source_file")
                    }
                ),
                "candidates": [
                    {
                        "parser_id": str(candidate.get("parser_id") or ""),
                        "source_file": str(candidate.get("source_file") or ""),
                        "source_document_sha256": str(
                            candidate.get("source_document_sha256") or ""
                        ),
                        "schedule_sha256": str(candidate.get("schedule_sha256") or ""),
                    }
                    for candidate in candidates
                ],
            }
            key = (batch_id, product_id)
            current = proposals.get(key)
            if current is None or (
                indexed["generated_at"],
                indexed["extractor_version"],
                indexed["proposal_path"],
            ) > (
                current["generated_at"],
                current["extractor_version"],
                current["proposal_path"],
            ):
                proposals[key] = indexed
    return proposals


def load_source_gap_index(
    source_gaps_dir: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    gaps: dict[tuple[str, str], dict[str, Any]] = {}
    if not source_gaps_dir.exists():
        return gaps
    for path in sorted(source_gaps_dir.glob("*source-gaps.json")):
        try:
            payload = read_json(path)
        except Exception:
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
                    "source_pending_reason": str(
                        gap.get("reason_code") or ""
                    ),
                    "next_action": str(
                        gap.get("next_action") or ""
                    ),
                    "processing_gate": (
                        "needs_exact_readable_source_or_verified_ocr"
                    ),
                    "source_gap_path": report_path(path),
                }
    return gaps


def load_queue_rows(queue_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for filename in ["pending-structure-records.jsonl", "source-pending-records.jsonl"]:
        path = queue_dir / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                batch_id = str(row.get("batch_id") or "")
                product_id = str(row.get("product_id") or "")
                if batch_id and product_id:
                    rows[(batch_id, product_id)] = row
    return rows


def has_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def required_inputs_from_reviewed(record: dict[str, Any], entries: list[dict[str, Any]]) -> set[str]:
    inputs: set[str] = set()
    selection_type = str(record.get("selection_type") or record.get("input_mode") or "")
    if selection_type in {"face_amount"}:
        inputs.add("basic_face_amount")
    elif selection_type == "face_amount_plan":
        inputs.update({"basic_face_amount", "plan"})
    elif selection_type == "paid_premium_factor_plan":
        inputs.update(
            {
                "plan",
                "paid_premium_total",
                "partial_termination_amount_total",
                "policy_account_value",
                "specified_factor",
            }
        )
    elif selection_type in {"unit", "multi_unit"}:
        inputs.add("units")
    elif selection_type == "plan":
        inputs.add("plan")
    elif selection_type == "plan_unit":
        inputs.update({"plan", "units"})
    elif selection_type == "account_value":
        inputs.add("policy_account_value")

    characteristics = record.get("version_characteristics")
    if isinstance(characteristics, dict):
        for item in characteristics.get("required_policy_inputs") or []:
            if isinstance(item, str) and item:
                inputs.add(item)

    for entry in entries:
        basis = str(entry.get("basis") or "")
        calculation_basis = str(entry.get("calculation_basis") or "")
        explicit_policy_state_keys = [
            key
            for key in entry.get("policy_state_keys") or []
            if isinstance(key, str) and key
        ]
        inputs.update(explicit_policy_state_keys)
        inputs.update(
            str(entry.get(field) or "")
            for field in (
                "quantity_state_key",
                "expense_state_key",
                "rate_state_key",
                "rate_condition_state_key",
                "tier_selection_state_key",
                "exclusion_state_key",
                "cumulative_paid_state_key",
            )
            if str(entry.get(field) or "")
        )
        if entry.get("minor_account_value_return_age"):
            inputs.add("insured_age_at_event")
        text = " ".join(
            str(entry.get(field) or "")
            for field in ("id", "name", "basis", "calculation_basis", "note", "source_ref")
        )
        if (
            calculation_basis in {"percentage_of_base", "table_multiplier"}
            or (
                calculation_basis == "tiered_or_stepped"
                and not entry.get("amount_tiers")
            )
        ):
            inputs.add("base_amount")
        if calculation_basis in {"per_unit", "per_unit_per_day"}:
            inputs.add("units")
        if calculation_basis == "per_day" and not entry.get("quantity_state_key"):
            inputs.add("days")
        if calculation_basis == "plan_schedule_lookup":
            inputs.add("plan")
        if calculation_basis in {"account_value", "account_value_annuity_factor"} or basis == "policy_account_value":
            inputs.add("policy_account_value")
        if calculation_basis == "account_value_annuity_factor":
            inputs.add("annuity_factor")
        if (
            not explicit_policy_state_keys
            and (
                calculation_basis == "greater_of"
                or calculation_basis == "death_or_funeral_greater_of"
                or "取其大" in text
                or "取最大" in text
            )
        ):
            inputs.update({"current_insured_amount", "policy_value_reserve", "paid_premium_total"})
        if basis == "hospital_daily_amount":
            inputs.add("hospital_daily_amount")
        if basis == "policy_recorded_limit" and not explicit_policy_state_keys:
            inputs.add("policy_recorded_limit")
        if basis == "policy_premium" or "保費" in text:
            inputs.add("premium_or_paid_premium")
        if calculation_basis == "waiver" or "豁免" in text:
            inputs.add("unexpired_premium")
        if (
            calculation_basis
            in {"reimbursement_with_cap", "percentage_of_actual_expense_with_cap"}
            and not entry.get("expense_state_key")
        ):
            inputs.add("actual_medical_expense")
    return inputs


def entry_bucket(entry: dict[str, Any]) -> str:
    calculation_basis = str(entry.get("calculation_basis") or "")
    basis = str(entry.get("basis") or "")
    if has_positive_number(entry.get("amount")):
        return "direct_amount"
    if any(
        has_positive_number(tier.get("amount"))
        for tier in entry.get("amount_tiers") or []
        if isinstance(tier, dict)
    ):
        return "terms_formula"
    if entry.get("policy_state_keys"):
        return "requires_policy_state"
    if calculation_basis in POLICY_STATE_BASES or basis in POLICY_STATE_BASIS_VALUES:
        return "requires_policy_state"
    if calculation_basis in USER_CALCULABLE_BASES:
        if calculation_basis == "percentage_of_base" and entry.get("rate_state_key"):
            return "terms_formula"
        if any(
            has_positive_number(entry.get(field))
            for field in (
                "rate",
                "rate_percent",
                "rate_min",
                "rate_min_percent",
                "rate_max",
                "rate_max_percent",
                "multiplier",
            )
        ):
            return "terms_formula"
        if calculation_basis in DIRECT_AMOUNT_BASES:
            return "terms_formula_missing_amount"
        if calculation_basis in {
            "plan_schedule_lookup",
            "reimbursement_with_cap",
            "percentage_of_actual_expense_with_cap",
            "tiered_or_stepped",
            "aggregate_cap",
        }:
            return "terms_formula"
    if calculation_basis == "unknown":
        return "unknown"
    return "not_calculable"


def claim_scenario_gap_reasons(entries: list[dict[str, Any]]) -> list[str]:
    reasons = set()
    for entry in entries:
        calculation_basis = str(entry.get("calculation_basis") or "")
        if (
            calculation_basis in {"per_day", "per_unit_per_day"}
            and not entry.get("quantity_state_key")
        ):
            reasons.add("days_not_applied_to_claim_total")
        if (
            calculation_basis
            in {"reimbursement_with_cap", "percentage_of_actual_expense_with_cap"}
            and not entry.get("expense_state_key")
            and not (
                str(entry.get("basis") or "") == "annual_limit"
                and str(entry.get("aggregation_rule") or "") == "cumulative_cap"
            )
        ):
            reasons.add("actual_expense_not_applied_to_claim_total")
        if (
            calculation_basis == "percentage_of_base"
            and not has_positive_number(entry.get("rate"))
            and not has_positive_number(entry.get("rate_percent"))
            and not entry.get("rate_state_key")
            and (
                has_positive_number(entry.get("rate_min"))
                or has_positive_number(entry.get("rate_min_percent"))
                or has_positive_number(entry.get("rate_max"))
                or has_positive_number(entry.get("rate_max_percent"))
            )
        ):
            reasons.add("benefit_rate_or_grade_selection_not_modeled")
    cash_payout_entries = [
        entry
        for entry in entries
        if str(entry.get("result_kind") or "cash_payout") == "cash_payout"
        and str(entry.get("amount_role") or "payout") not in {"limit", "reference"}
    ]
    if entries and not cash_payout_entries:
        reasons.add("no_cash_payout_formula")
    return sorted(reasons)


def classify_reviewed(record: dict[str, Any]) -> dict[str, Any]:
    entries = all_coverage_entries(record)
    buckets = Counter(entry_bucket(entry) for entry in entries)
    selection_type = str(record.get("selection_type") or record.get("input_mode") or "unknown")
    required_inputs = sorted(required_inputs_from_reviewed(record, entries))
    has_numeric_or_formula = any(
        buckets[bucket] > 0
        for bucket in ["direct_amount", "terms_formula", "requires_policy_state"]
    )
    has_policy_state = buckets["requires_policy_state"] > 0 or selection_type in POLICY_STATE_SELECTION_TYPES
    has_user_selection = selection_type in USER_INPUT_SELECTION_TYPES or bool(required_inputs)
    claim_gaps = claim_scenario_gap_reasons(entries)

    if not entries or not has_numeric_or_formula:
        status = "structured_unresolved"
        next_action = "Review the promoted schedule: it exists, but no calculable coverage entry was detected."
    elif has_policy_state:
        status = "structured_needs_policy_state"
        next_action = "Expose required policy-state fields in the user flow and calculate only after the user provides them."
    elif has_user_selection:
        status = "structured_user_input_calculable"
        next_action = "Ready for user calculation once the user enters plan, units, face amount, days, or expenses."
    else:
        status = "structured_direct_calculable"
        next_action = "Ready to display terms-owned benefit numbers without extra user policy-state input."

    return {
        "calculation_status": status,
        "next_action": next_action,
        "coverage_entry_count": len(entries),
        "entry_buckets": dict(sorted(buckets.items())),
        "selection_type": selection_type,
        "required_user_inputs": required_inputs,
        "coverage_schedule_ready": bool(entries and has_numeric_or_formula),
        "claim_scenario_ready": bool(
            entries and has_numeric_or_formula and not claim_gaps
        ),
        "claim_scenario_gap_reasons": claim_gaps,
        "reviewed_path": record.get("_reviewed_path") or "",
        "parser_id": record.get("parser_id") or "",
        "source_file": record.get("source_file") or "",
        "source_document_sha256": record.get("source_document_sha256") or "",
        "schedule_sha256": record.get("schedule_sha256") or "",
        "reviewed_at": record.get("reviewed_at") or "",
    }


def proposal_supersedes_reviewed(
    reviewed: dict[str, Any],
    proposal: dict[str, Any] | None,
) -> bool:
    if not proposal or proposal.get("status") != "proposed":
        return False
    reviewed_source_file = str(reviewed.get("source_file") or "")
    reviewed_source_sha = str(reviewed.get("source_document_sha256") or "")
    reviewed_schedule_sha = str(reviewed.get("schedule_sha256") or "")
    if not reviewed_source_sha or not reviewed_schedule_sha:
        return False
    for candidate in proposal.get("candidates") or []:
        candidate_source_file = str(candidate.get("source_file") or "")
        if (
            reviewed_source_file
            and candidate_source_file
            and candidate_source_file != reviewed_source_file
        ):
            continue
        if candidate.get("source_document_sha256") != reviewed_source_sha:
            continue
        candidate_schedule_sha = str(candidate.get("schedule_sha256") or "")
        if candidate_schedule_sha and candidate_schedule_sha != reviewed_schedule_sha:
            return True
    return False


def classify_reviewed_upgrade(
    reviewed: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    result = classify_reviewed(reviewed)
    result.update(
        {
            "calculation_status": "reviewable_upgrade_pending",
            "next_action": (
                "Source-review the newer exact-source schedule before replacing the "
                "currently reviewed calculation contract."
            ),
            "proposal": proposal,
        }
    )
    return result


def classify_unreviewed(
    key: tuple[str, str],
    summary_index: dict[tuple[str, str], dict[str, Any]],
    proposal_index: dict[tuple[str, str], dict[str, Any]],
    queue_rows: dict[tuple[str, str], dict[str, Any]],
    source_gap_index: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_gap_index = source_gap_index or {}
    proposal = proposal_index.get(key)
    summary = summary_index.get(key)
    queue_row = queue_rows.get(key) or {}
    if proposal and proposal.get("status") == "proposed":
        return {
            "calculation_status": "reviewable_proposal_pending",
            "next_action": "Source-review the proposal against exact source_batch_id + product_id + source document before promotion.",
            "proposal": proposal,
            "coverage_terms": (summary or {}).get("coverage_terms") or [],
            "summary_path": (summary or {}).get("summary_path") or "",
        }
    source_gap = source_gap_index.get(key)
    if source_gap:
        return {
            "calculation_status": "source_pending",
            "next_action": source_gap["next_action"],
            "source_pending_reason": source_gap[
                "source_pending_reason"
            ],
            "processing_gate": source_gap["processing_gate"],
            "source_gap_path": source_gap["source_gap_path"],
            "coverage_terms": (
                (summary or {}).get("coverage_terms") or []
            ),
            "summary_path": (
                (summary or {}).get("summary_path") or ""
            ),
        }
    if summary:
        return {
            "calculation_status": "needs_parser_or_proposal",
            "next_action": "Implement or extend deterministic parser rules from official terms; do not infer amounts from keyword summaries.",
            "coverage_terms": summary.get("coverage_terms") or [],
            "summary_path": summary.get("summary_path") or "",
            "priority": queue_row.get("priority") or "",
        }
    return {
        "calculation_status": "source_pending",
        "next_action": queue_row.get("next_recommended_action")
        or "Backfill or manually review official source terms for this exact version.",
        "source_pending_reason": queue_row.get("source_pending_reason") or "",
        "processing_gate": queue_row.get("processing_gate") or "",
    }


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": str(record.get("source_batch_id") or ""),
        "product_id": str(record.get("product_id") or ""),
        "company": str(record.get("company") or ""),
        "insurance_category": str(record.get("insurance_category") or ""),
        "product_name": str(record.get("product_name") or ""),
        "sale_status": str(record.get("sale_status") or ""),
        "sale_date": str(record.get("sale_date") or ""),
        "discontinued_date": str(record.get("discontinued_date") or ""),
        "edition_label": str(record.get("edition_label") or ""),
        "detail_saved": bool(record.get("detail_saved")),
        "detail_source_file": str(record.get("detail_source_file") or ""),
        "record_shard": str(record.get("_record_shard") or ""),
    }


def add_group_sample(group: dict[str, Any], row: dict[str, Any]) -> None:
    samples = group.setdefault("sample_products", [])
    if len(samples) >= 5:
        return
    samples.append(
        {
            "batch_id": row["batch_id"],
            "product_id": row["product_id"],
            "company": row["company"],
            "insurance_category": row["insurance_category"],
            "product_name": row["product_name"],
            "edition_label": row["edition_label"],
        }
    )


def status_sort_rank(status: str) -> int:
    return {
        "reviewable_upgrade_pending": 0,
        "reviewable_proposal_pending": 1,
        "needs_parser_or_proposal": 2,
        "structured_unresolved": 3,
        "source_pending": 4,
        "structured_needs_policy_state": 5,
        "structured_user_input_calculable": 6,
        "structured_direct_calculable": 7,
    }.get(status, 9)


def build_audit(
    *,
    records_root: Path,
    summary_dir: Path,
    reviewed_dir: Path,
    proposals_dir: Path,
    queue_dir: Path,
    source_gaps_dir: Path,
    records_output: Path,
    groups_output: Path,
) -> dict[str, Any]:
    records = load_life_records(records_root)
    summary_index = load_summary_index(summary_dir)
    reviewed_index = load_reviewed_index(reviewed_dir)
    proposal_index = load_proposal_index(proposals_dir)
    queue_rows = load_queue_rows(queue_dir)
    source_gap_index = load_source_gap_index(source_gaps_dir)

    rows: list[dict[str, Any]] = []
    category_counts: dict[str, Counter[str]] = defaultdict(Counter)
    input_counts: Counter[str] = Counter()
    source_gate_counts: Counter[str] = Counter()
    batch_groups: dict[tuple[str, str, str], dict[str, Any]] = {}

    for record in records:
        key = (str(record.get("source_batch_id") or ""), str(record.get("product_id") or ""))
        row = compact_record(record)
        reviewed = reviewed_index.get(key)
        proposal = proposal_index.get(key)
        if reviewed and proposal_supersedes_reviewed(reviewed, proposal):
            row.update(classify_reviewed_upgrade(reviewed, proposal))
        elif reviewed:
            row.update(classify_reviewed(reviewed))
        else:
            row.update(
                classify_unreviewed(
                    key,
                    summary_index,
                    proposal_index,
                    queue_rows,
                    source_gap_index,
                )
            )

        status = str(row["calculation_status"])
        category = row["insurance_category"]
        batch_id = row["batch_id"]
        category_counts[category][status] += 1
        for item in row.get("required_user_inputs") or []:
            input_counts[str(item)] += 1
        if row.get("processing_gate"):
            source_gate_counts[str(row.get("processing_gate"))] += 1

        group_key = (status, category, batch_id)
        group = batch_groups.setdefault(
            group_key,
            {
                "queue_id": f"{status}:{category}:{batch_id}",
                "calculation_status": status,
                "batch_id": batch_id,
                "insurance_category": category,
                "company_counts": Counter(),
                "record_count": 0,
                "required_user_input_counts": Counter(),
                "source_pending_reason_counts": Counter(),
                "processing_gate_counts": Counter(),
                "next_action": row.get("next_action") or "",
            },
        )
        group["record_count"] += 1
        group["company_counts"][row["company"]] += 1
        for item in row.get("required_user_inputs") or []:
            group["required_user_input_counts"][str(item)] += 1
        if row.get("source_pending_reason"):
            group["source_pending_reason_counts"][str(row.get("source_pending_reason"))] += 1
        if row.get("processing_gate"):
            group["processing_gate_counts"][str(row.get("processing_gate"))] += 1
        add_group_sample(group, row)
        rows.append(row)

    for group in batch_groups.values():
        group["company_counts"] = dict(group["company_counts"].most_common(5))
        group["required_user_input_counts"] = dict(group["required_user_input_counts"].most_common())
        group["source_pending_reason_counts"] = dict(group["source_pending_reason_counts"].most_common())
        group["processing_gate_counts"] = dict(group["processing_gate_counts"].most_common())

    group_list = sorted(
        batch_groups.values(),
        key=lambda item: (
            status_sort_rank(str(item["calculation_status"])),
            -int(item["record_count"]),
            batch_sort_key(str(item["batch_id"])),
        ),
    )
    write_jsonl(records_output, rows)
    write_json(groups_output, {"generated_at": now_iso(), "groups": group_list})

    status_counts = Counter(str(row["calculation_status"]) for row in rows)
    calculable_count = (
        status_counts["structured_direct_calculable"]
        + status_counts["structured_user_input_calculable"]
        + status_counts["structured_needs_policy_state"]
    )
    unresolved_count = len(rows) - calculable_count
    claim_scenario_ready_count = sum(
        bool(row.get("claim_scenario_ready"))
        and str(row.get("calculation_status") or "").startswith("structured_")
        for row in rows
    )
    category_summary = {}
    for category, counts in sorted(category_counts.items()):
        total = sum(counts.values())
        ready = (
            counts["structured_direct_calculable"]
            + counts["structured_user_input_calculable"]
            + counts["structured_needs_policy_state"]
        )
        category_summary[category] = {
            "total": total,
            "ready_for_user_number_flow": ready,
            "coverage_schedule_ready": ready,
            "claim_scenario_ready": sum(
                bool(row.get("claim_scenario_ready"))
                and str(row.get("calculation_status") or "").startswith("structured_")
                and row.get("insurance_category") == category
                for row in rows
            ),
            "unresolved": total - ready,
            "ready_rate": round(ready / total, 4) if total else 0,
            "status_counts": dict(sorted(counts.items())),
        }

    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "goal": "All life-insurance product versions should produce benefit numbers after collecting the inputs required by official terms, or have a clear unresolved reason.",
        "version_boundary": "source_batch_id + product_id + source document",
        "scope": {
            "life_records": len(rows),
            "reviewed_benefit_versions": len(reviewed_index),
            "document_summary_versions": len(summary_index),
            "reviewable_proposal_versions": len(proposal_index),
        },
        "status_definitions": {
            "structured_direct_calculable": "Reviewed terms provide benefit numbers or formulas that can display without policy-state inputs.",
            "structured_user_input_calculable": "Reviewed terms can calculate after the user enters plan, units, face amount, days, or expenses.",
            "structured_needs_policy_state": "Reviewed terms can calculate only after policy-state values such as account value, reserve, paid premium, declared rate, or annuity factor are supplied.",
            "structured_unresolved": "A reviewed schedule exists, but the audit cannot detect calculable coverage entries; inspect parser output.",
            "reviewable_upgrade_pending": "A newer exact-source proposed schedule differs from the reviewed calculation contract and requires source review before replacement.",
            "reviewable_proposal_pending": "A proposed exact-source schedule exists but has not been source-reviewed and promoted.",
            "needs_parser_or_proposal": "Official source summary exists, but deterministic parser/proposal coverage is missing.",
            "source_pending": "No usable exact source text exists for the version; source backfill, verified OCR, or manual source review is required.",
        },
        "completion": {
            "ready_for_user_number_flow": calculable_count,
            "coverage_schedule_ready": calculable_count,
            "claim_scenario_ready": claim_scenario_ready_count,
            "coverage_schedule_only": calculable_count - claim_scenario_ready_count,
            "unresolved": unresolved_count,
            "ready_rate": round(calculable_count / len(rows), 4) if rows else 0,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "category_summary": category_summary,
        "required_user_input_counts": dict(input_counts.most_common()),
        "source_processing_gate_counts": dict(source_gate_counts.most_common()),
        "outputs": {
            "records_jsonl": str(records_output.relative_to(ROOT)),
            "groups_json": str(groups_output.relative_to(ROOT)),
        },
        "next_groups": group_list[:20],
    }


def build_markdown(audit: dict[str, Any]) -> str:
    completion = audit["completion"]
    lines = [
        "# TII Life Calculation Readiness",
        "",
        f"- Generated at: `{audit['generated_at']}`",
        f"- Version boundary: `{audit['version_boundary']}`",
        "",
        "## Goal",
        "",
        audit["goal"],
        "",
        "## Completion",
        "",
        f"- Ready for user number flow: `{completion['ready_for_user_number_flow']}`",
        f"- Coverage schedule ready: `{completion['coverage_schedule_ready']}`",
        f"- Claim scenario total ready: `{completion['claim_scenario_ready']}`",
        f"- Coverage schedule only: `{completion['coverage_schedule_only']}`",
        f"- Unresolved: `{completion['unresolved']}`",
        f"- Ready rate: `{completion['ready_rate']}`",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in audit["status_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Category Summary", ""])
    lines.append("| Category | Total | Ready | Unresolved | Ready rate |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for category, item in audit["category_summary"].items():
        lines.append(
            f"| {category} | {item['total']} | {item['ready_for_user_number_flow']} | "
            f"{item['unresolved']} | {item['ready_rate']} |"
        )
    lines.extend(["", "## Most Common Required Inputs", ""])
    for key, count in list(audit["required_user_input_counts"].items())[:20]:
        lines.append(f"- `{key}`: `{count}`")
    lines.extend(["", "## Next Groups", ""])
    for group in audit["next_groups"][:20]:
        lines.append(
            "- "
            f"`{group['queue_id']}`: `{group['record_count']}` records. "
            f"{group.get('next_action') or ''}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-root", type=Path, default=DEFAULT_RECORDS_ROOT)
    parser.add_argument("--summary-dir", type=Path, default=DEFAULT_SUMMARY_DIR)
    parser.add_argument("--reviewed-dir", type=Path, default=DEFAULT_REVIEWED_DIR)
    parser.add_argument("--proposals-dir", type=Path, default=DEFAULT_PROPOSALS_DIR)
    parser.add_argument("--queue-dir", type=Path, default=DEFAULT_QUEUE_DIR)
    parser.add_argument(
        "--source-gaps-dir",
        type=Path,
        default=DEFAULT_SOURCE_GAPS_DIR,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--records-output", type=Path, default=DEFAULT_RECORDS_OUTPUT)
    parser.add_argument("--groups-output", type=Path, default=DEFAULT_GROUPS_OUTPUT)
    args = parser.parse_args()

    with IntegrationLock(
        canonical_integration_lock(ROOT),
        purpose="audit_tii_life_calculation_readiness",
        owner="audit_tii_life_calculation_readiness.py",
    ):
        audit = build_audit(
            records_root=args.records_root,
            summary_dir=args.summary_dir,
            reviewed_dir=args.reviewed_dir,
            proposals_dir=args.proposals_dir,
            queue_dir=args.queue_dir,
            source_gaps_dir=args.source_gaps_dir,
            records_output=args.records_output,
            groups_output=args.groups_output,
        )
        write_json(args.output, audit)
        atomic_write_text(args.markdown_output, build_markdown(audit))
    print(
        json.dumps(
            {
                "status": "ok",
                "life_records": audit["scope"]["life_records"],
                "ready_for_user_number_flow": audit["completion"]["ready_for_user_number_flow"],
                "unresolved": audit["completion"]["unresolved"],
                "ready_rate": audit["completion"]["ready_rate"],
                "status_counts": audit["status_counts"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

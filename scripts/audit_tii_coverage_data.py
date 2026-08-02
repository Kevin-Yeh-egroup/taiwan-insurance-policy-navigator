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
REVIEWED_BENEFITS_DIR = ROOT / "data" / "tii" / "reviewed-benefits"
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


def reviewed_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(REVIEWED_BENEFITS_DIR.glob("*.json")):
        payload = read_json(path)
        for record in payload.get("records") or []:
            if isinstance(record, dict):
                records.append(record)
    return records


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
    has_policy_state_formula = (
        calculation_basis
        in {
            "account_value",
            "account_value_annuity_factor",
            "annuity_amount_or_lump_sum",
            "greater_of",
            "policy_state_amount",
            "sum_policy_state_amounts",
            "death_or_funeral_greater_of",
            "waiver",
            "maturity_policy_account_value",
            "policy_value_component",
            "policy_value_plus_general_insurance_amount",
            "policy_value_plus_general_and_accidental_insurance_amount",
            "protected_amount_plus_policy_account_value",
            "net_amount_at_risk_plus_policy_account_value",
            "paid_premium_factor_account_value_formula",
            "policy_year_tiered_premium_or_face_amount",
            "policy_year_greater_of_face_reserve_premium_with_offset",
            "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset",
            "maturity_greater_of_face_and_premium_with_offset",
        }
        and entry.get("basis")
        in {
            "policy_account_value",
            "policy_premium",
            "policy_recorded_limit",
        }
        and (
            calculation_basis
            not in {
                "greater_of",
                "policy_state_amount",
                "sum_policy_state_amounts",
                "death_or_funeral_greater_of",
            }
            or bool(entry.get("policy_state_keys"))
            or calculation_basis == "greater_of"
        )
    )
    return (
        (
            has_amount
            or has_percentage_formula
            or has_multiplier_formula
            or has_policy_recorded_cap
            or has_policy_state_formula
        )
        and entry.get("source") == "terms"
        and bool(entry.get("source_ref"))
    )


def reviewed_amount_bucket(entry: dict[str, Any]) -> str:
    amount = entry.get("amount")
    if isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0:
        return "direct_amount"

    calculation_basis = entry.get("calculation_basis")
    basis = entry.get("basis")
    has_formula_value = any(
        isinstance(entry.get(field), (int, float))
        and not isinstance(entry.get(field), bool)
        and entry[field] > 0
        for field in (
            "rate",
            "rate_percent",
            "rate_min",
            "rate_min_percent",
            "rate_max",
            "rate_max_percent",
            "multiplier",
        )
    )
    if calculation_basis in {
        "percentage_of_base",
        "table_multiplier",
        "tiered_or_stepped",
        "plan_schedule_lookup",
    } and has_formula_value:
        return "terms_formula"
    if calculation_basis in {
        "account_value",
        "account_value_annuity_factor",
        "annuity_amount_or_lump_sum",
        "greater_of",
        "policy_state_amount",
        "sum_policy_state_amounts",
            "death_or_funeral_greater_of",
            "policy_year_tiered_premium_or_face_amount",
            "policy_year_greater_of_face_reserve_premium_with_offset",
            "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset",
            "maturity_greater_of_face_and_premium_with_offset",
            "policy_year_average_target_premium_account_value_addition",
            "policy_year_average_basic_premium_account_value_addition",
            "waiver",
    }:
        return "requires_policy_state"
    if basis in {"policy_recorded_limit", "hospital_daily_amount", "policy_premium", "policy_account_value"}:
        return "requires_policy_state"
    return "not_numeric_or_table_detail"


def reviewed_benefit_audit() -> dict[str, Any]:
    records = reviewed_records()
    amount_buckets = {
        "direct_amount": 0,
        "terms_formula": 0,
        "requires_policy_state": 0,
        "not_numeric_or_table_detail": 0,
    }
    selection_modes: dict[str, int] = {}
    field_dependencies: dict[str, int] = {}
    records_with_direct_amount = 0
    records_requiring_policy_state = 0
    records_with_any_structured_entries = 0

    def add_dependency(key: str) -> None:
        field_dependencies[key] = field_dependencies.get(key, 0) + 1

    policy_state_dependency_labels = {
        "policy_account_value": "保單帳戶價值",
        "benefit_valuation_policy_account_value": "給付評價日保單帳戶價值",
        "benefit_valuation_basic_premium_policy_account_value":
            "給付評價日基本保費保單帳戶價值",
        "annuity_start_policy_account_value":
            "年金開始日保單帳戶價值",
        "annuity_payment_amount": "保險公司列示年金給付金額",
        "excess_annuity_reserve_return_amount":
            "年金開始時超額帳戶價值返還額",
        "unpaid_annuity_balance": "未支領年金餘額",
        "maturity_policy_account_value": "滿期時保單帳戶價值",
        "maturity_basic_premium_policy_account_value":
            "滿期時基本保費保單帳戶價值",
        "maturity_interest_amount": "保險公司列示之祝壽金利息",
        "current_policy_amount": "當年度保險金額",
        "basic_face_amount": "基本保額",
        "current_threshold_face_amount": "目前門檻保額",
        "death_benefit_status": "身故給付適用狀態",
        "minor_death_benefit_status": "未成年身故給付生效狀態",
        "remaining_funeral_benefit_limit": "本保單可用喪葬費用剩餘額度",
        "insured_age_at_event": "事故時被保險人年齡",
    }

    for record in records:
        selection_type = str(record.get("selection_type") or record.get("input_mode") or "unknown")
        selection_modes[selection_type] = selection_modes.get(selection_type, 0) + 1
        entries = all_coverage_entries(record)
        if entries:
            records_with_any_structured_entries += 1
        record_has_direct_amount = False
        record_requires_policy_state = False
        record_dependencies: set[str] = set()
        for entry in entries:
            bucket = reviewed_amount_bucket(entry)
            amount_buckets[bucket] += 1
            if bucket == "direct_amount":
                record_has_direct_amount = True
            if bucket == "requires_policy_state":
                record_requires_policy_state = True
            calculation_basis = entry.get("calculation_basis")
            basis = entry.get("basis")
            text = " ".join(
                str(entry.get(field) or "")
                for field in ("id", "name", "basis", "calculation_basis", "note")
            )
            if bucket == "requires_policy_state":
                explicit_policy_state_keys = [
                    key
                    for key in entry.get("policy_state_keys") or []
                    if isinstance(key, str) and key
                ]
                for key in explicit_policy_state_keys:
                    record_dependencies.add(
                        policy_state_dependency_labels.get(key, key)
                    )
                if entry.get("minor_account_value_return_age"):
                    record_dependencies.add("事故時被保險人年齡")
                if calculation_basis in {"account_value", "account_value_annuity_factor"} or basis == "policy_account_value":
                    record_dependencies.add("保單帳戶價值")
                if calculation_basis == "account_value_annuity_factor":
                    record_dependencies.add("年金給付金額/年金因子")
                if "增值回饋" in text or "宣告利率" in text or "預定利率" in text:
                    record_dependencies.update({"前一年度末保單價值準備金", "宣告利率", "預定利率"})
                if (
                    not explicit_policy_state_keys
                    and (
                        calculation_basis == "greater_of"
                        or calculation_basis == "death_or_funeral_greater_of"
                        or "取其大" in text
                        or "取最大" in text
                    )
                ):
                    record_dependencies.update({"當年度保險金額", "保單價值準備金", "保費總和"})
                if basis == "hospital_daily_amount":
                    record_dependencies.add("保單記載住院日額")
                if basis == "policy_recorded_limit":
                    record_dependencies.add("保單記載限額/保單現況")
                if calculation_basis == "waiver" or "豁免" in text:
                    record_dependencies.add("未到期保費合計")
                if "紅利" in text:
                    record_dependencies.add("保單紅利/公司通知金額")
        if record_has_direct_amount:
            records_with_direct_amount += 1
        if record_requires_policy_state:
            records_requiring_policy_state += 1
        for dependency in record_dependencies:
            add_dependency(dependency)

    return {
        "reviewed_product_versions": len(records),
        "records_with_any_structured_entries": records_with_any_structured_entries,
        "records_with_direct_amount": records_with_direct_amount,
        "records_requiring_policy_state": records_requiring_policy_state,
        "flattened_coverage_entries": sum(amount_buckets.values()),
        "entry_amount_buckets": amount_buckets,
        "selection_modes": dict(sorted(selection_modes.items())),
        "policy_state_dependency_product_counts": dict(
            sorted(field_dependencies.items(), key=lambda item: (-item[1], item[0]))
        ),
        "interpretation": {
            "direct_amount": "條款或計畫表已提供可直接呈現的金額。",
            "terms_formula": "條款有比例、倍數或級距公式；需搭配保額、單位、計畫或條款表格呈現。",
            "requires_policy_state": "金額會隨保單帳戶價值、保價金、利率、保費、限額或事故日狀態變動，需使用者輸入或保險公司試算。",
            "not_numeric_or_table_detail": "條款目前只提供文字、非保證項目或未完整結構化的表格，不能自動算出單一金額。",
        },
    }


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

    reviewed = reviewed_benefit_audit()
    structured_records = int(reviewed["records_with_any_structured_entries"])
    records_requiring_policy_state = int(reviewed["records_requiring_policy_state"])
    structure_status_counts = {
        "calculated": max(structured_records - records_requiring_policy_state, 0),
        "needs_user_input": records_requiring_policy_state,
        "pending_structure": max(summary_records - structured_records, 0),
        "source_pending": max(total_records - summary_records, 0),
        "confirmed_no_amount": 0,
    }

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
            "structure_status": (
                "A consumer-facing grouping of whether a product can currently calculate "
                "benefits, needs user policy values, is pending benefit structuring, or "
                "still needs source text."
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
        "structure_status_counts": structure_status_counts,
        "structure_status_interpretation": {
            "calculated": "已完成條款給付項目、金額或可計算公式的結構化。",
            "needs_user_input": "已有條款公式，但需要保額、單位、計畫別或保單現況才能算出金額。",
            "pending_structure": "已有條款摘要或文件線索，但尚未整理成保障項目與金額；不代表條款沒有保障。",
            "source_pending": "目前只有商品清單或索引，尚未取得/整理可解析的官方條款內容。",
            "confirmed_no_amount": "已確認條款不提供固定或可自動計算金額；目前需人工標記。",
        },
        "reviewed_benefits": reviewed,
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
    parser.add_argument(
        "--mirror-output",
        type=Path,
        help="Optional second path that receives the identical audit payload.",
    )
    args = parser.parse_args()

    audit = build_audit()
    rendered = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output:
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    if args.mirror_output:
        mirror_path = (
            args.mirror_output
            if args.mirror_output.is_absolute()
            else ROOT / args.mirror_output
        )
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        mirror_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

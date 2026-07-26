from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION_FAILED: {message}")


def load_json(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        fail(f"missing {path}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_optional_json(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_tii_manifest(tii_results: dict) -> dict:
    manifest_path = tii_results.get("tii_manifest_path") or "data/tii/manifest.json"
    return load_optional_json(manifest_path)


def load_tii_records(tii_results: dict, tii_manifest: dict) -> list[dict]:
    inline_records = tii_results.get("records") or []
    if inline_records:
        return inline_records
    if not tii_results.get("records_are_sharded"):
        fail("TII results have no inline records and are not marked as sharded")
    if not tii_manifest:
        fail("TII results are sharded but manifest is missing")
    records: list[dict] = []
    total_record_shard_bytes = 0
    for shard in tii_manifest.get("record_shards", []):
        path = Path(shard.get("path", ""))
        if not path.exists():
            fail(f"TII record shard is missing: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        shard_records = payload.get("records") or []
        if payload.get("record_count") != len(shard_records):
            fail(f"TII record shard count mismatch: {path}")
        if shard.get("record_count") != len(shard_records):
            fail(f"TII manifest record shard count mismatch: {path}")
        total_record_shard_bytes += path.stat().st_size
        records.extend(shard_records)
    total_index_records = 0
    total_index_shard_bytes = 0
    for shard in tii_manifest.get("index_shards", []):
        path = Path(shard.get("path", ""))
        if not path.exists():
            fail(f"TII index shard is missing: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        shard_records = payload.get("records") or []
        if payload.get("record_count") != len(shard_records):
            fail(f"TII index shard count mismatch: {path}")
        if shard.get("record_count") != len(shard_records):
            fail(f"TII manifest index shard count mismatch: {path}")
        total_index_records += len(shard_records)
        total_index_shard_bytes += path.stat().st_size
    if tii_manifest.get("record_count") != len(records):
        fail("TII manifest record_count does not match record shards")
    if total_index_records != len(records):
        fail("TII compact index shard records do not match full record shards")
    if tii_results.get("record_count") != len(records):
        fail("TII result record_count does not match sharded records length")
    if tii_manifest.get("total_record_bytes") != total_record_shard_bytes:
        fail("TII manifest total_record_bytes does not match shard files")
    if tii_manifest.get("total_index_bytes") != total_index_shard_bytes:
        fail("TII manifest total_index_bytes does not match index shard files")
    return records


def validate_coverage_entries(entries: object, context: str) -> None:
    if not isinstance(entries, list) or not entries:
        fail(f"coverage entries are missing: {context}")
    allowed_fields = {
        "id",
        "name",
        "amount",
        "basis",
        "calculation_basis",
        "amount_role",
        "limit_scope",
        "aggregation_rule",
        "rate",
        "rate_percent",
        "rate_min",
        "rate_min_percent",
        "rate_max",
        "rate_max_percent",
        "multiplier",
        "unit_key",
        "amount_tiers",
        "conditions",
        "source",
        "note",
        "source_ref",
    }
    allowed_bases = {
        "per_unit",
        "policy_total",
        "daily_per_unit",
        "daily_total",
        "daily_limit",
        "per_event",
        "per_event_limit",
        "per_visit_limit",
        "per_hospitalization",
        "per_hospitalization_limit",
        "annual_limit",
        "benefit_base",
        "per_injury_limit",
        "additional_benefit",
        "face_amount",
        "policy_recorded_limit",
        "hospital_daily_amount",
        "policy_premium",
        "policy_account_value",
    }
    allowed_calculation_bases = {
        "fixed_amount",
        "percentage_of_base",
        "plan_schedule_lookup",
        "per_unit",
        "per_unit_per_day",
        "per_day",
        "reimbursement_with_cap",
        "percentage_of_actual_expense_with_cap",
        "aggregate_cap",
        "greater_of",
        "table_multiplier",
        "tiered_or_stepped",
        "additional_benefit",
        "unknown",
        "waiver",
        "account_value",
        "account_value_annuity_factor",
    }
    allowed_amount_roles = {
        "payout",
        "base",
        "limit",
        "reference",
        "premium_waiver",
        "unknown",
    }
    allowed_limit_scopes = {
        "per_policy",
        "per_event",
        "per_injury",
        "per_surgery",
        "per_procedure",
        "per_visit",
        "per_day",
        "per_hospitalization",
        "annual",
        "lifetime",
        "unknown",
    }
    allowed_aggregation_rules = {
        "separate",
        "conditional_additive",
        "choose_one",
        "highest",
        "cumulative_cap",
        "unknown",
    }
    entry_ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or not set(entry).issubset(allowed_fields):
            fail(f"coverage entry has unexpected fields: {context}")
        entry_id = entry.get("id")
        if not entry_id or entry_id in entry_ids or not entry.get("name"):
            fail(f"coverage entry identity is invalid: {context}")
        entry_ids.add(entry_id)
        amount = entry.get("amount")
        has_amount = (
            isinstance(amount, int)
            and not isinstance(amount, bool)
            and amount > 0
        )
        calculation_basis = entry.get("calculation_basis")
        has_percentage_formula = calculation_basis == "percentage_of_base" and any(
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
            )
        )
        has_greater_of_formula = calculation_basis == "greater_of" and any(
            isinstance(entry.get(field), (int, float))
            and not isinstance(entry.get(field), bool)
            and entry[field] > 0
            for field in ("rate", "rate_percent")
        )
        has_policy_recorded_greater_of = (
            calculation_basis == "greater_of"
            and amount is None
            and entry.get("basis") == "policy_recorded_limit"
        )
        has_policy_recorded_cap = (
            calculation_basis == "reimbursement_with_cap"
            and amount is None
            and entry.get("basis") == "policy_recorded_limit"
        )
        has_actual_expense_percentage_cap = (
            calculation_basis == "percentage_of_actual_expense_with_cap"
            and amount is None
            and entry.get("basis") == "policy_recorded_limit"
            and isinstance(entry.get("rate_percent"), (int, float))
            and not isinstance(entry.get("rate_percent"), bool)
            and entry["rate_percent"] > 0
        )
        has_multiplier_formula = (
            calculation_basis == "table_multiplier"
            and isinstance(entry.get("multiplier"), (int, float))
            and not isinstance(entry.get("multiplier"), bool)
            and entry["multiplier"] > 0
        )
        has_policy_recorded_unknown = (
            calculation_basis == "unknown"
            and amount is None
            and entry.get("basis") in {"policy_recorded_limit", "hospital_daily_amount"}
        )
        has_premium_waiver = (
            calculation_basis == "waiver"
            and amount is None
            and entry.get("basis") == "policy_premium"
            and entry.get("amount_role") == "premium_waiver"
            and bool(entry.get("unit_key"))
        )
        has_account_value_formula = (
            calculation_basis in {"account_value", "account_value_annuity_factor"}
            and amount is None
            and entry.get("basis") in {"policy_recorded_limit", "policy_account_value"}
            and bool(entry.get("unit_key"))
        )
        if not (
            has_amount
            or has_percentage_formula
            or has_greater_of_formula
            or has_policy_recorded_greater_of
            or has_policy_recorded_cap
            or has_actual_expense_percentage_cap
            or has_multiplier_formula
            or has_policy_recorded_unknown
            or has_premium_waiver
            or has_account_value_formula
        ):
            fail(f"coverage entry amount or calculable formula is invalid: {context}")
        if entry.get("basis") is not None and entry["basis"] not in allowed_bases:
            fail(f"coverage entry legacy basis is invalid: {context}")
        if not entry.get("basis") and not entry.get("calculation_basis"):
            fail(f"coverage entry has no calculation basis: {context}")
        if entry.get("source") != "terms":
            fail(f"coverage entry source is invalid: {context}")
        if entry.get("calculation_basis") is not None and entry["calculation_basis"] not in allowed_calculation_bases:
            fail(f"coverage entry calculation basis is invalid: {context}")
        if entry.get("amount_role") is not None and entry["amount_role"] not in allowed_amount_roles:
            fail(f"coverage entry amount role is invalid: {context}")
        if entry.get("limit_scope") is not None and entry["limit_scope"] not in allowed_limit_scopes:
            fail(f"coverage entry limit scope is invalid: {context}")
        if entry.get("aggregation_rule") is not None and entry["aggregation_rule"] not in allowed_aggregation_rules:
            fail(f"coverage entry aggregation rule is invalid: {context}")
        for rate_field in ["rate", "rate_min", "rate_max"]:
            if entry.get(rate_field) is not None and not (
                isinstance(entry[rate_field], (int, float)) and 0 < entry[rate_field] <= 10
            ):
                fail(f"coverage entry rate is invalid: {context} {rate_field}")
        for percent_field in ["rate_percent", "rate_min_percent", "rate_max_percent"]:
            if entry.get(percent_field) is not None and not (
                isinstance(entry[percent_field], (int, float)) and 0 < entry[percent_field] <= 1000
            ):
                fail(f"coverage entry percentage is invalid: {context} {percent_field}")
        if entry.get("multiplier") is not None and not (
            isinstance(entry["multiplier"], (int, float)) and entry["multiplier"] > 0
        ):
            fail(f"coverage entry multiplier is invalid: {context}")
        if entry.get("unit_key") is not None and not (
            isinstance(entry["unit_key"], str) and entry["unit_key"].strip()
        ):
            fail(f"coverage entry unit key is invalid: {context}")
        if entry.get("amount_tiers") is not None:
            tiers = entry["amount_tiers"]
            if not isinstance(tiers, list) or len(tiers) < 2:
                fail(f"coverage entry amount tiers are invalid: {context}")
            tier_labels = set()
            for tier in tiers:
                if not isinstance(tier, dict) or set(tier) != {"label", "amount"}:
                    fail(f"coverage entry amount tier fields are invalid: {context}")
                if (
                    not isinstance(tier.get("label"), str)
                    or not tier["label"].strip()
                    or tier["label"] in tier_labels
                    or not isinstance(tier.get("amount"), int)
                    or tier["amount"] <= 0
                ):
                    fail(f"coverage entry amount tier value is invalid: {context}")
                tier_labels.add(tier["label"])
        if entry.get("conditions") is not None and not (
            isinstance(entry["conditions"], str)
            or (
                isinstance(entry["conditions"], list)
                and all(isinstance(condition, str) and condition for condition in entry["conditions"])
            )
        ):
            fail(f"coverage entry conditions are invalid: {context}")


def validate_plan_options(record: dict, context: str) -> None:
    input_mode = record.get("selection_type") or record.get("input_mode")
    plan_options = record.get("plan_options")
    coverage_entries = record.get("coverage_entries")
    if record.get("selection_type") and record.get("input_mode") and record["selection_type"] != record["input_mode"]:
        fail(f"coverage selection type conflicts with input mode: {context}")
    if input_mode is None and plan_options is None and coverage_entries is None:
        return
    if input_mode not in {"face_amount", "plan", "unit", "multi_unit", "plan_unit", "fixed", "account_value", "unknown"}:
        fail(f"coverage input mode is invalid: {context}")
    if input_mode != "unknown" and record.get("selection_source") != "terms":
        fail(f"reviewed coverage input mode must declare selection_source=terms: {context}")
    if coverage_entries is not None:
        validate_coverage_entries(coverage_entries, context)
    unit_fields = record.get("unit_fields")
    if input_mode == "multi_unit":
        if not isinstance(unit_fields, list) or len(unit_fields) < 2:
            fail(f"multi-unit coverage fields are missing: {context}")
        unit_keys = set()
        for field in unit_fields:
            if not isinstance(field, dict) or set(field) != {"key", "label"}:
                fail(f"multi-unit coverage field is invalid: {context}")
            key = field.get("key")
            if not isinstance(key, str) or not key.strip() or key in unit_keys or not field.get("label"):
                fail(f"multi-unit coverage field identity is invalid: {context}")
            unit_keys.add(key)
        if not coverage_entries or any(entry.get("unit_key") not in unit_keys for entry in coverage_entries):
            fail(f"multi-unit coverage entries do not map to declared fields: {context}")
    elif unit_fields:
        fail(f"non-multi-unit coverage record should not have unit fields: {context}")
    if input_mode in {"plan", "plan_unit"}:
        if not isinstance(plan_options, list) or not plan_options:
            fail(f"plan coverage options are missing: {context}")
        plan_values = set()
        for option in plan_options:
            if not isinstance(option, dict) or set(option) != {"value", "label", "coverage_entries"}:
                fail(f"plan option fields are invalid: {context}")
            value = option.get("value")
            if not value or value in plan_values or not option.get("label"):
                fail(f"plan option identity is invalid: {context}")
            plan_values.add(value)
            validate_coverage_entries(option.get("coverage_entries"), f"{context} plan {value}")
    elif plan_options:
        fail(f"non-plan coverage record should not have plan options: {context}")

    version = record.get("version_characteristics")
    if version is not None:
        cancer_fields = {
            "cancer_initial_waiting_days",
            "cancer_reinstatement_waiting_days",
            "day_hospital_explicit",
            "disability_schedule_revision",
        }
        combined_health_fields = {
            "disease_initial_waiting_days",
            "major_disease_initial_waiting_days",
            "major_disease_reinstatement_waiting_days",
            "day_hospital_explicit",
            "post_expiry_readmission_excluded",
            "disability_schedule_revision",
        }
        combined_health_disability_term_fields = combined_health_fields | {
            "disability_term",
        }
        golden_lohas_fields = {
            "disease_initial_waiting_days",
            "disease_reinstatement_waiting_days",
            "major_disease_initial_waiting_days",
            "major_disease_reinstatement_waiting_days",
            "mild_cancer_initial_waiting_days",
            "mild_cancer_reinstatement_waiting_days",
            "day_hospital_explicit",
            "day_hospital_excluded",
            "overseas_stay_limit_days",
            "disability_schedule_revision",
        }
        golden_lohas_term_fields = golden_lohas_fields | {"disability_term"}
        golden_complete_fields = {
            "disease_initial_waiting_days",
            "disease_reinstatement_waiting_days",
            "cancer_initial_waiting_days",
            "cancer_reinstatement_waiting_days",
            "maximum_renewal_age",
            "day_hospital_explicit",
            "day_hospital_excluded",
            "disability_terminology",
            "cancer_definition_revision",
            "newborn_screening_revision",
            "reinstatement_notice_revision",
            "disability_schedule_revision",
            "missing_person_return_repayment_scope",
            "funeral_benefit_cap_reference",
        }
        new_lohas_fields = golden_lohas_fields | {
            "maximum_renewal_age",
            "reinstatement_notice_revision",
            "missing_person_return_repayment_scope",
            "funeral_benefit_cap_reference",
        }
        new_lohas_term_fields = new_lohas_fields | {"disability_term"}
        statutory_infectious_fields = {
            "disease_initial_waiting_days",
            "statutory_infectious_waiting_days",
            "maximum_renewal_age",
            "day_hospital_excluded",
            "statutory_death_rate_percent",
            "statutory_hospital_daily_rate_percent",
            "statutory_infectious_diagnosis_limit",
            "missing_person_return_rule",
        }
        farglory_kangfu_medical_fields = {
            "disease_initial_waiting_days",
            "day_hospital_excluded",
            "post_expiry_readmission_excluded",
            "nhi_uncovered_payment_rate_percent",
            "hospital_auxiliary_daily_fixed_amount",
            "hospital_consolation_daily_multiplier",
            "terms_revision",
            "insured_notice_revision",
        }
        yuanta_xiangyouxin_medical_fields = {
            "disease_initial_waiting_days",
            "renewal_disease_waiting_days",
            "day_hospital_excluded",
            "post_expiry_readmission_excluded",
            "nhi_uncovered_payment_rate_percent",
            "inpatient_medical_limit_after_60_days_multiplier",
            "outpatient_pre_admission_days",
            "outpatient_post_discharge_days",
            "maximum_renewal_age_primary_or_spouse",
            "maximum_renewal_age_child",
            "terms_revision",
            "claims_review_medical_opinion_revision",
        }
        yuanta_xiangan_medical_fields = {
            "terms_revision",
            "plan_count",
            "disease_initial_waiting_days",
            "day_hospital_excluded",
            "icu_room_limit_multiplier",
            "icu_room_limit_days",
            "inpatient_medical_limit_after_60_days_multiplier",
            "pre_admission_outpatient_days",
            "post_discharge_outpatient_days",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "non_nhi_payment_rate_percent",
            "surgery_table_min_percent",
            "surgery_table_max_percent",
            "newborn_metabolic_disease_revision",
            "claims_review_medical_opinion_revision",
        }
        yuanta_anxin100_critical_illness_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "disease_waiting_days",
            "cancer_waiting_days",
            "premium_total_multiplier",
            "specified_critical_rate_percent",
            "public_transport_accident_death_rate_percent",
            "maturity_age",
            "disability_terminology",
            "premium_waiver_disability_levels",
            "excluded_critical_illness_item_count",
        }
        yuanta_zhen_anxin_return_cancer_fields = {
            "terms_revision",
            "cancer_waiting_days",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "accidental_death_rate_percent",
            "mass_transit_accidental_death_rate_percent",
            "total_disability_benefit_formula",
            "total_disability_terminology",
            "accidental_first_degree_disability_rate_percent",
            "mass_transit_accidental_first_degree_disability_rate_percent",
            "accidental_disability_rate_min_percent",
            "accidental_disability_rate_max_percent",
            "accidental_disability_annual_cap_rate_percent",
            "accident_hospital_daily_rate_percent",
            "accident_hospital_policy_year_day_limit",
            "accident_hospital_lifetime_daily_limit_multiplier",
            "fracture_unhospitalized_daily_rate_percent",
            "fracture_table_max_days",
            "low_invasive_cancer_rate_percent",
            "initial_cancer_rate_percent",
            "initial_cancer_low_invasive_offset",
            "maturity_benefit_formula",
            "maturity_after_paid_up_years",
            "premium_multiplier",
            "face_amount_required",
            "policy_reserve_required",
            "annual_premium_total_required",
            "minor_death_or_disability_refund_rule",
            "funeral_benefit_limit_rule",
            "no_dividend",
            "health_part_no_cash_value",
        }
        yuanta_zhenai_baby_return_life_fields = {
            "product_family",
            "terms_revision",
            "approval_filing_number",
            "company_name_change_filing_number",
            "face_amount_required",
            "multiple_insured_supported",
            "unborn_child_policy",
            "insurance_benefit_basis",
            "specific_major_disability_category_count",
            "specific_major_disability_rate_percent",
            "specific_major_disability_per_category_limit_times",
            "specific_major_disability_cumulative_cap_percent",
            "cerebral_palsy_rate_percent",
            "cerebral_palsy_lifetime_limit_times",
            "major_burn_rate_percent",
            "accident_claim_days",
            "major_burn_definition_body_surface_percent",
            "survival_benefit_start_policy_anniversary",
            "survival_benefit_end_policy_anniversary",
            "survival_benefit_payment_count",
            "survival_benefit_formula",
            "survival_benefit_single_survivor_limit",
            "death_refund_formula",
            "fetal_condition_known_exclusion",
            "non_participating_policy",
        }
        yuanta_yuanman225_interest_endowment_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "regulatory_revision_date",
            "regulatory_revision_number",
            "policy_period_years",
            "expected_interest_rate_percent",
            "declared_rate_frequency",
            "value_sharing_bonus_available",
            "value_sharing_formula",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "maturity_policy_anniversary",
            "maturity_multiplier",
            "premium_multiplier",
            "policy_reserve_required",
            "annual_premium_total_required",
            "accumulated_paid_up_additions_required",
            "stored_interest_before_age_16",
            "minor_death_refund_rule",
            "funeral_benefit_limit_rule",
            "full_disability_table_item_count",
            "non_participating_policy",
        }
        yuanta_meinianduoli_usd_incremental_return_whole_life_fields = {
            "product_family",
            "terms_revision",
            "currency",
            "expected_interest_rate_percent",
            "declared_rate_frequency",
            "value_sharing_bonus_available",
            "value_sharing_formula",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "survival_benefit_during_payment_rate_percent",
            "survival_benefit_after_paid_up_annual_rate_percent",
            "monthly_survival_benefit_available",
            "maturity_age",
            "maturity_benefit_formula",
            "premium_multiplier",
            "policy_face_amount_required",
            "accumulated_paid_up_additions_required",
            "annual_insured_amount_required",
            "standard_annual_premium_required",
            "annual_premium_total_required",
            "policy_reserve_required",
            "received_survival_benefit_total_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosed",
            "no_contract_conversion_from_twd",
            "minor_death_refund_rule",
            "funeral_benefit_limit_rule",
            "disability_term",
            "non_participating_policy",
        }
        yuanta_meinianduoli_usd_incremental_return_whole_life_filing_fields = (
            yuanta_meinianduoli_usd_incremental_return_whole_life_fields
            | {
                "filing_date",
                "filing_number",
            }
        )
        yuanta_meinianduoli_usd_incremental_return_whole_life_article_2_fields = (
            yuanta_meinianduoli_usd_incremental_return_whole_life_fields
            | {
                "benefit_amount_definition_in_article_2",
            }
        )
        investment_life_guaranteed_face_amount_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "investment_linked_policy",
            "insurance_amount_basis",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "net_amount_at_risk_required",
            "investment_target_value_required",
            "redemption_valuation_timing_required",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "complete_disability_table_item_count",
            "disability_term",
            "non_participating_policy",
        }
        investment_life_guaranteed_face_amount_extended_fields = (
            investment_life_guaranteed_face_amount_fields
            | {
                "maturity_age",
                "net_amount_at_risk_formula_type",
                "basic_amount_required",
                "insurance_deduction_amount_required",
                "minor_death_before_age_15_account_value_rule",
                "minor_disability_before_age_15_account_value_rule",
            }
        )
        investment_life_guaranteed_face_amount_policy_maturity_fields = (
            investment_life_guaranteed_face_amount_extended_fields - {"maturity_age"}
        )
        prudential_legacy_investment_life_fields = (
            investment_life_guaranteed_face_amount_fields
            | {
                "payment_currency_label",
                "insurance_amount_formula",
                "maturity_age",
                "net_amount_at_risk_formula_type",
                "basic_amount_required",
                "basic_amount_formula_type",
                "minor_death_before_age_15_account_value_rule",
                "minor_disability_before_age_15_account_value_rule",
                "valuation_reference",
                "complete_disability_schedule_ref",
                "legacy_disability_wording",
                "total_disability_term",
            }
        )
        kgi_china_legacy_investment_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "investment_linked_policy",
            "insurance_amount_basis",
            "death_total_disability_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "risk_amount_required",
            "risk_amount_formula_type",
            "redemption_valuation_timing_required",
            "valuation_schedule_ref",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "premium_waiver_available",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
        }
        kgi_china_legacy_investment_life_currency_fields = (
            kgi_china_legacy_investment_life_fields | {"payment_currency_label"}
        )
        kgi_china_legacy_investment_life_waiver_fields = (
            kgi_china_legacy_investment_life_fields
            | {
                "premium_waiver_disability_levels",
                "premium_waiver_until",
            }
        )
        kgi_china_legacy_investment_life_waiver_currency_fields = (
            kgi_china_legacy_investment_life_currency_fields
            | {
                "premium_waiver_disability_levels",
                "premium_waiver_until",
            }
        )
        taiwan_xinxiangle_investment_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "investment_linked_policy",
            "insurance_type_required",
            "insurance_type_options",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "net_amount_at_risk_formula_type",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "survival_benefit_formula",
            "maturity_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "policy_account_value_required",
            "redemption_valuation_timing_required",
            "valuation_reference",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "policy_value_bonus_available",
            "policy_value_bonus_rate_percent",
            "policy_value_bonus_frequency_years",
            "policy_value_bonus_basis",
            "non_participating_policy",
        }
        taiwan_age111_variable_universal_life_base_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "filing_number",
            "investment_linked_policy",
            "variable_universal_life_policy",
            "foreign_currency_policy",
            "insurance_type_required",
            "insurance_type_options",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "death_total_disability_amount_formula",
            "net_amount_at_risk_required",
            "net_amount_at_risk_formula_type",
            "insurance_deduction_amount_required",
            "death_benefit_formula",
            "funeral_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "policy_account_value_required",
            "redemption_valuation_timing_required",
            "valuation_schedule_ref",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "policy_value_bonus_available",
            "non_participating_policy",
            "policy_dividend_available",
        }
        taiwan_age111_variable_universal_life_multiplier_fields = (
            taiwan_age111_variable_universal_life_base_fields
            | {"policy_value_multiplier_schedule"}
        )
        taiwan_age111_variable_universal_life_fixed_bonus_fields = (
            taiwan_age111_variable_universal_life_multiplier_fields
            | {
                "policy_value_bonus_type",
                "policy_value_bonus_rate_percent",
                "policy_value_bonus_basis",
            }
        )
        taiwan_age111_variable_universal_life_schedule_bonus_fields = (
            taiwan_age111_variable_universal_life_multiplier_fields
            | {
                "policy_value_bonus_type",
                "policy_value_bonus_basis",
                "policy_value_bonus_schedule",
            }
        )
        taiwan_xinfumanzai_usd_variable_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "filing_number",
            "investment_linked_policy",
            "variable_life_policy",
            "single_premium_policy",
            "foreign_currency_policy",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "death_total_disability_amount_formula",
            "net_amount_at_risk_required",
            "net_amount_at_risk_formula_type",
            "basic_amount_required",
            "death_benefit_formula",
            "funeral_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "maturity_interest_rate_source",
            "maturity_reduced_by_partial_withdrawal_or_policy_loan_offset",
            "reinstatement_excludes_maturity_benefit",
            "policy_account_value_required",
            "investment_target_value_required",
            "redemption_valuation_timing_required",
            "valuation_schedule_ref",
            "linked_investment_appendix",
            "linked_investment_type",
            "unlinked_investment_appendices",
            "account_value_return_on_time_bar",
            "guardianship_funeral_benefit_rule",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
            "policy_dividend_available",
        }
        taiwan_xinfu_life_maturity_guarantee_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "filing_number",
            "investment_linked_policy",
            "single_premium_policy",
            "foreign_currency_policy",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "net_amount_at_risk_required",
            "net_amount_at_risk_formula_type",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_benefit_formula",
            "maturity_guaranteed_amount_formula_ref",
            "maturity_income_amount_formula_ref",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "investment_target_value_required",
            "redemption_valuation_timing_required",
            "valuation_schedule_ref",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
        }
        taiwan_wudong_legacy_variable_universal_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "filing_number",
            "investment_linked_policy",
            "variable_universal_life_policy",
            "insurance_type_required",
            "insurance_type_options",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "death_total_disability_amount_formula",
            "net_amount_at_risk_required",
            "net_amount_at_risk_formula_type",
            "death_benefit_formula",
            "funeral_benefit_formula",
            "total_disability_benefit_formula",
            "terminal_illness_benefit_formula",
            "terminal_illness_rate_percent",
            "terminal_illness_survival_months_max",
            "terminal_illness_type_b_policy_value_multiplier_condition",
            "survival_benefit_formula",
            "maturity_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "policy_account_value_required",
            "redemption_valuation_timing_required",
            "valuation_reference",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_14_account_value_rule",
            "minor_disability_before_age_14_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
            "policy_dividend_available",
        }
        taiwan_wudong_legacy_variable_universal_life_minor15_fields = (
            taiwan_wudong_legacy_variable_universal_life_fields
            | {"minor_death_before_age_15_account_value_rule"}
        )
        taiwan_xindeyi_variable_universal_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "investment_linked_policy",
            "insurance_amount_basis",
            "death_total_disability_amount_formula",
            "death_benefit_formula",
            "funeral_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "face_amount_required",
            "investment_target_value_required",
            "redemption_valuation_timing_required",
            "valuation_schedule_ref",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_14_account_value_rule",
            "minor_disability_before_age_14_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
            "policy_dividend_available",
        }
        taiwan_zhiduoxin_variable_universal_life_fields = (
            taiwan_xindeyi_variable_universal_life_fields
            - {
                "minor_death_before_age_14_account_value_rule",
                "minor_disability_before_age_14_account_value_rule",
            }
            | {
                "minor_death_account_value_return_formula",
                "death_benefit_effective_age",
                "minor_death_before_age_15_account_value_rule",
                "minor_disability_before_age_15_account_value_rule",
                "mental_disability_funeral_benefit_rule",
            }
        )
        taiwan_zhangwo_variable_universal_life_fields = {
            "product_family",
            "terms_revision",
            "death_total_disability_amount_formula",
            "terminal_illness_rate_percent",
            "terminal_illness_cap_amount",
            "non_participating_policy",
        }
        china_xinchuang_variable_life_fields = {
            "product_family",
            "terms_revision",
            "death_total_disability_amount_formula",
            "maturity_benefit_formula",
            "total_disability_term",
            "non_participating_policy",
        }
        china_legacy_investment_linked_life_fields = {
            "product_family",
            "terms_revision",
            "death_total_disability_amount_formula",
            "maturity_benefit_formula",
            "investment_income_formula",
            "non_participating_policy",
        }
        fubon_xinxiangyouli_variable_life_fields = {
            "product_family",
            "terms_revision",
            "death_total_disability_amount_formula",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "maturity_benefit_formula",
            "total_disability_term",
            "non_participating_policy",
        }
        hsingfu_legacy_variable_universal_life_fields = {
            "product_family",
            "terms_revision",
            "death_total_disability_amount_formula",
            "insurance_type_options",
            "total_disability_term",
            "non_participating_policy",
        }
        global_ritai_financial_expert_investment_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "investment_linked_policy",
            "insurance_type_required",
            "insurance_type_options",
            "insurance_amount_basis",
            "death_total_disability_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "risk_amount_required",
            "risk_amount_formula_type",
            "redemption_valuation_timing_required",
            "valuation_reference",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "non_participating_policy",
        }
        global_ritai_financial_head_investment_life_fields = (
            global_ritai_financial_expert_investment_life_fields
            - {
                "minor_death_before_age_15_account_value_rule",
                "minor_disability_before_age_15_account_value_rule",
            }
            | {
                "minor_death_before_age_14_account_value_rule",
                "minor_disability_before_age_14_account_value_rule",
            }
        )
        variable_annuity_account_value_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "investment_linked_policy",
            "annuity_policy",
            "annuity_amount_formula",
            "policy_account_value_required",
            "annuity_start_date_required",
            "assumed_interest_rate_required",
            "annuity_life_table_required",
            "investment_target_value_required",
            "payment_frequency_options",
            "guarantee_period_required",
            "guarantee_period_options_years",
            "minimum_death_benefit",
            "unpaid_annuity_balance",
            "low_annual_annuity_lump_sum_rule",
            "high_annual_annuity_account_value_return_rule",
            "account_value_full_withdrawal_at_annuity_start",
            "non_participating_policy",
            "default_annuity_start_age",
            "max_annuity_start_age",
            "max_annuity_payment_age",
        }
        variable_annuity_account_value_required_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "investment_linked_policy",
            "annuity_policy",
            "annuity_amount_formula",
            "policy_account_value_required",
            "annuity_start_date_required",
            "assumed_interest_rate_required",
            "annuity_life_table_required",
            "investment_target_value_required",
            "payment_frequency_options",
            "guarantee_period_required",
            "minimum_death_benefit",
            "unpaid_annuity_balance",
            "low_annual_annuity_lump_sum_rule",
            "high_annual_annuity_account_value_return_rule",
            "non_participating_policy",
        }
        prudential_shared_generations_variable_universal_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "filing_number",
            "investment_linked_policy",
            "variable_universal_life_policy",
            "dual_insured_policy",
            "primary_insured_role",
            "secondary_insured_role",
            "insured_relationship_required",
            "basic_amount_same_for_both_insured",
            "basic_amount_max_target_premium_multiple",
            "primary_basic_amount_effective_age",
            "secondary_coverage_before_primary_age",
            "target_premium_single_payment",
            "excess_premium_allowed",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "net_amount_at_risk_required",
            "net_amount_at_risk_formula_type",
            "primary_death_before_age_25_formula",
            "primary_death_after_age_25_formula",
            "secondary_death_before_primary_age_25_formula",
            "primary_total_disability_before_age_25_formula",
            "primary_total_disability_after_age_25_formula",
            "secondary_total_disability_before_primary_age_25_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "investment_target_value_required",
            "redemption_valuation_timing_required",
            "valuation_reference",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "mental_disability_funeral_benefit_rule",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
            "policy_dividend_available",
        }
        prudential_chuangfu_variable_life_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "terms_revision",
            "investment_linked_policy",
            "insurance_amount_basis",
            "insurance_amount_formula",
            "death_total_disability_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "accumulated_premium_balance_required",
            "coverage_premium_ratio_required",
            "risk_amount_required",
            "risk_amount_formula_type",
            "investment_target_value_required",
            "redemption_valuation_timing_required",
            "valuation_reference",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "mental_disability_funeral_benefit_rule",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
            "policy_dividend_available",
        }
        prudential_youyou_legacy_investment_life_fields = (
            kgi_china_legacy_investment_life_currency_fields
            - {
                "risk_amount_formula_type",
                "valuation_schedule_ref",
            }
            | {
                "premium_waiver_disability_levels",
                "premium_waiver_until",
                "premium_waiver_schedule_ref",
            }
        )
        legacy_investment_life_face_or_account_value_fields = {
            "product_family",
            "company_group",
            "currency_basis",
            "payment_currency_label",
            "investment_linked_policy",
            "insurance_amount_basis",
            "death_total_disability_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_trigger",
            "maturity_age",
            "maturity_benefit_formula",
            "maturity_interest_crediting",
            "policy_account_value_required",
            "risk_amount_required",
            "risk_amount_formula_type",
            "redemption_valuation_timing_required",
            "valuation_schedule_ref",
            "insurance_cost_refund_after_event",
            "account_value_return_on_time_bar",
            "death_benefit_cap_rule",
            "funeral_benefit_limit_rule",
            "funeral_benefit_excludes_account_value",
            "minor_death_before_age_15_account_value_rule",
            "minor_disability_before_age_15_account_value_rule",
            "complete_disability_schedule_ref",
            "complete_disability_table_item_count",
            "legacy_disability_wording",
            "disability_term",
            "total_disability_term",
            "non_participating_policy",
        }
        hsingfu_fuyu_dwa_whole_life_fields = {
            "product_family",
            "terms_revision",
            "source_file_id",
            "partial_change_filing_date",
            "planned_interest_rate_percent",
            "declared_rate_addition_available",
            "declared_rate_frequency",
            "face_amount_formula",
            "insurance_amount_age_15_switch",
            "maturity_age",
            "death_benefit_rate_percent",
            "total_disability_benefit_rate_percent",
            "premium_waiver_disability_levels",
            "unexpired_premium_proration_included",
            "funeral_benefit_limit_rule",
            "non_participating_policy",
            "paid_up_addition_reference_required",
        }
        hsingfu_platinum_endowment_fields = {
            "product_family",
            "terms_revision",
            "filing_number",
            "latest_revision_basis",
            "annual_insured_amount_formula",
            "maturity_benefit_formula",
            "death_benefit_rate_percent",
            "total_disability_benefit_rate_percent",
            "funeral_benefit_limit_rule",
            "non_participating_policy",
            "annual_insured_amount_table_required",
        }
        yuanta_new_account_medical_fields = {
            "terms_revision",
            "disease_initial_waiting_days",
            "cancer_initial_waiting_days",
            "major_disease_initial_waiting_days",
            "day_hospital_excluded",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "face_amount_daily_multiplier",
            "medical_lifetime_cap_daily_multiplier",
            "medical_opinion_revision",
        }
        yuanta_health_life_early_fields = {
            "terms_revision",
            "disease_initial_waiting_days",
            "daily_amount_face_amount_rate_percent",
            "hospital_daily_days_limit",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "cumulative_medical_cap_daily_multiplier",
            "surgery_min_daily_multiplier",
            "surgery_max_daily_multiplier",
            "child_benefit_max_age",
            "child_specific_disease_daily_multiplier",
            "child_food_poisoning_daily_multiplier",
            "child_fracture_min_days",
            "child_fracture_max_days",
            "severe_burn_daily_multiplier",
            "moderate_burn_daily_multiplier",
            "burn_unit_daily_multiplier",
            "burn_outpatient_daily_rate_percent",
            "severe_burn_rehab_monthly_multiplier",
            "severe_burn_rehab_months_limit",
            "moderate_burn_rehab_monthly_multiplier",
            "moderate_burn_rehab_months_limit",
            "death_or_maturity_premium_rate_percent",
            "maturity_age",
            "premium_waiver_disability_levels",
            "regulatory_revision",
        }
        global_e_road_peace_overseas_illness_fields = {
            "terms_revision",
            "overseas_illness_lookback_days",
            "inpatient_claim_days_limit",
            "outpatient_limit_rate_percent",
            "emergency_limit_rate_percent",
            "non_nhi_payment_rate_percent",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "day_hospital_excluded",
            "claims_exchange_rate_basis",
            "regulatory_revision",
            "claims_medical_opinion_revision",
        }
        global_nccu_student_group_fields = {
            "terms_revision",
            "fixed_face_amount",
            "disability_levels",
            "disability_living_assistance_levels",
            "disability_living_assistance_annual_payments",
            "major_burn_rate_percent",
            "hospital_daily_days_limit",
            "fracture_daily_amount",
            "same_hospital_readmission_days",
            "non_nhi_payment_rate_percent",
            "post_expiry_accident_days_limit",
            "death_disability_annual_cap",
            "specific_accidental_death_excluded_from_cap",
            "regulatory_revision",
        }
        taiwan_taipei_student_group_fields = {
            "terms_revision",
            "disease_death_amount",
            "accidental_death_amount",
            "disease_disability_levels",
            "accident_disability_levels",
            "disability_living_assistance_levels",
            "disability_living_assistance_annual_payments",
            "hospital_daily_days_limit",
            "same_hospital_readmission_days",
            "post_accident_benefit_days_limit",
            "disease_death_disability_period_cap",
            "accidental_death_period_cap",
            "low_income_project_subsidy",
            "collective_food_poisoning_min_people",
            "facial_reconstruction_labor_disability_item",
        }
        taiwan_drug_anxin_cancer_precision_fields = {
            "terms_revision",
            "cancer_waiting_days",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "post_cancer_claim_window_years",
            "cancer_includes_carcinoma_in_situ",
            "drug_table_item_count",
            "health_promotion_renewal_discount_available",
        }
        yuanta_group_hospital_medical_fields = {
            "terms_revision",
            "plan_count",
            "disease_initial_waiting_days",
            "day_hospital_excluded",
            "day_hospital_definition_revision",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "non_nhi_payment_rate_percent",
            "inpatient_medical_limit_daily_multiplier",
            "surgery_limit_daily_multiplier",
            "insured_notice_revision",
        }
        yuanta_yuanqi_shizu_fields = {
            "terms_revision",
            "plan_count",
            "disease_initial_waiting_days",
            "renewal_disease_waiting_days",
            "cancer_screening_min_age",
            "hospital_daily_days_limit",
            "mental_hospital_days_limit",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "non_nhi_payment_rate_percent",
            "medical_device_heart_stent_annual_limit",
            "special_procedure_annual_limit",
            "surgery_table_min_percent",
            "surgery_table_max_percent",
            "insured_notice_revision",
        }
        fixed_hospital_medical_97_fields = {
            "disease_initial_waiting_days",
            "daily_hospital_days_limit",
            "intensive_care_days_limit",
            "same_hospital_readmission_days",
            "surgery_base_daily_multiplier",
            "surgery_total_cap_daily_multiplier",
            "cumulative_termination_daily_multiplier",
            "disability_terminology",
            "day_hospital_excluded",
            "post_expiry_readmission_excluded",
            "claims_review_medical_opinion_revision",
            "main_contract_forced_execution_exception",
            "terms_revision",
        }
        prudential_daily_hospital_96_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "plan_count",
            "daily_hospital_days_limit",
            "intensive_care_days_limit",
            "same_hospital_readmission_days",
            "cumulative_termination_daily_multiplier",
            "disability_terminology",
            "no_surrender_value",
        }
        china_legacy_cancer_whole_life_fields = {
            "terms_revision",
            "cancer_responsibility_start_day",
            "premium_waiver_disability_levels",
            "minor_funeral_benefit_rule",
        }
        taiwan_fishermen_group_medical_fields = {
            "terms_revision",
            "nhi_uncovered_payment_rate_percent",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "annual_hospital_daily_days_limit",
            "same_accident_deductible",
            "insured_notice_revision",
        }
        taiwan_group_long_term_care_service_fields = {
            "terms_revision",
            "long_term_care_plan_months",
            "lump_sum_face_amount_multiplier",
            "monthly_service_face_amount_multiplier",
            "unclaimed_balance_interest_rate_percent",
            "service_area_limited",
            "adl_impairment_min_items",
            "adl_assessment_months",
            "cdr_min_score",
            "service_fee_revision_notice_months",
            "service_fee_revision_limit_per_year",
            "privacy_revision",
        }
        taiwan_yiqijianzhi_specific_disease_fields = {
            "terms_revision",
            "specific_disease_waiting_days",
            "accident_exempt_waiting_period",
            "maximum_coverage_age",
            "no_claim_premium_refund_rate_percent",
            "health_promotion_discount_rate_percent",
            "installment_min_annual_amount",
            "source_terms_sha256",
        }
        taiwan_group_inpatient_limit_plan_fields = {
            "terms_revision",
            "plan_count",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "day_hospital_excluded",
            "outpatient_surgery_included",
            "nhi_paid_excluded",
            "daily_option_policy_face_page_days_limit",
            "day_hospital_definition_revision",
        }
        taiwan_gold_group_inpatient_limit_fields = {
            "terms_revision",
            "plan_count",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "day_hospital_excluded",
            "outpatient_surgery_included",
            "nhi_paid_excluded",
            "non_nhi_payment_rate_percent",
            "hospital_medical_icu_limit_multiplier",
            "hospital_daily_icu_multiplier",
            "hospital_daily_days_limit",
            "icu_daily_days_limit",
            "medical_expense_or_daily_choose_one",
            "conversion_right_after_months",
            "experience_dividend_formula",
        }
        taiwan_shishizai_inpatient_fields = {
            "filing_date",
            "filing_number",
            "disease_waiting_days",
            "guaranteed_renewal",
            "non_guaranteed_renewal_rate",
            "day_hospital_excluded",
            "hospital_days_limit",
            "mental_disease_annual_days_limit",
            "icu_or_burn_room_multiplier",
            "outpatient_surgery_annual_count_limit",
            "specified_procedure_annual_count_limit",
            "pre_hospital_outpatient_days",
            "post_discharge_outpatient_days",
            "non_nhi_payment_percent",
            "special_procedure_item_count",
        }
        fubon_golden_health_fields = {
            "terms_revision",
            "disease_initial_waiting_days",
            "same_hospital_readmission_days",
            "day_hospital_excluded",
            "post_expiry_readmission_excluded",
            "non_nhi_payment_rate_percent",
            "icu_daily_multiplier",
            "icu_daily_multiplier_days_limit",
            "hospital_daily_days_limit",
            "chronic_or_mental_annual_days_limit",
            "outpatient_medical_annual_days_limit",
            "medical_opinion_revision",
        }
        fubon_golden_luck_universal_whole_life_fields = {
            "product_family",
            "terms_revision",
            "fubon_code",
            "product_code",
            "filing_date",
            "filing_number",
            "revision_events",
            "universal_life_policy",
            "non_participating_policy",
            "declared_rate_frequency",
            "declared_rate_non_negative",
            "policy_value_reserve_formula",
            "insurance_cost_deduction_frequency",
            "premium_fee_table_required",
            "surrender_charge_table_required",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "maturity_age",
            "policy_face_amount_required",
            "policy_reserve_required",
            "paid_premium_total_required",
            "basic_premium_supported",
            "flexible_additional_premium_supported",
            "premium_payment_ratio_schedule_required",
            "installment_benefit_available",
            "installment_period_options",
            "installment_interest_rate_source",
            "minimum_specified_insurance_amount",
            "minimum_annual_installment_amount",
            "guardianship_funeral_benefit_rule",
            "funeral_benefit_limit_rule",
            "disability_schedule_item_count",
        }
        fubon_golden_medical_device_fields = {
            "terms_revision",
            "disease_initial_waiting_days",
            "maximum_coverage_age",
            "benefit_tiers_by_policy_year",
            "unit_reduction_revision",
            "all_items_paid_termination",
        }
        fubon_hsl_inpatient_fields = {
            "terms_revision",
            "disease_waiting_days",
            "day_hospital_excluded",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "non_nhi_payment_rate_percent",
            "room_daily_days_limit",
            "renewal_age_self_or_spouse",
            "renewal_age_child",
            "linked_non_deductible_medical_required",
            "newborn_metabolic_disease_exempt_waiting_period",
            "prosthetic_eye_limb_room_net_limit_multiplier",
        }
        chaoyang_xingnong_group_inpatient_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_number",
            "disease_waiting_days",
            "room_board_days_limit",
            "icu_days_limit",
            "same_accident_readmission_days",
            "social_insurance_unclaimed_payment_rate_percent",
            "surgery_table_min_percent",
            "surgery_table_max_percent",
            "experience_dividend",
        }
        chaoyang_xingnong_student_group_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_dates",
            "death_amount",
            "disability_term",
            "disability_grade_count",
            "disability_table_item_count",
            "disability_living_assistance_grades",
            "disability_living_assistance_annual_payments",
            "inpatient_medical_limit",
            "major_surgery_project_subsidy_limit",
            "major_surgery_table_item_count",
            "accident_outpatient_medical_limit",
            "accident_outpatient_minimum_expense",
            "same_hospital_readmission_days",
            "major_surgery_claim_window_years",
            "post_policy_claim_days_limit",
            "death_disability_period_cap",
        }
        prudential_china_life_accident_account_fields = {
            "terms_revision",
            "children_covered",
            "medical_rider_included",
            "hospital_daily_rider_included",
            "major_burn_rider_included",
            "disability_term",
            "accident_claim_days",
            "same_hospital_readmission_days",
            "post_expiry_readmission_excluded",
            "day_hospital_excluded",
            "non_nhi_payment_rate_percent",
            "hospital_daily_days_limit",
            "surgery_base_daily_multiplier",
            "surgery_per_hospitalization_daily_multiplier_limit",
            "surgery_table_min_percent",
            "surgery_table_max_percent",
        }
        prudential_china_life_one_three_five_accident_fields = {
            "terms_revision",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "accident_claim_days",
            "domestic_general_multiplier",
            "overseas_general_multiplier",
            "flight_multiplier",
            "same_accident_domestic_cap_multiplier",
            "same_accident_overseas_cap_multiplier",
            "same_accident_flight_cap_multiplier",
        }
        prudential_group_specific_accident_rider_fields = {
            "terms_revision",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "accident_claim_days",
            "general_specific_multiplier",
            "flight_multiplier",
            "same_accident_general_specific_cap_multiplier",
            "same_accident_flight_cap_multiplier",
        }
        prudential_fire_mass_transit_accident_fields = {
            "terms_revision",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "accident_claim_days",
            "fire_accident_multiplier",
            "land_water_mass_transit_multiplier",
            "same_accident_fire_cap_multiplier",
            "same_accident_land_water_mass_transit_cap_multiplier",
            "cumulative_fire_disability_cap_multiplier",
            "cumulative_land_water_mass_transit_disability_cap_multiplier",
        }
        taiwan_qianwan_chuxing_a_accident_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_number",
            "revision_basis",
            "maximum_coverage_age",
            "death_benefit_premium_total_rate_percent",
            "accident_claim_days",
            "air_or_train_mass_transit_accidental_death_multiplier",
            "water_or_nontrain_land_mass_transit_accidental_death_multiplier",
            "automobile_passenger_accidental_death_multiplier",
            "other_accidental_death_multiplier",
            "major_burn_rate_percent",
            "major_burn_lifetime_limit_times",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "installment_death_benefit_available",
        }
        taiwan_qianwan_chuxing_b_endowment_fields = {
            *taiwan_qianwan_chuxing_a_accident_fields,
            "maturity_age",
            "maturity_benefit_premium_total_rate_percent",
        }
        fubon_xianganbao_accident_medical_rider_fields = {
            "terms_revision",
            "fubon_code",
            "accident_claim_days",
            "overseas_medical_treatment_days_limit",
            "non_nhi_payment_rate_percent",
            "medical_icu_burn_center_limit_rate_percent",
            "medical_reimbursement_nhi_excess_only",
            "duplicate_reimbursement_excluded",
            "dislocation_base_amount",
            "dislocation_table_item_count",
            "dislocation_rate_min_percent",
            "dislocation_rate_max_percent",
        }
        yuanta_new_accident_medical_rider_fields = {
            "terms_revision",
            "yuanta_code",
            "accident_claim_days",
            "non_nhi_payment_rate_percent",
            "medical_reimbursement_nhi_excess_only",
            "policy_recorded_limit_label",
        }
        yuanta_personal_accident_rider_fields = {
            "terms_revision",
            "filing_signal",
            "accident_claim_days",
            "maximum_renewal_age",
            "child_maximum_renewal_age",
            "minor_death_premium_refund_before_age",
            "funeral_benefit_limit_rule",
            "death_benefit_rate_percent",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "major_burn_rate_percent",
            "major_burn_lifetime_limit_times",
            "death_disability_same_accident_cap",
        }
        yuanta_funxinyou_accident_medical_addendum_fields = {
            "terms_revision",
            "contract_reference",
            "accident_claim_days",
            "non_nhi_payment_rate_percent",
            "medical_reimbursement_nhi_excess_only",
            "policy_recorded_limit_label",
            "beneficiary_self_only",
        }
        fubon_family_gift_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "cancer_classification",
            "general_hospital_days_limit",
            "icu_days_limit",
            "accident_treatment_window_days",
            "accident_hospital_days_limit",
            "major_burn_survival_days",
            "disability_term",
            "disability_levels",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "same_hospital_readmission_days",
            "short_term_rate_table",
        }
        fubon_family_gift_accident_health_legacy_fields = (
            fubon_family_gift_accident_health_fields
            - {"cancer_classification", "disability_term"}
        )
        fubon_wanan_365_accident_fields = {
            "terms_revision",
            "plan_count",
            "plan_a_face_amount",
            "plan_b_face_amount",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "accident_claim_days",
            "major_burn_survival_days",
            "major_burn_rate_percent",
            "food_poisoning_annual_limit_times",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "natural_disaster_disability_min_level",
            "natural_disaster_disability_max_level",
        }
        fubon_golden_guard_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "cancer_classification",
            "cancer_discharge_recovery_days_limit",
            "cancer_radiation_days_limit_per_policy_year",
            "cancer_chemotherapy_days_limit_per_policy_year",
            "accident_claim_days",
            "major_burn_survival_days",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_tiantian_anxin_500_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "general_hospital_days_limit",
            "icu_days_limit",
            "burn_center_hospital_days_limit",
            "same_hospital_readmission_days",
            "accident_claim_days",
            "fracture_claim_days",
            "major_burn_survival_days",
            "major_burn_lifetime_limit_times",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_health_limit_up_accident_health_fields = {
            "terms_revision",
            "fubon_code",
            "fixed_terms_amount",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "general_hospital_days_limit",
            "icu_days_limit",
            "burn_center_hospital_days_limit",
            "same_hospital_readmission_days",
            "accident_claim_days",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_xinfu_life_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "cancer_waiting_days",
            "same_hospital_readmission_days",
            "general_hospital_days_limit",
            "icu_days_limit",
            "burn_center_hospital_days_limit",
            "cancer_discharge_recovery_days_limit",
            "cancer_radiation_days_limit_per_policy_year",
            "cancer_chemotherapy_days_limit_per_policy_year",
            "accident_claim_days",
            "accident_hospital_days_limit",
            "major_burn_survival_days",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_xinfu_life_accident_health_total_term_fields = (
            fubon_xinfu_life_accident_health_fields | {"total_disability_term"}
        )
        fubon_tzu_chi_marrow_group_life_medical_fields = {
            "terms_revision",
            "group_policy",
            "hospital_room_daily_limit",
            "surgery_fee_base",
            "hospital_miscellaneous_limit",
            "hospital_days_limit",
            "alternative_daily_allowance",
            "same_condition_readmission_days",
            "surgery_percentage_table",
            "total_disability_schedule_item_count",
        }
        fubon_tzu_chi_marrow_group_life_medical_total_limit_fields = (
            fubon_tzu_chi_marrow_group_life_medical_fields
            | {"hospital_total_limit"}
        )
        fubon_changanbao_life_service_fields = {
            "terms_revision",
            "terms_code",
            "service_provider",
            "service_plan_count",
            "service_table_sha1",
            "funeral_service_from_policy_year",
            "cash_conversion_allowed",
            "first_policy_year_face_amount_rate_percent",
            "second_policy_year_face_amount_rate_percent",
            "death_after_third_policy_year_face_amount_rate_percent",
            "maturity_age",
            "service_unavailable_compensation",
            "supervision_wording",
        }
        fubon_yongai_life_service_fields = {
            "terms_revision",
            "fubon_code",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_number",
            "revision_basis",
            "service_provider",
            "life_service_from_policy_year",
            "service_scope_taiwan_main_island",
            "life_service_not_cash_convertible",
            "first_policy_year_annual_face_amount_rate_percent",
            "second_policy_year_annual_face_amount_rate_percent",
            "death_after_third_year_cash_rate_percent",
            "maturity_age",
            "maturity_benefit_rate_percent",
            "service_unavailable_compensation",
            "service_shortfall_compensation_rate_percent",
            "non_participating_policy",
            "policy_loan_table_available",
        }
        taiwan_funeral_service_rider_fields = {
            "terms_revision",
            "service_provider",
            "service_option_count",
            "service_amount",
            "funeral_service_from_policy_year",
            "cash_conversion_allowed",
            "non_attributable_unavailable_cash_rate_percent",
            "attributable_unavailable_cash_rate_percent",
            "first_three_policy_year_death_premium_multiplier",
            "accidental_death_amount",
            "accidental_death_max_age",
            "accident_claim_days",
            "maturity_age",
            "funeral_benefit_limit_rule",
            "fixed_terms_amount",
        }
        taiwan_longzaitian_funeral_service_rider_fields = (
            taiwan_funeral_service_rider_fields
            - {
                "accidental_death_amount",
                "accidental_death_max_age",
                "accident_claim_days",
            }
            | {
                "product_family",
                "filing_date",
                "filing_number",
                "service_scope_taiwan_main_island",
                "service_lifetime_limit_times",
                "maturity_benefit_amount",
                "reduced_paid_up_excludes_funeral_service",
                "non_participating_policy",
            }
        )
        taiwan_longai_funeral_service_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "currency",
            "fixed_face_amount",
            "annual_insured_amount_formula",
            "service_provider",
            "service_option_count",
            "funeral_service_amount",
            "funeral_service_from_policy_year",
            "service_scope_taiwan_main_island",
            "service_lifetime_limit_times",
            "cash_conversion_allowed",
            "non_attributable_unavailable_cash_rate_percent",
            "attributable_unavailable_cash_rate_percent",
            "first_two_policy_year_death_premium_multiplier",
            "death_after_third_policy_year_cash_amount",
            "accidental_death_amount",
            "accidental_death_max_age",
            "accident_claim_days",
            "maturity_age",
            "maturity_benefit_amount",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "funeral_benefit_limit_rule",
            "reduced_paid_up_excludes_funeral_service",
            "fixed_terms_amount",
            "non_participating_policy",
        }
        taiwan_funeral_service_whole_life_early_plan_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_basis",
            "service_provider",
            "service_plan_count",
            "funeral_service_amount",
            "tower_plan_count",
            "funeral_service_from_policy_year",
            "cash_conversion_allowed",
            "non_attributable_unavailable_cash_rate_percent",
            "attributable_unavailable_cash_rate_percent",
            "first_policy_year_face_amount_rate_percent",
            "second_policy_year_face_amount_rate_percent",
            "maturity_age",
            "plan_price_includes_funeral_service",
            "service_scope_taiwan_main_island",
            "service_plan_amounts_fixed_from_table",
            "death_cash_uses_policy_reserve_floor",
            "funeral_benefit_limit_rule",
            "supervision_wording",
        }
        taiwan_funeral_service_whole_life_fields = {
            "terms_revision",
            "service_provider",
            "service_plan_count",
            "funeral_service_amount",
            "tower_plan_count",
            "funeral_service_from_policy_year",
            "cash_conversion_allowed_for_disability_or_maturity",
            "cash_conversion_allowed_for_death_exceptions",
            "non_attributable_unavailable_cash_rate_percent",
            "attributable_unavailable_cash_rate_percent",
            "maturity_age",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "plan_price_includes_funeral_service",
            "plan_price_deducted_from_life_cash_benefits",
            "service_scope_taiwan_main_island",
            "service_plan_amounts_fixed_from_table",
            "premium_total_wording",
        }
        taiwan_funeral_service_whole_life_early_tower_fields = {
            "terms_revision",
            "service_provider",
            "funeral_service_option_count",
            "funeral_service_amount",
            "tower_table_row_count",
            "tower_option_count",
            "tower_table_revision",
            "funeral_service_from_policy_year",
            "cash_conversion_allowed_for_disability_or_maturity",
            "cash_conversion_allowed_for_death_exceptions",
            "non_attributable_unavailable_cash_rate_percent",
            "attributable_unavailable_cash_rate_percent",
            "maturity_age",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "plan_price_includes_funeral_service",
            "plan_price_deducted_from_life_cash_benefits",
            "service_scope_taiwan_main_island",
            "service_plan_amounts_fixed_from_table",
            "premium_total_wording",
            "disability_terminology",
        }
        taiwan_interest_rate_whole_life_fields = {
            "terms_revision",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
        }
        taiwan_interest_rate_whole_life_statutory_infectious_fields = (
            taiwan_interest_rate_whole_life_fields
            | {
                "statutory_infectious_comfort_benefit",
                "statutory_infectious_rate_percent",
                "statutory_infectious_policy_year_limit",
                "statutory_infectious_limit_times",
            }
        )
        taiwan_fengfu_meili_usd_interest_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_available",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "statutory_infectious_comfort_benefit",
            "statutory_infectious_rate_percent",
            "statutory_infectious_policy_year_limit",
            "statutory_infectious_limit_times",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "health_surrender_value_available",
            "health_unpaid_premium_refund_available",
        }
        taiwan_yaozuan_chuanshi_usd_whole_life_cancer_health_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "payment_period_options",
            "cancer_waiting_days",
            "special_treatment_rate_percent",
            "robotic_surgery_rate_percent",
            "special_treatment_lifetime_limit_times",
            "robotic_surgery_lifetime_limit_times",
            "special_treatment_item_count",
            "robotic_surgery_system_table_required",
            "robotic_surgery_system_count",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "health_surrender_value_available",
            "health_unpaid_premium_refund_available",
        }
        taiwan_lehuo_meili_usd_whole_life_cancer_health_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "cancer_waiting_days",
            "special_treatment_benefit_formula",
            "special_treatment_lifetime_limit_times",
            "special_treatment_item_count",
            "special_treatment_payment_period_only",
            "terminal_benefits_choose_one_rule",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "health_surrender_value_available",
            "health_unpaid_premium_refund_available",
        }
        taiwan_interest_rate_specific_disease_whole_life_fields = {
            "terms_revision",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "specific_disease_waiting_days",
            "specific_disease_names",
            "specific_disease_count",
            "specific_disease_benefit_formula",
            "specific_disease_one_time_benefit",
            "specific_disease_disability_exclusive",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_min_years",
            "installment_period_max_years",
            "minimum_annual_installment_amount",
            "minimum_annual_installment_currency",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "payment_period_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "minor_death_under_15_funeral_benefit_rule",
        }
        taiwan_interest_rate_specific_disease_survival_whole_life_fields = {
            "terms_revision",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "specific_disease_waiting_days",
            "specific_disease_names",
            "specific_disease_count",
            "specific_disease_benefit_formula",
            "specific_disease_rate_percent",
            "specific_disease_one_time_benefit",
            "specific_disease_disability_exclusive",
            "total_disability_benefit_available",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_min_years",
            "installment_period_max_years",
            "minimum_annual_installment_amount",
            "minimum_annual_installment_currency",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "payment_period_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "minor_death_under_15_funeral_benefit_rule",
        }
        taiwan_interest_rate_accident_whole_life_fields = {
            "terms_revision",
            "product_family",
            "filing_date",
            "filing_number",
            "revision_filing_date",
            "revision_filing_number",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "age_16_value_sharing_special_rule",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "accidental_death_benefit_formula",
            "accidental_death_min_age_16_wording",
            "maturity_benefit_formula",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_min_years",
            "installment_period_max_years",
            "installment_interest_rate_source",
            "minimum_annual_installment_amount",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "accident_claim_days",
            "minor_death_under_15_funeral_benefit_rule",
            "guardianship_funeral_benefit_rule",
            "funeral_benefit_limit_rule",
            "policy_face_amount_required",
            "accumulated_paid_up_additions_required",
            "premium_total_required",
            "specified_insurance_amount_required_for_installment",
        }
        taiwan_chuanshi_fuli_whole_life_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_filing_date",
            "revision_filing_number",
            "revision_basis",
            "currency",
            "expected_interest_rate_schedule",
            "value_sharing_bonus",
            "age_16_value_sharing_special_rule",
            "payment_period_options",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "accidental_death_benefit_formula",
            "accidental_death_rate_percent",
            "accidental_death_min_age_16_wording",
            "total_disability_living_assistance_formula",
            "total_disability_living_assistance_rate_percent",
            "total_disability_living_assistance_max_payments",
            "maturity_benefit_formula",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_min_years",
            "installment_period_max_years",
            "installment_interest_rate_source",
            "minimum_annual_installment_amount",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "accident_claim_days",
            "minor_death_under_15_funeral_benefit_rule",
            "guardianship_funeral_benefit_rule",
            "funeral_benefit_limit_rule",
            "policy_face_amount_required",
            "policy_reserve_required",
            "policy_reserve_ratio_required",
            "policy_reserve_ratio_schedule",
            "premium_total_required",
            "premium_multiplier",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "specified_insurance_amount_required_for_installment",
        }
        taiwan_participating_whole_life_fields = {
            "terms_revision",
            "filing_number",
            "currency",
            "participating_policy",
            "policy_dividend_available",
            "policy_dividend_guaranteed",
            "annual_policy_dividend_start_year",
            "terminal_policy_dividend_available",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "terminal_illness_advance_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
        }
        taiwan_participating_return_whole_life_fields = {
            "terms_revision",
            "filing_number",
            "currency",
            "participating_policy",
            "policy_dividend_available",
            "policy_dividend_guaranteed",
            "annual_policy_dividend_start_year",
            "terminal_policy_dividend_available",
            "terminal_policy_dividend_start_year",
            "annual_insured_amount_formula",
            "survival_benefit_formula",
            "survival_benefit_basis",
            "survival_rate_min_percent",
            "survival_rate_max_percent",
            "monthly_survival_benefit_available",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "maturity_multiplier_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "terminal_illness_advance_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "payment_period_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
        }
        taiwan_term_life_fields = {
            "terms_revision",
            "filing_number",
            "currency",
            "product_form",
            "participating_policy",
            "annual_insured_amount_formula",
            "annual_insured_amount_schedule",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "premium_total_required",
            "coefficient_table_required",
            "payment_period_required",
            "insurance_period_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosure",
            "funeral_benefit_limit_rule",
            "installment_min_annual_payment",
            "installment_min_annual_payment_currency",
        }
        taiwan_simple_term_life_fields = {
            "terms_revision",
            "filing_number",
            "currency",
            "product_form",
            "participating_policy",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "unearned_premium_refund_component",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "premium_total_required",
            "coefficient_table_required",
            "payment_period_required",
            "insurance_period_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosure",
            "funeral_benefit_limit_rule",
            "renewal_mechanism",
            "expiry_conversion_right_available",
            "surrender_value_available",
        }
        taiwan_usd_no_disability_fields = {
            "terms_revision",
            "filing_number",
            "currency",
            "product_form",
            "participating_policy",
            "policy_period_years",
            "maturity_label",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "maturity_benefit_formula",
            "premium_multiplier",
            "policy_dividend_available",
            "terminal_policy_dividend_available",
            "installment_benefit_available",
            "installment_min_annual_payment",
            "installment_min_annual_payment_currency",
            "policy_face_amount_required",
            "policy_reserve_required",
            "policy_reserve_ratio_required",
            "premium_total_required",
            "coefficient_table_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosure",
            "funeral_benefit_limit_rule",
        }
        taiwan_usd_no_disability_maturity_age_fields = {
            *taiwan_usd_no_disability_fields,
            "maturity_age",
            "maturity_reference_age",
            "terminal_policy_dividend_start_policy_year",
        }
        taiwan_platinum_account_endowment_fields = {
            "product_family",
            "product_code",
            "terms_revision",
            "filing_number",
            "revision_basis",
            "universal_policy",
            "non_participating_policy",
            "insurance_amount_formula",
            "policy_value_reserve_required",
            "policy_value_reserve_formula_article",
            "maturity_benefit_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "unexpired_insurance_cost_added",
            "policy_value_reduction_offset_rule",
            "funeral_benefit_limit_rule",
        }
        taiwan_long_term_care_whole_life_fields = {
            "terms_revision",
            "filing_number",
            "currency",
            "product_form",
            "participating_policy",
            "annual_insured_amount_formula",
            "long_term_care_benefit_formula",
            "long_term_care_persistence_months",
            "long_term_care_adl_impairments_required",
            "long_term_care_cdr_min",
            "long_term_care_benefit_lifetime_limit",
            "death_benefit_formula",
            "accidental_death_benefit_formula",
            "accident_claim_days",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "coefficient_table_required",
            "payment_period_required",
            "long_term_care_claim_offset_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
        }
        taiwan_interest_rate_return_whole_life_fields = {
            "terms_revision",
            "currency",
            "expected_interest_rate_percent",
            "expected_interest_rate_schedule",
            "value_sharing_bonus",
            "annual_insured_amount_formula",
            "survival_benefit_formula",
            "survival_benefit_basis",
            "survival_rate_min_percent",
            "survival_rate_max_percent",
            "monthly_survival_benefit_available",
            "death_benefit_formula",
            "mass_transit_accidental_death_available",
            "mass_transit_accidental_death_rate_percent",
            "mass_transit_accidental_death_claim_age_limit",
            "accident_claim_days",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "maturity_multiplier_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "standard_premium_table_required",
            "payment_period_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
        }
        taiwan_interest_rate_return_whole_life_specific_cancer_fields = (
            taiwan_interest_rate_return_whole_life_fields
            | {
                "specific_cancer_benefit_available",
                "specific_cancer_rate_percent",
                "specific_cancer_waiting_days",
                "specific_cancer_lifetime_limit_times",
                "specific_cancer_basis",
            }
        )
        taiwan_interest_rate_endowment_fields = {
            "terms_revision",
            "currency",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "policy_period_years",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "installment_benefit_available",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "accumulated_paid_up_additions_required",
            "coefficient_table_required",
            "payment_period_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "minor_death_under_15_funeral_benefit_rule",
        }
        taiwan_usd_endowment_fields = {
            "terms_revision",
            "currency",
            "value_sharing_bonus",
            "policy_period_years",
            "face_amount_label",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "installment_benefit_available",
            "installment_period_min_years",
            "installment_period_max_years",
            "minimum_annual_installment_amount",
            "minimum_annual_installment_currency",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "coefficient_table_required",
            "payment_period_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "minor_death_under_15_funeral_benefit_rule",
        }
        taiwan_interest_rate_return_whole_life_legacy_fields = (
            taiwan_interest_rate_return_whole_life_fields
            - {
                "mass_transit_accidental_death_available",
                "mass_transit_accidental_death_rate_percent",
                "mass_transit_accidental_death_claim_age_limit",
                "accident_claim_days",
            }
        )
        taiwan_fixed_return_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_basis",
            "currency",
            "value_sharing_bonus",
            "annual_insured_amount_formula",
            "survival_benefit_formula",
            "survival_benefit_basis",
            "survival_rate_min_percent",
            "survival_rate_max_percent",
            "monthly_survival_benefit_available",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "reserve_component",
            "premium_component",
            "premium_multiplier",
            "post_fifth_policy_year_face_amount_multiplier",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_min_years",
            "installment_period_max_years",
            "minimum_annual_installment_amount",
            "premium_waiver_available",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "policy_reserve_ratio_required",
            "coefficient_table_required",
            "standard_premium_table_required",
            "foreign_currency_policy",
            "funeral_benefit_limit_rule",
            "minor_death_under_15_funeral_benefit_rule",
            "guardianship_funeral_benefit_rule",
        }
        taiwan_yibao_3xiang_medical_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_basis",
            "disease_waiting_days",
            "cancer_waiting_days",
            "initial_cancer_multiplier",
            "mild_cancer_multiplier",
            "severe_cancer_multiplier",
            "hospital_daily_multiplier",
            "hospital_care_fraction",
            "inpatient_surgery_specific_treatment_multiplier",
            "outpatient_surgery_specific_treatment_multiplier",
            "no_hospital_claim_bonus_rate_percent",
            "premium_refund_interest_rate_percent",
            "maturity_age",
            "premium_waiver_disability_levels",
            "medical_lifetime_cap_amount",
            "medical_lifetime_cap_currency",
            "surgery_table_required",
            "specific_treatment_table_required",
            "policy_face_amount_required",
            "life_part_insured_amount_required_for_death",
            "policy_reserve_required_for_death",
            "annual_premium_total_required",
            "health_surrender_value_available",
        }
        taiwan_yixiang_health_medical_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_basis",
            "fixed_policy_face_amount",
            "fixed_policy_face_amount_currency",
            "disease_waiting_days",
            "newborn_metabolic_disease_waiting_exception",
            "cancer_waiting_days",
            "initial_cancer_multiplier",
            "mild_cancer_multiplier",
            "severe_cancer_multiplier",
            "hospital_daily_amount",
            "hospital_daily_days_limit",
            "special_room_daily_amount",
            "special_room_days_limit",
            "inpatient_surgery_specific_treatment_amount",
            "outpatient_surgery_specific_treatment_amount",
            "no_hospital_claim_bonus_rate_percent",
            "no_hospital_claim_bonus_articles",
            "premium_refund_under_age_16_formula",
            "premium_refund_interest_available",
            "maturity_age",
            "premium_waiver_disability_levels",
            "medical_lifetime_cap_amount",
            "medical_lifetime_cap_currency",
            "surgery_table_required",
            "specific_treatment_table_required",
            "policy_face_amount_required",
            "life_part_insured_amount_required_for_death",
            "policy_reserve_required_for_death",
            "annual_premium_total_required",
            "health_surrender_value_available",
        }
        taiwan_lehuo_health_medical_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_basis",
            "fixed_policy_face_amount",
            "fixed_policy_face_amount_currency",
            "disease_waiting_days",
            "newborn_metabolic_disease_waiting_exception",
            "cancer_waiting_days",
            "initial_cancer_multiplier",
            "mild_cancer_multiplier",
            "severe_cancer_multiplier",
            "specific_disease_multiplier",
            "hospital_daily_amount",
            "hospital_daily_days_limit",
            "special_room_daily_amount",
            "special_room_days_limit",
            "inpatient_surgery_specific_treatment_amount",
            "outpatient_surgery_specific_treatment_amount",
            "medical_device_amount",
            "medical_device_multiplier",
            "no_hospital_claim_bonus_rate_percent",
            "no_hospital_claim_bonus_articles",
            "premium_refund_under_age_16_formula",
            "premium_refund_interest_available",
            "maturity_age",
            "premium_waiver_triggers",
            "premium_waiver_disability_levels",
            "medical_lifetime_cap_amount",
            "medical_lifetime_cap_currency",
            "surgery_table_required",
            "specific_treatment_table_required",
            "policy_face_amount_required",
            "life_part_insured_amount_required_for_death",
            "policy_reserve_required_for_death",
            "annual_premium_total_required",
            "health_surrender_value_available",
        }
        fubon_new_shouhu_jinnang_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "plan_1_2_maximum_renewal_age",
            "plan_3_4_maximum_renewal_age",
            "plan_5_10_maximum_renewal_age",
            "cancer_waiting_days",
            "general_hospital_days_limit",
            "icu_days_limit",
            "burn_center_hospital_days_limit",
            "same_hospital_readmission_days",
            "accident_claim_days",
            "accident_hospital_days_limit",
            "accident_outpatient_surgery_limit_times",
            "accident_reimbursement_non_nhi_rate_percent",
            "fracture_daily_rate_percent",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_new_shouhu_jinnang_late_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "general_hospital_days_limit",
            "icu_days_limit",
            "burn_center_hospital_days_limit",
            "same_hospital_readmission_days",
            "accident_claim_days",
            "accident_hospital_days_limit",
            "accident_outpatient_surgery_limit_times",
            "accident_reimbursement_non_nhi_rate_percent",
            "fracture_daily_rate_percent",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
            "day_hospital_explicit",
        }
        fubon_haozhouquan_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "general_hospital_days_limit",
            "same_hospital_readmission_days",
            "accident_claim_days",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_vision_life_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "day_hospital_excluded",
            "accident_claim_days",
            "accident_hospital_days_limit",
            "accident_icu_days_limit",
            "burn_center_days_limit",
            "accident_outpatient_surgery_limit_times",
            "fracture_daily_rate_percent",
            "major_burn_survival_days",
            "major_burn_lifetime_limit_times",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "mass_transit_additional_benefit",
            "short_term_rate_table",
        }
        fubon_anxin_financial_life_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "plan_1_3_maximum_renewal_age",
            "plan_4_5_maximum_renewal_age",
            "cancer_waiting_days",
            "major_disease_waiting_days",
            "day_hospital_explicit",
            "same_hospital_readmission_days",
            "hospital_daily_days_limit_per_policy_year_same_hospitalization",
            "icu_days_limit_per_policy_year_same_hospitalization",
            "burn_center_days_limit_per_policy_year_same_hospitalization",
            "accident_claim_days",
            "mild_cancer_lifetime_limit_times",
            "disability_term",
            "total_disability_schedule_item_count",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_new_million_heart_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "day_hospital_explicit",
            "same_hospital_readmission_days",
            "general_hospital_days_limit",
            "accident_claim_days",
            "major_burn_rate_percent",
            "major_burn_survival_days",
            "major_burn_lifetime_limit_times",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_million_heart_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "day_hospital_explicit",
            "same_hospital_readmission_days",
            "hospital_daily_days_limit_per_policy_year_same_hospitalization",
            "accident_claim_days",
            "death_disability_same_accident_cap",
            "disability_term",
            "total_disability_schedule_item_count",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_million_new_life_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "day_hospital_explicit",
            "same_hospital_readmission_days",
            "hospital_daily_days_limit_per_policy_year_same_hospitalization",
            "accident_claim_days",
            "accident_medical_limit",
            "accident_medical_daily_formula_per_10000_inpatient_only",
            "accident_medical_daily_formula_per_10000_inpatient_split",
            "accident_medical_daily_formula_per_10000_outpatient_split",
            "accident_medical_daily_formula_days_limit",
            "death_disability_same_accident_cap",
            "disability_term",
            "total_disability_schedule_item_count",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_comprehensive_accident_fields = {
            "terms_revision",
            "fubon_product_family",
            "plan_count",
            "policy_period_years",
            "guaranteed_renewal_years",
            "maximum_renewal_age",
            "accident_claim_days",
            "hospital_days_limit",
            "icu_days_limit",
            "nursing_days_limit",
            "burn_center_days_limit",
            "hospital_living_supplement_days_limit",
            "food_poisoning_lifetime_limit_times",
            "disability_living_supplement_lifetime_limit_times",
            "burn_lifetime_limit_times",
            "head_trauma_lifetime_limit_times",
            "fracture_unhospitalized_rate_percent",
            "occupational_class_by_plan",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "same_day_icu_or_burn_center_choose_one",
        }
        fubon_666_accident_health_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "accident_claim_days",
            "accident_hospital_days_limit",
            "fracture_daily_rate_percent",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "mass_transit_additional_benefit",
            "short_term_rate_table",
        }
        fubon_new_pingan_accident_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "accident_claim_days",
            "accident_medical_limit",
            "accident_medical_daily_formula_per_10000_inpatient_only",
            "accident_medical_daily_formula_per_10000_inpatient_split",
            "accident_medical_daily_formula_per_10000_outpatient_split",
            "accident_medical_daily_formula_days_limit",
            "accident_hospital_daily_amount",
            "accident_hospital_days_limit",
            "fracture_daily_rate_percent",
            "death_disability_same_accident_cap",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        fubon_anxin_456_accident_health_fields = {
            "terms_revision",
            "fixed_schedule",
            "non_guaranteed_renewal",
            "maximum_renewal_age",
            "cancer_waiting_days",
            "accident_claim_days",
            "accident_hospital_days_limit",
            "accident_icu_days_limit",
            "burn_center_days_limit",
            "fracture_daily_rate_percent",
            "major_burn_survival_days",
            "major_burn_lifetime_limit_times",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
        }
        china_life_jinhaoyi_fields = {
            "terms_revision",
            "special_multiplier_10_year_term",
            "special_multiplier_12_or_20_year_term",
            "accident_claim_days",
            "land_or_water_traffic_multiplier",
            "aviation_multiplier",
            "major_burn_rate_percent",
            "total_disability_schedule_item_count",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "disability_cumulative_cap_percent",
        }
        china_life_xinhaoyi_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_number",
            "special_multiplier_payment_period",
            "special_multiplier_after_payment_period",
            "paid_premium_interest_rate_percent",
            "accident_claim_days",
            "land_or_water_traffic_multiplier",
            "aviation_multiplier",
            "major_burn_rate_percent",
            "survival_rate_percent",
            "maturity_rate_percent",
            "maturity_age",
            "occupational_category_5_face_amount_rate_percent",
            "occupational_category_6_face_amount_rate_percent",
            "total_disability_schedule_item_count",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "disability_cumulative_cap_percent",
            "nonaccident_injury_surrender_value_refund",
        }
        china_life_foreign_currency_interest_whole_life_fields = {
            "terms_revision",
            "currency",
            "currency_label",
            "filing_date",
            "filing_number",
            "payment_period_options",
            "payment_period_required",
            "expected_interest_rate_percent",
            "expected_interest_rate_by_payment_period_percent",
            "value_sharing_bonus",
            "annual_insured_amount_formula",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "death_premium_component_formula",
            "total_disability_premium_component_formula",
            "survival_benefit_formula",
            "survival_rate_percent",
            "maturity_benefit_formula",
            "maturity_age",
            "premium_multiplier",
            "policy_face_amount_required",
            "accumulated_paid_up_additions_required",
            "standard_annual_premium_required",
            "policy_reserve_required",
            "survival_benefit_total_required",
            "maturity_table_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosed",
            "funeral_benefit_limit_rule",
            "minor_death_or_disability_refund_rule",
        }
        china_life_dameiwang_usd_periodic_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_events",
            "currency",
            "currency_label",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "value_sharing_bonus_basis",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "terminal_illness_advance_available",
            "terminal_illness_advance_rate_percent",
            "terminal_illness_advance_cap_amount",
            "terminal_illness_advance_cap_currency",
            "terminal_illness_survival_months_max",
            "terminal_illness_lifetime_limit_times",
            "terminal_illness_interest_deduction_months",
            "premium_multiplier",
            "reserve_component",
            "premium_component",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_options",
            "policy_face_amount_required",
            "accumulated_paid_up_additions_required",
            "annual_insured_amount_required",
            "policy_reserve_required",
            "value_coefficient_required",
            "premium_total_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosed",
            "no_contract_conversion_from_twd",
            "funeral_benefit_limit_rule",
        }
        china_life_meilifeng_usd_periodic_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_events",
            "currency",
            "currency_label",
            "expected_interest_rate_by_payment_period_percent",
            "value_sharing_bonus",
            "value_sharing_bonus_basis",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "reserve_component",
            "premium_component",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_options",
            "installment_minimum_specified_insurance_amount",
            "installment_minimum_annual_amount",
            "installment_minimum_currency",
            "increase_face_amount_option_available",
            "increase_face_amount_options_percent",
            "policy_face_amount_required",
            "accumulated_paid_up_additions_required",
            "annual_insured_amount_required",
            "policy_reserve_required",
            "value_coefficient_required",
            "premium_total_required",
            "standard_annual_premium_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosed",
            "no_contract_conversion_from_twd",
            "funeral_benefit_limit_rule",
        }
        china_life_meilexiangtui_usd_survival_whole_life_fields = {
            "product_family",
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_events",
            "approval_date",
            "approval_number",
            "later_filing_date",
            "later_filing_number",
            "latest_company_name",
            "currency",
            "currency_label",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "value_sharing_bonus_basis",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "survival_benefit_formula",
            "survival_rate_percent",
            "maturity_benefit_formula",
            "premium_waiver_available",
            "premium_waiver_disability_grade_min",
            "premium_waiver_disability_grade_max",
            "reserve_component",
            "premium_component",
            "maturity_age",
            "installment_benefit_available",
            "installment_period_options",
            "policy_face_amount_required",
            "accumulated_paid_up_additions_required",
            "annual_insured_amount_required",
            "policy_reserve_required",
            "value_coefficient_required",
            "premium_total_required",
            "standard_annual_premium_required",
            "terminal_survival_benefit_total_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosed",
            "no_contract_conversion_from_twd",
            "funeral_benefit_limit_rule",
        }
        china_life_foreign_currency_interest_endowment_fields = {
            "terms_revision",
            "currency",
            "currency_label",
            "filing_date",
            "filing_number",
            "original_filing_date",
            "original_filing_number",
            "expected_interest_rate_percent",
            "value_sharing_bonus",
            "value_sharing_bonus_basis",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "premium_refund_interest_rate_percent",
            "policy_face_amount_required",
            "policy_reserve_required",
            "premium_total_required",
            "foreign_currency_policy",
            "exchange_rate_risk_disclosed",
            "funeral_benefit_limit_rule",
            "minor_death_or_disability_refund_rule",
        }
        china_life_group_endowment_fields = {
            "terms_revision",
            "filing_date",
            "filing_number",
            "revision_date",
            "revision_basis",
            "product_family",
            "policy_type",
            "group_policy",
            "payment_period_options",
            "policy_period_same_as_payment_period",
            "death_benefit_formula",
            "total_disability_benefit_formula",
            "maturity_benefit_formula",
            "policy_face_amount_required",
            "per_insured_face_amount_required",
            "full_disability_table_item_count",
            "surrender_value_table_available",
            "surrender_value_table_unit_amount",
            "no_premium_loan",
            "no_reduced_paid_up_or_extended_term",
            "non_participating_policy",
        }
        fubon_tiantian_anxin_500_accident_health_legacy_fields = (
            fubon_tiantian_anxin_500_accident_health_fields
            | {"legacy_readable_validation"}
        )
        fubon_new_shouhu_jinnang_late_accident_health_legacy_fields = (
            fubon_new_shouhu_jinnang_late_accident_health_fields
            | {"legacy_readable_validation"}
        )
        fubon_anxin_financial_life_accident_health_legacy_fields = {
            "terms_revision",
            "plan_count",
            "non_guaranteed_renewal",
            "maximum_renewal_age_by_plan",
            "cancer_waiting_days",
            "major_disease_waiting_days",
            "legacy_cancer_split",
            "day_hospital_explicit",
            "general_hospital_days_limit",
            "icu_days_limit",
            "burn_center_hospital_days_limit",
            "same_hospital_readmission_days",
            "accident_claim_days",
            "disability_term",
            "disability_schedule_item_count",
            "disability_rate_min_percent",
            "disability_rate_max_percent",
            "short_term_rate_table",
            "legacy_readable_validation",
        }
        fubon_new_million_heart_accident_health_legacy_fields = (
            fubon_new_million_heart_accident_health_fields
            | {"legacy_readable_validation"}
        )
        fubon_new_pingan_accident_legacy_fields = (
            (fubon_new_pingan_accident_fields - {"fracture_daily_rate_percent"})
            | {"legacy_readable_validation"}
        )
        cancer_lifetime_pool_legacy_fields = {
            "cancer_waiting_days",
            "specific_cancer_rate_percent",
            "per_unit_total_cap",
            "funeral_benefit_rule",
        }
        cancer_lifetime_pool_fields = {
            *cancer_lifetime_pool_legacy_fields,
            "minor_death_or_disability_refund_rule",
            "maturity_age",
        }
        antai_new_cancer_lifetime_r11_fields = {
            "terms_revision",
            "cancer_observation_days",
            "minor_cancer_rate_percent",
            "hospital_days_tier_one_limit",
            "same_cancer_readmission_days",
            "hospice_anniversary_payments",
            "hospice_excluded_for_minor_cancer",
            "post_death_last_hospitalization_date_basis",
            "post_death_diagnosis_only_if_no_cancer_hospitalization",
            "premium_period_diagnosis_amount",
            "post_premium_period_diagnosis_amount",
        }
        antai_specific_major_disease_health_fields = {
            "terms_revision",
            "disease_waiting_days",
            "cancer_initial_waiting_days",
            "major_disease_waiting_days",
            "initial_cancer_lifetime_limit_times",
            "specific_cancer_lifetime_limit_times",
            "myocardial_infarction_or_coronary_bypass_lifetime_limit_times",
            "stroke_lifetime_limit_times",
            "systemic_lupus_lifetime_limit_times",
            "reconstruction_claim_days",
            "same_reconstruction_item_lifetime_limit_times",
            "claims_notification_days",
            "claim_payment_days_after_complete_documents",
        }
        antai_cancer_medical_term_fields = {
            "terms_revision",
            "cancer_waiting_days",
            "cancer_includes_carcinoma_in_situ",
            "family_type_options",
            "child_entry_age_limit",
            "newborn_child_covered_from_birth",
            "same_cancer_readmission_days",
            "radiation_annual_days_limit",
            "chemotherapy_annual_days_limit",
            "post_death_presumed_cancer_start_days",
            "premium_waiver_main_contract_death_or_disability",
        }
        cancer_annuity_fields = {
            "product_variant",
            "revision",
            "cancer_initial_waiting_days",
            "cancer_reinstatement_waiting_days",
            "cancer_renewal_waiting_days",
            "maximum_renewal_age",
            "terminates_next_policy_month_after_initial_cancer",
            "post_death_actual_diagnosis_date_evidence_allowed",
            "annuity_anniversary_basis",
        }
        new_complete_combined_fields = cancer_fields | {
            "disability_terminology",
            "cancer_classification",
            "missing_person_return_repayment_scope",
            "funeral_benefit_cap_reference",
            "source_conflicts",
        }
        versioned_combined_fields = new_complete_combined_fields - {
            "source_conflicts"
        }
        if not isinstance(version, dict):
            fail(f"coverage version characteristics fields are invalid: {context}")
        version_fields = frozenset(version)
        allowed_version_field_sets = {
            frozenset(cancer_fields),
            frozenset(combined_health_fields),
            frozenset(combined_health_disability_term_fields),
            frozenset(golden_lohas_fields),
            frozenset(golden_lohas_term_fields),
            frozenset(golden_complete_fields),
            frozenset(new_lohas_fields),
            frozenset(new_lohas_term_fields),
            frozenset(statutory_infectious_fields),
            frozenset(farglory_kangfu_medical_fields),
            frozenset(yuanta_xiangyouxin_medical_fields),
            frozenset(yuanta_xiangan_medical_fields),
            frozenset(yuanta_anxin100_critical_illness_fields),
            frozenset(yuanta_zhen_anxin_return_cancer_fields),
            frozenset(yuanta_zhenai_baby_return_life_fields),
            frozenset(yuanta_yuanman225_interest_endowment_fields),
            frozenset(yuanta_meinianduoli_usd_incremental_return_whole_life_fields),
            frozenset(
                yuanta_meinianduoli_usd_incremental_return_whole_life_filing_fields
            ),
            frozenset(
                yuanta_meinianduoli_usd_incremental_return_whole_life_article_2_fields
            ),
            frozenset(investment_life_guaranteed_face_amount_fields),
            frozenset(investment_life_guaranteed_face_amount_extended_fields),
            frozenset(investment_life_guaranteed_face_amount_policy_maturity_fields),
            frozenset(prudential_legacy_investment_life_fields),
            frozenset(kgi_china_legacy_investment_life_fields),
            frozenset(kgi_china_legacy_investment_life_currency_fields),
            frozenset(kgi_china_legacy_investment_life_waiver_fields),
            frozenset(kgi_china_legacy_investment_life_waiver_currency_fields),
            frozenset(taiwan_xinxiangle_investment_life_fields),
            frozenset(taiwan_age111_variable_universal_life_base_fields),
            frozenset(taiwan_age111_variable_universal_life_multiplier_fields),
            frozenset(taiwan_age111_variable_universal_life_fixed_bonus_fields),
            frozenset(taiwan_age111_variable_universal_life_schedule_bonus_fields),
            frozenset(taiwan_xinfumanzai_usd_variable_life_fields),
            frozenset(taiwan_xinfu_life_maturity_guarantee_fields),
            frozenset(taiwan_wudong_legacy_variable_universal_life_fields),
            frozenset(taiwan_wudong_legacy_variable_universal_life_minor15_fields),
            frozenset(taiwan_xindeyi_variable_universal_life_fields),
            frozenset(taiwan_zhiduoxin_variable_universal_life_fields),
            frozenset(taiwan_zhangwo_variable_universal_life_fields),
            frozenset(china_xinchuang_variable_life_fields),
            frozenset(china_legacy_investment_linked_life_fields),
            frozenset(fubon_xinxiangyouli_variable_life_fields),
            frozenset(hsingfu_legacy_variable_universal_life_fields),
            frozenset(global_ritai_financial_expert_investment_life_fields),
            frozenset(global_ritai_financial_head_investment_life_fields),
            frozenset(variable_annuity_account_value_fields),
            frozenset(prudential_shared_generations_variable_universal_life_fields),
            frozenset(prudential_chuangfu_variable_life_fields),
            frozenset(prudential_youyou_legacy_investment_life_fields),
            frozenset(legacy_investment_life_face_or_account_value_fields),
            frozenset(hsingfu_fuyu_dwa_whole_life_fields),
            frozenset(hsingfu_platinum_endowment_fields),
            frozenset(yuanta_new_account_medical_fields),
            frozenset(yuanta_health_life_early_fields),
            frozenset(global_e_road_peace_overseas_illness_fields),
            frozenset(global_nccu_student_group_fields),
            frozenset(taiwan_taipei_student_group_fields),
            frozenset(taiwan_drug_anxin_cancer_precision_fields),
            frozenset(yuanta_group_hospital_medical_fields),
            frozenset(yuanta_yuanqi_shizu_fields),
            frozenset(fixed_hospital_medical_97_fields),
            frozenset(prudential_daily_hospital_96_fields),
            frozenset(china_legacy_cancer_whole_life_fields),
            frozenset(taiwan_fishermen_group_medical_fields),
            frozenset(taiwan_group_long_term_care_service_fields),
            frozenset(taiwan_yiqijianzhi_specific_disease_fields),
            frozenset(taiwan_group_inpatient_limit_plan_fields),
            frozenset(taiwan_gold_group_inpatient_limit_fields),
            frozenset(taiwan_shishizai_inpatient_fields),
            frozenset(fubon_golden_health_fields),
            frozenset(fubon_golden_luck_universal_whole_life_fields),
            frozenset(fubon_golden_medical_device_fields),
            frozenset(fubon_hsl_inpatient_fields),
            frozenset(chaoyang_xingnong_group_inpatient_fields),
            frozenset(chaoyang_xingnong_student_group_fields),
            frozenset(prudential_china_life_accident_account_fields),
            frozenset(prudential_china_life_one_three_five_accident_fields),
            frozenset(prudential_group_specific_accident_rider_fields),
            frozenset(prudential_fire_mass_transit_accident_fields),
            frozenset(taiwan_qianwan_chuxing_a_accident_fields),
            frozenset(taiwan_qianwan_chuxing_b_endowment_fields),
            frozenset(fubon_xianganbao_accident_medical_rider_fields),
            frozenset(yuanta_new_accident_medical_rider_fields),
            frozenset(yuanta_personal_accident_rider_fields),
            frozenset(yuanta_funxinyou_accident_medical_addendum_fields),
            frozenset(fubon_family_gift_accident_health_legacy_fields),
            frozenset(fubon_family_gift_accident_health_fields),
            frozenset(fubon_wanan_365_accident_fields),
            frozenset(fubon_golden_guard_accident_health_fields),
            frozenset(fubon_tiantian_anxin_500_accident_health_fields),
            frozenset(fubon_tiantian_anxin_500_accident_health_legacy_fields),
            frozenset(fubon_xinfu_life_accident_health_fields),
            frozenset(fubon_xinfu_life_accident_health_total_term_fields),
            frozenset(fubon_tzu_chi_marrow_group_life_medical_fields),
            frozenset(fubon_tzu_chi_marrow_group_life_medical_total_limit_fields),
            frozenset(fubon_changanbao_life_service_fields),
            frozenset(fubon_yongai_life_service_fields),
            frozenset(taiwan_funeral_service_rider_fields),
            frozenset(taiwan_longzaitian_funeral_service_rider_fields),
            frozenset(taiwan_longai_funeral_service_whole_life_fields),
            frozenset(taiwan_funeral_service_whole_life_early_plan_fields),
            frozenset(taiwan_funeral_service_whole_life_early_tower_fields),
            frozenset(taiwan_funeral_service_whole_life_fields),
            frozenset(taiwan_interest_rate_accident_whole_life_fields),
            frozenset(taiwan_chuanshi_fuli_whole_life_fields),
            frozenset(taiwan_interest_rate_whole_life_fields),
            frozenset(taiwan_interest_rate_whole_life_statutory_infectious_fields),
            frozenset(taiwan_fengfu_meili_usd_interest_whole_life_fields),
            frozenset(
                taiwan_yaozuan_chuanshi_usd_whole_life_cancer_health_fields
            ),
            frozenset(taiwan_lehuo_meili_usd_whole_life_cancer_health_fields),
            frozenset(taiwan_interest_rate_specific_disease_whole_life_fields),
            frozenset(
                taiwan_interest_rate_specific_disease_survival_whole_life_fields
            ),
            frozenset(taiwan_participating_whole_life_fields),
            frozenset(taiwan_participating_return_whole_life_fields),
            frozenset(taiwan_term_life_fields),
            frozenset(taiwan_simple_term_life_fields),
            frozenset(taiwan_usd_no_disability_fields),
            frozenset(taiwan_usd_no_disability_maturity_age_fields),
            frozenset(taiwan_platinum_account_endowment_fields),
            frozenset(taiwan_long_term_care_whole_life_fields),
            frozenset(taiwan_interest_rate_return_whole_life_legacy_fields),
            frozenset(taiwan_interest_rate_return_whole_life_fields),
            frozenset(taiwan_interest_rate_return_whole_life_specific_cancer_fields),
            frozenset(taiwan_interest_rate_endowment_fields),
            frozenset(taiwan_usd_endowment_fields),
            frozenset(taiwan_fixed_return_whole_life_fields),
            frozenset(taiwan_yibao_3xiang_medical_whole_life_fields),
            frozenset(taiwan_yixiang_health_medical_whole_life_fields),
            frozenset(taiwan_lehuo_health_medical_whole_life_fields),
            frozenset(fubon_new_shouhu_jinnang_accident_health_fields),
            frozenset(fubon_new_shouhu_jinnang_late_accident_health_fields),
            frozenset(fubon_new_shouhu_jinnang_late_accident_health_legacy_fields),
            frozenset(fubon_haozhouquan_accident_health_fields),
            frozenset(fubon_health_limit_up_accident_health_fields),
            frozenset(fubon_vision_life_accident_health_fields),
            frozenset(fubon_anxin_financial_life_accident_health_fields),
            frozenset(fubon_anxin_financial_life_accident_health_legacy_fields),
            frozenset(fubon_new_million_heart_accident_health_fields),
            frozenset(fubon_new_million_heart_accident_health_legacy_fields),
            frozenset(fubon_million_heart_accident_health_fields),
            frozenset(fubon_million_new_life_accident_health_fields),
            frozenset(fubon_comprehensive_accident_fields),
            frozenset(fubon_new_pingan_accident_fields),
            frozenset(fubon_new_pingan_accident_legacy_fields),
            frozenset(fubon_666_accident_health_fields),
            frozenset(fubon_anxin_456_accident_health_fields),
            frozenset(china_life_jinhaoyi_fields),
            frozenset(china_life_xinhaoyi_fields),
            frozenset(china_life_foreign_currency_interest_whole_life_fields),
            frozenset(china_life_dameiwang_usd_periodic_whole_life_fields),
            frozenset(china_life_meilifeng_usd_periodic_whole_life_fields),
            frozenset(
                china_life_meilexiangtui_usd_survival_whole_life_fields
            ),
            frozenset(china_life_foreign_currency_interest_endowment_fields),
            frozenset(china_life_group_endowment_fields),
            frozenset(cancer_lifetime_pool_legacy_fields),
            frozenset(cancer_lifetime_pool_fields),
            frozenset(antai_new_cancer_lifetime_r11_fields),
            frozenset(antai_specific_major_disease_health_fields),
            frozenset(antai_cancer_medical_term_fields),
            frozenset(cancer_annuity_fields),
            frozenset(versioned_combined_fields),
            frozenset(new_complete_combined_fields),
        }
        variable_annuity_account_value_version = (
            version_fields.issubset(variable_annuity_account_value_fields)
            and variable_annuity_account_value_required_fields.issubset(version_fields)
        )
        if (
            version_fields not in allowed_version_field_sets
            and not variable_annuity_account_value_version
        ):
            fail(f"coverage version characteristics fields are invalid: {context}")
        if variable_annuity_account_value_version:
            if (
                version["product_family"]
                != "investment-linked-variable-annuity-account-value"
            ):
                fail(f"coverage annuity product family is invalid: {context}")
            if version["currency_basis"] not in {"twd", "foreign_currency"}:
                fail(f"coverage annuity currency basis is invalid: {context}")
            if (
                version["annuity_amount_formula"]
                != "policy_account_value_at_annuity_start_using_assumed_interest_rate_and_annuity_life_table"
            ):
                fail(f"coverage annuity amount formula is invalid: {context}")
            for flag in [
                "investment_linked_policy",
                "annuity_policy",
                "policy_account_value_required",
                "annuity_start_date_required",
                "assumed_interest_rate_required",
                "annuity_life_table_required",
                "investment_target_value_required",
                "guarantee_period_required",
                "minimum_death_benefit",
                "unpaid_annuity_balance",
                "low_annual_annuity_lump_sum_rule",
                "high_annual_annuity_account_value_return_rule",
                "account_value_full_withdrawal_at_annuity_start",
                "non_participating_policy",
            ]:
                if flag in version and not isinstance(version[flag], bool):
                    fail(f"coverage annuity {flag} flag is invalid: {context}")
            payment_frequency_options = version["payment_frequency_options"]
            if (
                not isinstance(payment_frequency_options, list)
                or not payment_frequency_options
            ):
                fail(f"coverage annuity payment frequency options are invalid: {context}")
            allowed_payment_frequency_options = {
                "lump_sum",
                "annual",
                "semiannual",
                "quarterly",
                "monthly",
            }
            if any(
                option not in allowed_payment_frequency_options
                for option in payment_frequency_options
            ):
                fail(f"coverage annuity payment frequency option is invalid: {context}")
            if "guarantee_period_options_years" in version:
                guarantee_period_options = version["guarantee_period_options_years"]
                if not isinstance(guarantee_period_options, list) or any(
                    value not in {5, 10, 15, 20}
                    for value in guarantee_period_options
                ):
                    fail(f"coverage annuity guarantee periods are invalid: {context}")
            for age_key in [
                "default_annuity_start_age",
                "max_annuity_start_age",
                "max_annuity_payment_age",
            ]:
                if age_key in version and version[age_key] not in {70, 80, 110}:
                    fail(f"coverage annuity age characteristic is invalid: {context}")
        if "cancer_initial_waiting_days" in version and version["cancer_initial_waiting_days"] not in {0, 30, 90}:
            fail(f"coverage initial waiting days are invalid: {context}")
        if "cancer_reinstatement_waiting_days" in version and version["cancer_reinstatement_waiting_days"] not in {0, 30, 90}:
            fail(f"coverage reinstatement waiting days are invalid: {context}")
        if "cancer_renewal_waiting_days" in version and version["cancer_renewal_waiting_days"] != 0:
            fail(f"coverage renewal waiting days are invalid: {context}")
        if "product_variant" in version and version["product_variant"] not in {
            "traditional",
            "investment-linked",
        }:
            fail(f"coverage product variant is invalid: {context}")
        if "revision" in version and version["revision"] not in {
            "original",
            "first-revision",
        }:
            fail(f"coverage revision is invalid: {context}")
        if "maximum_renewal_age" in version and version["maximum_renewal_age"] not in {50, 55, 60, 65, 70, 75}:
            fail(f"coverage maximum renewal age is invalid: {context}")
        for flag in [
            "terminates_next_policy_month_after_initial_cancer",
            "post_death_actual_diagnosis_date_evidence_allowed",
        ]:
            if flag in version and not isinstance(version[flag], bool):
                fail(f"coverage {flag} flag is invalid: {context}")
        if "annuity_anniversary_basis" in version and version["annuity_anniversary_basis"] not in {
            "initial-cancer-benefit-payment-date",
            "policy-anniversary-after-diagnosis",
        }:
            fail(f"coverage annuity anniversary basis is invalid: {context}")
        if set(version) == cancer_annuity_fields:
            if (
                version["cancer_initial_waiting_days"] != 90
                or version["cancer_reinstatement_waiting_days"] != 90
                or version["cancer_renewal_waiting_days"] != 0
            ):
                fail(f"coverage cancer-annuity waiting periods are invalid: {context}")
            expected_age = 65 if version["product_variant"] == "traditional" else 75
            expected_basis = (
                "policy-anniversary-after-diagnosis"
                if version["product_variant"] == "traditional"
                else "initial-cancer-benefit-payment-date"
            )
            if (
                version["maximum_renewal_age"] != expected_age
                or version["annuity_anniversary_basis"] != expected_basis
            ):
                fail(f"coverage cancer-annuity variant rules are invalid: {context}")
            terminates_after_initial_cancer = version[
                "terminates_next_policy_month_after_initial_cancer"
            ]
            post_death_evidence_allowed = version[
                "post_death_actual_diagnosis_date_evidence_allowed"
            ]
            if terminates_after_initial_cancer != post_death_evidence_allowed:
                fail(f"coverage cancer-annuity revision rules are invalid: {context}")
            if version["product_variant"] == "traditional" and terminates_after_initial_cancer:
                fail(f"coverage cancer-annuity revision rules are invalid: {context}")
            if (
                version["product_variant"] == "investment-linked"
                and version["revision"] == "first-revision"
                and not terminates_after_initial_cancer
            ):
                fail(f"coverage cancer-annuity revision rules are invalid: {context}")
        if "disease_initial_waiting_days" in version and version["disease_initial_waiting_days"] not in {0, 30}:
            fail(f"coverage disease waiting days are invalid: {context}")
        if "disease_reinstatement_waiting_days" in version and version["disease_reinstatement_waiting_days"] != 0:
            fail(f"coverage disease reinstatement waiting days are invalid: {context}")
        if "major_disease_initial_waiting_days" in version and version["major_disease_initial_waiting_days"] not in {30, 90}:
            fail(f"coverage major-disease initial waiting days are invalid: {context}")
        if "major_disease_reinstatement_waiting_days" in version and version["major_disease_reinstatement_waiting_days"] not in {0, 90}:
            fail(f"coverage major-disease reinstatement waiting days are invalid: {context}")
        if "mild_cancer_initial_waiting_days" in version and version["mild_cancer_initial_waiting_days"] != 90:
            fail(f"coverage mild-cancer initial waiting days are invalid: {context}")
        if "mild_cancer_reinstatement_waiting_days" in version and version["mild_cancer_reinstatement_waiting_days"] not in {0, 90}:
            fail(f"coverage mild-cancer reinstatement waiting days are invalid: {context}")
        if "cancer_waiting_days" in version and version["cancer_waiting_days"] not in {0, 30, 90}:
            fail(f"coverage cancer waiting days are invalid: {context}")
        if "specific_cancer_rate_percent" in version and version["specific_cancer_rate_percent"] not in {1, 15}:
            fail(f"coverage specific-cancer rate is invalid: {context}")
        if "specific_cancer_waiting_days" in version and version["specific_cancer_waiting_days"] != 90:
            fail(f"coverage specific-cancer waiting days are invalid: {context}")
        if "specific_cancer_lifetime_limit_times" in version and version["specific_cancer_lifetime_limit_times"] != 1:
            fail(f"coverage specific-cancer lifetime limit is invalid: {context}")
        if "specific_cancer_basis" in version and version["specific_cancer_basis"] != "basic_face_amount":
            fail(f"coverage specific-cancer basis is invalid: {context}")
        if "per_unit_total_cap" in version and version["per_unit_total_cap"] != 1_000_000:
            fail(f"coverage per-unit total cap is invalid: {context}")
        if "funeral_benefit_rule" in version and version["funeral_benefit_rule"] not in {
            "pre-2010-fixed-funeral-cap",
            "2010-estate-tax-half-deduction",
        }:
            fail(f"coverage funeral-benefit rule is invalid: {context}")
        if "minor_death_or_disability_refund_rule" in version and not isinstance(
            version["minor_death_or_disability_refund_rule"], bool
        ):
            fail(f"coverage minor death or disability refund rule is invalid: {context}")
        if "maturity_age" in version and version["maturity_age"] not in {
            85,
            91,
            96,
            99,
            100,
            110,
            111,
        }:
            fail(f"coverage maturity age is invalid: {context}")
        if "day_hospital_explicit" in version and not isinstance(version["day_hospital_explicit"], bool):
            fail(f"coverage day-hospital flag is invalid: {context}")
        if "day_hospital_excluded" in version and not isinstance(version["day_hospital_excluded"], bool):
            fail(f"coverage day-hospital exclusion flag is invalid: {context}")
        if "overseas_stay_limit_days" in version and version["overseas_stay_limit_days"] != 180:
            fail(f"coverage overseas-stay limit is invalid: {context}")
        if "post_expiry_readmission_excluded" in version and not isinstance(
            version["post_expiry_readmission_excluded"], bool
        ):
            fail(f"coverage post-expiry readmission flag is invalid: {context}")
        if "disability_schedule_revision" in version and version["disability_schedule_revision"] not in {
            "original-75-items",
            "104-revised-79-items",
            "109-revised-80-items",
            "original-67-items",
            "104-revised-71-items",
        }:
            fail(f"coverage disability schedule revision is invalid: {context}")
        if "disability_terminology" in version and version["disability_terminology"] not in {
            "殘廢",
            "失能",
            "完全殘廢",
            "完全失能",
        }:
            fail(f"coverage disability terminology is invalid: {context}")
        if "total_disability_term" in version and version["total_disability_term"] not in {
            "完全殘廢",
            "完全失能",
        }:
            fail(f"coverage total disability term is invalid: {context}")
        if "disability_term" in version and version["disability_term"] not in {
            "殘廢",
            "失能",
        }:
            fail(f"coverage disability term is invalid: {context}")
        if "cancer_classification" in version and version["cancer_classification"] not in {
            "original-two-tier",
            "2018-three-tier",
        }:
            fail(f"coverage cancer classification is invalid: {context}")
        if "cancer_definition_revision" in version and version[
            "cancer_definition_revision"
        ] not in {"pre-108-pathology-or-cytology", "108-standardized-pathology"}:
            fail(f"coverage cancer definition revision is invalid: {context}")
        if "newborn_screening_revision" in version and version[
            "newborn_screening_revision"
        ] not in {"original-screening-list", "109-genetic-disease-list"}:
            fail(f"coverage newborn screening revision is invalid: {context}")
        if "reinstatement_notice_revision" in version and version[
            "reinstatement_notice_revision"
        ] not in {"pre-109", "109-pre-expiry-reminder"}:
            fail(f"coverage reinstatement notice revision is invalid: {context}")
        if "missing_person_return_repayment_scope" in version and version[
            "missing_person_return_repayment_scope"
        ] not in {"death-benefit-only", "refund-or-death-benefit"}:
            fail(f"coverage missing-person repayment scope is invalid: {context}")
        if "funeral_benefit_cap_reference" in version and version[
            "funeral_benefit_cap_reference"
        ] not in {"contract-inception", "statutory-deduction"}:
            fail(f"coverage funeral-benefit cap reference is invalid: {context}")
        if "source_conflicts" in version:
            conflicts = version["source_conflicts"]
            expected_conflict_fields = {
                "field",
                "policy_terms_value",
                "product_summary_value",
                "authoritative_source",
                "resolution",
                "policy_terms_page",
                "product_summary_page",
                "note",
            }
            if not isinstance(conflicts, list) or not conflicts:
                fail(f"coverage source conflicts are invalid: {context}")
            for conflict in conflicts:
                if not isinstance(conflict, dict) or set(conflict) != expected_conflict_fields:
                    fail(f"coverage source conflict fields are invalid: {context}")
                if (
                    conflict.get("field") != "cancer_reinstatement_waiting_days"
                    or conflict.get("policy_terms_value") != 0
                    or conflict.get("product_summary_value") != 30
                    or conflict.get("authoritative_source") != "policy_terms"
                    or conflict.get("resolution") != "policy_terms_precedence"
                    or not isinstance(conflict.get("policy_terms_page"), int)
                    or conflict["policy_terms_page"] <= 0
                    or not isinstance(conflict.get("product_summary_page"), int)
                    or conflict["product_summary_page"] <= 0
                    or not isinstance(conflict.get("note"), str)
                    or not conflict["note"].strip()
                ):
                    fail(f"coverage source conflict value is invalid: {context}")


SCHEDULE_FIELDS = (
    "selection_type",
    "input_mode",
    "selection_source",
    "selection_label",
    "selection_guidance",
    "unit_fields",
    "version_characteristics",
    "plan_options",
    "coverage_entries",
)


def schedule_from_record(record: dict) -> dict:
    return {field: record[field] for field in SCHEDULE_FIELDS if field in record}


def schedule_sha256(record: dict) -> str:
    canonical = json.dumps(
        schedule_from_record(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_reviewed_benefits() -> int:
    reviewed_paths = sorted(Path("data/tii/reviewed-benefits").glob("*.json"))
    seen_product_ids = set()
    reviewed_count = 0
    allowed_fields = {
        "product_id",
        "status",
        "extractor_version",
        "parser_id",
        "source_file",
        "source_document_sha256",
        "schedule_sha256",
        "reviewed_by",
        "reviewed_at",
        "review_note",
        *SCHEDULE_FIELDS,
    }
    for path in reviewed_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        batch_id = path.stem
        records = payload.get("records") or []
        if payload.get("batch_id") != batch_id or payload.get("record_count") != len(records):
            fail(f"reviewed benefit metadata mismatch: {path}")
        content_path = Path("data/tii/document-content") / f"{batch_id}.json"
        if not content_path.is_file():
            fail(f"reviewed benefit content batch is missing: {path}")
        content_payload = json.loads(content_path.read_text(encoding="utf-8"))
        content_records = {
            str(record.get("product_id") or ""): record
            for record in content_payload.get("records", [])
        }
        for record in records:
            product_id = str(record.get("product_id") or "")
            context = f"{path} product {product_id}"
            if not product_id or product_id in seen_product_ids:
                fail(f"reviewed benefit product id is invalid or duplicated: {context}")
            seen_product_ids.add(product_id)
            if not set(record).issubset(allowed_fields):
                fail(f"reviewed benefit has unexpected fields: {context}")
            if record.get("status") != "verified_reference":
                fail(f"reviewed benefit status is invalid: {context}")
            for field in ["extractor_version", "parser_id", "source_file", "reviewed_by", "reviewed_at"]:
                if not record.get(field):
                    fail(f"reviewed benefit lacks {field}: {context}")
            for hash_field in ["source_document_sha256", "schedule_sha256"]:
                if not re.fullmatch(r"[0-9a-f]{64}", str(record.get(hash_field) or "")):
                    fail(f"reviewed benefit {hash_field} is invalid: {context}")
            if schedule_sha256(record) != record["schedule_sha256"]:
                fail(f"reviewed benefit schedule hash mismatch: {context}")
            validate_plan_options(record, context)
            content_record = content_records.get(product_id)
            if not content_record:
                fail(f"reviewed benefit has no public content record: {context}")
            if schedule_from_record(content_record) != schedule_from_record(record):
                fail(f"reviewed benefit differs from public content: {context}")

            source_path = (
                Path("work/tii-documents") / batch_id / product_id / record["source_file"]
            )
            if source_path.is_file():
                source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
                if source_hash != record["source_document_sha256"]:
                    fail(f"reviewed benefit source PDF hash mismatch: {context}")
            reviewed_count += 1
    return reviewed_count


def main() -> None:
    source_index = load_json("data/source-index.json")
    taxonomy = load_json("data/consumer-taxonomy.json")
    crawl_status = load_json("data/crawl-status.json")
    policy_insights = load_json("data/policy-insights.json")
    tii_metadata = load_json("data/tii-query-metadata.json")
    tii_results = load_json("data/tii-policy-results.json")
    tii_manifest = load_tii_manifest(tii_results)
    tii_records = load_tii_records(tii_results, tii_manifest)
    tii_execution_progress = load_json("data/tii-execution-progress.json")
    batch_plan = load_json("data/batch-plan.json")
    batch_progress = load_json("data/batch-progress.json")
    policy_batch_results = load_json("data/policy-batch-results.json")
    policy_content_extracts = load_json("data/policy-content-extracts.json")
    site_summary = load_json("data/site-summary.json")
    reviewed_benefit_count = validate_reviewed_benefits()

    if not source_index.get("urls"):
        fail("source-index has no urls")
    if not taxonomy.get("sections"):
        fail("consumer taxonomy has no sections")

    ids = set()
    for item in source_index["urls"]:
        for field in ["id", "url", "domain", "company", "kind", "visibility", "should_crawl"]:
            if field not in item:
                fail(f"url record missing {field}")
        if item["id"] in ids:
            fail(f"duplicate url id {item['id']}")
        ids.add(item["id"])
        parsed = urlparse(item["url"])
        if item["should_crawl"] and parsed.scheme != "https":
            fail(f"crawl candidate is not https: {item['url']}")
        if item["should_crawl"] and item["domain"] == "docs.google.com":
            fail("private Google Docs URL marked crawlable")

    public_urls = [item for item in source_index["urls"] if item["should_crawl"]]
    if not public_urls:
        fail("no public crawl candidates")

    if not crawl_status.get("results"):
        fail("crawl-status has no results")
    if not policy_insights.get("policies"):
        fail("policy-insights has no policies")
    if not tii_metadata.get("companies"):
        fail("tii metadata has no companies")
    if tii_metadata.get("captcha_required") is not True:
        fail("tii metadata should record captcha boundary")
    if not batch_plan.get("policy_url_batches"):
        fail("batch plan has no policy URL batches")
    if not batch_plan.get("tii_priority_batches"):
        fail("batch plan has no TII priority batches")
    if not batch_plan.get("tii_company_type_groups"):
        fail("batch plan has no TII company type groups")
    if not batch_plan.get("tii_manual_matrix_batches"):
        fail("batch plan has no TII manual matrix batches")
    matrix_count = batch_plan["summary"].get("tii_manual_matrix_batch_count")
    if matrix_count != len(batch_plan["tii_manual_matrix_batches"]):
        fail("TII manual matrix batch count does not match summary")
    matrix_types = {batch.get("company_type") for batch in batch_plan["tii_manual_matrix_batches"]}
    if not {"property", "life"}.issubset(matrix_types):
        fail("TII manual matrix should include both property and life batches")
    if tii_results.get("record_count") != len(tii_records):
        fail("TII result record_count does not match records length")
    tii_completed_batches = tii_results.get("completed_batch_count", len(tii_results.get("completed_batches", [])))
    if tii_completed_batches != len(tii_results.get("completed_batches", [])):
        fail("TII completed_batch_count does not match completed_batches length")
    tii_indexed_batches = tii_results.get("indexed_batch_count", len(tii_results.get("indexed_batches", [])))
    if tii_indexed_batches != len(tii_results.get("indexed_batches", [])):
        fail("TII indexed_batch_count does not match indexed_batches length")
    if tii_completed_batches > tii_indexed_batches:
        fail("TII completed batches cannot exceed indexed batches")
    if tii_completed_batches > matrix_count:
        fail("TII completed batches cannot exceed manual matrix batch count")
    for record in tii_records:
        for field in [
            "source_batch_id",
            "company",
            "insurance_category",
            "product_id",
            "detail_url",
            "product_name",
            "sale_status",
            "record_identity_key",
            "identity_basis",
            "edition_label",
        ]:
            if not record.get(field):
                fail(f"TII imported record missing {field}: {record.get('id')}")
        undated_official_status = any(
            status in str(record.get("sale_status", "")) for status in ["未銷售", "未停售"]
        )
        if not record.get("sale_date") and not (
            record.get("identity_basis") == "tii_product_id"
            and record.get("detail_saved")
            and undated_official_status
        ):
            fail(f"TII imported record missing sale_date: {record.get('id')}")
        if record.get("identity_basis") == "tii_product_id" and record.get("record_identity_key") != f"tii-product-id:{record.get('product_id')}":
            fail(f"TII record identity key should preserve productId: {record.get('id')}")
        if record.get("sale_status") == "已停售" and not record.get("discontinued_date"):
            fail(f"TII discontinued record missing discontinued_date: {record.get('id')}")
        if not str(record["detail_url"]).startswith("https://insprod.tii.org.tw/DetailList.aspx?productId="):
            fail(f"TII detail_url is not an official detail URL: {record.get('id')}")
        if "raw_text" in record:
            fail(f"TII imported record should not publish raw_text: {record.get('id')}")
    same_name_groups: dict[tuple[str, str], set[str]] = {}
    for record in tii_records:
        same_name_groups.setdefault((record.get("company", ""), record.get("product_name", "")), set()).add(record.get("product_id", ""))
    multi_product_name_groups = {key: ids for key, ids in same_name_groups.items() if len({item for item in ids if item}) > 1}
    for record in tii_records:
        if (record.get("company", ""), record.get("product_name", "")) in multi_product_name_groups:
            if int(record.get("same_name_product_id_count") or 0) <= 1:
                fail(f"TII same-name different-product record missing version marker: {record.get('id')}")
    if not isinstance(tii_results.get("batch_summaries", []), list):
        fail("TII batch_summaries should be a list")
    tii_batch_ids_from_records = {record.get("source_batch_id") for record in tii_records}
    tii_batch_ids_from_summaries = {summary.get("batch_id") for summary in tii_results.get("batch_summaries", [])}
    if tii_batch_ids_from_summaries != set(tii_results.get("indexed_batches", [])):
        fail("TII indexed_batches should match batch summary ids")
    if not tii_batch_ids_from_records.issubset(tii_batch_ids_from_summaries):
        fail("TII record source batches should be included in batch summaries")
    for summary in tii_results.get("batch_summaries", []):
        for field in [
            "batch_id",
            "status",
            "expected_total_count",
            "saved_page_count",
            "imported_record_count",
            "unique_product_id_count",
            "official_row_count",
            "duplicate_product_id_count",
        ]:
            if field not in summary:
                fail(f"TII batch summary missing {field}")
        if summary["status"] == "complete" and summary["unique_product_id_count"] != summary["expected_total_count"]:
            official_row_count = int(summary.get("official_row_count") or 0)
            duplicate_product_id_count = int(summary.get("duplicate_product_id_count") or 0)
            expected_pages = int(summary.get("expected_total_pages") or 0)
            saved_page_count = int(summary.get("saved_page_count") or 0)
            if (
                official_row_count != summary["expected_total_count"]
                or duplicate_product_id_count <= 0
                or (expected_pages and saved_page_count < expected_pages)
            ):
                fail(f"TII complete batch does not match expected count: {summary['batch_id']}")
        if summary["imported_record_count"] != summary["unique_product_id_count"]:
            fail(f"TII imported count should match unique product ids: {summary['batch_id']}")
    tii_runs = tii_execution_progress.get("runs", [])
    tii_execution_summary = tii_execution_progress.get("summary", {})
    for run in tii_runs:
        fetched_pages = run.get("fetched_pages") or {}
        for page in fetched_pages.get("saved_pages") or []:
            if not Path(page).exists():
                fail(f"TII progress references missing saved page: {page}")
    if tii_execution_summary.get("attempted_batches", len(tii_runs)) != len(tii_runs):
        fail("TII attempted batch count does not match runs length")
    if tii_execution_summary.get("completed_batches", 0) > len(tii_runs):
        fail("TII completed execution count cannot exceed attempted runs")
    if tii_execution_summary.get("attempted_batches", 0) > matrix_count:
        fail("TII attempted batches cannot exceed manual matrix batch count")
    if not batch_progress.get("batches"):
        fail("batch progress has no executed batches")
    if not policy_batch_results.get("batches"):
        fail("policy batch results has no batches")
    if not policy_content_extracts.get("records"):
        fail("policy content extracts has no records")
    if site_summary.get("tii", {}).get("imported_policy_records") != tii_results.get("record_count"):
        fail("site summary TII imported count does not match TII results")
    if site_summary.get("tii", {}).get("detail_saved_count") != tii_results.get("detail_saved_count"):
        fail("site summary TII detail saved count does not match TII results")
    if site_summary.get("tii", {}).get("completed_batches") != tii_results.get("completed_batch_count"):
        fail("site summary TII completed batch count does not match TII results")
    content_records = policy_content_extracts["records"]
    content_summary = policy_content_extracts.get("summary", {})
    if content_summary.get("record_count") != len(content_records):
        fail("policy content record count does not match records length")
    if content_summary.get("record_count") != batch_progress["summary"]["policy_url_ok"]:
        fail("policy content extract count should match successful policy URL fetches")
    if content_summary.get("extracted_text_count") != len(content_records):
        fail("every policy content record should have parsed text")
    if content_summary.get("pdf_record_count", 0) + content_summary.get("html_record_count", 0) != len(content_records):
        fail("policy content PDF/HTML counts do not match records length")
    if content_summary.get("records_with_field_hits", 0) <= 0:
        fail("policy content extracts have no field hits")
    if content_summary.get("total_text_characters", 0) <= 0:
        fail("policy content extracts have no text characters")
    if not content_summary.get("focus_counts"):
        fail("policy content extracts have no reader focus counts")

    content_hits = 0
    focus_counts = {}
    total_text_characters = 0
    allowed_content_kinds = {"pdf", "html"}
    required_focus_keys = {"coverage", "definitions", "special", "claims"}
    forbidden_text_fields = {"text", "raw_text", "full_text", "content_text", "extracted_text"}
    for record in content_records:
        for field in ["policy_url", "final_url", "company", "product_name", "document_kind", "extraction_status"]:
            if not record.get(field):
                fail(f"policy content record missing {field}")
        if record["document_kind"] not in allowed_content_kinds:
            fail(f"unsupported policy content document kind: {record['document_kind']}")
        if record["extraction_status"] != "extracted":
            fail(f"policy content record was not extracted: {record.get('policy_id')}")
        if not isinstance(record.get("text_char_count"), int) or record["text_char_count"] <= 0:
            fail(f"policy content record has no parsed text characters: {record.get('policy_id')}")
        if record["document_kind"] == "pdf" and record.get("pages_parsed", 0) <= 0:
            fail(f"PDF policy content record has no parsed pages: {record.get('policy_id')}")
        if not isinstance(record.get("field_hits"), list):
            fail(f"policy content record field_hits must be a list: {record.get('policy_id')}")
        if forbidden_text_fields.intersection(record):
            fail(f"policy content record should not publish full text: {record.get('policy_id')}")
        reader_focus = record.get("reader_focus")
        if not isinstance(reader_focus, list) or len(reader_focus) != 4:
            fail(f"policy content record should have four reader focus cards: {record.get('policy_id')}")
        focus_keys = {card.get("key") for card in reader_focus}
        if focus_keys != required_focus_keys:
            fail(f"policy content reader focus keys are incomplete: {record.get('policy_id')}")
        detected_focus = 0
        for card in reader_focus:
            for field in ["key", "label", "reader_question", "status", "summary", "terms", "pages"]:
                if field not in card:
                    fail(f"reader focus card missing {field}: {record.get('policy_id')}")
            if card["status"] == "detected":
                detected_focus += 1
                focus_counts[card["label"]] = focus_counts.get(card["label"], 0) + 1
                if not card["terms"]:
                    fail(f"detected reader focus card has no terms: {record.get('policy_id')}")
        if record.get("focus_score") != detected_focus:
            fail(f"policy content focus score does not match detected cards: {record.get('policy_id')}")
        if record["field_hits"]:
            content_hits += 1
        total_text_characters += record["text_char_count"]
    if content_hits != content_summary.get("records_with_field_hits"):
        fail("policy content field-hit count does not match records")
    if total_text_characters != content_summary.get("total_text_characters"):
        fail("policy content text-character total does not match records")
    summary_focus_counts = {item["label"]: item["count"] for item in content_summary["focus_counts"]}
    if focus_counts != summary_focus_counts:
        fail("policy content reader focus counts do not match records")

    document_content_paths = sorted(Path("data/tii/document-content").glob("*.json"))
    document_summary_paths = sorted(Path("data/tii/document-summaries").glob("*.json"))
    if {path.stem for path in document_summary_paths} != {path.stem for path in document_content_paths}:
        fail("TII browser document summaries do not cover every document-content batch")
    required_summary_fields = {"product_id", "coverage_tags", "reader_focus"}
    allowed_summary_fields = required_summary_fields | {
        "selection_type",
        "input_mode",
        "selection_source",
        "selection_label",
        "selection_guidance",
        "unit_fields",
        "version_characteristics",
        "plan_options",
        "coverage_entries",
    }
    allowed_focus_fields = {"key", "label", "summary", "terms"}
    for path in document_summary_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") or []
        if payload.get("batch_id") != path.stem or payload.get("record_count") != len(records):
            fail(f"TII browser document summary metadata mismatch: {path}")
        product_ids = set()
        for record in records:
            if not required_summary_fields.issubset(record) or not set(record).issubset(allowed_summary_fields):
                fail(f"TII browser document summary has unexpected fields: {path}")
            product_id = record.get("product_id")
            if not product_id or product_id in product_ids:
                fail(f"TII browser document summary has invalid product id: {path}")
            product_ids.add(product_id)
            if not isinstance(record.get("coverage_tags"), list) or not isinstance(record.get("reader_focus"), list):
                fail(f"TII browser document summary lists are invalid: {path}")
            focus_keys = set()
            for card in record["reader_focus"]:
                if set(card) != allowed_focus_fields or card.get("key") not in required_focus_keys:
                    fail(f"TII browser document summary focus card is invalid: {path}")
                if card["key"] in focus_keys or not isinstance(card.get("terms"), list):
                    fail(f"TII browser document summary focus card is duplicated: {path}")
                focus_keys.add(card["key"])
            validate_plan_options(record, f"{path} product {product_id}")
    known_ids = {item["id"] for item in source_index["urls"]}
    for result in crawl_status["results"]:
        if result["url_id"] not in known_ids:
            fail(f"crawl result references unknown url_id {result['url_id']}")

    print(
        json.dumps(
            {
                "status": "ok",
                "source_files": source_index["source_file_count"],
                "total_urls": source_index["total_unique_url_count"],
                "public_crawl_candidates": source_index["public_crawl_candidate_count"],
                "crawl_checked": crawl_status["summary"]["checked"],
                "crawl_ok": crawl_status["summary"]["ok"],
                "policy_count": policy_insights["summary"]["policy_count"],
                "policy_discontinued": policy_insights["summary"]["discontinued_count"],
                "tii_companies": len(tii_metadata["companies"]),
                "policy_url_batches": batch_plan["summary"]["policy_url_batch_count"],
                "tii_priority_batches": batch_plan["summary"]["tii_priority_batch_count"],
                "tii_manual_matrix_batches": batch_plan["summary"]["tii_manual_matrix_batch_count"],
                "tii_attempted_manual_batches": tii_execution_summary.get("attempted_batches", 0),
                "tii_captcha_required_batches": tii_execution_summary.get("captcha_required_batches", 0),
                "tii_completed_manual_batches": tii_completed_batches,
                "tii_indexed_manual_batches": tii_indexed_batches,
                "tii_imported_records": tii_results["record_count"],
                "completed_policy_url_batches": batch_progress["summary"]["completed_policy_url_batches"],
                "policy_url_items_processed": batch_progress["summary"]["policy_url_items_processed"],
                "policy_content_extracted": content_summary["extracted_text_count"],
                "policy_content_field_hits": content_summary["records_with_field_hits"],
                "tii_document_summary_batches": len(document_summary_paths),
                "tii_reviewed_benefit_records": reviewed_benefit_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

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
        "per_event",
        "annual_limit",
        "benefit_base",
        "per_injury_limit",
        "additional_benefit",
    }
    allowed_calculation_bases = {
        "fixed_amount",
        "percentage_of_base",
        "plan_schedule_lookup",
        "per_unit",
        "per_unit_per_day",
        "per_day",
        "reimbursement_with_cap",
        "table_multiplier",
        "tiered_or_stepped",
        "additional_benefit",
        "unknown",
    }
    allowed_amount_roles = {"payout", "base", "limit", "reference", "unknown"}
    allowed_limit_scopes = {
        "per_policy",
        "per_event",
        "per_injury",
        "per_surgery",
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
            for field in ("rate", "rate_percent")
        )
        has_multiplier_formula = (
            calculation_basis == "table_multiplier"
            and isinstance(entry.get("multiplier"), (int, float))
            and not isinstance(entry.get("multiplier"), bool)
            and entry["multiplier"] > 0
        )
        if not (has_amount or has_percentage_formula or has_multiplier_formula):
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
    if input_mode not in {"face_amount", "plan", "unit", "multi_unit", "plan_unit", "fixed", "unknown"}:
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
        golden_complete_fields = {
            "disease_initial_waiting_days",
            "disease_reinstatement_waiting_days",
            "cancer_initial_waiting_days",
            "cancer_reinstatement_waiting_days",
            "maximum_renewal_age",
            "day_hospital_explicit",
            "day_hospital_excluded",
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
        cancer_lifetime_pool_fields = {
            "cancer_waiting_days",
            "specific_cancer_rate_percent",
            "per_unit_total_cap",
            "funeral_benefit_rule",
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
        if not isinstance(version, dict) or set(version) not in {
            frozenset(cancer_fields),
            frozenset(combined_health_fields),
            frozenset(golden_lohas_fields),
            frozenset(golden_complete_fields),
            frozenset(new_lohas_fields),
            frozenset(cancer_lifetime_pool_fields),
            frozenset(cancer_annuity_fields),
            frozenset(versioned_combined_fields),
            frozenset(new_complete_combined_fields),
        }:
            fail(f"coverage version characteristics fields are invalid: {context}")
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
        if "maximum_renewal_age" in version and version["maximum_renewal_age"] not in {65, 75}:
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
            revised_investment = (
                version["product_variant"] == "investment-linked"
                and version["revision"] == "first-revision"
            )
            if (
                version["terminates_next_policy_month_after_initial_cancer"]
                != revised_investment
                or version["post_death_actual_diagnosis_date_evidence_allowed"]
                != revised_investment
            ):
                fail(f"coverage cancer-annuity revision rules are invalid: {context}")
        if "disease_initial_waiting_days" in version and version["disease_initial_waiting_days"] != 30:
            fail(f"coverage disease waiting days are invalid: {context}")
        if "disease_reinstatement_waiting_days" in version and version["disease_reinstatement_waiting_days"] != 0:
            fail(f"coverage disease reinstatement waiting days are invalid: {context}")
        if "major_disease_initial_waiting_days" in version and version["major_disease_initial_waiting_days"] != 90:
            fail(f"coverage major-disease initial waiting days are invalid: {context}")
        if "major_disease_reinstatement_waiting_days" in version and version["major_disease_reinstatement_waiting_days"] not in {0, 90}:
            fail(f"coverage major-disease reinstatement waiting days are invalid: {context}")
        if "mild_cancer_initial_waiting_days" in version and version["mild_cancer_initial_waiting_days"] != 90:
            fail(f"coverage mild-cancer initial waiting days are invalid: {context}")
        if "mild_cancer_reinstatement_waiting_days" in version and version["mild_cancer_reinstatement_waiting_days"] not in {0, 90}:
            fail(f"coverage mild-cancer reinstatement waiting days are invalid: {context}")
        if "cancer_waiting_days" in version and version["cancer_waiting_days"] != 90:
            fail(f"coverage cancer waiting days are invalid: {context}")
        if "specific_cancer_rate_percent" in version and version["specific_cancer_rate_percent"] != 15:
            fail(f"coverage specific-cancer rate is invalid: {context}")
        if "per_unit_total_cap" in version and version["per_unit_total_cap"] != 1_000_000:
            fail(f"coverage per-unit total cap is invalid: {context}")
        if "funeral_benefit_rule" in version and version["funeral_benefit_rule"] not in {
            "pre-2010-fixed-funeral-cap",
            "2010-estate-tax-half-deduction",
        }:
            fail(f"coverage funeral-benefit rule is invalid: {context}")
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
        }:
            fail(f"coverage disability terminology is invalid: {context}")
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

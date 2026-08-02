from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


FAMILY_FINGERPRINT = "6c343a367843bf79a0d0fd26"
SOURCE_ROWS = (
    ("211313M11A00907", 7, "211313M11A00907-A.pdf", 8, "pypdf", "7ecd4e514cd0b37c954bb2e4fc57d69eedee7c20a8e89834ccc0f3fbbbd998f6", "031412ceb1a848d35f24c24ec9ca18f21f3d7394b305bc37a5a1e630c4d1bd59"),
    ("211313M11A00908", 8, "211313M11A00908-A.pdf", 8, "pypdf", "724116eed35fc334cb62a1cfa3ed6f677ebced392d091011d9b611c1950b6dd1", "82a8ae7bbc4496cf1948c0a43f101508cc7b730999e25df0c558e2d951bb4720"),
    ("211313MZ1A00921A11Z10000009", 9, "211313MZ1A00921A11Z10000009-A.pdf", 8, "pypdf", "42e30a706b0b65399257b5fc7f6da02a905ffae4307189e10e0df894f98544c8", "828ab3515041b9439a6ff5f81fdffc3624e96587e12b7ed00132e2d0af07c31a"),
    ("211313MZ1A00921A11Z10000010", 10, "211313MZ1A00921A11Z10000010-A.pdf", 8, "pypdf", "642e5eb6edbe88aa1821fec5ee73e0b073489f668fc4b21be7495586057f00c3", "e522d718c1be13da91a70a5df50a3b577caff1db3f5a0b032a300f835f20538b"),
    ("211313MZ1A00921A11Z10000011", 11, "211313MZ1A00921A11Z10000011-A.pdf", 8, "pypdf", "642e5eb6edbe88aa1821fec5ee73e0b073489f668fc4b21be7495586057f00c3", "e522d718c1be13da91a70a5df50a3b577caff1db3f5a0b032a300f835f20538b"),
    ("211313MZ1A00921A11Z10000012", 12, "211313MZ1A00921A11Z10000012-A.pdf", 9, "pypdf", "bc9defcd2b5c6be4e88f04ecdc712dd4e33d84b294fe8fb18328db7064de354b", "3bf58a4ab0237f4f887ad76f175996883f49d729ff36b31ac75385c4a98b530c"),
    ("211317M11A00900", 0, "211317M11A0090-A.pdf", 8, "pypdf", "bd95f1eea57bd85d541a5f052f2e1d8adac98129921eabbedbc39b8ece1d0254", "af27533e145fa3aca891041e1e34e928ef72f8a8164e050121a434f4bdd22ff4"),
    ("211317M11A00901", 1, "211317M11A0091-A.pdf", 9, "windows_ocr", "b3e70fef41453a3f973a136f2ed3ad25e71433562b26ca35635226e0925d8191", "b483dc53f05a12cf6da42ee52ee32c3ff8fd970df34c6aae3ae07d4d02a51a8f"),
    ("211317M11A00902", 2, "211317M11A00902-A.pdf", 8, "pypdf", "06e721857f41c8ef1b89edf2318061e01b0ecd95fedc74e589ddbe6f4b88a476", "9a4c242a917c3f1e2ff8863074c3d68f3a10a6174cece194bb2ae58dc5d5634c"),
    ("211317M11A00903", 3, "211317M11A00903-A.pdf", 8, "pypdf", "bc67fa789a1c5b4bc3c69d007342699e1f98531e8f6f075c29b8cd3a7ec570f9", "f6fc50ca65f26e303afb95c4fdda1024f037196defe89aae8cf9288e3ebecf13"),
    ("211317M11A00904", 4, "211317M11A00904-A.pdf", 9, "pypdf", "52861250225cfd47058beb34c21790a1f445e09e45a2385681ae67009605878d", "5ee5f37e23127eeb2c4cd7cc348225af4a6f4002c55195e6637c1bc98ecd77c3"),
    ("211317M11A00905", 5, "211317M11A00905-A.pdf", 8, "pypdf", "759faa9e0959dcb78d5f9c505df582b48f88a6f8b4d4c1ffc0be4a228b8ba410", "39df41be192365ae531c255afb38b80cdf570deba66750f0f5fccb94c8cb0fc5"),
    ("211317M11A00906", 6, "211317M11A00906-A.pdf", 8, "pypdf", "ee4eb168ccc24ffd769af5041b015a4df6d0c45977107f2a683ea16323188108", "9554bc88ec343637e0345023661e1518f146d38ce6677d8dc861b47b028fc1c8"),
)
VERSIONS = {
    product_id: {
        "revision": revision,
        "file_name": file_name,
        "page_count": page_count,
        "source_text_extractor": extractor,
        "source_document_sha256": document_sha,
        "source_text_sha256": text_sha,
    }
    for product_id, revision, file_name, page_count, extractor, document_sha, text_sha
    in SOURCE_ROWS
}
PRODUCT_IDS = frozenset(VERSIONS)

EVENT_STATUS_KEY = "mercantile_group_new_hospital_event_claim_status"
ROOM_DAILY_LIMIT_KEY = "mercantile_group_new_hospital_room_daily_limit"
MEDICAL_LIMIT_KEY = "mercantile_group_new_hospital_medical_limit"
SURGERY_BASE_LIMIT_KEY = "mercantile_group_new_hospital_surgery_base_limit"

POLICY_RECORDED_REVISIONS = frozenset({0, 1})
POST_EXPIRY_EXCLUSION_REVISIONS = frozenset(range(6, 13))
DAY_HOSPITAL_EXCLUSION_REVISIONS = frozenset({8, 9, 10, 11, 12})

VERSION_FIELDS = {
    "source_product_id",
    "family_fingerprint",
    "product_family",
    "company_group",
    "source_batch_id",
    "terms_revision",
    "semantic_phase",
    "source_document_sha256",
    "source_text_sha256",
    "source_text_extractor",
    "source_text_quality",
    "source_page_count",
    "currency_basis",
    "group_policy",
    "policy_term_years",
    "selection_basis",
    "plan_options",
    "unit_count_required",
    "unit_count_positive_integer",
    "insured_amount_unit_twd",
    "policy_recorded_limits_required",
    "benefit_entry_count",
    "actual_expense_reimbursement",
    "daily_cash_choice_available",
    "disease_waiting_days",
    "same_hospital_readmission_days",
    "post_expiry_readmission_excluded",
    "day_hospital_excluded",
    "post_discharge_radiotherapy_expense_days",
    "original_receipt_required_for_reimbursement",
    "daily_cash_when_original_receipt_unavailable",
    "hospital_day_limit_per_stay",
    "medical_limit_proration_threshold_days",
    "non_nhi_payment_rate_percent",
    "unlisted_surgery_nhi_points_per_ten_percent",
    "death_benefit_available",
    "premium_waiver_available",
    "required_policy_inputs",
    "claim_event_inputs",
    "amount_presentation",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text))


def is_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    version = VERSIONS.get(product_id)
    return bool(
        version
        and str(document.get("batch_id") or "") == "tii-life-062"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
        and str(document.get("source_document_sha256") or "")
        == version["source_document_sha256"]
    )


def uses_policy_recorded_limits(revision: int) -> bool:
    return revision in POLICY_RECORDED_REVISIONS


def has_post_expiry_exclusion(revision: int) -> bool:
    return revision in POST_EXPIRY_EXCLUSION_REVISIONS


def has_day_hospital_exclusion(revision: int) -> bool:
    return revision in DAY_HOSPITAL_EXCLUSION_REVISIONS


def semantic_phase(revision: int) -> str:
    phases = (
        "legacy-social-insurance-policy-limits",
        "legacy-social-insurance-policy-limits-ocr-revision",
        "nhi-per-hundred-insured-amount-table",
        "nhi-table-regulatory-revision-2007",
        "nhi-table-regulatory-revision-2008",
        "nhi-table-regulatory-revision-2009",
        "post-expiry-readmission-exclusion-2010",
        "post-expiry-wording-revision-2012",
        "day-hospital-and-post-expiry-exclusion-2014",
        "day-hospital-and-post-expiry-2015",
        "medical-opinion-revision-2020",
        "medical-opinion-regulatory-revision-2022",
        "medical-opinion-regulatory-revision-2024",
    )
    return phases[revision]


def eligibility(revision: int, claim_mode: str) -> dict[str, Any]:
    opposite = "daily_cash" if claim_mode == "reimbursement" else "reimbursement"
    ineligible = [opposite, "confirmed_not_eligible"]
    uncertain = ["uncertain"]
    if has_post_expiry_exclusion(revision):
        ineligible.append("post_expiry_readmission")
    else:
        uncertain.append("post_expiry_readmission")
    if has_day_hospital_exclusion(revision):
        ineligible.append("day_hospital_or_day_care")
    else:
        uncertain.append("day_hospital_or_day_care")
    return {
        "eligibility_state_key": EVENT_STATUS_KEY,
        "ineligible_values": ineligible,
        "uncertain_values": uncertain,
    }


def reimbursement_common(revision: int) -> dict[str, Any]:
    return {
        "amount_role": "payout",
        "aggregation_rule": "choose_one",
        "benefit_group_id": "mercantile-group-new-hospital-reimbursement-or-daily",
        "rate_percent": 66,
        "rate_condition_state_key": "national_health_insurance_payment_status",
        "rate_condition_value": "not_covered",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **eligibility(revision, "reimbursement"),
    }


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    policy_recorded = uses_policy_recorded_limits(revision)
    room_amount = None if policy_recorded else 100
    medical_amount = None if policy_recorded else 3_000
    surgery_amount = None if policy_recorded else 4_000
    room_basis = "policy_recorded_limit" if policy_recorded else "daily_per_unit"
    other_basis = "policy_recorded_limit" if policy_recorded else "per_unit"
    room_unit_key = ROOM_DAILY_LIMIT_KEY if policy_recorded else None
    medical_unit_key = MEDICAL_LIMIT_KEY if policy_recorded else None
    surgery_unit_key = SURGERY_BASE_LIMIT_KEY if policy_recorded else None
    common = reimbursement_common(revision)
    entries = [
        {
            "id": "daily-room-expense-reimbursement",
            "name": "每日病房費用保險金",
            "amount": room_amount,
            "basis": room_basis,
            "source": "terms",
            "note": "按符合條款的病房、膳食及護理實際費用核付；每次住院最高一百二十日。",
            "source_ref": "每日病房費用保險金之給付與附表三",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": room_unit_key,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap": 120,
            "expense_state_key": "hospital_room_expense",
            "limit_scope": "per_hospitalization",
            **common,
        },
        {
            "id": "inpatient-medical-expense-reimbursement",
            "name": "住院醫療費用保險金",
            "amount": medical_amount,
            "basis": other_basis,
            "source": "terms",
            "note": "同一次住院三十日內依基本限額；超過三十日後以基本限額除以三十再乘實際住院日數，最高計一百二十日。",
            "source_ref": "住院醫療費用保險金之給付與附表三",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": medical_unit_key,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap": 120,
            "limit_proration_threshold": 30,
            "expense_state_key": "inpatient_medical_expense",
            "limit_scope": "per_hospitalization",
            **common,
        },
        {
            "id": "inpatient-surgery-expense-reimbursement",
            "name": "手術費用保險金",
            "amount": surgery_amount,
            "basis": other_basis,
            "source": "terms",
            "note": "每次手術基準限額乘手術名稱及費用表百分比，並以符合條款的實際手術費用為上限。",
            "source_ref": "手術費用保險金之給付、手術名稱及費用表與附表三",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": surgery_unit_key,
            "limit_rate_state_key": "surgery_benefit_rate_percent",
            "rate_max_percent": 500,
            "expense_state_key": "inpatient_surgery_expense",
            "limit_scope": "per_surgery",
            **common,
        },
        {
            "id": "hospital-daily-cash-alternative",
            "name": "住院日額保險金選擇權",
            "amount": room_amount,
            "basis": room_basis,
            "source": "terms",
            "note": "無法提供醫療費用收據正本時，可按每日病房費用限額與實際住院日數改領日額；同一次事故不得再申請三項實支給付。",
            "source_ref": "住院日額保險金選擇權",
            "calculation_basis": "reimbursement_with_cap",
            "amount_role": "payout",
            "unit_key": room_unit_key,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap": 120,
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "choose_one",
            "benefit_group_id": "mercantile-group-new-hospital-reimbursement-or-daily",
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            **eligibility(revision, "daily_cash"),
        },
    ]
    return [{key: value for key, value in entry.items() if value is not None} for entry in entries]


def expected_entry_contracts(revision: int) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        entry["id"]: {
            key: value
            for key, value in entry.items()
            if key not in ignored and key != "id"
        }
        for entry in coverage_entries(revision)
    }


def expected_identity(product_id: str) -> dict[str, Any]:
    source = VERSIONS[product_id]
    revision = int(source["revision"])
    policy_recorded = uses_policy_recorded_limits(revision)
    required_policy_inputs = (
        [ROOM_DAILY_LIMIT_KEY, MEDICAL_LIMIT_KEY, SURGERY_BASE_LIMIT_KEY]
        if policy_recorded
        else ["unit_count"]
    )
    claim_event_inputs = [
        EVENT_STATUS_KEY,
        "hospitalization_days",
        "hospital_room_expense",
        "inpatient_medical_expense",
        "inpatient_surgery_expense",
        "surgery_benefit_rate_percent",
        "national_health_insurance_payment_status",
    ]
    return {
        "source_product_id": product_id,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_family": "mercantile-group-new-hospital-medical",
        "company_group": "mercantile_life",
        "source_batch_id": "tii-life-062",
        "terms_revision": "initial" if revision == 0 else f"partial_change_{revision}",
        "semantic_phase": semantic_phase(revision),
        "source_document_sha256": source["source_document_sha256"],
        "source_text_sha256": source["source_text_sha256"],
        "source_text_extractor": source["source_text_extractor"],
        "source_text_quality": (
            "machine_readable_exact_hash_windows_ocr_full_document"
            if source["source_text_extractor"] == "windows_ocr"
            else "machine_readable_exact_hash"
        ),
        "source_page_count": source["page_count"],
        "currency_basis": "twd",
        "group_policy": True,
        "policy_term_years": 1,
        "selection_basis": (
            "policy_recorded_limits"
            if policy_recorded
            else "each_unit_equals_twd_100_insured_amount"
        ),
        "plan_options": False,
        "unit_count_required": not policy_recorded,
        "unit_count_positive_integer": not policy_recorded,
        "insured_amount_unit_twd": None if policy_recorded else 100,
        "policy_recorded_limits_required": policy_recorded,
        "benefit_entry_count": 4,
        "actual_expense_reimbursement": True,
        "daily_cash_choice_available": True,
        "disease_waiting_days": 0,
        "same_hospital_readmission_days": 14,
        "post_expiry_readmission_excluded": has_post_expiry_exclusion(revision),
        "day_hospital_excluded": has_day_hospital_exclusion(revision),
        "post_discharge_radiotherapy_expense_days": 90 if revision <= 1 else 0,
        "original_receipt_required_for_reimbursement": True,
        "daily_cash_when_original_receipt_unavailable": True,
        "hospital_day_limit_per_stay": 120,
        "medical_limit_proration_threshold_days": 30,
        "non_nhi_payment_rate_percent": 66,
        "unlisted_surgery_nhi_points_per_ten_percent": 500,
        "death_benefit_available": False,
        "premium_waiver_available": False,
        "required_policy_inputs": required_policy_inputs,
        "claim_event_inputs": claim_event_inputs,
        "amount_presentation": (
            "policy_recorded_limits_with_claim_expenses_and_choice"
            if policy_recorded
            else "insured_amount_units_with_claim_expenses_and_choice"
        ),
    }


def parse_policy(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    source = VERSIONS[product_id]
    if (
        document.get("page_count") != source["page_count"]
        or document.get("pages_parsed") != source["page_count"]
        or str(document.get("source_text_extractor") or "")
        != source["source_text_extractor"]
    ):
        return None
    text = normalize_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != source["source_text_sha256"]:
        return None
    dense = compact_text(text)
    common_signals = (
        "團體新住院醫療保險",
        "每日病房費用保險金",
        "住院醫療費用保險金",
        "手術費用保險金",
        "住院日額保險金",
        "醫療費用收據正本",
        "手術名稱及費用表",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(source["revision"])
    if revision != 1:
        phase_checks = (
            ("每百元保額" in dense, revision >= 2),
            ("社會保險" in dense, revision == 0),
            (
                "出院後九十日內仍繼續接受門診放射線治療" in dense,
                revision == 0,
            ),
            ("日間住院" in dense, has_day_hospital_exclusion(revision)),
            (
                "契約有效期間屆滿後出院" in dense,
                has_post_expiry_exclusion(revision),
            ),
            ("醫學專業意見" in dense, revision >= 10),
        )
        if any(actual is not expected for actual, expected in phase_checks):
            return None
    policy_recorded = uses_policy_recorded_limits(revision)
    result = {
        "selection_type": "policy_state" if policy_recorded else "unit",
        "input_mode": "policy_state" if policy_recorded else "unit",
        "selection_source": "terms",
        "selection_label": "輸入保單記載限額" if policy_recorded else "投保單位數",
        "selection_guidance": (
            "這個早期版本的官方條款未附數值限額表；請依保險單、保險證、名冊或批註輸入每日病房、每次住院醫療及每次手術基準限額。"
            if policy_recorded
            else "請輸入保單記載的正整數投保單位；條款附表三明定每一單位等於新臺幣 100 元保額。"
        ),
        "version_characteristics": expected_identity(product_id),
        "coverage_entries": coverage_entries(revision),
    }
    if policy_recorded:
        result["plan_options"] = []
    return result


def validate_contract(
    record: dict[str, Any],
    version: dict[str, Any],
    context: str,
    *,
    fail: Callable[[str], None],
    validate_entries: Callable[[object, dict[str, dict[str, Any]], str], None],
) -> None:
    product_id = str(version.get("source_product_id") or "")
    source = VERSIONS.get(product_id)
    if source is None:
        fail(f"coverage Mercantile group new hospital source product is invalid: {context}")
    revision = int(source["revision"])
    policy_recorded = uses_policy_recorded_limits(revision)
    if (
        record.get("product_id") not in {None, product_id}
        or record.get("selection_type") != ("policy_state" if policy_recorded else "unit")
        or record.get("input_mode") != ("policy_state" if policy_recorded else "unit")
        or record.get("selection_source") != "terms"
        or (policy_recorded and record.get("plan_options") != [])
        or (not policy_recorded and "plan_options" in record)
        or any(
            version.get(key) != value
            for key, value in expected_identity(product_id).items()
        )
    ):
        fail(
            "coverage Mercantile group new hospital source or version boundary "
            f"is invalid: {context}"
        )
    validate_entries(
        record.get("coverage_entries"),
        expected_entry_contracts(revision),
        f"{context} Mercantile group new hospital medical",
    )

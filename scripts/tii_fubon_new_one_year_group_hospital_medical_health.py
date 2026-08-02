from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


FAMILY_FINGERPRINT = "0a450de970798bc35158c095"
SOURCE_ROWS = (
    ("209313M11A00206", 0, "209313M11A00206-A.pdf", 9, "pypdf", "2323ccfdbafdf98c2d16fae5adc9a201b639a180df3e034008cef9c9ce0629a7", "7f78795faed107221a899539539f27d236b78a13a60df47b379d615276392f87"),
    ("209313M11A00207", 1, "209313M11A00207-A.pdf", 9, "pypdf", "bafef802c9d4c2835a106e97e84cacbb6924952a0cd7181e0cb0e00b72f83509", "fe429d837affc611ed3fdb8f75e72e215f8cccdce15ad476f0273d3559a9d87e"),
    ("209313MZ1A00121A11Z10000008", 2, "209313MZ1A00121A11Z10000008-A.pdf", 10, "pypdf", "d6272f5b3e55b7cba9a60c3499253e78ebdf570cba1da16697c079986c0cd35e", "86401ea3207621c2f85d70c9b302857a94868db3f635273fea98d855211f805b"),
    ("209313MZ1A00121A11Z10000009", 3, "209313MZ1A00121A11Z10000009-A.pdf", 10, "pypdf", "7dda212ce304c294504656f740d3c7bfacfdd98d996fb66967f8436ea1018562", "ddc9e04a975b5b195fa1e51bb2286263d7e77652a86300df2c62bc3ee5ea343c"),
    ("209313MZ1A00121A11Z10000010", 4, "209313MZ1A00121A11Z10000010-A.pdf", 10, "pypdf", "8e0c48f601afb31d129f558fc6297df843154beb8cf9f0704a13c0a4fb1e0180", "17f4a6547fdc010f63135a0b4be7750664018667018e9c27cd201f46e1b26ef7"),
    ("209313MZ1A00121A11Z10000011", 5, "209313MZ1A00121A11Z10000011-A.pdf", 10, "pypdf", "977157e9efe86ad335227f9def207b1ffebf6109a807b3384bf832d56bbe33f5", "f5c6116614da2dab3bc4b4b85af2af22813136d5ce4a96741b1c1193f86a910e"),
    ("209313MZ1A00121A11Z10000012", 6, "209313MZ1A00121A11Z10000012-A.pdf", 10, "pypdf", "b6325909f4e35f6a57fede0f2c5df8b9c0d52103c3f2d28c07713024c50a1878", "cf8ffc43a7856ff07094ea4257e05550e3c74df5b8e2a7f5f29ebeee802b0371"),
    ("209313MZ1A00121A11Z10000013", 7, "209313MZ1A00121A11Z10000013-A.pdf", 10, "pypdf", "27298e668d4fc9b4caf6a01d5804c02d09040ba1a3c3cfc6f2716dd26ded75a4", "c1e5ff59f4d92760b7e17eb8f340e573c17bed8f990f9ae907c160ef3c3ee09f"),
    ("209317M11A00701", 8, "209317M11A00701-A.pdf", 9, "pypdf", "f1c229dfac299d47fe6da4e29631f9314d11404eaa59db5105f638fd8231293e", "a017b7d37a1b9949f8ffbe8555158bf30d208fc921caeeba9c4015c41e1527f9"),
    ("209317M11A00702", 9, "209317M11A00702-A.pdf", 9, "pypdf", "41d789c035ac791f7996e4672917ebafef816de578a3cffab3ff24c77747f538", "189a4918069a1ce77f16cb0c9d4d3f55c1cd29add0845a78c74c93d697bbcdaa"),
    ("209317M11A00703", 10, "209317M11A00703-A.pdf", 9, "pymupdf", "274dfe83b17a39f05ddba491254f36e567451b09cae6b58d592c6bbb342b8773", "4337e82407ca1181c66549c5b81ae1f144e2ce43bc3bec89c29ba98bb658dfd3"),
    ("209317M11A00704", 11, "209317M11A00704-A.pdf", 9, "pypdf", "bd8a9217bb9f01de90a35ce0480a28e1251f20f833c0da137fcf71db42d65910", "ab226bca1b1209f24aad62d9a1d3e10e4dc006b6280c387b84193c659adcb49d"),
    ("209317M11A00705", 12, "209317M11A00705-A.pdf", 9, "pypdf", "745ffbecc613ffe6f62d107dd5817abe4134e3a254508d92d58679541b42f999", "4a2039e7da85946c4efb85f778e8995d6a2de0b0f55142fe02d9169a5ea0c8b5"),
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

EVENT_STATUS_KEY = "fubon_new_group_hospital_event_claim_status"
ROOM_DAILY_LIMIT_KEY = "fubon_new_group_hospital_room_daily_limit"
MEDICAL_LIMIT_KEY = "fubon_new_group_hospital_medical_limit"
SURGERY_LIMIT_KEY = "fubon_new_group_hospital_surgery_limit"
MAX_DAYS_KEY = "fubon_new_group_hospital_max_days"
ICU_DAILY_LIMIT_KEY = "fubon_new_group_hospital_icu_daily_limit"
ICU_MAX_DAYS_KEY = "fubon_new_group_hospital_icu_max_days"
BURN_DAILY_LIMIT_KEY = "fubon_new_group_hospital_burn_daily_limit"
BURN_MAX_DAYS_KEY = "fubon_new_group_hospital_burn_max_days"
SPECIAL_AGREEMENT_KEY = "fubon_new_group_hospital_special_agreement_status"

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
    "plan_options",
    "unit_count_required",
    "benefit_entry_count",
    "actual_expense_reimbursement",
    "daily_cash_choice_available",
    "disease_waiting_days",
    "accident_waiting_period_exempt",
    "newborn_screening_exception",
    "same_hospital_readmission_days",
    "post_expiry_readmission_excluded",
    "day_hospital_excluded",
    "temporary_stay_over_six_hours_covered",
    "outpatient_surgery_day_covered",
    "accident_emergency_hours",
    "accident_emergency_expense_limit",
    "pre_hospital_outpatient_days",
    "post_hospital_outpatient_days",
    "post_surgery_outpatient_days",
    "non_nhi_payment_rate_percent",
    "surgery_rate_min_percent",
    "surgery_rate_max_percent",
    "maximum_hospital_days_policy_recorded",
    "icu_special_agreement_required",
    "burn_special_agreement_required",
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
        and str(document.get("batch_id") or "") == "tii-life-050"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
        and str(document.get("source_document_sha256") or "")
        == version["source_document_sha256"]
    )


def has_newborn_screening_exception(revision: int) -> bool:
    return revision <= 7 or revision >= 11


def has_post_expiry_exclusion(revision: int) -> bool:
    return revision <= 7 or revision == 12


def has_day_hospital_exclusion(revision: int) -> bool:
    return revision <= 7


def semantic_phase(revision: int) -> str:
    phases = (
        "day_hospital_newborn_post_expiry_2014",
        "template_revision_2015",
        "group_definition_revision_2015",
        "medical_opinion_revision_2020",
        "regulatory_revision_2022",
        "notice_method_revision_2023",
        "template_revision_late_2023",
        "central_authority_revision_2024",
        "initial_2009",
        "special_agreement_disclosure_2009",
        "claim_revision_2010",
        "newborn_exception_2012",
        "post_expiry_clause_2013",
    )
    return phases[revision]


def eligibility(revision: int, claim_mode: str) -> dict[str, Any]:
    opposite = "daily_cash" if claim_mode == "reimbursement" else "reimbursement"
    ineligible = [
        f"{opposite}_disease_after_waiting",
        f"{opposite}_injury",
        f"{opposite}_newborn_screening_exception",
        "disease_waiting_not_met",
        "confirmed_not_eligible",
    ]
    uncertain = ["uncertain"]
    own_newborn = f"{claim_mode}_newborn_screening_exception"
    if not has_newborn_screening_exception(revision):
        ineligible.append(own_newborn)
    if has_day_hospital_exclusion(revision):
        ineligible.append("day_hospital_or_day_care")
    else:
        uncertain.append("day_hospital_or_day_care")
    if has_post_expiry_exclusion(revision):
        ineligible.append("post_expiry_readmission")
    else:
        uncertain.append("post_expiry_readmission")
    return {
        "eligibility_state_key": EVENT_STATUS_KEY,
        "ineligible_values": ineligible,
        "uncertain_values": uncertain,
    }


def reimbursement_common(revision: int) -> dict[str, Any]:
    return {
        "amount_role": "payout",
        "aggregation_rule": "choose_one",
        "benefit_group_id": "fubon-new-group-hospital-reimbursement-or-daily",
        "rate_percent": 65,
        "rate_condition_state_key": "national_health_insurance_payment_status",
        "rate_condition_value": "not_covered",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **eligibility(revision, "reimbursement"),
    }


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    common = reimbursement_common(revision)
    entries = [
        {
            "id": "room-and-board-reimbursement",
            "name": "病房及膳食費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "以保險單每日病房及膳食費限額乘實際住院日數，並與實際支出取低；日數受保單記載最高給付日數限制。",
            "source_ref": "第八條",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": ROOM_DAILY_LIMIT_KEY,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap_state_key": MAX_DAYS_KEY,
            "expense_state_key": "hospital_room_expense",
            "limit_scope": "per_hospitalization",
            **common,
        },
        {
            "id": "hospital-medical-reimbursement",
            "name": "每次住院醫療費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "依條款列舉的住院醫療、六小時以上暫留、門診手術當日、意外急診與住院前後門診費用，與保險單每次住院限額取低。",
            "source_ref": "第九條",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": MEDICAL_LIMIT_KEY,
            "expense_state_key": "inpatient_medical_expense",
            "limit_scope": "per_hospitalization",
            **common,
        },
        {
            "id": "surgery-reimbursement",
            "name": "每次外科手術費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "以保險單手術限額乘手術附表百分率，再與實際手術費取低；同一手術位置多器官只取最高比例。",
            "source_ref": "第十條及附表一",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": SURGERY_LIMIT_KEY,
            "limit_rate_state_key": "surgery_benefit_rate_percent",
            "rate_min_percent": 10,
            "rate_max_percent": 500,
            "expense_state_key": "inpatient_surgery_expense",
            "limit_scope": "per_surgery",
            **common,
        },
        {
            "id": "intensive-care-reimbursement",
            "name": "加護病房費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "僅在要保人與保險公司有特別約定且可申領病房費用時，按保單每日限額乘加護病房日數，與實際支出取低。",
            "source_ref": "第十一條",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": ICU_DAILY_LIMIT_KEY,
            "quantity_state_key": "intensive_care_days",
            "quantity_cap_state_key": ICU_MAX_DAYS_KEY,
            "expense_state_key": "intensive_care_room_expense",
            "exclusion_state_key": SPECIAL_AGREEMENT_KEY,
            "exclusion_values": ["burn_only", "neither_included"],
            "limit_scope": "per_hospitalization",
            **common,
        },
        {
            "id": "burn-center-reimbursement",
            "name": "燒燙傷中心費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "僅在要保人與保險公司有特別約定且可申領病房費用時，按保單每日限額乘燒燙傷中心日數，與實際支出取低。",
            "source_ref": "第十二條",
            "calculation_basis": "reimbursement_with_cap",
            "unit_key": BURN_DAILY_LIMIT_KEY,
            "quantity_state_key": "burn_unit_days",
            "quantity_cap_state_key": BURN_MAX_DAYS_KEY,
            "expense_state_key": "burn_unit_room_expense",
            "exclusion_state_key": SPECIAL_AGREEMENT_KEY,
            "exclusion_values": ["icu_only", "neither_included"],
            "limit_scope": "per_hospitalization",
            **common,
        },
        {
            "id": "hospital-daily-cash-alternative",
            "name": "住院日額補償保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "同一次住院可改選日額給付；按每日病房及膳食費限額乘實際住院日數，受保單最高給付日數限制，選擇後不得再申領第八至十二條。",
            "source_ref": "第十三條",
            "calculation_basis": "reimbursement_with_cap",
            "amount_role": "payout",
            "unit_key": ROOM_DAILY_LIMIT_KEY,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap_state_key": MAX_DAYS_KEY,
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "choose_one",
            "benefit_group_id": "fubon-new-group-hospital-reimbursement-or-daily",
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            **eligibility(revision, "daily_cash"),
        },
        {
            "id": "accident-emergency-expense-sublimit",
            "name": "意外急診費用子限額",
            "amount": 5_000,
            "basis": "per_event_limit",
            "source": "terms",
            "note": "意外事故發生後二十四小時內急診的實際費用，以五千元為上限，且仍屬每次住院醫療費用保險金的列舉範圍，不另行加總。",
            "source_ref": "第九條第十六款",
            "calculation_basis": "fixed_amount",
            "amount_role": "reference",
            "limit_scope": "per_event",
            "aggregation_rule": "separate",
            "result_kind": "reference",
            "amount_stage": "not_applicable",
        },
    ]
    return entries


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
    required_policy_inputs = [
        ROOM_DAILY_LIMIT_KEY,
        MEDICAL_LIMIT_KEY,
        SURGERY_LIMIT_KEY,
        MAX_DAYS_KEY,
        ICU_DAILY_LIMIT_KEY,
        ICU_MAX_DAYS_KEY,
        BURN_DAILY_LIMIT_KEY,
        BURN_MAX_DAYS_KEY,
        SPECIAL_AGREEMENT_KEY,
    ]
    claim_event_inputs = [
        EVENT_STATUS_KEY,
        "hospitalization_days",
        "hospital_room_expense",
        "inpatient_medical_expense",
        "inpatient_surgery_expense",
        "intensive_care_days",
        "intensive_care_room_expense",
        "burn_unit_days",
        "burn_unit_room_expense",
        "surgery_benefit_rate_percent",
        "national_health_insurance_payment_status",
    ]
    return {
        "source_product_id": product_id,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_family": "fubon-new-one-year-group-hospital-medical-health",
        "company_group": "fubon_life",
        "source_batch_id": "tii-life-050",
        "terms_revision": f"partial_change_{revision}",
        "semantic_phase": semantic_phase(revision),
        "source_document_sha256": source["source_document_sha256"],
        "source_text_sha256": source["source_text_sha256"],
        "source_text_extractor": source["source_text_extractor"],
        "source_text_quality": "machine_readable_exact_hash",
        "source_page_count": source["page_count"],
        "currency_basis": "twd",
        "group_policy": True,
        "policy_term_years": 1,
        "plan_options": False,
        "unit_count_required": False,
        "benefit_entry_count": 7,
        "actual_expense_reimbursement": True,
        "daily_cash_choice_available": True,
        "disease_waiting_days": 30,
        "accident_waiting_period_exempt": True,
        "newborn_screening_exception": has_newborn_screening_exception(revision),
        "same_hospital_readmission_days": 14,
        "post_expiry_readmission_excluded": has_post_expiry_exclusion(revision),
        "day_hospital_excluded": has_day_hospital_exclusion(revision),
        "temporary_stay_over_six_hours_covered": True,
        "outpatient_surgery_day_covered": True,
        "accident_emergency_hours": 24,
        "accident_emergency_expense_limit": 5_000,
        "pre_hospital_outpatient_days": 7,
        "post_hospital_outpatient_days": 7,
        "post_surgery_outpatient_days": 14,
        "non_nhi_payment_rate_percent": 65,
        "surgery_rate_min_percent": 10,
        "surgery_rate_max_percent": 500,
        "maximum_hospital_days_policy_recorded": True,
        "icu_special_agreement_required": True,
        "burn_special_agreement_required": True,
        "death_benefit_available": False,
        "premium_waiver_available": False,
        "required_policy_inputs": required_policy_inputs,
        "claim_event_inputs": claim_event_inputs,
        "amount_presentation": "policy_recorded_limits_with_exact_claim_expenses_and_choice",
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
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != source[
        "source_text_sha256"
    ]:
        return None
    dense = compact_text(text)
    common_signals = (
        "富邦人壽新一年定期住院醫療團體健康保險",
        "病房及膳食費用保險金之給付",
        "每次住院醫療費用保險金之給付",
        "每次外科手術費用保險金之給付",
        "加護病房費用保險金之給付",
        "燒燙傷中心費用保險金之給付",
        "住院日額補償保險金選擇給付",
        "手術名稱及費用表",
        "新台幣五千元",
        "實際支付之各項費用之65%給付",
        "10%",
        "500%",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(source["revision"])
    phase_checks = (
        ("先天性代謝異常疾病" in dense, has_newborn_screening_exception(revision)),
        ("本公司就再次住院部分不予給付保險金" in dense, has_post_expiry_exclusion(revision)),
        ("日間住院" in dense, has_day_hospital_exclusion(revision)),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "輸入保險單限額與本次住院理賠資料",
        "selection_guidance": (
            "請依本 productId 的保險單、被保險人名冊或批註輸入各項限額與最高日數；再依診斷、收據、手術附表及本次選擇的實支實付或日額方式輸入事故資料。"
        ),
        "plan_options": [],
        "version_characteristics": expected_identity(product_id),
        "coverage_entries": coverage_entries(revision),
    }


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
        fail(f"coverage Fubon new group hospital source product is invalid: {context}")
    revision = int(source["revision"])
    if (
        record.get("product_id") not in {None, product_id}
        or record.get("selection_type") != "policy_state"
        or record.get("input_mode") != "policy_state"
        or record.get("selection_source") != "terms"
        or record.get("plan_options") != []
        or any(
            version.get(key) != value
            for key, value in expected_identity(product_id).items()
        )
    ):
        fail(
            f"coverage Fubon new group hospital source or version boundary is invalid: {context}"
        )
    validate_entries(
        record.get("coverage_entries"),
        expected_entry_contracts(revision),
        f"{context} Fubon new one-year group hospital medical health",
    )

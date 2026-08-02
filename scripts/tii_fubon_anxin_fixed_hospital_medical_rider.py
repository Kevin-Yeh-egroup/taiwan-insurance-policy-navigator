from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


FAMILY_FINGERPRINT = "bda5324329f53195079062df"
SOURCE_ROWS = (
    ("209311R11A00200", 0, "209311R11A002-A.pdf", 6, "pypdf", "6878354c41b33faadc1e5cfa36f82da719eb6efaac000cfbb38635b32556961f", "d8e78f8686c3bc0ab46bda0e9cda1307be4cab4fc1a8f932c8a1fba58ffdc867"),
    ("209311R11A00201", 1, "209311R11A00201-A.pdf", 7, "pymupdf", "33bba7db1f7db16053dc0f4b5844c0cad648f87ec132d586a366cceb12db3905", "bf70f62f87d6dbb437e0a2520fbd64e44083e11ed65fe3a69c5c9b730464f535"),
    ("209311R11A00202", 2, "209311R11A00202-A.pdf", 6, "pymupdf", "f3be2f725ee501cb9dcfcdcc3bd5b099bf12a101b26a098a9b52952c86b6f8d7", "87c0958228b35dcdc90b4ce1c0504486114b629a1537d875c7fff78ee7c42bc4"),
    ("209311R11A00203", 3, "209311R11A00203-A.pdf", 6, "pymupdf", "1e61ffb1a572ea56e4c561612365fec4e6318ae1150642fa556be83c3346577f", "b7943250e48890c4a37144854ebfde6ab2517aa23d57be9b53462571dc2a725f"),
    ("209311R11A00204", 4, "209311R11A00204-A.pdf", 6, "pypdf", "d4b1409bb5d01eba6c82ea8b38ccc860a29705d07bc21b36c15042595d9872e7", "0771ed71a4fa5ec2880db769317c57d23546ffe72b14221ad1c989f5a99212eb"),
    ("209311R11A00205", 5, "209311R11A00205-A.pdf", 6, "pypdf", "2421cd7441ea48393c80eef3ff928f73a835cb5f62bdd2ef445efec6dfbe6c4e", "88e7418db2d6a54dcafdf32cfaa0c3a734ffdcb6aa84ee0ca8dd264c177ffb8d"),
    ("209311R11A00206", 6, "209311R11A00206-A.pdf", 8, "pypdf", "8ff8140d2ba24d9b70ff37292cace644714b201804336bd66c724cd7949e5181", "bd5f31ce636a5d4756063b45d22b1c7e14e309dda179213554a30998a4392754"),
    ("209311R11A00207", 7, "209311R11A00207-A.pdf", 8, "pypdf", "e0caedd84c07847547ad8d87b6b86068efda4894efd657bb42aa429154b42a4d", "b81170a4b46f0754bce3f7492d44c546cc96c1ec2dc8afd0241d4acd1a8e8f37"),
    ("209311R11A00208", 8, "209311R11A00208-A.pdf", 8, "pypdf", "918700102a6f77c78bb42ffccad4e8e8d8af26369c010b19f2dea33d9d5dd0de", "3e2e8f4078409b547fc394a21be653a0a2288e92fbe5063faacfad0487e3f7c1"),
    ("209311R11A00209", 9, "209311R11A00209-A.pdf", 8, "pypdf", "784063c9ccdf604cc83fcfe02a695070578445a66d97d431bb5cda40d7bc5de2", "4ad8cabd01c739f269c60af7ab479c317cd7a2ee290001a66cc7d7a445b98c2e"),
    ("209311RZ1A01021A11Z10000010", 10, "209311RZ1A01021A11Z10000010-A.pdf", 8, "pypdf", "ababf37719ad9c6d6d76574d2b0e6c8692cb6d42c2b09f1644e40f68d1d231b2", "e916402bb136e787ab1011f7b700b25c4afbe9bcf7d4ef2629cc855868c68ee1"),
    ("209311RZ1A01021A11Z10000011", 11, "209311RZ1A01021A11Z10000011-A.pdf", 8, "pypdf", "26534323e173c68f0902fbd464a1722d8a67dad034b50eb869579aaa92b217e8", "9b0e23a3dce0ec3eb764018cbe0b12f99ffb118fe2f5480e79f7451c03084918"),
    ("209311RZ1A01021A11Z10000012", 12, "209311RZ1A01021A11Z10000012-A.pdf", 9, "pypdf", "3503454a3d5920ed67e3293df1a8f9e1caabb70d7a413c60b12c8d22fd17e726", "ad9093c13802b4c8e1e0db333fe4e2ff6065078cb5330d15c593e4e393011bf9"),
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

EVENT_STATUS_KEY = "fubon_anxin_hospital_event_status"
HEALTH_INCREMENT_RATE_KEY = "fubon_anxin_health_increment_rate_percent"
HIGHEST_SURGERY_RATE_KEY = "fubon_anxin_highest_surgery_rate_percent"

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
    "rider",
    "policy_amount_source",
    "disease_waiting_days",
    "accident_waiting_period_exempt",
    "same_hospital_readmission_days",
    "post_expiry_readmission_excluded",
    "day_hospital_excluded",
    "day_hospital_legal_reference_revision",
    "hospital_day_limit",
    "hospital_day_31_to_365_rate_percent",
    "intensive_care_daily_rate_percent",
    "intensive_care_day_limit",
    "burn_unit_daily_rate_percent",
    "burn_unit_day_limit",
    "inpatient_nursing_daily_rate_percent",
    "inpatient_nursing_day_limit",
    "discharge_recuperation_daily_rate_percent",
    "discharge_recuperation_day_limit",
    "surgery_base_daily_multiplier",
    "surgery_nursing_base_daily_multiplier",
    "surgery_rate_min_percent",
    "surgery_rate_max_percent",
    "same_stay_surgery_aggregate_rule",
    "same_location_surgery_rule",
    "health_increment_interval_months",
    "health_increment_rate_percent",
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


def semantic_phase(revision: int) -> str:
    if revision <= 1:
        return "ninety_day_readmission"
    if revision <= 7:
        return "fourteen_day_readmission"
    if revision == 8:
        return "post_expiry_readmission_exclusion"
    return "day_hospital_and_post_expiry_exclusions"


def eligibility(revision: int) -> dict[str, Any]:
    ineligible = ["disease_waiting_not_met", "confirmed_not_eligible"]
    uncertain = ["uncertain"]
    if revision >= 9:
        ineligible.append("day_hospital_or_day_stay")
    else:
        uncertain.append("day_hospital_or_day_stay")
    if revision >= 8:
        ineligible.append("post_expiry_readmission")
    else:
        uncertain.append("post_expiry_readmission")
    return {
        "eligibility_state_key": EVENT_STATUS_KEY,
        "ineligible_values": ineligible,
        "uncertain_values": uncertain,
    }


def _entry(
    entry_id: str,
    name: str,
    note: str,
    source_ref: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "name": name,
        "amount": None,
        "basis": "hospital_daily_amount",
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **fields,
    }


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    eligible = eligibility(revision)
    hospital_related_ids = [
        "hospital-daily-tiered-benefit",
        "intensive-care-additional-benefit",
        "burn-unit-additional-benefit",
        "inpatient-nursing-benefit",
        "post-discharge-recuperation-benefit",
        "surgery-benefit",
        "surgery-nursing-benefit",
    ]
    common = {
        "amount_role": "payout",
        "limit_scope": "per_hospitalization",
        "aggregation_rule": "separate",
        **eligible,
    }
    entries = [
        _entry(
            "hospital-daily-tiered-benefit",
            "住院醫療保險金",
            "以保單記載住院醫療日額計算；第 1 至 30 日按一倍，第 31 至 365 日按二倍。",
            "第十二條",
            calculation_basis="tiered_or_stepped",
            quantity_state_key="hospitalization_days",
            policy_state_keys=[
                "hospital_daily_amount",
                "hospitalization_days",
            ],
            amount_tiers=[
                {"label": "第 1 至 30 日", "multiplier": 1, "min_quantity": 1, "max_quantity": 30},
                {"label": "第 31 至 365 日", "multiplier": 2, "min_quantity": 31, "max_quantity": 365},
            ],
            **common,
        ),
        _entry(
            "intensive-care-additional-benefit",
            "加護病房保險金",
            "住進加護病房期間，另按住院醫療日額二倍逐日給付，每次最長九十日。",
            "第十三條",
            calculation_basis="table_multiplier",
            multiplier=2,
            unit_key="hospital_daily_amount",
            quantity_state_key="intensive_care_days",
            quantity_cap=90,
            aggregation_rule="conditional_additive",
            **{key: value for key, value in common.items() if key != "aggregation_rule"},
        ),
        _entry(
            "burn-unit-additional-benefit",
            "燒燙傷中心醫療保險金",
            "住進燒燙傷中心期間，另按住院醫療日額三倍逐日給付，每次最長九十日。",
            "第十四條",
            calculation_basis="table_multiplier",
            multiplier=3,
            unit_key="hospital_daily_amount",
            quantity_state_key="burn_unit_days",
            quantity_cap=90,
            aggregation_rule="conditional_additive",
            **{key: value for key, value in common.items() if key != "aggregation_rule"},
        ),
        _entry(
            "inpatient-nursing-benefit",
            "住院看護保險金",
            "按第十二條可給付日數及住院醫療日額二分之一計算，每次最長九十日。",
            "第十五條",
            calculation_basis="table_multiplier",
            multiplier=0.5,
            unit_key="hospital_daily_amount",
            quantity_state_key="hospitalization_days",
            quantity_cap=90,
            **common,
        ),
        _entry(
            "post-discharge-recuperation-benefit",
            "出院後療養保險金",
            "出院後按第十二條可給付日數及住院醫療日額二分之一計算，每次最長九十日。",
            "第十六條",
            calculation_basis="table_multiplier",
            multiplier=0.5,
            unit_key="hospital_daily_amount",
            quantity_state_key="hospitalization_days",
            quantity_cap=90,
            **common,
        ),
        _entry(
            "surgery-benefit",
            "外科手術保險金",
            "住院醫療日額三十倍乘本次手術附表比例；同一位置多項手術只取較高比例。",
            "第十七條及手術項目給付比率表",
            calculation_basis="table_multiplier",
            multiplier=30,
            unit_key="hospital_daily_amount",
            rate_state_key="surgery_benefit_rate_percent",
            rate_min_percent=10,
            rate_max_percent=500,
            limit_scope="per_surgery",
            **{key: value for key, value in common.items() if key != "limit_scope"},
        ),
        _entry(
            "same-stay-surgery-aggregate-cap",
            "同一次住院外科手術保險金合計上限",
            "同一次住院兩次以上手術分別計算，但合計不超過住院醫療日額三十倍乘該次住院手術附表最高比例。",
            "第十七條及手術項目給付比率表",
            calculation_basis="table_multiplier",
            multiplier=30,
            unit_key="hospital_daily_amount",
            rate_state_key=HIGHEST_SURGERY_RATE_KEY,
            rate_min_percent=10,
            rate_max_percent=500,
            amount_role="limit",
            limit_scope="per_hospitalization",
            aggregation_rule="cumulative_cap",
            result_kind="reference",
            amount_stage="not_applicable",
            **eligible,
        ),
        _entry(
            "surgery-nursing-benefit",
            "外科手術看護保險金",
            "住院醫療日額十倍乘本次手術附表比例。",
            "第十八條及手術項目給付比率表",
            calculation_basis="table_multiplier",
            multiplier=10,
            unit_key="hospital_daily_amount",
            rate_state_key="surgery_benefit_rate_percent",
            rate_min_percent=10,
            rate_max_percent=500,
            limit_scope="per_surgery",
            **{key: value for key, value in common.items() if key != "limit_scope"},
        ),
        {
            "id": "health-increment-benefit",
            "name": "健康增值保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "前次醫療理賠事故出院日至本次入院日超過二十四個月時，按本次第十二條至第十八條給付合計增加百分之二十。",
            "source_ref": "第十九條",
            "calculation_basis": "percentage_of_base",
            "amount_role": "payout",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "conditional_additive",
            "benefit_group_id": "fubon-anxin-medical-benefits",
            "unit_key": "current_eligible_hospital_benefit_total_amount",
            "rate_state_key": HEALTH_INCREMENT_RATE_KEY,
            "rate_max_percent": 20,
            "policy_state_keys": [
                "current_eligible_hospital_benefit_total_amount",
                HEALTH_INCREMENT_RATE_KEY,
            ],
            "applies_to_entry_ids": hospital_related_ids,
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            **eligible,
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


def parse_policy(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    version = VERSIONS[product_id]
    if (
        document.get("page_count") != version["page_count"]
        or document.get("pages_parsed") != version["page_count"]
        or str(document.get("source_text_extractor") or "")
        != version["source_text_extractor"]
    ):
        return None
    text = normalize_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version[
        "source_text_sha256"
    ]:
        return None
    dense = compact_text(text)
    common_signals = (
        "安心住院醫療定額給付保險附約",
        "住院醫療保險金",
        "加護病房保險金",
        "燒燙傷中心醫療保險金",
        "住院看護保險金",
        "出院後療養保險金",
        "外科手術保險金",
        "外科手術看護保險金",
        "健康增值保險金",
        "住院醫療保險金日額",
        "手術項目給付比率表",
        "超過二十四個月",
        "增加給付金額的百分之二十",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(version["revision"])
    has_ninety_day_rule = (
        "未超過九十天" in dense or "未超過九十日" in dense
    )
    phase_checks = (
        (has_ninety_day_rule, revision <= 1),
        ("出院後十四日內再次住院" in dense, revision >= 2),
        ("有效期間屆滿後出院" in dense, revision >= 8),
        ("全民健康保險法第五十一條所稱之日間住院" in dense, revision >= 9),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    required_policy_inputs = ["hospital_daily_amount"]
    claim_event_inputs = [
        EVENT_STATUS_KEY,
        "hospitalization_days",
        "intensive_care_days",
        "burn_unit_days",
        "surgery_benefit_rate_percent",
        HIGHEST_SURGERY_RATE_KEY,
        "current_eligible_hospital_benefit_total_amount",
        HEALTH_INCREMENT_RATE_KEY,
    ]
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "輸入保單住院日額與本次事故資料",
        "selection_guidance": (
            "請先輸入保單首頁或批註所載住院醫療保險金日額；有住院、特殊病房或手術時，再依本 productId 條款與診斷文件輸入日數及手術附表比例。"
        ),
        "plan_options": [],
        "version_characteristics": {
            "source_product_id": product_id,
            "family_fingerprint": FAMILY_FINGERPRINT,
            "product_family": "fubon-anxin-fixed-hospital-medical-rider",
            "company_group": "fubon_life",
            "source_batch_id": "tii-life-050",
            "terms_revision": f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "group_policy": False,
            "rider": True,
            "policy_amount_source": "policy_schedule_daily_hospital_amount",
            "disease_waiting_days": 30,
            "accident_waiting_period_exempt": True,
            "same_hospital_readmission_days": 90 if revision <= 1 else 14,
            "post_expiry_readmission_excluded": revision >= 8,
            "day_hospital_excluded": revision >= 9,
            "day_hospital_legal_reference_revision": (
                "nhi_article_51_and_mental_health_article_35"
                if revision >= 9
                else "not_explicit"
            ),
            "hospital_day_limit": 365,
            "hospital_day_31_to_365_rate_percent": 200,
            "intensive_care_daily_rate_percent": 200,
            "intensive_care_day_limit": 90,
            "burn_unit_daily_rate_percent": 300,
            "burn_unit_day_limit": 90,
            "inpatient_nursing_daily_rate_percent": 50,
            "inpatient_nursing_day_limit": 90,
            "discharge_recuperation_daily_rate_percent": 50,
            "discharge_recuperation_day_limit": 90,
            "surgery_base_daily_multiplier": 30,
            "surgery_nursing_base_daily_multiplier": 10,
            "surgery_rate_min_percent": 10,
            "surgery_rate_max_percent": 500,
            "same_stay_surgery_aggregate_rule": "daily_amount_30x_times_highest_schedule_rate",
            "same_location_surgery_rule": "highest_rate_only",
            "health_increment_interval_months": 24,
            "health_increment_rate_percent": 20,
            "required_policy_inputs": required_policy_inputs,
            "claim_event_inputs": claim_event_inputs,
            "amount_presentation": "policy_daily_amount_with_exact_claim_event_formulas",
        },
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
        fail(f"coverage Fubon Anxin source product is invalid: {context}")
    revision = int(source["revision"])
    expected_identity = {
        "source_product_id": product_id,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_family": "fubon-anxin-fixed-hospital-medical-rider",
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
        "group_policy": False,
        "rider": True,
        "policy_amount_source": "policy_schedule_daily_hospital_amount",
        "disease_waiting_days": 30,
        "accident_waiting_period_exempt": True,
        "same_hospital_readmission_days": 90 if revision <= 1 else 14,
        "post_expiry_readmission_excluded": revision >= 8,
        "day_hospital_excluded": revision >= 9,
        "day_hospital_legal_reference_revision": (
            "nhi_article_51_and_mental_health_article_35"
            if revision >= 9
            else "not_explicit"
        ),
        "hospital_day_limit": 365,
        "hospital_day_31_to_365_rate_percent": 200,
        "intensive_care_daily_rate_percent": 200,
        "intensive_care_day_limit": 90,
        "burn_unit_daily_rate_percent": 300,
        "burn_unit_day_limit": 90,
        "inpatient_nursing_daily_rate_percent": 50,
        "inpatient_nursing_day_limit": 90,
        "discharge_recuperation_daily_rate_percent": 50,
        "discharge_recuperation_day_limit": 90,
        "surgery_base_daily_multiplier": 30,
        "surgery_nursing_base_daily_multiplier": 10,
        "surgery_rate_min_percent": 10,
        "surgery_rate_max_percent": 500,
        "same_stay_surgery_aggregate_rule": "daily_amount_30x_times_highest_schedule_rate",
        "same_location_surgery_rule": "highest_rate_only",
        "health_increment_interval_months": 24,
        "health_increment_rate_percent": 20,
        "required_policy_inputs": ["hospital_daily_amount"],
        "claim_event_inputs": [
            EVENT_STATUS_KEY,
            "hospitalization_days",
            "intensive_care_days",
            "burn_unit_days",
            "surgery_benefit_rate_percent",
            HIGHEST_SURGERY_RATE_KEY,
            "current_eligible_hospital_benefit_total_amount",
            HEALTH_INCREMENT_RATE_KEY,
        ],
        "amount_presentation": "policy_daily_amount_with_exact_claim_event_formulas",
    }
    if (
        record.get("product_id") not in {None, product_id}
        or record.get("selection_type") != "policy_state"
        or record.get("input_mode") != "policy_state"
        or record.get("selection_source") != "terms"
        or record.get("plan_options") != []
        or any(version.get(key) != value for key, value in expected_identity.items())
    ):
        fail(f"coverage Fubon Anxin source or version boundary is invalid: {context}")
    validate_entries(
        record.get("coverage_entries"),
        expected_entry_contracts(revision),
        f"{context} Fubon Anxin fixed hospital medical rider",
    )

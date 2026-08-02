from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


FAMILY_FINGERPRINT = "2d659dc9c399c02cadd9c7ac"
SOURCE_GAP_PRODUCT_IDS = frozenset({"211317M11A00802"})
SOURCE_ROWS = (
    ("211313M11A00807", 7, "211313M11A00807-A.pdf", 10, "pypdf", "3df1eee2093e3486850b5eca37e7bb25751797ea86ebd1b4fd19002e60f71c36", "d25acb8d1919e1f25058ac9aa931fa9c2caf1fb29f9947ae557747a49432cdd2"),
    ("211313M11A00808", 8, "211313M11A00808-A.pdf", 10, "pypdf", "17a34861b8ac0491768104cf1867036d6e5a64cb4076538566827e7f739ac4f5", "2d06a88acec98ad85921a6d498a613bb33ca595cc0007efedc7ec31755284c79"),
    ("211313MZ1A00821A11Z10000009", 9, "211313MZ1A00821A11Z10000009-A.pdf", 10, "pypdf", "e329a6105b013af19f48fde3c72f3dc28eb574288c07424c59debe10af9b43ba", "f1ea753488c09924657bcdec3c8ab0c2844d206dea5f305e35a06e5071a594d4"),
    ("211313MZ1A00821A11Z10000010", 10, "211313MZ1A00821A11Z10000010-A.pdf", 10, "pypdf", "c5cae47e740aa074ee263437b7b9964b089ddedaf7f998243a7abdca97558f92", "64a23803a36d079d6df449df60e107728bc8b6b8f19f8d433df53ba7b6774e29"),
    ("211313MZ1A00821A11Z10000011", 11, "211313MZ1A00821A11Z10000011-A.pdf", 10, "pypdf", "f55e6044a14ac741bdd9c04b9511584e617e22d9c254b41adc3fd8b9d2ae8a6c", "ca92747bc38195269459b79ec4eadf8db392a89cebcfe8748241bd5db66aa9c5"),
    ("211313MZ1A00821A11Z10000012", 12, "211313MZ1A00821A11Z10000012-A.pdf", 10, "pypdf", "5fc1f72046cdae985907d03c93e8a84e3d63f93f418f10d268acefede14aebea", "01211407bbee14aaf99a4a708b48d2d0626a073ae6cfdf18e8612439b755a853"),
    ("211317M11A00800", 0, "211317M11A0080-A.pdf", 9, "pypdf", "502e69298af133392a88374105c0823fbe74bdf5d73a1f0be38b947e363c858e", "057857f98c502e251f0811df50fa170a0e6e881f1534c3c82614d5fe338bf5e2"),
    ("211317M11A00801", 1, "211317M11A0081-A.pdf", 9, "windows_ocr", "36a001c694f7d6bc2bcc1e7fd2fbbd0c162202485678b84335344bf8abe6926b", "c1f585c75c76f852ffb52aed3025f3755682bab241cf6d838f6b494c2da16bb8"),
    ("211317M11A00803", 3, "211317M11A00803-A.pdf", 8, "pypdf", "cf7aef8040ba723954cc89ca054dcc3ddf0cc8893b3d3e436f48bddaa486b38a", "0f493d441e87b02ee8cfa0449ad3f881fa20eaf5b2ecb05cbdc2b46c0e5b4117"),
    ("211317M11A00804", 4, "211317M11A00804-A.pdf", 9, "pypdf", "4a543f08799e7c454a24f46cab8906e7db14da76250f3f7a2c70bf01b44bc6aa", "e12afae9ddc6664cfe61ff7b3e1901299e2ba2b25b7e920145288c1b940213d4"),
    ("211317M11A00805", 5, "211317M11A00805-A.pdf", 10, "pypdf", "e2fd3a31ac08e1a069580daaff92d7c3bb4bedbb2b9505652e8fc15beda49933", "b05b6973563b99f7bd9f1abb2799d8fae15803f3cd53a1e136b3b1204f7d4927"),
    ("211317M11A00806", 6, "211317M11A00806-A.pdf", 10, "pypdf", "1017e0f4ffb34b07a6b72cbdafe58657fdfa0fae696cc894b7bc366ddc4afbf0", "ff09f9180ade5037e62a0e0fdba4abf491d0bc11d196b63ddcbcd952bb6769c9"),
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

EVENT_STATUS_KEY = "mercantile_group_daily_event_status"
MAX_HOSPITAL_DAYS_KEY = "mercantile_group_daily_max_hospital_days"
SURGERY_OPTION_STATUS_KEY = "mercantile_group_daily_surgery_option_status"
DISCHARGE_OPTION_STATUS_KEY = "mercantile_group_daily_discharge_option_status"

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
    "daily_amount_source",
    "maximum_hospital_days_source",
    "benefit_entry_count",
    "hospital_daily_formula",
    "intensive_care_formula",
    "surgery_formula",
    "discharge_recuperation_formula",
    "surgery_clause_optional",
    "discharge_recuperation_clause_optional",
    "surgery_points_per_multiplier",
    "disease_waiting_days",
    "same_hospital_readmission_days",
    "same_policy_year_scope",
    "post_expiry_readmission_excluded",
    "day_hospital_excluded",
    "claim_medical_review_clause",
    "reimbursement_benefit",
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


def has_post_expiry_exclusion(revision: int) -> bool:
    return revision >= 6


def has_day_hospital_exclusion(revision: int) -> bool:
    return revision >= 8


def semantic_phase(revision: int) -> str:
    if revision == 0:
        return "initial_policy_recorded_maximum_days"
    if revision == 1:
        return "initial_policy_recorded_maximum_days_ocr_revision"
    if revision == 3:
        return "same_hospitalization_wording"
    if revision <= 5:
        return "same_policy_year_scope"
    if revision <= 7:
        return "post_expiry_readmission_exclusion"
    if revision <= 9:
        return "day_hospital_and_post_expiry_exclusion"
    return "medical_opinion_revision"


def eligibility(revision: int) -> dict[str, Any]:
    ineligible = ["confirmed_not_eligible"]
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


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    common = {
        "amount": None,
        "basis": "face_amount",
        "source": "terms",
        "amount_role": "payout",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **eligibility(revision),
    }
    return [
        {
            "id": "hospital-daily-benefit",
            "name": "住院保險金",
            "note": "每日住院保險金額乘實際住院日數，最高以投保申請書或保險單記載日數為限。",
            "source_ref": "住院醫療日額保險金的給付",
            "calculation_basis": "table_multiplier",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "separate",
            "multiplier": 1,
            "unit_key": "face_amount",
            "quantity_state_key": "hospitalization_days",
            "quantity_cap_state_key": MAX_HOSPITAL_DAYS_KEY,
            **common,
        },
        {
            "id": "intensive-care-additional-benefit",
            "name": "加護病房住院保險金",
            "note": "第 1 至 30 日每日給付日額的 0.5 倍，第 31 至 120 日每日給付 1 倍。",
            "source_ref": "加護病房保險金的給付",
            "calculation_basis": "tiered_or_stepped",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "conditional_additive",
            "benefit_group_id": "mercantile-group-daily-hospital-additions",
            "applies_to_entry_ids": ["hospital-daily-benefit"],
            "unit_key": "face_amount",
            "quantity_state_key": "intensive_care_days",
            "quantity_cap": 120,
            "amount_tiers": [
                {"label": "第 1 至 30 日", "multiplier": 0.5, "min_quantity": 1, "max_quantity": 30},
                {"label": "第 31 至 120 日", "multiplier": 1, "min_quantity": 31, "max_quantity": 120},
            ],
            **common,
        },
        {
            "id": "surgery-benefit",
            "name": "手術保險金",
            "note": "每日住院保險金額乘手術附表比例；同次同部位以最高倍率計，未列手術按健保點數換算。",
            "source_ref": "手術醫療保險金的給付及手術項目給付倍數表",
            "calculation_basis": "table_multiplier",
            "limit_scope": "per_surgery",
            "aggregation_rule": "highest",
            "multiplier_state_key": "surgery_benefit_multiplier_decimal",
            "unit_key": "face_amount",
            "exclusion_state_key": SURGERY_OPTION_STATUS_KEY,
            "exclusion_values": ["not_included"],
            **common,
        },
        {
            "id": "discharge-recuperation-benefit",
            "name": "出院療養保險金",
            "note": "第 1 至 15 日每日給付日額的 0.5 倍，第 16 至 120 日每日給付 1 倍。",
            "source_ref": "出院療養保險金的給付",
            "calculation_basis": "tiered_or_stepped",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "separate",
            "unit_key": "face_amount",
            "quantity_state_key": "hospitalization_days",
            "quantity_cap": 120,
            "amount_tiers": [
                {"label": "第 1 至 15 日", "multiplier": 0.5, "min_quantity": 1, "max_quantity": 15},
                {"label": "第 16 至 120 日", "multiplier": 1, "min_quantity": 16, "max_quantity": 120},
            ],
            "exclusion_state_key": DISCHARGE_OPTION_STATUS_KEY,
            "exclusion_values": ["not_included"],
            **common,
        },
    ]


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
    return {
        "source_product_id": product_id,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_family": "mercantile-group-new-hospital-medical-daily",
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
        "daily_amount_source": "policy_recorded_daily_hospital_amount",
        "maximum_hospital_days_source": "application_or_policy_recorded_value",
        "benefit_entry_count": 4,
        "hospital_daily_formula": "daily_amount_x_eligible_hospitalization_days",
        "intensive_care_formula": "days_1_30_x0_5_days_31_120_x1",
        "surgery_formula": "daily_amount_x_exact_schedule_multiplier",
        "discharge_recuperation_formula": "days_1_15_x0_5_days_16_120_x1",
        "surgery_clause_optional": True,
        "discharge_recuperation_clause_optional": True,
        "surgery_points_per_multiplier": 500,
        "disease_waiting_days": 0,
        "same_hospital_readmission_days": 14,
        "same_policy_year_scope": revision >= 4,
        "post_expiry_readmission_excluded": has_post_expiry_exclusion(revision),
        "day_hospital_excluded": has_day_hospital_exclusion(revision),
        "claim_medical_review_clause": revision >= 10,
        "reimbursement_benefit": False,
        "death_benefit_available": False,
        "premium_waiver_available": False,
        "required_policy_inputs": [
            "face_amount",
            MAX_HOSPITAL_DAYS_KEY,
            SURGERY_OPTION_STATUS_KEY,
            DISCHARGE_OPTION_STATUS_KEY,
        ],
        "claim_event_inputs": [
            EVENT_STATUS_KEY,
            "hospitalization_days",
            "intensive_care_days",
            "surgery_benefit_multiplier_decimal",
        ],
        "amount_presentation": "policy_recorded_daily_amount_with_exact_event_inputs",
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
        "團體新住院醫療日額型保險",
        "住院保險金",
        "加護病房住院保險金",
        "手術保險金",
        "出院療養保險金",
    )
    revision = int(source["revision"])
    required_signals = common_signals[:1] if revision == 1 else common_signals
    if any(compact_text(signal) not in dense for signal in required_signals):
        return None
    return {
        "selection_type": "face_amount",
        "input_mode": "face_amount",
        "selection_source": "terms",
        "selection_label": "每日住院保險金額",
        "face_amount_label": "每日住院保險金額",
        "selection_guidance": "請依這個 product ID 的保險單或投保資料輸入每日住院保險金額；手術與出院療養是否納入也須依保單勾選。",
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
        fail(f"coverage Mercantile group daily source product is invalid: {context}")
    if (
        record.get("product_id") not in {None, product_id}
        or record.get("selection_type") != "face_amount"
        or record.get("input_mode") != "face_amount"
        or record.get("selection_source") != "terms"
        or record.get("face_amount_label") != "每日住院保險金額"
        or any(
            version.get(key) != value
            for key, value in expected_identity(product_id).items()
        )
    ):
        fail(
            "coverage Mercantile group daily source or version boundary "
            f"is invalid: {context}"
        )
    validate_entries(
        record.get("coverage_entries"),
        expected_entry_contracts(int(source["revision"])),
        f"{context} Mercantile group new hospital medical daily",
    )

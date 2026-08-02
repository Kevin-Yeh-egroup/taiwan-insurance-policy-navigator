from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "8ea58163f00063e5f3372ba8"
SOURCE_ROWS = (
    ("204317R11AMAA00", 0, "204317R11AMAA00-A.pdf", 6, "pymupdf", "7f12f91c5997657f94ad519f8867cd5deb42b5a1716634efe1eda6c3da58c879", "409c3d719bbcbe6b24e8cf5ff33d127d713c6f382c7ed6dae5fb4132262fb266"),
    ("204317R11AMAA01", 1, "204317R11AMAA01-A.pdf", 6, "pymupdf", "f0d4a50bc428f33c698bfaba693502da72feba9c68e13d22a67952b27793a7a3", "c7d673915431219a3e3f15229553622e6ae5042cbb6e3dd642775d28f19a0ead"),
    ("204317R11AMAA02", 2, "204317R11AMAA02-A.pdf", 6, "windows_ocr", "59fadda1bbc410cee16dc82f6da6ebf01524869139f2c76133b0a33ae3bebb2b", "4edf250058b438bf387aaa08c859d9140d6ee37bf77ea60352b8187707c34a4c"),
    ("204317R11AMAA03", 3, "204317R11AMAA03-A.pdf", 6, "pypdf", "8d3e0667cfc419737e7d70ff54ce326903600cde84b1e7bbfcb7cda947de663a", "d7794f945d853534252c72bf872d8e1e2450fdfb666810c3f5942f8feba57ac1"),
    ("204317R11AMAA04", 4, "204317R11AMAA04-A.pdf", 6, "pypdf", "768327efbb2d738700b9bd94e7a37b875d07c4f0afab39a2e6f695a084d1a072", "9b8e6cbfb28e6fda62d94e076111cbc08c769075999905e64b0d20976b1b7c98"),
    ("204317R11AMAA05", 5, "204317R11AMAA05-A.pdf", 6, "pymupdf", "cce38d76de7d3ebc92b7d98c22e8cb231e79332db340a70b63d828967c3f5158", "ba875499d29ff87d1742e8c0360823573948cad36f0061b315c23eb415b1252b"),
    ("204313R11AMAA06", 6, "204313R11AMAA06-A.pdf", 6, "pymupdf", "25cbb0a37b6266693d5236f49b951da90d9b8ab39305e62cdab238091d7cc82a", "0af0e4a517fc36d21b2359589aba136f548dbc29d90204be04c6b493a7f6339d"),
    ("204313RZ1AMA321A11Z10000007", 7, "204313RZ1AMA321A11Z10000007-A.pdf", 6, "pymupdf", "78e5cd74f1ea0c26774c5850c52ba29f35cb8022ea738f0dc54a3c5786a3ce50", "464fed67c5af64ecb41aa379ecedff6df1630149d5e5237de7acf0d309228c4e"),
    ("204313RZ1AMA321A11Z10000008", 8, "204313RZ1AMA321A11Z10000008-A.pdf", 7, "pymupdf", "d6b70ef6ee8341ddc964708956e590519041be72416110d492692be2e18b1b82", "aa423755c235cca3757e736481bfcc0e4d6b993594a1c10b98d48b789337ded0"),
    ("204313RZ1AMA321A11Z10000009", 9, "204313RZ1AMA321A11Z10000009-A.pdf", 7, "pymupdf", "8ef99b2a6804cd7073c8a263d4260ec36af625009bcf90456b7691a2abb7069c", "6db109a2b693993b9c7c660a4db051cec77a679a74a845a82ea8c780c8ec4fef"),
    ("204313RZ1AMA321A11Z10000010", 10, "204313RZ1AMA321A11Z10000010-A.pdf", 7, "pymupdf", "229f1c9c2a687a78e9cc7ed8acfe87a782ca8b0a0b12684567daf92cf1a471cc", "bc8da3713b6f9e8b7f55a44b9e86ee231dd5e66c753cd1f186d63c67e285cad5"),
    ("204313RZ1AMA321A11Z10000011", 11, "204313RZ1AMA321A11Z10000011-A.pdf", 7, "pymupdf", "c2a354cfbbe4a56d886b7caf3982e986ee489a1cfb72832e0db9b32366333b15", "48f5c087b8503058a1530cf1cce4f4c50d93c7f34f66609473336e5fcb9c4205"),
    ("204313RZ1AMA321A11Z10000012", 12, "204313RZ1AMA321A11Z10000012-A.pdf", 7, "pymupdf", "8f3978b8184bbeef387fc97db8ff35d6bf1f085a8df8bbe2f83d81c03fffa48e", "87bc2a62d05918156d51ece5825d5002d06f074b2595ecac02286666f5ce2c64"),
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

EVENT_STATE_KEY = "cathay_group_quanyi_event_status"
NHI_STATE_KEY = "cathay_group_quanyi_nhi_status"


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def is_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    version = VERSIONS.get(product_id)
    return bool(
        version
        and str(document.get("batch_id") or "") == "tii-life-020"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
    )


def semantic_phase(revision: int) -> str:
    phases = {
        0: "original-designated-physician-expense",
        1: "partial-change-1-designated-physician-expense",
        2: "partial-change-2-designated-physician-expense",
        3: "designated-physician-expense-removed",
        4: "newborn-screening-11-disease-exception",
        5: "post-expiry-readmission-exclusion",
        6: "medical-corporation-day-hospital-exclusion",
        7: "other-agreed-method-wording",
        8: "newborn-screening-21-disease-exception",
        9: "medical-opinion-review",
        10: "main-policy-termination-continuation",
        11: "premium-notice-multichannel",
        12: "day-stay-day-care-wording",
    }
    return phases[revision]


def entry(
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
        "basis": "policy_recorded_limit",
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
        **fields,
    }


def eligibility(plan_name: str, revision: int) -> dict[str, Any]:
    ineligible = ["confirmed_not_eligible"]
    uncertain = ["uncertain"]
    if plan_name == "A":
        ineligible.append("disease_waiting_not_met")
        if revision < 4:
            uncertain.append("eligible_newborn_screening_exception")
    if revision >= 6:
        ineligible.append("day_hospital_or_day_stay")
    else:
        uncertain.append("day_hospital_or_day_stay")
    return {
        "eligibility_state_key": EVENT_STATE_KEY,
        "ineligible_values": ineligible,
        "uncertain_values": uncertain,
    }


def coverage_entries(plan_name: str, revision: int) -> list[dict[str, Any]]:
    common = {
        "calculation_basis": "percentage_of_actual_expense_with_cap",
        "amount_role": "payout",
        "rate_percent": 65,
        "rate_condition_state_key": NHI_STATE_KEY,
        "rate_condition_value": "not_nhi_covered",
        "limit_scope": "per_hospitalization",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **eligibility(plan_name, revision),
    }
    conditions = [
        "甲型疾病須符合三十日等待期；乙型疾病自生效、加保翌日或復效日起適用。",
        "同一疾病、傷害或併發症於出院後十四日內再次住院，合併視為同一次住院。",
        "未以全民健康保險身分或在非健保醫院住院者，按實際費用百分之六十五給付，仍受原限額拘束。",
    ]
    if revision >= 5:
        conditions.append("契約有效期間屆滿後出院者，再次住院部分不給付。")
    if revision >= 6:
        conditions.append("日間住院及精神衛生日間留院不屬條款所稱住院。")
    return [
        entry(
            "daily-room-expense-benefit",
            "每日病房費用保險金",
            "依實際病房、膳食及護理費用核付；同一次住院以每日限額乘可給付日數為上限。",
            "第十四條 每日病房費用保險金之給付",
            unit_key="cathay_group_quanyi_daily_room_limit",
            quantity_state_key="hospitalization_days",
            quantity_cap_state_key="cathay_group_quanyi_max_hospital_days",
            expense_state_key="hospital_room_expense",
            conditions=conditions,
            **common,
        ),
        entry(
            "inpatient-medical-expense-benefit",
            "住院醫療費用保險金",
            "依實際住院醫療費用核付，包含條款列明之藥品、輸血、救護車、手術及相關醫療費用。",
            "第十五條 住院醫療費用保險金之給付",
            unit_key="cathay_group_quanyi_inpatient_medical_limit",
            expense_state_key="inpatient_medical_expense",
            conditions=conditions,
            **common,
        ),
    ]


def expected_entry_contracts(
    plan_name: str,
    revision: int,
) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        item["id"]: {
            key: value
            for key, value in item.items()
            if key not in ignored and key != "id"
        }
        for item in coverage_entries(plan_name, revision)
    }


def parse_policy(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    version = VERSIONS[product_id]
    if (
        document.get("page_count") != version["page_count"]
        or document.get("pages_parsed") != version["page_count"]
        or str(document.get("source_document_sha256") or "")
        != version["source_document_sha256"]
        or str(document.get("source_text_extractor") or "")
        != version["source_text_extractor"]
    ):
        return None
    text = normalize_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version[
        "source_text_sha256"
    ]:
        return None
    dense_text = re.sub(r"\s+", "", text)
    if any(
        signal not in dense_text
        for signal in (
            "國泰人壽團體住院醫療限額給付健康保險附約",
            "每日病房費用保險金",
            "住院醫療費用保險金",
        )
    ):
        return None
    revision = int(version["revision"])
    newborn_count = 0 if revision < 4 else 11 if revision < 8 else 21
    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "承保型別",
        "selection_guidance": (
            "請依保險證或保險手冊選擇甲型或乙型，並輸入每日病房限額、最高給付日數與每次住院醫療限額。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "cathay-group-hospital-medical-limit-ab",
            "company_group": "cathay_life",
            "source_batch_id": "tii-life-020",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "terms_revision": f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": (
                "verified_windows_ocr_exact_hash"
                if version["source_text_extractor"] == "windows_ocr"
                else "machine_readable_exact_hash"
            ),
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "group_policy": True,
            "plan_options": ["A", "B"],
            "plan_required": True,
            "unit_count_required": False,
            "plan_a_disease_waiting_days": 30,
            "plan_b_disease_waiting_days": 0,
            "accident_waiting_period_exempt": True,
            "newborn_screening_exception_count": newborn_count,
            "designated_physician_expense_included": revision <= 2,
            "post_expiry_readmission_excluded": revision >= 5,
            "day_hospital_excluded": revision >= 6,
            "mental_day_stay_excluded": revision >= 6,
            "medical_corporation_hospital_wording": revision >= 6,
            "other_agreed_method_wording": revision >= 7,
            "medical_opinion_review_wording": revision >= 9,
            "main_policy_termination_continuation": revision >= 10,
            "premium_notice_multichannel": revision >= 11,
            "day_stay_day_care_wording": revision >= 12,
            "benefit_entry_count": 2,
            "separate_surgery_benefit_present": False,
            "separate_outpatient_benefit_present": False,
            "non_nhi_actual_expense_rate_percent": 65,
            "required_policy_inputs": [
                "plan_name",
                "cathay_group_quanyi_daily_room_limit",
                "cathay_group_quanyi_max_hospital_days",
                "cathay_group_quanyi_inpatient_medical_limit",
            ],
            "claim_event_inputs": [
                EVENT_STATE_KEY,
                NHI_STATE_KEY,
                "hospitalization_days",
                "hospital_room_expense",
                "inpatient_medical_expense",
            ],
            "amount_presentation": "selected_plan_with_policy_recorded_limits_and_actual_expenses",
        },
        "plan_options": [
            {
                "value": plan_name,
                "label": f"{plan_name} 型",
                "coverage_entries": coverage_entries(plan_name, revision),
            }
            for plan_name in ("A", "B")
        ],
    }

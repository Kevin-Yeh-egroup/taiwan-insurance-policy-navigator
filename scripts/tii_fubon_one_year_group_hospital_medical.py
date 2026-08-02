from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "629a7e54a13d118ee2a7ae6e"
SOURCE_ROWS = (
    ("209317M11A00605", 0, "209317M11A00605-A.pdf", 9, "pypdf", "3857d36687991fde17876e691126f8661a5febf9255a9e7fa96a3e83d0e913a0", "7fc966789d5d00e650c422c138133719a2be0eb6a5288eb69ab7c272bcc1f006"),
    ("209317M11A00606", 1, "209317M11A00606-A.pdf", 9, "pypdf", "d3477ac2913e57ca1bc99ddadedb47c1b87b223386fa1e3057ff3f7dc4f77e3d", "79a9e0e85eb17cdd1dd3ea46e4e917c9c7cb7fbfed82468b838e66580e9f0b1d"),
    ("209317M11A00607", 2, "209317M11A00607-A.pdf", 9, "pypdf", "6342b13a8e885cd7ce68881aef4b797f71ab941caa03832fa305231c8a7ab20a", "b0ccb932c8fbf852b8dd7187cb5ac4969f796033b87e5282af3455d3b356835b"),
    ("209313M11A00308", 3, "209313M11A00308-A.pdf", 9, "pypdf", "116e9acee534b417cfa1fa60850dbbe6f6d00897c7b14e4f01adf0ebd9795644", "f1bf9a5248f2d24a3b60ed2b0a89589f068c427318e3fd97463a8e8f7d10e612"),
    ("209313MZ1A00221A11Z10000009", 4, "209313MZ1A00221A11Z10000009-A.pdf", 9, "pymupdf", "2b92265cfb047f5dd19628e6570baa5fc3dc521e4c6fc4799e0672079fb4750e", "3fa246b3a3e37e74a7cf31e43f18df6d4ccbdea36349c8d53979ef6aa618a3ae"),
    ("209313MZ1A00221A11Z10000010", 5, "209313MZ1A00221A11Z10000010-A.pdf", 9, "pypdf", "f3b15e7ebdae5f5db1102dc85482a809dd37347f55ab93198455a78977c28ec0", "de174d600f57a07e2abe60b7172aea8e0018cdf1756e3cd569e59c37fc799a69"),
    ("209313MZ1A00221A11Z10000011", 6, "209313MZ1A00221A11Z10000011-A.pdf", 9, "pymupdf", "a1693bcb9a8276323a71eeb5b4fda97a82fa4e5fec9e7f03d78fecd2b5969b4d", "ac4be30f65d8d97c76a312464f58c2bff6eb6840f778e41694b3c77a9f64a3ad"),
    ("209313MZ1A00221A11Z10000012", 7, "209313MZ1A00221A11Z10000012-A.pdf", 10, "pymupdf", "4ff30c81dc5a109147e213f79e91744b2ead711c768d3729c3bcfaae4fe36242", "84adfd6917ae4e0da7cfffcd06df11ec2a87100ce8e85c9ced57ba026844df89"),
    ("209313MZ1A00221A11Z10000013", 8, "209313MZ1A00221A11Z10000013-A.pdf", 10, "pymupdf", "9571a0dcb7c75c12f0700b69f1646961b9433817125cbc6c102251bcdb2bc78e", "200e3d0bba1bf27a1945e4b243369770f128c26131bd4d1ddb3298368feb44b8"),
    ("209313MZ1A00221A11Z10000014", 9, "209313MZ1A00221A11Z10000014-A.pdf", 10, "pymupdf", "75a89f73bd6685e903e7626c66bfac8b11acbae7961e02d2c0beaf65967e38fd", "b9a4dc39d6c31867924fe35711efaabf3ffcef969fd13f369844f722c5e6f5ec"),
    ("209313MZ1A00221A11Z10000015", 10, "209313MZ1A00221A11Z10000015-A.pdf", 10, "pymupdf", "df0b9d501e6e48bd2b9a8563a1e1a594bc47270fcb499319861bdfc82baec6b9", "16b384898b1da013ffc948e4c2221a39cef0de8ffd0bd04e335e2e280cd2f758"),
    ("209313MZ1A00221A11Z10000016", 11, "209313MZ1A00221A11Z10000016-A.pdf", 10, "pymupdf", "ec6d91a87b6cfa136d0af09803a847237992354a455692be16e094710de87ac3", "bb4568f2f2a5e747f9266d7359125fd73dee2d081075203e22e5106b9fe09979"),
    ("209313MZ1A00221A11Z10000017", 12, "209313MZ1A00221A11Z10000017-A.pdf", 10, "pypdf", "152ec78071cc343e2c7bb7d376018e1a309e62f2935b91e4d06ed318daaeea10", "ea97faf502d732453b684d82943e663d791aa3f2ea826246afd3492cbc21924f"),
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

DAILY_ROOM_LIMIT_KEY = "fubon_group_hospital_daily_room_limit"
ORDINARY_SURGERY_LIMIT_KEY = "fubon_group_hospital_ordinary_surgery_limit"
MAJOR_SURGERY_LIMIT_KEY = "fubon_group_hospital_major_surgery_limit"
MISC_LIMIT_KEY = "fubon_group_hospital_misc_limit"
MISC_DAILY_LIMIT_KEY = "fubon_group_hospital_misc_daily_limit"
DEDUCTIBLE_KEY = "fubon_group_hospital_deductible"
MAX_DAYS_KEY = "fubon_group_hospital_max_days"
ROOM_CLASS_KEY = "fubon_group_hospital_room_class"
CLAIM_MODE_KEY = "fubon_group_hospital_claim_mode"


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
    if revision <= 2:
        return "ninety-day-readmission-daily-choice"
    if revision <= 5:
        return "day-hospital-excluded-ninety-day-daily-choice"
    if revision <= 10:
        return "fourteen-day-readmission-daily-choice"
    if revision == 11:
        return "daily-choice-removed"
    return "electronic-document-accepted"


def common_reimbursement_fields(revision: int) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "rate_percent": 65,
        "rate_condition_state_key":
            "national_health_insurance_payment_status",
        "rate_condition_value": "not_covered",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
    }
    if revision <= 10:
        fields.update(
            {
                "eligibility_state_key": CLAIM_MODE_KEY,
                "ineligible_values": ["daily_cash"],
                "uncertain_values": ["uncertain"],
            }
        )
    return fields


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    choice_group = "fubon-group-hospital-reimbursement-or-daily-choice"
    common = common_reimbursement_fields(revision)
    entries: list[dict[str, Any]] = [
        {
            "id": "daily-room-reimbursement-benefit",
            "name": "每日病房費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "以保險金表所載每日病房費限額乘以符合條款的住院日數，並以實際病房費用為上限。",
            "source_ref": "保險金表與第四章第一條",
            "calculation_basis": "reimbursement_with_cap",
            "amount_role": "payout",
            "unit_key": DAILY_ROOM_LIMIT_KEY,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap_state_key": MAX_DAYS_KEY,
            "expense_state_key": "hospital_room_expense",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "choose_one" if revision <= 10 else "separate",
            "benefit_group_id": choice_group,
            **common,
        },
        {
            "id": "surgery-reimbursement-benefit",
            "name": "手術費用保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "普通手術限額乘以手術費用表百分比；超過 100% 的重大手術另受保險金表重大手術限額約束。",
            "source_ref": "手術費用表及保險金表說明第(4)、(5)、(7)款",
            "calculation_basis": "reimbursement_with_schedule_and_major_cap",
            "amount_role": "payout",
            "unit_key": ORDINARY_SURGERY_LIMIT_KEY,
            "secondary_limit_state_key": MAJOR_SURGERY_LIMIT_KEY,
            "rate_state_key": "surgery_benefit_rate_percent",
            "rate_min_percent": 1,
            "rate_max_percent": 400,
            "rate_threshold_percent": 100,
            "expense_state_key": "inpatient_surgery_expense",
            "limit_scope": "per_surgery",
            "aggregation_rule": "choose_one" if revision <= 10 else "separate",
            "benefit_group_id": choice_group,
            **common,
        },
        {
            "id": "hospital-misc-reimbursement-benefit",
            "name": "每次住院醫院雜費保險金",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "最高住院日數超過 31 日的計畫，以保險金表雜費限額與每日限額乘住院日數兩者較高者為上限。",
            "source_ref": "兩種最高住院日數計畫的保險金表",
            "calculation_basis": "reimbursement_with_greater_of_daily_cap",
            "amount_role": "payout",
            "unit_key": MISC_LIMIT_KEY,
            "secondary_limit_state_key": MISC_DAILY_LIMIT_KEY,
            "quantity_state_key": "hospitalization_days",
            "quantity_cap_state_key": MAX_DAYS_KEY,
            "expense_state_key": "inpatient_medical_expense",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "choose_one" if revision <= 10 else "separate",
            "benefit_group_id": choice_group,
            **common,
        },
    ]
    if revision <= 10:
        entries.append(
            {
                "id": "hospital-medical-daily-cash-alternative",
                "name": "住院醫療日額替代給付",
                "amount": None,
                "basis": "policy_recorded_limit",
                "source": "terms",
                "note": "僅限條款仍提供二者擇一且非社保負額型者；以保險金表每日金額乘符合條款的住院日數。",
                "source_ref": "條款首頁給付項目及保險金表",
                "calculation_basis": "reimbursement_with_cap",
                "amount_role": "payout",
                "unit_key": MISC_DAILY_LIMIT_KEY,
                "quantity_state_key": "hospitalization_days",
                "quantity_cap_state_key": MAX_DAYS_KEY,
                "eligibility_state_key": CLAIM_MODE_KEY,
                "ineligible_values": [
                    "reimbursement",
                    "daily_cash_not_available",
                ],
                "uncertain_values": ["uncertain"],
                "limit_scope": "per_hospitalization",
                "aggregation_rule": "choose_one",
                "benefit_group_id": choice_group,
                "result_kind": "cash_payout",
                "amount_stage": "gross_contract_benefit",
            }
        )
    entries.append(
        {
            "id": "hospital-deductible-reference",
            "name": "每次住院自負額",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "實際理賠仍須依保險金表記載的每次住院自負額自總保險金中扣除；此項僅顯示保單條件，不重複從每一給付項目扣除。",
            "source_ref": "第四章第一條及保險金表",
            "calculation_basis": "policy_state_amount",
            "amount_role": "reference",
            "policy_state_keys": [DEDUCTIBLE_KEY],
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "separate",
            "result_kind": "reference",
            "amount_stage": "not_applicable",
        }
    )
    return entries


def expected_entry_contracts(revision: int) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        item["id"]: {
            key: value
            for key, value in item.items()
            if key not in ignored and key != "id"
        }
        for item in coverage_entries(revision)
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
        "富邦人壽一年定期住院醫療團體健康保險",
        "每日病房費",
        "每次住院普通手術費",
        "每次住院重大手術費",
        "每次住院醫院雜費",
        "每次住院自負額",
        "手術費用表",
        "社保給付額",
        "實際支付之各項費用之65%給付",
        "醫療費用明細表及收據正本",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(version["revision"])
    phase_checks = (
        ("住院醫療日額給付,二者擇一" in dense, revision <= 10),
        ("十四日內再次住院" in dense, revision >= 6),
        ("日間住院" in dense, revision >= 3),
        ("如為電子文件" in dense, revision >= 12),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    required_policy_inputs = [
        DAILY_ROOM_LIMIT_KEY,
        ORDINARY_SURGERY_LIMIT_KEY,
        MAJOR_SURGERY_LIMIT_KEY,
        MISC_LIMIT_KEY,
        MISC_DAILY_LIMIT_KEY,
        DEDUCTIBLE_KEY,
        MAX_DAYS_KEY,
    ]
    claim_inputs = [
        "hospitalization_days",
        "hospital_room_expense",
        "inpatient_surgery_expense",
        "inpatient_medical_expense",
        "national_health_insurance_payment_status",
        "surgery_benefit_rate_percent",
    ]
    if revision <= 10:
        claim_inputs.append(CLAIM_MODE_KEY)
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "輸入保險金表與理賠狀態",
        "selection_guidance": (
            "請依此 productId 的保險金表輸入病房、普通及重大手術、雜費、每日額、自負額、最高住院日數與病房等級；理賠估算再輸入實際費用、住院日數、手術表百分比及健保狀態。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "fubon-one-year-group-hospital-medical",
            "company_group": "fubon_life",
            "source_batch_id": "tii-life-050",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "terms_revision": "initial" if revision == 0 else f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "group_policy": True,
            "policy_term_years": 1,
            "plan_options": False,
            "unit_count_required": False,
            "benefit_entry_count": len(coverage_entries(revision)),
            "actual_expense_reimbursement": True,
            "daily_cash_choice_available": revision <= 10,
            "daily_cash_unavailable_for_social_insurance_negative_plan": revision <= 10,
            "same_hospital_readmission_days": 90 if revision <= 5 else 14,
            "day_hospital_excluded": revision >= 3,
            "electronic_receipt_document_accepted": revision >= 12,
            "original_receipt_required": True,
            "non_nhi_payment_rate_percent": 65,
            "major_surgery_threshold_percent": 100,
            "surgery_rate_min_percent": 1,
            "surgery_rate_max_percent": 400,
            "multiple_surgery_aggregate_cap": True,
            "maximum_hospital_days_policy_recorded": True,
            "room_class_policy_recorded": True,
            "death_benefit_available": False,
            "premium_waiver_available": False,
            "required_policy_inputs": required_policy_inputs,
            "claim_event_inputs": claim_inputs,
            "amount_presentation": "policy_recorded_limits_with_claim_state_and_schedule_rate",
        },
        "coverage_entries": coverage_entries(revision),
    }

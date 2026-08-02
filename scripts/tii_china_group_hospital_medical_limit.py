from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "e18d8c4c6d5993c92360f597"
SOURCE_ROWS = (
    ("205317M11A07200", 0, "205317M11A072-A.pdf", 6, "pymupdf", "d1361ab3d71738f32af69c15a5c9f03fbfec57ba3cf62e53101f3110aa84b62d", "3adefe6e08eabffa85aeb3c463dabf62bd29a1432f5a329685448a4a8ffead14"),
    ("205317M11A07201", 1, "205317M11A07201-A.pdf", 9, "pymupdf", "5b845a197ad1910e8b957396cd47d9737120ece2f0b2d736a13a94a856367500", "7f99acabd0b8f6020268dfa89bcb54375c33f717dff5d48da5d48af6acb2b66a"),
    ("205317M11A07202", 2, "205317M11A07202-A.pdf", 7, "pymupdf", "ca4786aaef5a02bcc5fe56e0e37f92cd185fc9770083631125eebaa338b11b39", "3f66c8774a5ffa9a0ce7e886da5b0caef8d990990981ecdc6bda743c6deb2f08"),
    ("205317M11A07203", 3, "205317M11A07203-A.pdf", 7, "pymupdf", "9f96e3d12aec243bd3cd96a28e27d7e3e03742a52a5fbae8e2ce020a064b9e36", "92ef1a25d3a7735562d970344de099d3ddabf930f47786490e3060dd2fe70867"),
    ("205317M11A07204", 4, "205317M11A07204-A.pdf", 6, "pymupdf", "c39cd81c89cea7789ecbe3b400de535d5add7eb32d199ec3d0254bf97ad1fe11", "ccff94659e493ec2d3fc9ac4c8ad3c54ac594f30a2eaf2b70f8c20f0e332f1e6"),
    ("205317M11A07205", 5, "205317M11A07205-A.pdf", 7, "pymupdf", "d8466ef7b4e8ae9262a8ced604ce4850a713586175cb44c3f7d1d5f0f9991263", "a1b96616fc9f46aca0b64fffd43668547596c5188f86fa692fd90f59acc849b4"),
    ("205317M11A07206", 6, "205317M11A07206-A.pdf", 7, "pymupdf", "0b1b0993fe67f0d41470dac2de9162f44e79ed4591f8d219b1e663c18c8a3d8e", "95f0023eda1d44a16ea35f5dee89063e4882b69ff466c1b4d2cf8150bd3630ff"),
    ("205317M11A07207", 7, "205317M11A07207-A.pdf", 7, "pymupdf", "5e46b31135b8f7edffc16e434c3ac2875a3268f16f1e3cbba110a5f6c891c2f6", "8ddd0da7709c6045750a2168abad0fc580c6d4e96987b8747c04eb6be2b4fdc7"),
    ("205317M11A07208", 8, "205317M11A07208-A.pdf", 7, "pymupdf", "b4011a779097ee62f8bc49825e7e1977bf8ea55871adab8e9ecb4bd5c24d33c8", "7ca794a2e5344ca3300e77c62f04512e13d36d0a3953b22b5b1ec04797d2c0c3"),
    ("205313M11A07209", 9, "205313M11A07209-A.pdf", 7, "pymupdf", "9f46113e3d3a4851fad378290df916cbb50f26dc4c4ea4eaa9fd5f7e0228ebe8", "c769a80ffd395fe307048e6a3c85d989f0f6cd2ca1f0ed7cbc5189a84ce17469"),
    ("205313MZ1A00121A11Z10000010", 10, "205313MZ1A00121A11Z10000010-A.pdf", 7, "pymupdf", "6bfa4f3e2640d033d2557894bfe0c17c1415a41f3b056d6bb2dc1f757ac36f3e", "677966e59eaff1317d9741eb6afc64643fe5fead48599bb38ea45987b9fa916a"),
    ("205313MZ1A00121A11Z10000011", 11, "205313MZ1A00121A11Z10000011-A.pdf", 7, "pymupdf", "35ee351b3e2f727b842743646f28e827bb04d39614aa3a2fe522e3d39e7bc3a1", "76458a4c1dbb9ff2faadf6a96b2bb06b7d97f9a6df67ebd3b1abf6c46cd8c43a"),
    ("205313MZ1A00121A11Z10000012", 12, "205313MZ1A00121A11Z10000012-A.pdf", 7, "pymupdf", "5b3df1cbfe13c3a35fd2b1692f118efac775c83dcf4aa42a09bf29d84295f380", "dbd081288545da71b3e786f979fd98a90d52ca38a5657e40165ef19213480b25"),
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

TOTAL_LIMIT_STATE_KEY = "china_group_hospital_medical_total_limit"
ACTUAL_EXPENSE_STATE_KEY = "china_group_hospital_medical_actual_expense"
ROOM_MEAL_EXPENSE_STATE_KEY = "china_group_hospital_room_meal_expense"
EVENT_STATE_KEY = "china_group_hospital_medical_event_type"
ENTRY_ID = "hospital-medical-reimbursement-benefit"


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
        and str(document.get("batch_id") or "") == "tii-life-026"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
        and str(document.get("source_document_sha256") or "")
        == version["source_document_sha256"]
    )


def semantic_phase(revision: int) -> str:
    if revision == 0:
        return "original-inpatient-original-receipt"
    if revision == 1:
        return "inpatient-receipt-copy"
    if revision <= 4:
        return "inpatient-room-meal-wording"
    if revision <= 8:
        return "outpatient-surgery-emergency-extension"
    if revision <= 10:
        return "beneficiary-id-extension"
    return "medical-opinion-review-extension"


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    entry: dict[str, Any] = {
        "id": ENTRY_ID,
        "name": "住院醫療保險金",
        "amount": None,
        "basis": "policy_recorded_limit",
        "source": "terms",
        "note": (
            "以符合條款的實際自付醫療費用計算，每次事故不超過保單記載總限額；"
            "住院時每日病房及膳食費另以總限額百分之三為上限。"
        ),
        "source_ref": "第十三條（原始版第十條）保險範圍與保險給付",
        "calculation_basis": "reimbursement_with_total_and_daily_room_cap",
        "amount_role": "payout",
        "rate_percent": 3,
        "unit_key": TOTAL_LIMIT_STATE_KEY,
        "quantity_state_key": "hospitalization_days",
        "expense_state_key": ACTUAL_EXPENSE_STATE_KEY,
        "policy_state_keys": [ROOM_MEAL_EXPENSE_STATE_KEY],
        "limit_scope": "per_event",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        "conditions": [
            "每次事故的全部給付合計不得超過保單記載的住院醫療保險金總限額。",
            "住院的每日病房及膳食費，以總限額的百分之三為每日上限。",
            "條款未列固定計畫金額，總限額須依保單、名冊、批註或保險公司資料輸入。",
        ],
    }
    if revision >= 5:
        entry.update(
            {
                "eligibility_state_key": EVENT_STATE_KEY,
                "ineligible_values": ["confirmed_not_eligible"],
                "uncertain_values": ["uncertain"],
            }
        )
        entry["conditions"].extend(
            [
                "未住院但當日於醫院接受外科手術的實際自付醫療費用，依同一限額規則給付。",
                "急診有實際暫留且收取暫留床費，或診斷證明記載治療超過六小時，依同一限額規則給付。",
            ]
        )
    return [entry]


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
    revision = int(version["revision"])
    required_signals = (
        "實際自付醫療費用",
        "住院醫療保險金總限額",
        "百分之三",
        "醫療費用收據",
    )
    if any(compact_text(signal) not in dense for signal in required_signals):
        return None
    has_outpatient_extension = all(
        compact_text(signal) in dense
        for signal in ("雖未住院", "治療超過六小時")
    )
    if has_outpatient_extension is not (revision >= 5):
        return None
    if ("收據正本" in dense) is not (revision == 0):
        return None
    if ("受益人的身分證明" in dense) is not (revision >= 9):
        return None
    if ("徵詢其他醫師之醫學專業意見" in dense) is not (revision >= 11):
        return None

    required_policy_inputs = [TOTAL_LIMIT_STATE_KEY]
    if revision >= 5:
        required_policy_inputs.append(EVENT_STATE_KEY)
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "保單記載總限額",
        "selection_guidance": (
            "請輸入保單、被保險人名冊、批註或保險公司資料列示的住院醫療保險金總限額；"
            "再依本次事故填入實際自付費用。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "china-group-hospital-medical-limit",
            "company_group": "kgi_china_life",
            "source_batch_id": "tii-life-026",
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
            "plan_options": False,
            "unit_count_required": False,
            "benefit_entry_count": 1,
            "actual_expense_reimbursement": True,
            "per_event_total_limit_policy_recorded": True,
            "daily_room_meal_limit_percent": 3,
            "hospitalization_day_limit_in_terms": False,
            "outpatient_surgery_covered": revision >= 5,
            "emergency_observation_covered": revision >= 5,
            "emergency_observation_hours_threshold": 6 if revision >= 5 else None,
            "original_receipt_required": revision == 0,
            "beneficiary_identity_document_required": revision >= 9,
            "medical_opinion_review_available": revision >= 11,
            "nhi_reduction_percent": None,
            "separate_surgery_benefit_present": False,
            "death_benefit_available": False,
            "premium_waiver_available": False,
            "required_policy_inputs": required_policy_inputs,
            "claim_event_inputs": [
                ACTUAL_EXPENSE_STATE_KEY,
                ROOM_MEAL_EXPENSE_STATE_KEY,
                "hospitalization_days",
            ],
            "amount_presentation": "actual_expense_capped_by_policy_total_and_daily_room_percent",
        },
        "coverage_entries": coverage_entries(revision),
    }

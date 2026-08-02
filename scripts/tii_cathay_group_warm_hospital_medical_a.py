from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "30cb06369ca439ef550ff62c"
SOURCE_ROWS = (
    ("204317R11AMLA00", 0, "204317R11AMLA00-A.pdf", 6, "windows_ocr", "1ff19c238330dedc535f989449986504efe08dbfc5298f4b80ac03e95e9d192b", "c90954416cfa15c66564639fd891c1900b2acc5d22773ac1ccd48fa4486959e8"),
    ("204317R11AMLA01", 1, "204317R11AMLA01-A.pdf", 6, "pymupdf", "ca31e360320ae4820ee96ee33659c137942c160bd6e095d76e49b56c7bfac77a", "fb7d3f8f50ca06086999af09d81b31f4a6e9dae328f426305df1bf0751ed3374"),
    ("204317R11AMLA02", 2, "204317R11AMLA02-A.pdf", 6, "pymupdf", "ca31e360320ae4820ee96ee33659c137942c160bd6e095d76e49b56c7bfac77a", "fb7d3f8f50ca06086999af09d81b31f4a6e9dae328f426305df1bf0751ed3374"),
    ("204317R11AMLA03", 3, "204317R11AMLA03-A.pdf", 6, "pypdf", "49a88e441a61a78f0869d4c462c41eca5cf2e221bff57153ebbf002f7b76cee7", "84c9a622495496f35db730f835320d528309d8557fcb7e86b98bb98fb3c09864"),
    ("204317R11AMLA04", 4, "204317R11AMLA04-A.pdf", 6, "pypdf", "a4f70aa1d877519ff10031f0aba450dc7133f593e6ed23ba2e44f5353a659fb9", "afce07f2dd33c81eae368c4af66483eb1138e080a7084ac294da04ab980f9d24"),
    ("204317R11AMLA05", 5, "204317R11AMLA05-A.pdf", 6, "pymupdf", "9a464a70253264676aff7cbb6ce9b23ac4179eabfd69478f41836a674fd00318", "242f72005dd24969485b4359ede76424fa082fb545b741aa7daf2638e69c9d8e"),
    ("204313R11AMLA06", 6, "204313R11AMLA06-A.pdf", 6, "pymupdf", "02ff8634c7889589fefa1ee8e0bd4ef0cfe3b0d14053d02b235e8853e6fa6bb7", "c223121bb9625e2afe9ec0f223727ccd3fff7ecb766ef4c7b372a7a30818a4d1"),
    ("204313RZ1AMLA21A11Z10000007", 7, "204313RZ1AMLA21A11Z10000007-A.pdf", 7, "pymupdf", "34b193fbf2c01a1dd793c8799ca060d60afff22a56b2945720400fa112dc0826", "9b4df28133aabeed875e57aafeec31efb7476cfe69cea8261a9895b1c796cb4c"),
    ("204313RZ1AMLA21A11Z10000008", 8, "204313RZ1AMLA21A11Z10000008-A.pdf", 7, "pymupdf", "3670460dfa5191b4704c48f6a7666fdcc6b87fe30c3dc26216e01e1a98af5b6e", "ca8dad07f4188431dfa2037c072be45386f36472994b870f73dfad1511f4f450"),
    ("204313RZ1AMLA21A11Z10000009", 9, "204313RZ1AMLA21A11Z10000009-A.pdf", 7, "pymupdf", "28f88ddb1508fcf564f1cc145c58c268dd75dad83bc7874276c7a48fc17df46d", "a6ec9b4f2819084540e95d8e385fa0522144efb19bc928c58a68f650ca805fc6"),
    ("204313RZ1AMLA21A11Z10000010", 10, "204313RZ1AMLA21A11Z10000010-A.pdf", 7, "pymupdf", "7cea2bb5840122bcbf886958bc3b0186a2fae83140a4af8e10d6eb2237a0d399", "19f879373cbfee995ec65b0fad4e411a00d3b828c9d770ef54e2c2dacb822adb"),
    ("204313RZ1AMLA21A11Z10000011", 11, "204313RZ1AMLA21A11Z10000011-A.pdf", 7, "pypdf", "d162f6c05e1e365c330445048b59b245234b7e1811591d9e16e011884593b21f", "3440391caaedf2812b50f85dbc60c8222e39157d0cd817b4310211c16c41dfa2"),
    ("204313RZ1AMLA21A11Z10000012", 12, "204313RZ1AMLA21A11Z10000012-A.pdf", 7, "pypdf", "44ee238418148aedfc75d7869d28b90be9d39c96ee7580f8468720e50dbb5606", "206d0fdd371dc4b54486faeb498a2eb1b2562222ed5c5a00d8db18135db891ce"),
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

PLAN_VALUES = {
    "M10": (1_000, 100_000, 1_300),
    "M11": (1_100, 110_000, 1_400),
    "M12": (1_200, 120_000, 1_500),
    "M13": (1_300, 130_000, 1_600),
    "M14": (1_400, 140_000, 1_700),
    "M15": (1_500, 150_000, 1_750),
    "M16": (1_600, 160_000, 1_800),
    "M17": (1_700, 170_000, 1_900),
    "M18": (1_800, 180_000, 2_000),
    "M19": (1_900, 190_000, 2_100),
    "M20": (2_000, 200_000, 2_200),
    "M21": (2_100, 210_000, 2_300),
    "M22": (2_200, 220_000, 2_400),
    "M23": (2_300, 230_000, 2_500),
    "M24": (2_400, 240_000, 2_600),
    "M25": (2_500, 250_000, 2_700),
    "M26": (2_600, 260_000, 2_900),
    "M27": (2_700, 270_000, 3_000),
    "M28": (2_800, 280_000, 3_100),
    "M29": (2_900, 290_000, 3_200),
    "M30": (3_000, 300_000, 3_300),
}

EVENT_STATE_KEY = "cathay_group_warm_event_status"
BENEFIT_CHOICE_STATE_KEY = "cathay_group_warm_benefit_choice"
NHI_STATE_KEY = "cathay_group_warm_nhi_status"
ICU_LIMIT_RATE_STATE_KEY = "cathay_group_warm_icu_limit_rate"


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


def eligibility(revision: int) -> dict[str, Any]:
    ineligible = ["disease_waiting_not_met", "confirmed_not_eligible"]
    uncertain = ["uncertain"]
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


def entry(
    entry_id: str,
    name: str,
    amount: int,
    basis: str,
    note: str,
    source_ref: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "name": name,
        "amount": amount,
        "basis": basis,
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
        **fields,
    }


def coverage_entries(plan_name: str, revision: int) -> list[dict[str, Any]]:
    room_limit, inpatient_limit, daily_amount = PLAN_VALUES[plan_name]
    common_conditions = [
        "疾病須符合附約生效或中途加保後三十日等待期；意外傷害不受等待期限制。",
        "同一疾病、傷害或其併發症於出院後十四日內再次住院，合併視為同一次住院。",
        "同一次住院僅能選擇實支實付型或住院日額型之一申請。",
    ]
    reimbursement = {
        "calculation_basis": "percentage_of_actual_expense_with_cap",
        "amount_role": "payout",
        "rate_percent": 65,
        "rate_condition_state_key": NHI_STATE_KEY,
        "rate_condition_value": "not_nhi_covered",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        "exclusion_state_key": BENEFIT_CHOICE_STATE_KEY,
        "exclusion_values": ["daily_cash"],
        **eligibility(revision),
    }
    return [
        entry(
            "daily-room-expense-benefit",
            "每日病房費用保險金",
            room_limit,
            "daily_limit",
            f"{plan_name} 每日限額 {room_limit:,} 元，乘符合條款的住院日數後，與實際病房費用取低；同一次住院最高三百六十五日。",
            "第十三條實支實付型第一款及附表投保計畫別暨各項保險金給付表",
            limit_scope="per_day",
            quantity_state_key="hospitalization_days",
            quantity_cap=365,
            expense_state_key="hospital_room_expense",
            conditions=common_conditions,
            **reimbursement,
        ),
        entry(
            "inpatient-medical-expense-benefit",
            "住院醫療費用保險金",
            inpatient_limit,
            "per_hospitalization_limit",
            f"{plan_name} 每次住院限額 {inpatient_limit:,} 元；曾入住加護病房時限額提高為二倍，再與符合條款的實際住院醫療費用取低。手術費包含於本項，沒有另列手術保險金。",
            "第十三條實支實付型第二款及附表投保計畫別暨各項保險金給付表",
            limit_scope="per_hospitalization",
            secondary_limit_rate_state_key=ICU_LIMIT_RATE_STATE_KEY,
            expense_state_key="inpatient_medical_expense",
            conditions=[
                *common_conditions,
                "未以全民健康保險身分就醫、非健保醫院住院或費用未經健保給付時，符合項目的實際費用按百分之六十五計算，仍受限額約束。",
            ],
            **reimbursement,
        ),
        entry(
            "hospital-daily-benefit",
            "住院日額保險金",
            daily_amount,
            "daily_total",
            f"{plan_name} 每日 {daily_amount:,} 元，乘實際住院日數；同一次住院最高三百六十五日。",
            "第十三條日額給付型及附表投保計畫別暨各項保險金給付表",
            calculation_basis="per_day",
            amount_role="payout",
            limit_scope="per_day",
            aggregation_rule="separate",
            quantity_state_key="hospitalization_days",
            quantity_cap=365,
            result_kind="cash_payout",
            amount_stage="gross_contract_benefit",
            exclusion_state_key=BENEFIT_CHOICE_STATE_KEY,
            exclusion_values=["reimbursement"],
            conditions=common_conditions,
            **eligibility(revision),
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
    dense = re.sub(r"\s+", "", text)
    if any(
        signal not in dense
        for signal in (
            "國泰人壽團體溫情住院醫療健康保險附約",
            "每日病房費用保險金",
            "住院醫療費用保險金",
            "住院日額保險金",
            "三百六十五日",
            "65%",
            "加護病房",
            "二倍",
        )
    ):
        return None
    revision = int(version["revision"])
    newborn_count = 0 if revision < 4 else 11 if revision < 8 else 21
    plan_names = list(PLAN_VALUES)
    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "投保計畫別",
        "selection_guidance": (
            "請依保單選擇 M10 至 M30 的計畫；本商品沒有投保單位數。"
            "查看特定住院事故時，再選實支實付或住院日額，並填事故、健保、加護病房、住院日數與實際費用狀態。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "cathay-group-warm-hospital-medical-a",
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
            "plan_options": plan_names,
            "plan_required": True,
            "unit_count_required": False,
            "numeric_plan_table_in_terms": True,
            "plan_count": len(plan_names),
            "disease_waiting_days": 30,
            "accident_waiting_period_exempt": True,
            "same_hospital_readmission_days": 14,
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
            "benefit_entry_count": 3,
            "daily_cash_alternative_mutually_exclusive": True,
            "separate_surgery_benefit_present": False,
            "separate_outpatient_benefit_present": False,
            "hospitalization_day_limit": 365,
            "icu_inpatient_medical_limit_multiplier": 2,
            "non_nhi_actual_expense_rate_percent": 65,
            "required_policy_inputs": ["plan_name"],
            "claim_event_inputs": [
                EVENT_STATE_KEY,
                BENEFIT_CHOICE_STATE_KEY,
                NHI_STATE_KEY,
                ICU_LIMIT_RATE_STATE_KEY,
                "hospitalization_days",
                "hospital_room_expense",
                "inpatient_medical_expense",
            ],
            "amount_presentation": (
                "selected_plan_with_exact_limits_and_claim_event_inputs"
            ),
        },
        "plan_options": [
            {
                "value": plan_name,
                "label": f"計畫 {plan_name}",
                "coverage_entries": coverage_entries(plan_name, revision),
            }
            for plan_name in plan_names
        ],
    }

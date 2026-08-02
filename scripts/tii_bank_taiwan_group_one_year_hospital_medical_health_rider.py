from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "f33fa70679366b456489c3f5"
SOURCE_ROWS = (
    ("201317R11A05A01", 1, "201317R11A05A01-A.pdf", 8, "pypdf", "ea3cb9944d92564939c39280f3d2bf65cb2574220af31842f5c13b3b71341876", "9980625961755680d9417fb5afd78f8afa06dc39ab2ec505622303cf20bef306"),
    ("201317R11A05A02", 2, "201317R11A05A02-A.pdf", 10, "pypdf", "a85d8abe80b51949925292da2d1bc376adbaadc244422f137a3c2dd5429ac9f6", "0a227e948499597db4f81d5f3391d8fe3a04c8b3d40804af990952c0195ac469"),
    ("201317R11A05A03", 3, "201317R11A05A03-A.pdf", 10, "pypdf", "3ce9b32ae158deffe62b9d58db2dec17c5ef772fd7190085ce3c9037d3f2591a", "a3b7ef56d1e3e981ecaa7a1442fc3d5d8128c54440cfbd7833c69ece2456c4d0"),
    ("201317R11A05A04", 4, "201317R11A05A04-A.pdf", 10, "pypdf", "bcb63dc42de1b706e03a4884913f4235f3f7f9b6f02dad69cf082839cd3770f8", "8c17a18389391c10a04f5ae9fa4055380e97b59a0577956b32d7efb1eda292fa"),
    ("201317R11A05A05", 5, "201317R11A05A05-A.pdf", 10, "pypdf", "d93659fc87a8fbd71cd2344b88ad467b0a29875f891331125d82dacfaa5e1e2f", "ae7763ad9b4587ef9eeef76e608dde6d92300651f407246c94b0ce5c9a854521"),
    ("201317R11A05A06", 6, "201317R11A05A06-A.pdf", 10, "pypdf", "1ddf76c339dd380244d90acfce79ae8d25d3c8452380af49250e8d921cb97135", "b288e9d47cffbc54fbd0397640ce3719fa3cbb88d995e56665ed86e3e6b4126f"),
    ("201317R11A05A07", 7, "201317R11A05A07-A.pdf", 10, "pypdf", "7fbdc6659aa7c1485f1232da334fc2b39d13f69c9c2734a4dda29c0ef2884900", "f28738814d8ee494d16ee20580ff973374c7de9f2f615c87eef0fa39b3f4efd1"),
    ("201313R11A05A08", 8, "201313R11A05A08-A.pdf", 10, "pypdf", "cc7515677049c238b2413ba382f77b23d318829ef79ad5af11bc6b81d83fe5a6", "07c5b3abc931921f3c46f8571aa8c55bd77dd7e503cb947dde140a4a772b7374"),
    ("201313RZ1A05A21A11Z10000009", 9, "201313RZ1A05A21A11Z10000009-A.pdf", 11, "pypdf", "cc32ec24ce1ce6a0fd6e2607701c01773f877cbf07a8dbd6625c993deaa82221", "c1497786a16ef2588168265973008ac07dafbb014c59881b083610cc5aa65f70"),
    ("201313RZ1A05A21A11Z10000010", 10, "201313RZ1A05A21A11Z10000010-A.pdf", 11, "pypdf", "a0e58b38b9c56931be79f0a5e0cd6762a263f811290eab642671e2077bda7fe3", "925cf30c719235df81c40bd232161305356650c931e318bf4675046573bab4f3"),
    ("201313RZ1A05A21A11Z10000011", 11, "201313RZ1A05A21A11Z10000011-A.pdf", 11, "pypdf", "3e9059e2e35733e5a643cd65d22cac77e0d0f7cf779fa67d9f0930e3e5aec688", "d7bb9f6735d4f4fc50187a429cfdf77b55a3df84ed745a49028b829c9a63076a"),
    ("201313RZ1A05A21A11Z10000012", 12, "201313RZ1A05A21A11Z10000012-A.pdf", 11, "pypdf", "bd8583c98b5a998b72334d77ac9f94f0f685ffa6ad1d6f23c6576244718617ca", "27600a57edb25af864aecaf959157ec8dfd1498fde133939e9266122ce3b1430"),
    ("201313RZ1A05A21A11Z10000013", 13, "201313RZ1A05A21A11Z10000013-A.pdf", 11, "pypdf", "1c5aa130f7d3663009dd620636c81626219f3a21d922e2677e95420bcda2c7bb", "0b483514d7011df2af3637dd3f9d19d74603e0eff60e18ef63fabb9090a69ddc"),
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


def is_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    version = VERSIONS.get(product_id)
    return bool(
        version
        and str(document.get("batch_id") or "") == "tii-life-002"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
    )


def semantic_phase(revision: int) -> str:
    if revision == 1:
        return "legacy_social_insurance_original_receipt_daily_fallback"
    if revision <= 4:
        return "nhi_70_percent_designated_physician_expense"
    if revision == 5:
        return "nhi_70_percent_standard_expense_scope"
    if revision == 6:
        return "newborn_screening_exception"
    if revision == 7:
        return "post_expiry_readmission_exclusion"
    return "day_hospital_exclusion"


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


def reimbursement_entries(revision: int) -> list[dict[str, Any]]:
    settlement_fields: dict[str, Any]
    if revision == 1:
        settlement_fields = {
            "eligibility_state_key": (
                "bank_taiwan_legacy_reimbursement_eligibility_status"
            ),
            "ineligible_values": [
                "missing_social_insurance_or_original_receipt"
            ],
            "uncertain_values": ["uncertain"],
        }
    else:
        settlement_fields = {
            "rate_percent": 70,
            "rate_condition_state_key": "national_health_insurance_payment_status",
            "rate_condition_value": "not_covered",
        }
    common = {
        "calculation_basis": "reimbursement_with_cap",
        "amount_role": "limit",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **settlement_fields,
    }
    legacy_condition = (
        "最早版須以條款所稱社會保險身分住院並檢具醫療費用收據正本；否則依日額型給付。"
        if revision == 1
        else "未經全民健康保險給付時，符合條款的實際費用先按百分之七十計算，再與限額取低。"
    )
    return [
        entry(
            "daily-room-expense-reimbursement",
            "每日病房費用保險金",
            500,
            "daily_per_unit",
            "每單位每日最高五百元，乘投保單位數及符合條款的住院日數後，與實際病房費用取低。",
            "保單條款住院醫療保險金（實支實付型）及附表給付限額表",
            limit_scope="per_day",
            quantity_state_key="hospitalization_days",
            expense_state_key="hospital_room_expense",
            conditions=[legacy_condition, "同一次住院僅可選擇實支實付型或日額型之一。"],
            **common,
        ),
        entry(
            "inpatient-medical-expense-reimbursement",
            "住院醫療費用保險金",
            10_000,
            "per_unit",
            "每單位每次住院最高一萬元，乘投保單位數後，與符合條款的實際住院醫療費用取低。",
            "保單條款住院醫療保險金（實支實付型）及附表給付限額表",
            limit_scope="per_hospitalization",
            expense_state_key="inpatient_medical_expense",
            conditions=[legacy_condition, "同一次住院僅可選擇實支實付型或日額型之一。"],
            **common,
        ),
        entry(
            "inpatient-surgery-expense-reimbursement",
            "手術費用保險金",
            10_000,
            "per_unit",
            "每單位每次住院最高一萬元，乘投保單位數後，與符合條款的實際手術費用取低；同一住院多項手術合計仍受本限額約束。",
            "保單條款住院醫療保險金（實支實付型）及附表給付限額表",
            limit_scope="per_hospitalization",
            expense_state_key="inpatient_surgery_expense",
            conditions=[legacy_condition, "同一次住院僅可選擇實支實付型或日額型之一。"],
            **common,
        ),
    ]


def expected_entry_contracts(
    revision: int,
    settlement_type: str,
) -> dict[str, dict[str, Any]]:
    if settlement_type == "reimbursement":
        entries = reimbursement_entries(revision)
    elif settlement_type == "daily":
        entries = [
            entry(
                "hospital-daily-benefit",
                "住院醫療日額保險金",
                500,
                "daily_per_unit",
                "每單位每日五百元，乘投保單位數及實際住院日數；同一疾病或傷害最高三百六十五日。",
                "保單條款住院醫療保險金（日額型）及附表給付限額表",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="separate",
                quantity_state_key="hospitalization_days",
                quantity_cap=365,
                result_kind="cash_payout",
                amount_stage="gross_contract_benefit",
                conditions=["同一次住院僅可選擇實支實付型或日額型之一。"],
            )
        ]
    else:
        raise ValueError(f"unsupported settlement type: {settlement_type}")
    ignored = {"source", "note", "source_ref"}
    return {
        item["id"]: {
            key: value
            for key, value in item.items()
            if key not in ignored and key != "id"
        }
        for item in entries
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

    text = " ".join(
        unicodedata.normalize("NFKC", str(document.get("text") or "")).split()
    )
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version[
        "source_text_sha256"
    ]:
        return None
    dense = re.sub(r"\s+", "", text)
    common_signals = (
        "臺銀人壽團體一年期住院醫療健康保險附約",
        "每日病房費用保險金",
        "住院醫療費用保險金",
        "手術費用保險金",
        "住院醫療日額保險金",
        "每一單位給付限額",
        "五OO元",
        "一O、OOO元",
        "三百六十五日",
        "十四日",
    )
    if any(signal not in dense for signal in common_signals):
        return None

    revision = int(version["revision"])
    phase_checks = (
        ("社會保險" in dense, revision == 1),
        ("全民健康保險" in dense, revision >= 2),
        ("70%" in dense, revision >= 2),
        ("醫療收據正本" in dense, revision == 1),
        ("指定醫師" in dense, revision <= 4),
        ("醫療法人" in dense, revision >= 4),
        ("新生兒先天性代謝異常疾病篩檢" in dense, revision >= 6),
        ("本公司就再次住院部分不予給付保險金" in dense, revision >= 7),
        ("日間住院" in dense, revision >= 8),
        ("日間留院" in dense, revision >= 8),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    claim_inputs_a = [
        "hospitalization_days",
        "hospital_room_expense",
        "inpatient_medical_expense",
        "inpatient_surgery_expense",
        (
            "bank_taiwan_legacy_reimbursement_eligibility_status"
            if revision == 1
            else "national_health_insurance_payment_status"
        ),
    ]
    return {
        "selection_type": "plan_unit",
        "input_mode": "plan_unit",
        "selection_source": "terms",
        "selection_label": "理賠型別與投保單位數",
        "selection_guidance": (
            "請依本次住院選擇實支實付型或日額型，並輸入保單記載的正整數投保單位數；"
            "同一次住院不可同時申領兩型。最早版本若未以社會保險身分住院或無收據正本，請選日額型。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "bank-taiwan-group-one-year-hospital-medical-health-rider",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "company_group": "bank_taiwan_life",
            "source_batch_id": "tii-life-002",
            "terms_revision": f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "group_policy": True,
            "policy_period_years": 1,
            "renewal_not_guaranteed": True,
            "settlement_type_options": ["reimbursement", "daily"],
            "selected_settlement_type_mutually_exclusive": True,
            "unit_count_required": True,
            "unit_count_positive_integer": True,
            "maximum_units_per_insured": 5,
            "disease_waiting_days": 0,
            "same_hospital_readmission_days": 14,
            "social_insurance_wording": revision == 1,
            "original_receipt_required_for_reimbursement": revision == 1,
            "legacy_social_insurance_daily_fallback": revision == 1,
            "nhi_uncovered_payment_rate_percent": None if revision == 1 else 70,
            "designated_physician_expense_included": revision <= 4,
            "newborn_screening_waiting_exception": revision >= 6,
            "post_expiry_readmission_excluded": revision >= 7,
            "day_hospital_excluded": revision >= 8,
            "per_unit_room_daily_limit": 500,
            "per_unit_inpatient_medical_limit": 10_000,
            "per_unit_surgery_per_hospitalization_limit": 10_000,
            "per_unit_hospital_daily_amount": 500,
            "hospital_daily_day_limit": 365,
            "death_cash_benefit_available": False,
            "outpatient_medical_benefit_available": False,
            "required_policy_inputs": ["plan_name", "unit_count"],
            "claim_event_inputs_by_plan": {
                "reimbursement": claim_inputs_a,
                "daily": ["hospitalization_days"],
            },
            "amount_presentation": (
                "selected_settlement_type_and_units_with_claim_event_inputs"
            ),
        },
        "plan_options": [
            {
                "value": "reimbursement",
                "label": "實支實付型",
                "coverage_entries": reimbursement_entries(revision),
            },
            {
                "value": "daily",
                "label": "日額型",
                "coverage_entries": [
                    {
                        "id": entry_id,
                        **contract,
                        "source": "terms",
                        "note": "每單位每日五百元，乘投保單位數及實際住院日數；同一疾病或傷害最高三百六十五日。",
                        "source_ref": "保單條款住院醫療保險金（日額型）及附表給付限額表",
                    }
                    for entry_id, contract in expected_entry_contracts(
                        revision,
                        "daily",
                    ).items()
                ],
            },
        ],
    }

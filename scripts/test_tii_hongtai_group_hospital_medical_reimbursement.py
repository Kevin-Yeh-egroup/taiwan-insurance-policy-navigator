from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_PRODUCT_IDS,
    HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_VERSIONS,
    complete_strict_source_document,
    parse_hongtai_group_hospital_medical_reimbursement_unit,
    parse_hongtai_hospital_medical_rider_plan_unit,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-086"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-086-hongtai-group-hospital-medical-reimbursement-v265.json"
)
PARSER_ID = (
    "hongtai-group-hospital-medical-reimbursement-unit-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_VERSIONS[
            product_id
        ]
    )
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": source_sha256,
        },
        source_path,
    )
    return document, source_path


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-086/hongtai-group-reimbursement",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Hongtai group schedule"
        )


schedules: dict[str, dict] = {}
ocr_product_count = 0
for product_id in sorted(
    HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_PRODUCT_IDS
):
    source_version = (
        HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_VERSIONS[
            product_id
        ]
    )
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    if document["source_text_extractor"] == "windows_ocr":
        ocr_product_count += 1

    schedule = (
        parse_hongtai_group_hospital_medical_reimbursement_unit(
            document
        )
    )
    assert schedule is not None, product_id
    assert parse_hongtai_hospital_medical_rider_plan_unit(document) is None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["source_page_count"] == source_version["page_count"]
    assert version["non_nhi_payment_rate_percent"] == 65
    assert version["original_receipt_required"] is (revision >= 5)
    assert version["designated_physician_expense_covered"] is (
        revision <= 5
    )
    assert version["day_hospital_explicit"] is (revision >= 9)
    assert version["outpatient_benefit_present"] is False
    assert schedule["selection_type"] == "unit"
    assert schedule["input_mode"] == "unit"

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    expected_ids = {
        "daily-room-expense-reimbursement",
        "inpatient-medical-expense-reimbursement",
        "inpatient-surgery-expense-reimbursement",
    }
    if revision >= 9:
        expected_ids.update(
            {
                "day-hospital-medical-expense-reimbursement",
                "day-hospital-daily-cash-fallback",
            }
        )
    assert set(entries) == expected_ids
    assert entries["daily-room-expense-reimbursement"]["amount"] == 100
    assert entries["daily-room-expense-reimbursement"][
        "quantity_cap"
    ] == 365
    assert entries["inpatient-medical-expense-reimbursement"][
        "amount"
    ] == 3_000
    assert entries["inpatient-surgery-expense-reimbursement"][
        "amount"
    ] == 3_000
    assert entries["inpatient-surgery-expense-reimbursement"][
        "rate_min_percent"
    ] == 2.5
    if revision >= 9:
        fallback = entries["day-hospital-daily-cash-fallback"]
        assert "amount" not in fallback
        assert fallback["calculation_basis"] == "policy_state_amount"
        assert fallback["policy_state_keys"] == [
            "day_hospital_daily_cash_amount"
        ]
    schedules[product_id] = schedule


wrong_rate = copy.deepcopy(schedules["217313M11A00209"])
wrong_rate["version_characteristics"][
    "non_nhi_payment_rate_percent"
] = 70
assert_invalid_schedule(wrong_rate, "identity or formula is invalid")

wrong_fallback = copy.deepcopy(schedules["217313M11A00209"])
wrong_fallback["coverage_entries"][-1]["amount"] = 100
assert_invalid_schedule(wrong_fallback, "exact entry contract is invalid")

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v265"
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "ocr_product_count": ocr_product_count,
        "semantic_phase_count": 5,
    }
)

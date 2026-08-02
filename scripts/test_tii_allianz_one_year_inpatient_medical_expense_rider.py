from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_PRODUCT_IDS,
    ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_allianz_one_year_inpatient_medical_expense_rider_unit,
    parse_hongtai_group_hospital_medical_reimbursement_unit,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-092"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-092-allianz-one-year-inpatient-medical-expense-rider-v266.json"
)
PARSER_ID = (
    "allianz-one-year-inpatient-medical-expense-rider-unit-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_VERSIONS[
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
            "negative/tii-life-092/allianz-one-year-inpatient-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Allianz schedule"
        )


schedules: dict[str, dict] = {}
pymupdf_product_count = 0
for product_id in sorted(
    ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_PRODUCT_IDS
):
    source_version = (
        ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_VERSIONS[
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
    if document["source_text_extractor"] == "pymupdf":
        pymupdf_product_count += 1

    schedule = (
        parse_allianz_one_year_inpatient_medical_expense_rider_unit(
            document
        )
    )
    assert schedule is not None, product_id
    assert (
        parse_hongtai_group_hospital_medical_reimbursement_unit(
            document
        )
        is None
    )
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
    assert version["insured_amount_per_unit"] == 100
    assert version["annual_same_hospitalization_day_limit"] is (
        revision == 5 or revision >= 8
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 11
    )
    assert version["day_hospital_excluded"] is (revision >= 12)
    assert version["outpatient_benefit_present"] is False
    assert schedule["selection_type"] == "unit"
    assert schedule["input_mode"] == "unit"

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "daily-room-expense-reimbursement",
        "inpatient-medical-expense-reimbursement",
        "inpatient-surgery-expense-reimbursement",
        "hospital-daily-cash-alternative",
    }
    assert entries["daily-room-expense-reimbursement"]["amount"] == 100
    assert entries["inpatient-medical-expense-reimbursement"][
        "amount"
    ] == 3_000
    assert entries["inpatient-medical-expense-reimbursement"][
        "limit_proration_threshold"
    ] == 30
    assert entries["inpatient-surgery-expense-reimbursement"][
        "amount"
    ] == 4_000
    assert entries["inpatient-surgery-expense-reimbursement"][
        "rate_min_percent"
    ] == 15
    assert entries["hospital-daily-cash-alternative"]["amount"] == 120
    schedules[product_id] = schedule


wrong_rate = copy.deepcopy(schedules["218311R12D00203"])
wrong_rate["version_characteristics"][
    "non_health_insurance_payment_rate_percent"
] = 65
assert_invalid_schedule(wrong_rate, "identity or formula is invalid")

wrong_surgery_limit = copy.deepcopy(schedules["218311R12D00211"])
wrong_surgery_limit["coverage_entries"][2]["amount"] = 3_000
assert_invalid_schedule(
    wrong_surgery_limit,
    "exact entry contract is invalid",
)

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v266"
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        ALLIANZ_ONE_YEAR_INPATIENT_MEDICAL_EXPENSE_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "pymupdf_product_count": pymupdf_product_count,
        "semantic_phase_count": 6,
    }
)

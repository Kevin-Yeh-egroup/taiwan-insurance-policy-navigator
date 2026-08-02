from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    MERCANTILE_NEW_HOSPITAL_MEDICAL_PLAN_LIMITS,
    MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS,
    MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_hongtai_hospital_medical_rider_plan_unit,
    parse_mercantile_new_hospital_medical_rider_plan,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-062"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-062-mercantile-new-hospital-medical-rider-v248.json"
)
PARSER_ID = "mercantile-new-hospital-medical-rider-plan-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_DIR / product_id / version["file_name"]
    )
    source_sha256 = hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest()
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
            "negative/tii-life-062/mercantile-new-hospital-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Mercantile schedule"
        )


schedules: dict[str, dict] = {}
ocr_product_count = 0
for product_id in sorted(
    MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS
):
    source_version = (
        MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_VERSIONS[product_id]
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

    schedule = parse_mercantile_new_hospital_medical_rider_plan(
        document
    )
    assert schedule is not None, product_id
    assert parse_hongtai_hospital_medical_rider_plan_unit(
        document
    ) is None
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
    assert version["source_page_count"] == (
        source_version["page_count"]
    )
    assert version["social_insurance_wording"] is (
        revision == 0
    )
    assert version[
        "designated_physician_expense_included"
    ] is (revision <= 8)
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 10
    )
    assert version["day_hospital_excluded"] is (
        revision >= 11
    )
    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert [
        option["value"] for option in schedule["plan_options"]
    ] == list(MERCANTILE_NEW_HOSPITAL_MEDICAL_PLAN_LIMITS)

    for option in schedule["plan_options"]:
        room, surgery, medical = (
            MERCANTILE_NEW_HOSPITAL_MEDICAL_PLAN_LIMITS[
                option["value"]
            ]
        )
        entries = {
            entry["id"]: entry
            for entry in option["coverage_entries"]
        }
        assert set(entries) == {
            "daily-room-expense-reimbursement",
            "inpatient-medical-expense-reimbursement",
            "inpatient-surgery-expense-reimbursement",
            "hospital-daily-cash-alternative",
        }
        assert entries[
            "daily-room-expense-reimbursement"
        ]["amount"] == room
        assert entries[
            "inpatient-surgery-expense-reimbursement"
        ]["amount"] == surgery
        assert entries[
            "inpatient-medical-expense-reimbursement"
        ]["amount"] == medical
        assert entries[
            "inpatient-medical-expense-reimbursement"
        ]["limit_proration_threshold"] == 30
        assert entries[
            "hospital-daily-cash-alternative"
        ]["amount"] == room
    schedules[product_id] = schedule


wrong_phase = copy.deepcopy(schedules["211311R11A00611"])
wrong_phase["version_characteristics"][
    "day_hospital_excluded"
] = False
assert_invalid_schedule(
    wrong_phase,
    "version flag is invalid",
)

wrong_threshold = copy.deepcopy(schedules["211311R11A00609"])
wrong_threshold["plan_options"][0]["coverage_entries"][1][
    "limit_proration_threshold"
] = 31
assert_invalid_schedule(
    wrong_threshold,
    "exact entry contract is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v248"
)
assert proposal_payload["proposal_count"] == 16
assert proposal_payload["proposed_count"] == 16
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        MERCANTILE_NEW_HOSPITAL_MEDICAL_RIDER_VERSIONS[
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

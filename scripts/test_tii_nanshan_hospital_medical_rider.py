from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS,
    NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_hospital_medical_rider_unit,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-032"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-032-nanshan-hospital-medical-rider-v237.json"
)
PARSER_ID = "nanshan-hospital-medical-rider-unit-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
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
            "negative/tii-life-032/nanshan-hospital-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS
):
    source_version = (
        NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[product_id]
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

    schedule = parse_nanshan_hospital_medical_rider_unit(
        document
    )
    assert schedule is not None, product_id
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
    assert version["required_policy_inputs"] == ["unit_count"]
    assert version["family_member_coverage"] is (revision <= 3)
    assert version["social_insurance_wording"] is (
        revision <= 2
    )
    assert version["non_nhi_payment_rate_percent"] == (
        65 if revision >= 3 else None
    )
    assert version["cash_alternative_available"] is (
        revision <= 2 or revision >= 9
    )
    assert version[
        "unnotified_other_insurance_daily_fallback"
    ] is (revision >= 3)
    assert version[
        "unadmitted_six_hour_emergency_covered"
    ] is (3 <= revision <= 14)
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 14
    )
    assert version["day_hospital_excluded"] is (
        revision >= 15
    )
    assert version["designated_physician_expense_covered"] is (
        revision <= 12
    )
    assert schedule["selection_type"] == "unit"
    assert schedule["input_mode"] == "unit"
    assert schedule.get("plan_options") in (None, [])

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    expected_ids = {
        "daily-room-expense-reimbursement",
        "icu-room-expense-reimbursement",
        "surgery-stay-room-expense-reimbursement",
        "hospital-misc-surgery-reimbursement",
        "major-surgery-misc-reimbursement",
        "injury-pre-admission-emergency-sublimit",
        "pre-post-hospital-outpatient-reimbursement",
        "accident-accessory-per-item-sublimit",
        "accident-prosthetic-accessory-aggregate-limit",
    }
    if 3 <= revision <= 14:
        expected_ids.add(
            "unadmitted-six-hour-emergency-reimbursement"
        )
    if revision <= 2 or revision >= 9:
        expected_ids.add("hospital-cash-alternative-daily")
    if revision >= 3:
        expected_ids.add(
            "unnotified-other-insurance-daily-fallback"
        )
    assert set(entries) == expected_ids
    assert entries["daily-room-expense-reimbursement"][
        "amount"
    ] == 100
    assert entries["icu-room-expense-reimbursement"][
        "amount"
    ] == 200
    assert entries["surgery-stay-room-expense-reimbursement"][
        "amount"
    ] == 150
    assert entries["hospital-misc-surgery-reimbursement"][
        "amount"
    ] == 5_000
    assert entries["major-surgery-misc-reimbursement"][
        "amount"
    ] == 15_000
    assert entries["pre-post-hospital-outpatient-reimbursement"][
        "amount"
    ] == 500
    schedules[product_id] = schedule


assert (
    NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        "206311R11A30107"
    ]["source_text_sha256"]
    == NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        "206311R11A30108"
    ]["source_text_sha256"]
)
assert (
    NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        "206311R11A30107"
    ]["source_document_sha256"]
    != NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        "206311R11A30108"
    ]["source_document_sha256"]
)
assert (
    schedules["206311R11A30107"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["206311R11A30108"]["version_characteristics"][
        "source_product_id"
    ]
)

wrong_phase = copy.deepcopy(schedules["206311R11A30114"])
wrong_phase["version_characteristics"][
    "post_expiry_readmission_excluded"
] = False
assert_invalid_schedule(
    wrong_phase,
    "version flag is invalid",
)

wrong_limit = copy.deepcopy(schedules["206311R11A30109"])
wrong_limit["coverage_entries"][0]["amount"] = 90
assert_invalid_schedule(
    wrong_limit,
    "exact entry contract is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v237"
)
assert proposal_payload["proposal_count"] == 18
assert proposal_payload["proposed_count"] == 18
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == NANSHAN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        NANSHAN_HOSPITAL_MEDICAL_RIDER_VERSIONS[product_id][
            "source_document_sha256"
        ]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "ocr_product_count": 0,
        "semantic_phase_count": 6,
    }
)

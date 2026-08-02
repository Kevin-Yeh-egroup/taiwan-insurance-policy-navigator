from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_PRODUCT_IDS,
    HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS,
    HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_VERSIONS,
    complete_strict_source_document,
    parse_hongtai_group_hospital_medical_fixed_unit,
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
    / "tii-life-086-hongtai-group-hospital-medical-fixed-v284.json"
)
PARSER_ID = "hongtai-group-hospital-medical-fixed-benefit-unit-v1"


def source_document(
    product_id: str,
    versions: dict[str, dict] | None = None,
) -> tuple[dict, Path]:
    version = (versions or HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS)[
        product_id
    ]
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


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-086/hongtai-group-fixed",
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
    HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_PRODUCT_IDS
):
    source_version = HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS[
        product_id
    ]
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    if document["source_text_extractor"] == "windows_ocr":
        ocr_product_count += 1

    schedule = parse_hongtai_group_hospital_medical_fixed_unit(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source_version[
        "source_text_sha256"
    ]
    assert version["source_page_count"] == source_version["page_count"]
    assert version["newborn_screening_waiting_exception"] is (
        revision >= 5
    )
    assert version["day_hospital_included"] is (revision >= 7)
    assert version["death_unexpired_premium_refund_notice"] is (
        revision >= 1
    )
    assert version["hospitalization_day_limit_present"] is False
    assert version["per_unit_room_daily_amount"] == 100
    assert version["per_unit_intensive_care_daily_amount"] == 200
    assert version["per_unit_burn_unit_daily_amount"] == 200
    assert version["per_unit_home_recuperation_daily_amount"] == 100
    assert version["occupational_injury_daily_rate_percent"] == 150
    assert version["per_unit_surgery_base_amount"] == 3_000
    assert schedule["selection_type"] == "unit"
    assert schedule["input_mode"] == "unit"

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "daily-room-medical-benefit",
        "daily-intensive-care-medical-benefit",
        "daily-burn-unit-medical-benefit",
        "daily-home-recuperation-benefit",
        "inpatient-or-outpatient-surgery-medical-benefit",
        "unexpired-premium-refund",
    }
    for entry_id, amount, quantity_key in (
        ("daily-room-medical-benefit", 100, "general_ward_days"),
        (
            "daily-intensive-care-medical-benefit",
            200,
            "intensive_care_days",
        ),
        ("daily-burn-unit-medical-benefit", 200, "burn_unit_days"),
        (
            "daily-home-recuperation-benefit",
            100,
            "home_recuperation_days",
        ),
    ):
        entry = entries[entry_id]
        assert entry["amount"] == amount
        assert entry["calculation_basis"] == "per_unit_per_day"
        assert entry["quantity_state_key"] == quantity_key
        assert entry["rate_percent"] == 150
        assert entry["rate_condition_value"] == (
            "eligible_occupational_injury"
        )

    surgery = entries[
        "inpatient-or-outpatient-surgery-medical-benefit"
    ]
    assert surgery["amount"] == 3_000
    assert surgery["calculation_basis"] == "percentage_of_base"
    assert surgery["rate_state_key"] == "surgery_benefit_rate_percent"
    assert surgery["rate_min_percent"] == 2.5
    assert surgery["rate_max_percent"] == 100
    assert surgery["exclusion_values"] == ["not_attached"]
    assert "rate_percent" not in surgery
    schedules[product_id] = schedule


assert ocr_product_count == 5
assert len(schedules) == 14
assert (
    HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS[
        "217313MZ1A00121A11Z10000009"
    ]["source_document_sha256"]
    == HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS[
        "217313MZ1A00121A11Z10000010"
    ]["source_document_sha256"]
)

document, _ = source_document("217313M11A00107")
wrong_sha = copy.deepcopy(document)
wrong_sha["source_document_sha256"] = "0" * 64
assert parse_hongtai_group_hospital_medical_fixed_unit(wrong_sha) is None

wrong_text = copy.deepcopy(document)
wrong_text["text"] += "source mutation"
assert parse_hongtai_group_hospital_medical_fixed_unit(wrong_text) is None

cross_family, _ = source_document(
    "217317M11A00200",
    HONGTAI_GROUP_HOSPITAL_MEDICAL_REIMBURSEMENT_VERSIONS,
)
assert parse_hongtai_group_hospital_medical_fixed_unit(cross_family) is None

wrong_amount = copy.deepcopy(schedules["217313M11A00107"])
wrong_amount["coverage_entries"][0]["amount"] = 101
assert_invalid_schedule(wrong_amount, "exact entry contract is invalid")

wrong_version = copy.deepcopy(schedules["217317M11A00104"])
wrong_version["version_characteristics"][
    "newborn_screening_waiting_exception"
] = True
assert_invalid_schedule(wrong_version, "identity or formula is invalid")

assert PROPOSAL_PATH.exists(), PROPOSAL_PATH
proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v284"
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"] for proposal in proposal_payload["proposals"]
} == HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS[product_id][
            "source_document_sha256"
        ]
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

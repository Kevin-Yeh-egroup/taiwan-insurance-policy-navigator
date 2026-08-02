from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_PRODUCT_IDS,
    GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_VERSIONS,
    HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS,
    complete_strict_source_document,
    parse_global_inpatient_medical_fixed_rider_plan,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-164"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-164-global-inpatient-medical-fixed-rider-v287.json"
)
PARSER_ID = "global-inpatient-medical-fixed-rider-plan-v1"


def source_document(
    product_id: str,
    *,
    versions: dict[str, dict] | None = None,
    batch_id: str = BATCH_ID,
) -> tuple[dict, Path]:
    version = (versions or GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_VERSIONS)[
        product_id
    ]
    source_path = (
        ROOT
        / "work"
        / "tii-documents"
        / batch_id
        / product_id
        / version["file_name"]
    )
    document = complete_strict_source_document(
        {
            "batch_id": batch_id,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": hashlib.sha256(
                source_path.read_bytes()
            ).hexdigest(),
        },
        source_path,
    )
    return document, source_path


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-164/global-fixed-inpatient",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


schedules: dict[str, dict] = {}
pymupdf_count = 0
for product_id in sorted(GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_PRODUCT_IDS):
    source_version = GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_VERSIONS[product_id]
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    pymupdf_count += document["source_text_extractor"] == "pymupdf"

    schedule = parse_global_inpatient_medical_fixed_rider_plan(document)
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
        revision >= 6
    )
    assert version["post_expiry_readmission_excluded"] is (revision >= 7)
    assert version["day_hospital_excluded"] is (revision >= 8)
    assert version["disability_terminology"] == (
        "失能" if revision >= 10 else "殘廢"
    )
    assert version["contract_termination_unexpired_premium_refund"] is (
        revision >= 1
    )
    assert version["hospital_daily_day_limit"] == 365
    assert version["intensive_care_day_limit"] == 30
    assert version["burn_unit_day_limit"] == 60
    assert version["surgery_rate_min_percent"] == 5
    assert version["surgery_rate_max_percent"] == 300

    if revision <= 1:
        assert schedule["selection_type"] == "policy_state"
        assert "plan_options" not in schedule
        entries = {
            entry["id"]: entry for entry in schedule["coverage_entries"]
        }
        assert entries["hospital-daily-benefit"]["policy_state_keys"] == [
            "hospital_daily_amount"
        ]
        assert entries["intensive-care-daily-benefit"][
            "policy_state_keys"
        ] == ["global_fixed_icu_daily_amount"]
        assert entries["surgery-fixed-benefit"]["policy_state_keys"] == [
            "global_fixed_surgery_base_amount"
        ]
        assert ("unexpired-premium-refund" in entries) is (revision >= 1)
    else:
        expected_count = 12 if revision == 2 else 10
        assert schedule["selection_type"] == "plan"
        assert len(schedule["plan_options"]) == expected_count
        assert schedule["plan_options"][0]["value"] == "HI-05"
        assert schedule["plan_options"][-1]["value"] == (
            "HI-60" if revision == 2 else "HI-50"
        )
        for index, option in enumerate(schedule["plan_options"], start=1):
            entries = {
                entry["id"]: entry
                for entry in option["coverage_entries"]
            }
            daily = index * 500
            assert entries["hospital-daily-benefit"]["amount"] == daily
            assert entries["intensive-care-daily-benefit"]["amount"] == (
                daily * 2
            )
            assert entries["burn-unit-daily-benefit"]["amount"] == daily * 2
            assert entries["surgery-fixed-benefit"]["amount"] == daily * 15
            assert entries["surgery-aggregate-cap"]["amount"] == daily * 45
    schedules[product_id] = schedule


assert len(schedules) == 14
assert pymupdf_count == 3

document, _ = source_document("264311R11AMIR08")
wrong_sha = copy.deepcopy(document)
wrong_sha["source_document_sha256"] = "0" * 64
assert parse_global_inpatient_medical_fixed_rider_plan(wrong_sha) is None

wrong_text = copy.deepcopy(document)
wrong_text["text"] += "source mutation"
assert parse_global_inpatient_medical_fixed_rider_plan(wrong_text) is None

cross_family, _ = source_document(
    "217313M11A00107",
    versions=HONGTAI_GROUP_HOSPITAL_MEDICAL_FIXED_VERSIONS,
    batch_id="tii-life-086",
)
assert parse_global_inpatient_medical_fixed_rider_plan(cross_family) is None

wrong_amount = copy.deepcopy(schedules["264311R11AMIR02"])
wrong_amount["plan_options"][0]["coverage_entries"][0]["amount"] = 501
assert_invalid_schedule(wrong_amount, "exact entry contract is invalid")

wrong_phase = copy.deepcopy(schedules["264311R11AMIR05"])
wrong_phase["version_characteristics"][
    "newborn_screening_waiting_exception"
] = True
assert_invalid_schedule(wrong_phase, "identity or formula is invalid")

assert PROPOSAL_PATH.exists(), PROPOSAL_PATH
proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v287"
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"] for proposal in proposal_payload["proposals"]
} == GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        GLOBAL_INPATIENT_MEDICAL_FIXED_RIDER_VERSIONS[product_id][
            "source_document_sha256"
        ]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "pymupdf_product_count": pymupdf_count,
        "semantic_phase_count": 10,
    }
)

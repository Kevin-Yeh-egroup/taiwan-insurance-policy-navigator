from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_PRODUCT_IDS,
    TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_inpatient_daily_health_rider_policy_state,
    taiwan_inpatient_daily_health_rider_semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-008"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-008-taiwan-inpatient-daily-health-rider-v267.json"
)
PARSER_ID = (
    "taiwan-inpatient-daily-health-rider-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_VERSIONS[
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
            "negative/tii-life-008/taiwan-inpatient-daily",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Taiwan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_PRODUCT_IDS
):
    source_version = (
        TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_VERSIONS[
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
    schedule = (
        parse_taiwan_inpatient_daily_health_rider_policy_state(
            document
        )
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
    assert version["semantic_phase"] == (
        taiwan_inpatient_daily_health_rider_semantic_phase(
            revision
        )
    )
    assert version["required_policy_inputs"] == [
        "hospital_daily_amount",
        "hospitalization_days",
        "taiwan_inpatient_daily_event_status",
    ]
    assert version["disease_waiting_days"] == 30
    assert version["accident_waiting_period_exempt"] is True
    assert version["same_hospital_readmission_days"] == 14
    assert version["hospital_daily_days_limit"] == 90
    assert version["annual_same_hospitalization_day_limit"] is (
        revision >= 4
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 6
    )
    assert version["day_hospital_excluded"] is (
        revision >= 7
    )
    assert version["mental_day_stay_excluded"] is (
        revision >= 7
    )
    assert version["special_room_benefit_present"] is False
    assert version["surgery_benefit_present"] is False
    assert version["convalescence_benefit_present"] is False
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    assert len(schedule["coverage_entries"]) == 1
    entry = schedule["coverage_entries"][0]
    assert entry["id"] == "hospital-daily-benefit"
    assert entry["calculation_basis"] == "policy_state_amount"
    assert entry["basis"] == "policy_recorded_limit"
    assert entry["quantity_state_key"] == "hospitalization_days"
    assert entry["quantity_cap"] == 90
    assert entry["exclusion_state_key"] == (
        "taiwan_inpatient_daily_event_status"
    )
    assert entry["exclusion_values"] == [
        "disease_within_waiting_period",
    ]
    assert entry["policy_state_keys"] == [
        "hospital_daily_amount",
    ]
    schedules[product_id] = schedule


assert sum(
    version["source_text_extractor"] == "pymupdf"
    for version in TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_VERSIONS.values()
) == 5

wrong_phase = copy.deepcopy(schedules["202311R11AG6106"])
wrong_phase["version_characteristics"][
    "post_expiry_readmission_excluded"
] = False
assert_invalid_schedule(
    wrong_phase,
    "identity or formula is invalid",
)

wrong_extra_benefit = copy.deepcopy(
    schedules["202311RZ1AG6121A11Z10000014"]
)
wrong_extra_benefit["version_characteristics"][
    "surgery_benefit_present"
] = True
assert_invalid_schedule(
    wrong_extra_benefit,
    "identity or formula is invalid",
)

wrong_cap = copy.deepcopy(schedules["202311R11AG6101"])
wrong_cap["coverage_entries"][0]["quantity_cap"] = 120
assert_invalid_schedule(
    wrong_cap,
    "exact entry contract is invalid",
)

bad_document, _ = source_document("202311R11AG6101")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_taiwan_inpatient_daily_health_rider_policy_state(
        bad_document
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v267"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        TAIWAN_INPATIENT_DAILY_HEALTH_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "pymupdf_product_count": 5,
        "semantic_phase_count": len(
            {
                schedule["version_characteristics"][
                    "semantic_phase"
                ]
                for schedule in schedules.values()
            }
        ),
    }
)

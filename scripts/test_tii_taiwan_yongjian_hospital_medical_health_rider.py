from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS,
    TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_yongjian_hospital_medical_health_rider_policy_state,
    taiwan_yongjian_hospital_medical_health_rider_semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-008"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-008-taiwan-yongjian-hospital-medical-health-rider-v269.json"
)
PARSER_ID = (
    "taiwan-yongjian-hospital-medical-health-rider-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
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
            "negative/tii-life-008/taiwan-yongjian",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Yongjian schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
):
    source_version = (
        TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
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
        parse_taiwan_yongjian_hospital_medical_health_rider_policy_state(
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
        taiwan_yongjian_hospital_medical_health_rider_semantic_phase(
            revision
        )
    )
    assert version["family_fingerprint"] == (
        "445e409e23a2eaf7a27544c0"
    )
    assert version[
        "daily_amount_input_includes_no_claim_increment"
    ] is True
    assert version["no_claim_bonus_waiting_policy_years"] == 2
    assert version["no_claim_bonus_rate_percent"] == 20
    assert version["hospital_daily_days_limit"] == 365
    assert version["annual_same_hospitalization_day_limit"] is (
        revision >= 4
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 6
    )
    assert version["day_hospital_excluded"] is (
        revision >= 7
    )
    assert version["benefit_article_start"] == (
        10 if revision >= 14 else 9
    )
    assert version["surgery_table_multiplier_min"] == 1
    assert version["surgery_table_multiplier_max"] == 50
    assert version["reimbursement_benefit_present"] is False
    assert version["outpatient_benefit_present"] is False
    assert version["required_policy_inputs"] == [
        "hospital_daily_amount",
        "hospitalization_days",
        "intensive_care_days",
        "burn_unit_days",
        "hospital_transfer_count",
        "taiwan_yongjian_surgery_multiplier",
        "taiwan_inpatient_daily_event_status",
    ]
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    assert [
        entry["id"]
        for entry in schedule["coverage_entries"]
    ] == [
        "hospital-daily-medical-benefit",
        "discharge-recuperation-benefit",
        "surgery-benefit",
        "surgery-recuperation-benefit",
        "intensive-care-benefit",
        "burn-unit-benefit",
        "hospital-transfer-benefit",
    ]
    hospital_entry = schedule["coverage_entries"][0]
    assert hospital_entry["calculation_basis"] == (
        "tiered_or_stepped"
    )
    assert hospital_entry["amount_tiers"] == [
        {
            "label": "第 1 至 30 日",
            "min_quantity": 1,
            "max_quantity": 30,
            "multiplier": 1,
        },
        {
            "label": "第 31 至 365 日",
            "min_quantity": 31,
            "max_quantity": 365,
            "multiplier": 1.5,
        },
    ]
    surgery_entry = schedule["coverage_entries"][2]
    assert surgery_entry["multiplier_state_key"] == (
        "taiwan_yongjian_surgery_multiplier"
    )
    assert surgery_entry["minimum_multiplier"] == 1
    schedules[product_id] = schedule


wrong_phase = copy.deepcopy(schedules["202311R11AAC006"])
wrong_phase["version_characteristics"][
    "post_expiry_readmission_excluded"
] = False
assert_invalid_schedule(
    wrong_phase,
    "identity or formula is invalid",
)

wrong_tier = copy.deepcopy(schedules["202311R11AAC001"])
wrong_tier["coverage_entries"][0]["amount_tiers"][1][
    "multiplier"
] = 2
assert_invalid_schedule(
    wrong_tier,
    "exact entry contract is invalid",
)

wrong_source, _ = source_document("202311R11AAC001")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_taiwan_yongjian_hospital_medical_health_rider_policy_state(
        wrong_source
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v269"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        TAIWAN_YONGJIAN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"]["version_characteristics"][
        "source_product_id"
    ] == product_id

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "parser_id": PARSER_ID,
    }
)

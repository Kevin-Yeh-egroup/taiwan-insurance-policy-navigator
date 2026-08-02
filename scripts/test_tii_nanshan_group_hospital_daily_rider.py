from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_PRODUCT_IDS,
    NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_group_hospital_daily_rider_policy_state,
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
    / "tii-life-032-nanshan-group-hospital-daily-rider-v245.json"
)
PARSER_ID = "nanshan-group-hospital-daily-rider-policy-state-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_VERSIONS[
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
            "negative/tii-life-032/nanshan-group-hospital-daily",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_PRODUCT_IDS
):
    source_version = (
        NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_VERSIONS[
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
        parse_nanshan_group_hospital_daily_rider_policy_state(
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
    assert version["required_policy_inputs"] == [
        "hospital_daily_amount",
        "hospitalization_days",
    ]
    assert version["benefit_article"] == (
        16 if revision <= 1 else 15 if revision <= 5 else 13
    )
    assert version["inclusive_admission_discharge_days"] is (
        revision >= 6
    )
    assert version["discharge_day_requires_hospital_charge"] is (
        revision <= 5
    )
    assert version["separate_readmission_article"] is (
        revision >= 8
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 8
    )
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    assert len(schedule["coverage_entries"]) == 1
    entry = schedule["coverage_entries"][0]
    assert entry["id"] == "hospital-daily-tiered-benefit"
    assert entry["basis"] == "hospital_daily_amount"
    assert entry["quantity_state_key"] == "hospitalization_days"
    assert [tier["multiplier"] for tier in entry["amount_tiers"]] == [
        1,
        1.25,
        1.5,
    ]
    schedules[product_id] = schedule


assert (
    NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_VERSIONS[
        "206317R11A30108"
    ]["source_document_sha256"]
    == NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_VERSIONS[
        "206313R11A30209"
    ]["source_document_sha256"]
)
assert (
    schedules["206317R11A30108"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["206313R11A30209"]["version_characteristics"][
        "source_product_id"
    ]
)

wrong_tier = copy.deepcopy(schedules["206313R11A30210"])
wrong_tier["coverage_entries"][0]["amount_tiers"][1][
    "multiplier"
] = 1.2
assert_invalid_schedule(
    wrong_tier,
    "exact entry contract is invalid",
)

wrong_phase = copy.deepcopy(schedules["206317R11A30105"])
wrong_phase["version_characteristics"][
    "inclusive_admission_discharge_days"
] = True
assert_invalid_schedule(
    wrong_phase,
    "version flag is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v245"
)
assert proposal_payload["proposal_count"] == 16
assert proposal_payload["proposed_count"] == 16
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        NANSHAN_GROUP_HOSPITAL_DAILY_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "parser_id": PARSER_ID,
    }
)

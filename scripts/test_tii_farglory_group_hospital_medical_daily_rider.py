from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_PRODUCT_IDS,
    FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_farglory_group_hospital_medical_daily_rider_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-080"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-080-farglory-group-hospital-medical-daily-rider-v279.json"
)
PARSER_ID = (
    "farglory-group-hospital-medical-daily-rider-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_VERSIONS[
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
            "negative/tii-life-080/farglory-group-daily",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Farglory schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_PRODUCT_IDS
):
    source_version = (
        FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_VERSIONS[
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
        parse_farglory_group_hospital_medical_daily_rider_policy_state(
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
    assert version["family_fingerprint"] == (
        "e75bafd08aae5b32951bea47"
    )
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["required_policy_inputs"] == [
        "hospital_daily_amount",
        "hospitalization_days",
        "hospitalization_day_limit_per_stay",
    ]
    assert version["disease_waiting_days"] == 30
    assert version["same_hospital_readmission_days"] == 90
    assert version["day_hospital_excluded"] is (
        revision >= 4
    )
    assert version["claim_medical_review_clause"] is (
        revision >= 7
    )
    assert version["day_care_reference"] is (
        revision >= 12
    )
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    assert len(schedule["coverage_entries"]) == 1
    entry = schedule["coverage_entries"][0]
    assert entry["id"] == "hospital-daily-benefit"
    assert entry["calculation_basis"] == "policy_state_amount"
    assert entry["quantity_state_key"] == "hospitalization_days"
    assert entry["quantity_cap_state_key"] == (
        "hospitalization_day_limit_per_stay"
    )
    assert entry["policy_state_keys"] == [
        "hospital_daily_amount"
    ]
    schedules[product_id] = schedule


assert schedules["216312R12B61303"]["version_characteristics"][
    "semantic_phase"
] == "legacy_90_day_readmission"
assert schedules["216312R12B61304"]["version_characteristics"][
    "semantic_phase"
] == "day_hospital_legal_references"
assert schedules[
    "216313RZ1A61321A11Z10000007"
]["version_characteristics"]["semantic_phase"] == (
    "claim_medical_review_clause"
)
assert schedules[
    "216313RZ1A61321A11Z10000012"
]["version_characteristics"]["semantic_phase"] == (
    "day_care_reference"
)

wrong_phase = copy.deepcopy(schedules["216312R12B61303"])
wrong_phase["version_characteristics"][
    "day_hospital_excluded"
] = True
assert_invalid_schedule(
    wrong_phase,
    "version flag is invalid",
)

wrong_cap_key = copy.deepcopy(
    schedules["216313RZ1A61321A11Z10000013"]
)
wrong_cap_key["coverage_entries"][0][
    "quantity_cap_state_key"
] = "hospitalization_days"
assert_invalid_schedule(
    wrong_cap_key,
    "exact entry contract is invalid",
)

wrong_hash = copy.deepcopy(schedules["216312R12B61300"])
wrong_hash["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
assert_invalid_schedule(
    wrong_hash,
    "version formula is invalid",
)

bad_document, _ = source_document("216312R12B61300")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_farglory_group_hospital_medical_daily_rider_policy_state(
        bad_document
    )
    is None
)

cross_version, _ = source_document("216312R12B61300")
cross_version["product_id"] = "216312R12B61301"
cross_version["file_name"] = "216312R12B61301-A.pdf"
assert (
    parse_farglory_group_hospital_medical_daily_rider_policy_state(
        cross_version
    )
    is None
)

cross_product, _ = source_document("216312R12B61301")
cross_product["product_id"] = "209317R11A00100"
assert (
    parse_farglory_group_hospital_medical_daily_rider_policy_state(
        cross_product
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v279"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FARGLORY_GROUP_HOSPITAL_MEDICAL_DAILY_RIDER_VERSIONS[
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

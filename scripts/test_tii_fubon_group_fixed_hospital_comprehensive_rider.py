from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_PRODUCT_IDS,
    FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_VERSIONS,
    complete_strict_source_document,
    parse_fubon_group_fixed_hospital_comprehensive_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-050"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-group-fixed-hospital-comprehensive-rider-v262.json"
)
PARSER_ID = (
    "fubon-group-fixed-hospital-comprehensive-rider-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_VERSIONS[
        product_id
    ]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": source_hash,
        },
        source_path,
    )
    return document, source_path


def entries_by_id(schedule: dict, plan: str) -> dict[str, dict]:
    option = next(
        option
        for option in schedule["plan_options"]
        if option["value"] == plan
    )
    return {
        entry["id"]: entry
        for entry in option["coverage_entries"]
    }


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-050/fubon-fixed-hospital",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Fubon schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_PRODUCT_IDS
):
    version = (
        FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_VERSIONS[
            product_id
        ]
    )
    revision = int(version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        version["source_text_extractor"]
    )
    schedule = (
        parse_fubon_group_fixed_hospital_comprehensive_policy_state(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == (
        version["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version["source_text_sha256"]
    )
    assert characteristics["same_hospital_readmission_days"] == (
        90 if revision <= 9 else 14
    )
    assert characteristics["neonatal_screening_exception"] is (
        revision >= 5
    )
    assert characteristics["post_expiry_readmission_excluded"] is (
        revision >= 6
    )
    assert characteristics["day_hospital_excluded"] is (
        revision >= 7
    )
    assert schedule["selection_type"] == "plan"
    assert [option["value"] for option in schedule["plan_options"]] == [
        "A",
        "B",
        "C",
        "D",
        "E",
    ]

    plan_a = entries_by_id(schedule, "A")
    assert set(plan_a) == {
        "general-hospital-benefit",
        "intensive-care-additional-benefit",
        "burn-unit-additional-benefit",
    }
    assert plan_a["general-hospital-benefit"][
        "quantity_cap_state_key"
    ] == "hospitalization_day_limit_per_stay"
    assert plan_a["intensive-care-additional-benefit"][
        "rate_percent"
    ] == 200
    assert plan_a["intensive-care-additional-benefit"][
        "quantity_cap"
    ] == 30
    assert plan_a["burn-unit-additional-benefit"][
        "rate_percent"
    ] == 300
    assert plan_a["burn-unit-additional-benefit"][
        "quantity_cap"
    ] == 30

    plan_d = entries_by_id(schedule, "D")["surgery-benefit"]
    assert plan_d["unit_key"] == "surgery_fixed_amount"
    assert plan_d["rate_state_key"] == (
        "surgery_total_benefit_rate_percent"
    )
    assert plan_d["rate_min_percent"] == 10
    assert plan_d["rate_max_percent"] == 500
    plan_e = entries_by_id(schedule, "E")[
        "surgery-nursing-benefit"
    ]
    assert plan_e["unit_key"] == (
        "surgery_nursing_fixed_amount"
    )
    assert plan_e["rate_state_key"] == (
        "surgery_benefit_rate_percent"
    )
    schedules[product_id] = schedule


assert (
    FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_VERSIONS[
        "209317R11A00203"
    ]["source_document_sha256"]
    == FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_VERSIONS[
        "209317R11A00204"
    ]["source_document_sha256"]
)
assert (
    schedules["209317R11A00203"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["209317R11A00204"]["version_characteristics"][
        "source_product_id"
    ]
)

wrong_phase = copy.deepcopy(schedules["209313R11A00208"])
wrong_phase["version_characteristics"][
    "same_hospital_readmission_days"
] = 14
assert_invalid_schedule(
    wrong_phase,
    "version formula is invalid",
)

wrong_cap = copy.deepcopy(
    schedules["209313RZ1A00221A11Z10000014"]
)
entries_by_id(wrong_cap, "A")[
    "intensive-care-additional-benefit"
]["quantity_cap"] = 31
assert_invalid_schedule(
    wrong_cap,
    "exact entry contract is invalid",
)

wrong_hash = copy.deepcopy(schedules["209317R11A00201"])
wrong_hash["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
assert_invalid_schedule(
    wrong_hash,
    "version formula is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v262"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FUBON_GROUP_FIXED_HOSPITAL_COMPREHENSIVE_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "source_gap_count": 1,
        "parser_id": PARSER_ID,
    }
)

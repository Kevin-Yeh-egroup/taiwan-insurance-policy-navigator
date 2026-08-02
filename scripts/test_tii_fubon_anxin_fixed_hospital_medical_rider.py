from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
    sha256_file,
)
from tii_fubon_anxin_fixed_hospital_medical_rider import (
    FAMILY_FINGERPRINT,
    VERSIONS,
    parse_policy,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-050"
PARSER_ID = "fubon-anxin-fixed-hospital-medical-rider-policy-state-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-anxin-fixed-hospital-medical-rider-v301.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-050-fubon-anxin-fixed-hospital-medical-rider-v301-review-packet"
    / "tii-life-050-fubon-anxin-fixed-hospital-medical-rider-v301-review-packet.json"
)


def source_document(product_id: str) -> dict:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_ROOT / product_id / version["file_name"]
    document = {
        "batch_id": "tii-life-050",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/fubon-anxin-fixed")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


assert len(VERSIONS) == 13
schedules: dict[str, dict] = {}
for product_id, source in VERSIONS.items():
    document = source_document(product_id)
    schedule = parse_policy(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-050/{product_id}")
    schedules[product_id] = schedule

    revision = int(source["revision"])
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == source[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source["source_text_sha256"]
    assert version["source_text_extractor"] == source[
        "source_text_extractor"
    ]
    assert version["source_page_count"] == source["page_count"]
    assert version["same_hospital_readmission_days"] == (
        90 if revision <= 1 else 14
    )
    assert version["post_expiry_readmission_excluded"] is (revision >= 8)
    assert version["day_hospital_excluded"] is (revision >= 9)
    assert version["health_increment_rate_percent"] == 20
    assert version["required_policy_inputs"] == ["hospital_daily_amount"]

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "hospital-daily-tiered-benefit",
        "intensive-care-additional-benefit",
        "burn-unit-additional-benefit",
        "inpatient-nursing-benefit",
        "post-discharge-recuperation-benefit",
        "surgery-benefit",
        "same-stay-surgery-aggregate-cap",
        "surgery-nursing-benefit",
        "health-increment-benefit",
    }
    assert entries["hospital-daily-tiered-benefit"]["amount_tiers"] == [
        {
            "label": "第 1 至 30 日",
            "multiplier": 1,
            "min_quantity": 1,
            "max_quantity": 30,
        },
        {
            "label": "第 31 至 365 日",
            "multiplier": 2,
            "min_quantity": 31,
            "max_quantity": 365,
        },
    ]
    assert entries["surgery-benefit"]["multiplier"] == 30
    assert entries["surgery-nursing-benefit"]["multiplier"] == 10
    assert entries["same-stay-surgery-aggregate-cap"]["amount_role"] == (
        "limit"
    )


base_document = source_document("209311R11A00200")
assert parse_policy({**base_document, "batch_id": "tii-life-080"}) is None
assert parse_policy({**base_document, "file_name": "209311R11A00200-F.pdf"}) is None
assert parse_policy(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_policy({**base_document, "text": base_document["text"] + "跨版補值"}) is None
assert parse_policy({**base_document, "product_id": "209317R11A00200"}) is None

wrong_phase = copy.deepcopy(schedules["209311R11A00208"])
wrong_phase["version_characteristics"]["post_expiry_readmission_excluded"] = False
assert_invalid_schedule(wrong_phase, "source or version boundary is invalid")

wrong_formula = copy.deepcopy(schedules["209311RZ1A01021A11Z10000012"])
for entry in wrong_formula["coverage_entries"]:
    if entry["id"] == "surgery-benefit":
        entry["multiplier"] = 20
assert_invalid_schedule(wrong_formula, "exact entry contract is invalid")

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["proposal_count"] == 13
assert proposal["proposed_count"] == 13
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == set(VERSIONS)

review = json.loads(REVIEW_PACKET_PATH.read_text(encoding="utf-8"))
assert review["proposal_count"] == 13
assert review["status_counts"] == {"ready_for_human_source_review": 13}
assert len(review["items"]) == 13
assert all(
    item["review_packet_status"] == "ready_for_human_source_review"
    and item["errors"] == []
    for item in review["items"]
)

print("TII Fubon Anxin fixed hospital medical rider parser tests passed.")

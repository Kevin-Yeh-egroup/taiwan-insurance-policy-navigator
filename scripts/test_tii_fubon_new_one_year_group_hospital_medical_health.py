from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
    sha256_file,
)
from tii_fubon_new_one_year_group_hospital_medical_health import (
    FAMILY_FINGERPRINT,
    VERSIONS,
    has_day_hospital_exclusion,
    has_newborn_screening_exception,
    has_post_expiry_exclusion,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-050"
PARSER_ID = "fubon-new-one-year-group-hospital-medical-health-policy-state-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-new-one-year-group-hospital-medical-health-v302.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-050-fubon-new-one-year-group-hospital-medical-health-v302-review-packet"
    / "tii-life-050-fubon-new-one-year-group-hospital-medical-health-v302-review-packet.json"
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
        validate_plan_options(schedule, "negative/fubon-new-group-hospital")
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
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["source_document_sha256"] == source[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source["source_text_sha256"]
    assert version["source_text_extractor"] == source[
        "source_text_extractor"
    ]
    assert version["source_page_count"] == source["page_count"]
    assert version["newborn_screening_exception"] is (
        has_newborn_screening_exception(revision)
    )
    assert version["post_expiry_readmission_excluded"] is (
        has_post_expiry_exclusion(revision)
    )
    assert version["day_hospital_excluded"] is (
        has_day_hospital_exclusion(revision)
    )
    assert version["non_nhi_payment_rate_percent"] == 65
    assert version["accident_emergency_expense_limit"] == 5_000
    assert version["surgery_rate_min_percent"] == 10
    assert version["surgery_rate_max_percent"] == 500

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "room-and-board-reimbursement",
        "hospital-medical-reimbursement",
        "surgery-reimbursement",
        "intensive-care-reimbursement",
        "burn-center-reimbursement",
        "hospital-daily-cash-alternative",
        "accident-emergency-expense-sublimit",
    }
    assert entries["room-and-board-reimbursement"]["rate_percent"] == 65
    assert entries["surgery-reimbursement"]["limit_rate_state_key"] == (
        "surgery_benefit_rate_percent"
    )
    assert entries["surgery-reimbursement"]["rate_max_percent"] == 500
    assert entries["intensive-care-reimbursement"]["exclusion_values"] == [
        "burn_only",
        "neither_included",
    ]
    assert entries["burn-center-reimbursement"]["expense_state_key"] == (
        "burn_unit_room_expense"
    )
    assert entries["accident-emergency-expense-sublimit"]["amount"] == 5_000
    assert entries["accident-emergency-expense-sublimit"]["amount_role"] == (
        "reference"
    )


base_document = source_document("209313M11A00206")
assert parse_policy({**base_document, "batch_id": "tii-life-080"}) is None
assert parse_policy({**base_document, "file_name": "209313M11A00206-F.pdf"}) is None
assert parse_policy(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_policy({**base_document, "text": base_document["text"] + "跨版補值"}) is None
assert parse_policy({**base_document, "product_id": "209317M11A00605"}) is None

prior_family_path = (
    DOCUMENTS_ROOT
    / "209317M11A00605"
    / "209317M11A00605-A.pdf"
)
prior_family_document = complete_strict_source_document(
    {
        "batch_id": "tii-life-050",
        "product_id": "209317M11A00605",
        "file_name": prior_family_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(prior_family_path),
    },
    prior_family_path,
)
assert parse_policy(prior_family_document) is None

wrong_phase = copy.deepcopy(schedules["209317M11A00701"])
wrong_phase["version_characteristics"]["day_hospital_excluded"] = True
assert_invalid_schedule(wrong_phase, "source or version boundary is invalid")

wrong_source = copy.deepcopy(schedules["209313M11A00206"])
wrong_source["version_characteristics"]["family_fingerprint"] = (
    "629a7e54a13d118ee2a7ae6e"
)
assert_invalid_schedule(wrong_source, "source or version boundary is invalid")

wrong_formula = copy.deepcopy(schedules["209313MZ1A00121A11Z10000013"])
for entry in wrong_formula["coverage_entries"]:
    if entry["id"] == "surgery-reimbursement":
        entry["rate_max_percent"] = 400
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

print("TII Fubon new one-year group hospital medical health parser tests passed.")

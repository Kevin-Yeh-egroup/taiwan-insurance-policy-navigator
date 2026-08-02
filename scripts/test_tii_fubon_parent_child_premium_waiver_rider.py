from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_fubon_premium_waiver_rider_policy_state,
    parse_plan_table_with_parser,
    sha256_file,
)
from tii_fubon_parent_child_premium_waiver_rider import (
    FAMILY_FINGERPRINT,
    VERSIONS,
    parse_policy,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-050"
PARSER_ID = "fubon-parent-child-premium-waiver-rider-policy-state-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-parent-child-premium-waiver-rider-v304.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-050-fubon-parent-child-premium-waiver-rider-v304-review-packet"
    / "tii-life-050-fubon-parent-child-premium-waiver-rider-v304-review-packet.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-050-fubon-parent-child-premium-waiver-rider.json"
)
schedules: dict[str, dict] = {}


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/fubon-parent-child-waiver")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "strict validator accepted an invalid Fubon parent-child waiver schedule"
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


assert len(VERSIONS) == 13
for product_id, version in VERSIONS.items():
    document = source_document(product_id)
    schedule = parse_policy(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-050/{product_id}")
    schedules[product_id] = schedule

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == "tii-life-050"
    assert characteristics["family_fingerprint"] == FAMILY_FINGERPRINT
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    assert characteristics["source_page_count"] == version["page_count"]
    assert characteristics["terms_revision"] == f"partial_change_{revision}"
    assert characteristics[
        "main_policyholder_must_be_parent_of_main_insured"
    ] is True
    assert characteristics["eligible_event_types"] == [
        "death",
        "scheduled_impairment",
    ]
    assert characteristics["impairment_term"] == (
        "殘廢" if revision <= 5 else "失能"
    )
    assert characteristics["universal_waiting_days"] == 0
    assert characteristics["death_cash_benefit_available"] is False
    assert characteristics["waiver_is_non_cash_effect"] is True

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    waiver = entries["future-premium-waiver"]
    assert waiver["calculation_basis"] == "waiver"
    assert waiver["amount_role"] == "premium_waiver"
    assert waiver["unit_key"] == "remaining_premium_amount"
    assert waiver["result_kind"] == "non_cash_effect"
    assert waiver["eligibility_state_key"] == (
        "fubon_parent_child_waiver_event_status"
    )

    if revision >= 9:
        assert set(entries) == {
            "future-premium-waiver",
            "contract-own-waiver-periodic-refund",
            "other-waiver-rider-balance-refund",
        }
        assert characteristics["overlap_refunds_available"] is True
        assert characteristics[
            "other_waiver_riders_excluded_from_scope"
        ] is True
        assert entries["contract-own-waiver-periodic-refund"][
            "unit_key"
        ] == "fubon_parent_child_contract_own_waiver_refund_amount"
        assert entries["other-waiver-rider-balance-refund"][
            "unit_key"
        ] == "fubon_parent_child_other_waiver_balance_refund_amount"
    else:
        assert set(entries) == {"future-premium-waiver"}
        assert characteristics["overlap_refunds_available"] is False
        assert characteristics[
            "other_waiver_riders_excluded_from_scope"
        ] is False


parent_document = source_document("209342R11A00105")
assert parse_policy({**parent_document, "batch_id": "tii-life-080"}) is None
assert parse_policy({**parent_document, "file_name": "209342R11A00105-F.pdf"}) is None
assert parse_policy(
    {**parent_document, "source_document_sha256": "0" * 64}
) is None
assert parse_policy(
    {**parent_document, "text": f"{parent_document['text']}跨版補值"}
) is None
assert parse_fubon_premium_waiver_rider_policy_state(parent_document) is None

general_product_id = "209341R11A00104"
general_path = (
    DOCUMENTS_ROOT
    / general_product_id
    / f"{general_product_id}-A.pdf"
)
general_document = complete_strict_source_document(
    {
        "batch_id": "tii-life-050",
        "product_id": general_product_id,
        "file_name": general_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(general_path),
    },
    general_path,
)
assert parse_fubon_premium_waiver_rider_policy_state(general_document) is not None
assert parse_policy(general_document) is None

duplicate_a = VERSIONS["209341RZ1A00522A11Z10000009"]
duplicate_b = VERSIONS["209341RZ1A00522A11Z10000010"]
assert duplicate_a["source_document_sha256"] == duplicate_b[
    "source_document_sha256"
]
assert duplicate_a["source_text_sha256"] == duplicate_b["source_text_sha256"]
latest_a = VERSIONS["209341RZ1A00522A11Z10000016"]
latest_b = VERSIONS["209341RZ1A00522A11Z10000017"]
assert latest_a["source_document_sha256"] == latest_b[
    "source_document_sha256"
]
assert latest_a["source_text_sha256"] == latest_b["source_text_sha256"]

wrong_phase = copy.deepcopy(schedules["209341RZ1A00522A11Z10000013"])
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "parent_death_or_impairment_with_overlap_refunds"
)
assert_invalid_schedule(wrong_phase, "source or version boundary is invalid")

wrong_entry = copy.deepcopy(schedules["209341RZ1A00522A11Z10000014"])
for entry in wrong_entry["coverage_entries"]:
    if entry["id"] == "other-waiver-rider-balance-refund":
        entry["unit_key"] = "fubon_premium_waiver_overlap_refund_amount"
assert_invalid_schedule(wrong_entry, "exact entry contract is invalid")

matrix_payload = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix_payload["product_count"] == 13
assert matrix_payload["status_counts"] == {"readable": 13}
assert {row["product_id"] for row in matrix_payload["rows"]} == set(VERSIONS)

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["proposal_count"] == 13
assert proposal_payload["proposed_count"] == 13
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"] for proposal in proposal_payload["proposals"]
} == set(VERSIONS)

review_payload = json.loads(REVIEW_PACKET_PATH.read_text(encoding="utf-8"))
assert review_payload["proposal_count"] == 13
assert review_payload["status_counts"] == {
    "ready_for_human_source_review": 13
}
assert len(review_payload["items"]) == 13
assert all(
    item["review_packet_status"] == "ready_for_human_source_review"
    and item["errors"] == []
    for item in review_payload["items"]
)


print("TII Fubon parent-child premium waiver rider parser tests passed.")

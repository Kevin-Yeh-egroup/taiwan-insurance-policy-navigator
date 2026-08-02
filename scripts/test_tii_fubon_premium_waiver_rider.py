from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    FUBON_PREMIUM_WAIVER_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_fubon_premium_waiver_rider_policy_state,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-050"
PARSER_ID = "fubon-premium-waiver-rider-policy-state-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-premium-waiver-rider-v300.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-050-fubon-premium-waiver-rider-v300-review-packet"
    / "tii-life-050-fubon-premium-waiver-rider-v300-review-packet.json"
)
schedules: dict[str, dict] = {}


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/fubon-premium-waiver")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "strict validator accepted an invalid Fubon waiver schedule"
        )


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_ROOT / product_id / f"{product_id}-A.pdf"
    )
    document = {
        "batch_id": "tii-life-050",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(FUBON_PREMIUM_WAIVER_RIDER_VERSIONS) == 13
for product_id, version in FUBON_PREMIUM_WAIVER_RIDER_VERSIONS.items():
    document = source_document(product_id)
    schedule = parse_fubon_premium_waiver_rider_policy_state(document)
    assert schedule is not None
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
    assert characteristics["family_fingerprint"] == (
        "80ee9daa763499a2d5c34fb7"
    )
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_text_extractor"] == "pypdf"
    assert characteristics["source_page_count"] == version["page_count"]
    assert characteristics["terms_revision"] == (
        f"partial_change_{revision}"
    )
    assert characteristics["continuous_incapacity_days_required"] == 180
    assert characteristics["incapacity_term"] == (
        "失能" if revision <= 8 else "喪失工作能力"
    )
    assert characteristics["death_benefit_available"] is False
    assert characteristics["waiver_is_non_cash_effect"] is True

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) >= {
        "collected-premium-refund-within-180-days",
        "future-premium-waiver",
    }
    assert entries["collected-premium-refund-within-180-days"][
        "unit_key"
    ] == "fubon_premium_waiver_collected_refund_amount"
    waiver = entries["future-premium-waiver"]
    assert waiver["calculation_basis"] == "waiver"
    assert waiver["amount_role"] == "premium_waiver"
    assert waiver["unit_key"] == "remaining_premium_amount"
    assert waiver["result_kind"] == "non_cash_effect"

    if revision >= 13:
        assert set(entries) == {
            "collected-premium-refund-within-180-days",
            "future-premium-waiver",
            "current-unexpired-premium-refund",
            "overlapping-waiver-periodic-premium-refund",
        }
        assert characteristics[
            "current_unexpired_premium_refund_available"
        ] is True
        assert characteristics[
            "overlapping_waiver_periodic_refund_available"
        ] is True
        assert entries["overlapping-waiver-periodic-premium-refund"][
            "unit_key"
        ] == "fubon_premium_waiver_overlap_refund_amount"
        assert (
            "貼現一次給付"
            in entries["overlapping-waiver-periodic-premium-refund"][
                "conditions"
            ][1]
        )
    else:
        assert set(entries) == {
            "collected-premium-refund-within-180-days",
            "future-premium-waiver",
        }
        assert characteristics[
            "current_unexpired_premium_refund_available"
        ] is False
        assert characteristics[
            "overlapping_waiver_periodic_refund_available"
        ] is False


base_document = source_document("209341R11A00104")
assert parse_fubon_premium_waiver_rider_policy_state(
    {**base_document, "batch_id": "tii-life-080"}
) is None
assert parse_fubon_premium_waiver_rider_policy_state(
    {**base_document, "file_name": "209341R11A00104-F.pdf"}
) is None
assert parse_fubon_premium_waiver_rider_policy_state(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_fubon_premium_waiver_rider_policy_state(
    {**base_document, "text": f"{base_document['text']}跨版補值"}
) is None
assert parse_fubon_premium_waiver_rider_policy_state(
    {**base_document, "product_id": "209317R11A00200"}
) is None


latest_a = FUBON_PREMIUM_WAIVER_RIDER_VERSIONS[
    "209341RZ1A00422A11Z10000015"
]
latest_b = FUBON_PREMIUM_WAIVER_RIDER_VERSIONS[
    "209341RZ1A00422A11Z10000016"
]
assert latest_a["source_document_sha256"] == latest_b[
    "source_document_sha256"
]
assert latest_a["source_text_sha256"] == latest_b["source_text_sha256"]

wrong_phase = copy.deepcopy(
    schedules["209341RZ1A00422A11Z10000012"]
)
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "work_incapacity_refunds_and_overlap_coordination"
)
assert_invalid_schedule(wrong_phase, "source or version boundary is invalid")

wrong_overlap = copy.deepcopy(
    schedules["209341RZ1A00422A11Z10000013"]
)
for entry in wrong_overlap["coverage_entries"]:
    if entry["id"] == "overlapping-waiver-periodic-premium-refund":
        entry["unit_key"] = "overlapping_waiver_settlement_amount"
assert_invalid_schedule(wrong_overlap, "exact entry contract is invalid")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["proposal_count"] == 13
assert proposal_payload["proposed_count"] == 13
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"] for proposal in proposal_payload["proposals"]
} == set(FUBON_PREMIUM_WAIVER_RIDER_VERSIONS)

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


print("TII Fubon premium waiver rider parser tests passed.")

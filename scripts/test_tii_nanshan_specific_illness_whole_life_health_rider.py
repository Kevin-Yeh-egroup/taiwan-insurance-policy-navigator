from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_SPECIFIC_ILLNESS_ITEMS,
    NANSHAN_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_PRODUCT_IDS,
    NANSHAN_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_specific_illness_whole_life_health_rider_face_amount,
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
    / (
        "tii-life-032-nanshan-specific-illness-"
        "whole-life-health-rider-v260.json"
    )
)
PARSER_ID = (
    "nanshan-specific-illness-whole-life-health-rider-"
    "face-amount-v1"
)


def source_document(product_id: str) -> dict:
    version = (
        NANSHAN_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "source_document_sha256": version[
                "source_document_sha256"
            ],
            "text": "",
        },
        source_path,
    )


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-032/nanshan-specific-illness",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_PRODUCT_IDS
):
    version_source = (
        NANSHAN_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    revision = int(version_source["revision"])
    source_path = (
        DOCUMENTS_DIR / product_id / version_source["file_name"]
    )
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == version_source["source_document_sha256"]
    )

    document = source_document(product_id)
    assert document["source_text_extractor"] == (
        version_source["source_text_extractor"]
    )
    assert document["page_count"] == version_source["page_count"]
    assert document["pages_parsed"] == version_source["page_count"]
    assert (
        hashlib.sha256(document["text"].encode("utf-8")).hexdigest()
        == version_source["source_text_sha256"]
    )

    schedule = (
        parse_nanshan_specific_illness_whole_life_health_rider_face_amount(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    expected_phase = (
        "legacy-wait-disability-grade-1-to-3"
        if revision <= 3
        else "legacy-wait-disability-grade-1-to-6"
        if revision <= 5
        else "day31-wait-disability-grade-1-to-6"
        if revision <= 8
        else "day31-wait-definition-revision-disability-grade-1-to-6"
        if revision <= 13
        else "day31-wait-definition-revision-impairment-grade-1-to-6"
    )
    version = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert schedule["face_amount_label"] == "保險金額"
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        version_source["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        version_source["source_text_sha256"]
    )
    assert version["semantic_phase"] == expected_phase
    assert version["specific_illness_item_count"] == 18
    assert version["specific_illness_items"] == (
        NANSHAN_SPECIFIC_ILLNESS_ITEMS
    )
    assert version["specific_illness_waiting_days"] == 30
    assert version["accident_waiting_exception_items"] == [
        "重大燒燙傷",
        "嚴重頭部創傷",
        "昏迷",
    ]
    assert version["maximum_claim_count"] == 1
    assert version["contract_terminates_after_benefit"] is True
    assert version["installment_benefit_available"] is False
    assert version["premium_waiver_available"] is True
    assert version["premium_waiver_disability_term"] == (
        "失能" if revision >= 14 else "殘廢"
    )
    assert version["premium_waiver_disability_grade_max"] == (
        3 if revision <= 3 else 6
    )
    assert version["required_policy_inputs"] == [
        "nanshan_specific_illness_event_status"
    ]

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "specific-illness-benefit",
        "initial-waiting-period-premium-refund",
        "increased-face-amount-premium-refund",
        "future-premium-waiver",
        "termination-unexpired-premium-refund",
    }
    assert entries["specific-illness-benefit"]["rate_percent"] == 100
    assert entries["initial-waiting-period-premium-refund"][
        "policy_state_keys"
    ] == ["paid_premium_total"]
    assert entries["increased-face-amount-premium-refund"][
        "policy_state_keys"
    ] == ["increased_face_amount_premium_paid_total"]
    assert entries["future-premium-waiver"]["policy_state_keys"] == [
        "remaining_premium_amount"
    ]
    assert entries["termination-unexpired-premium-refund"][
        "policy_state_keys"
    ] == ["unexpired_premium_refund_amount"]
    assert {
        entry["exclusion_state_key"]
        for entry in entries.values()
    } == {"nanshan_specific_illness_event_status"}
    schedules[product_id] = schedule


wrong_source = source_document("206391R11A30100")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_nanshan_specific_illness_whole_life_health_rider_face_amount(
        wrong_source
    )
    is None
)
wrong_product = source_document("206391R11A30100")
wrong_product["product_id"] = "206391R11A39999"
assert (
    parse_nanshan_specific_illness_whole_life_health_rider_face_amount(
        wrong_product
    )
    is None
)

wrong_item_count = copy.deepcopy(
    schedules["206391RZ1A30123A11Z10000014"]
)
wrong_item_count["version_characteristics"][
    "specific_illness_item_count"
] = 17
assert_invalid_schedule(
    wrong_item_count,
    "version formula is invalid",
)

wrong_refund_key = copy.deepcopy(schedules["206391R11A30100"])
wrong_refund_key["coverage_entries"][2]["policy_state_keys"] = [
    "paid_premium_total"
]
assert_invalid_schedule(
    wrong_refund_key,
    "entry contract is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v260"
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    item["product_id"]
    for item in proposal_payload["proposals"]
} == NANSHAN_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_PRODUCT_IDS
assert all(
    item["candidates"][0]["parser_id"] == PARSER_ID
    for item in proposal_payload["proposals"]
)

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
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

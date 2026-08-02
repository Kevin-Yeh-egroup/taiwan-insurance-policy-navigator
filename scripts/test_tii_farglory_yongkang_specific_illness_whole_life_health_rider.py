from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    FARGLORY_YONGKANG_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_PRODUCT_IDS,
    FARGLORY_YONGKANG_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    farglory_yongkang_specific_illness_items,
    farglory_yongkang_specific_illness_semantic_phase,
    is_farglory_yongkang_specific_illness_whole_life_health_rider_strict_source,
    normalize_terms_text,
    parse_farglory_yongkang_specific_illness_whole_life_health_rider_face_amount,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-080"
FAMILY_FINGERPRINT = "b417f93847a588ff36487ef4"
PARSER_ID = (
    "farglory-yongkang-specific-illness-"
    "whole-life-health-rider-face-amount-v1"
)
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-080-farglory-yongkang-specific-illness-whole-life-health-rider-v281.json"
)
CROSS_PRODUCT_ID = "216351R12G02500"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        FARGLORY_YONGKANG_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": hashlib.sha256(
                source_path.read_bytes()
            ).hexdigest(),
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
            "negative/tii-life-080/farglory-yongkang",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Yongkang schedule"
        )


expected_ids = {
    "216351R11A09700",
    "216351R11A09701",
    "216351R11A09702",
    "216351R11A09703",
    "216351RZ1A09723A11Z10000004",
    "216351RZ1A09723A11Z10000005",
    "216351RZ1A09723A11Z10000006",
    "216351RZ1A09723A11Z10000007",
    "216351RZ1A09723A11Z10000008",
    "216351RZ1A09723A11Z10000009",
    "216351RZ1A09723A11Z10000010",
    "216351RZ1A09723A11Z10000011",
    "216351RZ1A09723A11Z10000012",
    "216351RZ1A09723A11Z10000013",
}
assert (
    FARGLORY_YONGKANG_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_PRODUCT_IDS
    == expected_ids
)
schedules: dict[str, dict] = {}

for product_id in sorted(expected_ids):
    source_contract = (
        FARGLORY_YONGKANG_SPECIFIC_ILLNESS_WHOLE_LIFE_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    revision = int(source_contract["revision"])
    document, source_path = source_document(product_id)
    assert source_path.exists()
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_contract["source_document_sha256"]
    )
    assert document["source_text_extractor"] == source_contract[
        "source_text_extractor"
    ]
    assert document["page_count"] == source_contract["page_count"]
    assert document["pages_parsed"] == source_contract["page_count"]
    assert (
        hashlib.sha256(
            normalize_terms_text(document["text"]).encode("utf-8")
        ).hexdigest()
        == source_contract["source_text_sha256"]
    )

    schedule = (
        parse_farglory_yongkang_specific_illness_whole_life_health_rider_face_amount(
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
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["semantic_phase"] == (
        farglory_yongkang_specific_illness_semantic_phase(revision)
    )
    assert version["specific_illness_items"] == (
        farglory_yongkang_specific_illness_items(revision)
    )
    assert version["specific_illness_item_count"] == 18
    assert version["specific_illness_waiting_days"] == 30
    assert version["maximum_claim_count"] == 1
    assert version["contract_terminates_after_benefit"] is True
    assert version["premium_waiver_available"] is False
    assert version["death_benefit_available"] is False
    assert version["maturity_benefit_available"] is False
    assert version["unexpired_premium_refund_requires_policy_state"] is True
    assert (
        version["unexpired_premium_proration_rounding_rule_available"]
        is False
    )
    assert version["required_policy_inputs"] == [
        "farglory_yongkang_event_status"
    ]
    assert version["claim_event_inputs"] == [
        "unexpired_premium_refund_amount"
    ]

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "specific-illness-benefit",
        "unexpired-premium-refund",
    }
    assert entries["specific-illness-benefit"]["rate_percent"] == 100
    assert entries["specific-illness-benefit"]["unit_key"] == "face_amount"
    assert entries["unexpired-premium-refund"]["unit_key"] == (
        "unexpired_premium_refund_amount"
    )
    schedules[product_id] = schedule


valid_document, _ = source_document("216351R11A09702")
for field, invalid_value in (
    ("batch_id", "tii-life-081"),
    ("product_id", CROSS_PRODUCT_ID),
    ("file_name", "216351R11A09703-A.pdf"),
    ("source_document_sha256", "0" * 64),
):
    invalid_document = copy.deepcopy(valid_document)
    invalid_document[field] = invalid_value
    assert not is_farglory_yongkang_specific_illness_whole_life_health_rider_strict_source(
        invalid_document
    )
    assert (
        parse_farglory_yongkang_specific_illness_whole_life_health_rider_face_amount(
            invalid_document
        )
        is None
    )

for field, invalid_value in (
    ("source_text_extractor", "pymupdf"),
    ("page_count", 99),
    ("pages_parsed", 99),
):
    invalid_document = copy.deepcopy(valid_document)
    invalid_document[field] = invalid_value
    assert (
        parse_farglory_yongkang_specific_illness_whole_life_health_rider_face_amount(
            invalid_document
        )
        is None
    )

invalid_text_document = copy.deepcopy(valid_document)
invalid_text_document["text"] += "\n非本版條款內容"
assert (
    parse_farglory_yongkang_specific_illness_whole_life_health_rider_face_amount(
        invalid_text_document
    )
    is None
)

wrong_source_schedule = copy.deepcopy(schedules["216351R11A09702"])
wrong_source_schedule["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
assert_invalid_schedule(wrong_source_schedule, "version formula is invalid")

wrong_phase_schedule = copy.deepcopy(
    schedules["216351RZ1A09723A11Z10000009"]
)
wrong_phase_schedule["version_characteristics"][
    "semantic_phase"
] = "legacy_eighteen_illness_definitions"
assert_invalid_schedule(wrong_phase_schedule, "version formula is invalid")

wrong_items_schedule = copy.deepcopy(
    schedules["216351RZ1A09723A11Z10000008"]
)
wrong_items_schedule["version_characteristics"][
    "specific_illness_items"
][0] = "心肌梗塞"
assert_invalid_schedule(wrong_items_schedule, "version formula is invalid")

wrong_entry_schedule = copy.deepcopy(schedules["216351R11A09700"])
wrong_entry_schedule["coverage_entries"][0]["rate_percent"] = 99
assert_invalid_schedule(wrong_entry_schedule, "exact entry contract is invalid")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == expected_ids

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phases": sorted(
            {
                schedule["version_characteristics"][
                    "semantic_phase"
                ]
                for schedule in schedules.values()
            }
        ),
        "cross_product_isolated": CROSS_PRODUCT_ID,
    }
)

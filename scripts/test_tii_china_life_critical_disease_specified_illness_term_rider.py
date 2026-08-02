from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_PRODUCT_IDS,
    CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_VERSIONS,
    complete_strict_source_document,
    parse_china_life_critical_disease_specified_illness_term_face_amount,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-026"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / (
        "tii-life-026-china-life-critical-disease-"
        "specified-illness-term-rider-v258.json"
    )
)
PARSER_ID = (
    "china-life-critical-disease-specified-illness-term-"
    "face-amount-v1"
)


def source_document(product_id: str) -> dict:
    version = (
        CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_VERSIONS[
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
            "negative/tii-life-026/china-life-critical-specified",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid China Life schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_PRODUCT_IDS
):
    version_source = (
        CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_VERSIONS[
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
    assert document["source_document_sha256"] == (
        version_source["source_document_sha256"]
    )
    assert document["source_text_extractor"] == "pymupdf"
    assert document["page_count"] == version_source["page_count"]
    assert document["pages_parsed"] == version_source["page_count"]
    assert (
        hashlib.sha256(
            document["text"].encode("utf-8")
        ).hexdigest()
        == version_source["normalized_text_sha256"]
    )

    schedule = (
        parse_china_life_critical_disease_specified_illness_term_face_amount(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    expected_semantic_phase = (
        "legacy-critical-and-specified-definitions"
        if revision <= 5
        else "severe-critical-legacy-specified-definitions"
        if revision <= 7
        else "severe-critical-reinstatement-wording"
        if revision == 8
        else "severe-critical-disability-language"
        if revision == 9
        else "severe-critical-and-severe-specified-definitions"
    )
    version = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert schedule["face_amount_label"] == "基本保險金額"
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        version_source["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        version_source["normalized_text_sha256"]
    )
    assert version["source_page_count"] == version_source["page_count"]
    assert version["semantic_phase"] == expected_semantic_phase
    assert version["critical_disease_item_count"] == 7
    assert version["specified_illness_item_count"] == 21
    assert version["critical_disease_waiting_days"] == 90
    assert version["specified_illness_waiting_days"] == 30
    assert version["maximum_claim_count"] == 1
    assert version["benefit_events_mutually_exclusive"] is True
    assert version["contract_terminates_after_benefit"] is True
    assert version["premium_waiver_available"] is False
    assert version["death_benefit_available"] is False
    assert version["disability_benefit_available"] is False
    assert version["surrender_value_available"] is False
    assert version["required_policy_inputs"] == [
        "critical_specified_benefit_claim_status"
    ]

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "critical-disease-trigger-benefit",
        "specified-illness-trigger-benefit",
        "unexpired-premium-refund",
    }
    assert {
        entries[entry_id]["benefit_group_id"]
        for entry_id in entries
    } == {
        "china-life-critical-disease-specified-illness-single-benefit"
    }
    assert (
        entries["critical-disease-trigger-benefit"][
            "aggregation_rule"
        ]
        == "choose_one"
    )
    assert (
        entries["specified-illness-trigger-benefit"][
            "aggregation_rule"
        ]
        == "choose_one"
    )
    assert (
        entries["unexpired-premium-refund"][
            "aggregation_rule"
        ]
        == "conditional_additive"
    )
    assert entries["unexpired-premium-refund"][
        "applies_to_entry_ids"
    ] == [
        "critical-disease-trigger-benefit",
        "specified-illness-trigger-benefit",
    ]
    assert entries["unexpired-premium-refund"][
        "policy_state_keys"
    ] == ["unexpired_premium_refund_amount"]
    assert {
        entry["exclusion_state_key"]
        for entry in entries.values()
    } == {"critical_specified_benefit_claim_status"}
    assert {
        tuple(entry["exclusion_values"])
        for entry in entries.values()
    } == {("already_paid",)}
    schedules[product_id] = schedule


wrong_source = source_document("205351R11A00200")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_china_life_critical_disease_specified_illness_term_face_amount(
        wrong_source
    )
    is None
)
wrong_product = source_document("205351R11A00200")
wrong_product["product_id"] = "205351R11A09999"
assert (
    parse_china_life_critical_disease_specified_illness_term_face_amount(
        wrong_product
    )
    is None
)

wrong_item_count = copy.deepcopy(
    schedules["205351RZ1A00222A11Z10000014"]
)
wrong_item_count["version_characteristics"][
    "specified_illness_item_count"
] = 12
assert_invalid_schedule(
    wrong_item_count,
    "version formula is invalid",
)

wrong_aggregation = copy.deepcopy(schedules["205351R11A00200"])
wrong_aggregation["coverage_entries"][0][
    "aggregation_rule"
] = "separate"
assert_invalid_schedule(
    wrong_aggregation,
    "event key is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v258"
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        CHINA_LIFE_CRITICAL_DISEASE_SPECIFIED_ILLNESS_TERM_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "ocr_product_count": 0,
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

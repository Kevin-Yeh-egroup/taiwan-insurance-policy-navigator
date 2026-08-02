from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_LEGACY_ITEMS,
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_PRODUCT_IDS,
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_DISABILITY_ITEMS,
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_IMPAIRMENT_ITEMS,
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS,
    complete_strict_source_document,
    parse_fubon_group_one_year_critical_illness_face_amount,
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
    / "tii-life-050-fubon-group-one-year-critical-illness-v261.json"
)
PARSER_ID = (
    "fubon-group-one-year-critical-illness-face-amount-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
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
            "negative/tii-life-050/fubon-group-critical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Fubon schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_PRODUCT_IDS
):
    source_contract = (
        FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
            product_id
        ]
    )
    revision = int(source_contract["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_contract["source_document_sha256"]
    )
    assert document["source_text_extractor"] == "pypdf"

    schedule = (
        parse_fubon_group_one_year_critical_illness_face_amount(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    expected_items = (
        FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_LEGACY_ITEMS
        if revision <= 9
        else FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_DISABILITY_ITEMS
        if revision == 10
        else FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_IMPAIRMENT_ITEMS
    )
    expected_disability_term = (
        "失能" if revision >= 11 else "殘廢"
    )
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == (
        "7302aeff2b249067c5173d49"
    )
    assert version["source_document_sha256"] == (
        source_contract["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_contract["source_text_sha256"]
    )
    assert version["source_page_count"] == (
        source_contract["page_count"]
    )
    assert version["critical_disease_definition_items"] == (
        expected_items
    )
    assert version["disability_term"] == (
        expected_disability_term
    )
    assert version["critical_disease_waiting_value"] == (
        90 if revision >= 9 else 3
    )
    assert version["critical_disease_waiting_unit"] == (
        "days" if revision >= 9 else "months"
    )
    assert version["required_policy_inputs"] == [
        "face_amount",
        "policy_effect_status_at_event",
        "death_benefit_status",
        "remaining_funeral_benefit_limit",
    ]
    assert version[
        "benefit_amount_clause_explicit_percentage"
    ] is False
    assert version[
        "gross_amount_before_unpaid_premium_offset"
    ] is True
    assert version[
        "unpaid_premium_offset_requires_insurer_confirmation"
    ] is True
    assert schedule["selection_type"] == "face_amount"
    assert schedule["plan_options"] == []

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "critical-illness-benefit",
        "death-or-funeral-benefit",
        "complete-disability-benefit",
    }
    assert {
        entries[entry_id]["benefit_group_id"]
        for entry_id in entries
    } == {
        "fubon-group-one-year-critical-illness-terminal-benefit"
    }
    assert {
        entries[entry_id]["aggregation_rule"]
        for entry_id in entries
    } == {"choose_one"}
    assert (
        entries["complete-disability-benefit"]["name"]
        == f"完全{expected_disability_term}保險金"
    )
    assert all(
        entry["exclusion_state_key"]
        == "policy_effect_status_at_event"
        and "policy_state_keys" not in entry
        for entry in entries.values()
    )
    schedules[product_id] = schedule

assert (
    FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "209357M12B00106"
    ]["source_document_sha256"]
    == FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "209357M12B00107"
    ]["source_document_sha256"]
)
assert (
    schedules["209357M12B00106"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["209357M12B00107"]["version_characteristics"][
        "source_product_id"
    ]
)

wrong_definition = copy.deepcopy(
    schedules["209353MZ5B00121A11Z10000010"]
)
wrong_definition["version_characteristics"][
    "critical_disease_definition_items"
] = FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_IMPAIRMENT_ITEMS
assert_invalid_schedule(
    wrong_definition,
    "version formula is invalid",
)

wrong_source = copy.deepcopy(
    schedules["209353MZ5B00121A11Z10000018"]
)
wrong_source["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
assert_invalid_schedule(
    wrong_source,
    "source identity is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FUBON_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "extractor_version": EXTRACTOR_VERSION,
    }
)

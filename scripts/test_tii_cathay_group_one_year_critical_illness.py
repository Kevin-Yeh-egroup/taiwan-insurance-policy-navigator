from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_LEGACY_ITEMS,
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_PRODUCT_IDS,
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_DISABILITY_ITEMS,
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_IMPAIRMENT_ITEMS,
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS,
    complete_strict_source_document,
    parse_cathay_group_one_year_critical_illness_face_amount,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-020"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-020-cathay-group-one-year-critical-illness-v236.json"
)
OCR_EVIDENCE_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-020-cathay-group-one-year-critical-illness-"
    "204357M11AQD006-ocr-evidence.json"
)
PARSER_ID = (
    "cathay-group-one-year-critical-illness-face-amount-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
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
            "negative/tii-life-020/cathay-group-critical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Cathay schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_PRODUCT_IDS
):
    version_source = (
        CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
            product_id
        ]
    )
    revision = int(version_source["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == version_source["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        version_source["source_text_extractor"]
    )

    schedule = (
        parse_cathay_group_one_year_critical_illness_face_amount(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    plan_required = revision >= 6
    expected_items = (
        CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_LEGACY_ITEMS
        if revision <= 10
        else CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_DISABILITY_ITEMS
        if revision == 11
        else CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_IMPAIRMENT_ITEMS
    )
    expected_disability_term = (
        "失能" if revision >= 12 else "殘廢"
    )
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        version_source["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        version_source["source_text_sha256"]
    )
    assert version["source_page_count"] == (
        version_source["page_count"]
    )
    assert version["critical_disease_definition_items"] == (
        expected_items
    )
    assert version["disability_term"] == (
        expected_disability_term
    )
    assert version["survival_condition_required"] is False
    assert version["required_policy_inputs"] == ["face_amount"]
    assert version["plan_required"] is plan_required
    assert version["plan_options"] == (
        ["A", "B"] if plan_required else []
    )
    assert version["critical_disease_waiting_days"] == (
        None if plan_required else 60
    )
    assert version["critical_disease_waiting_days_by_plan"] == (
        {"A": 60, "B": 90} if plan_required else None
    )
    assert version["waiting_period_article_location"] == (
        "article_3_definition"
        if revision == 17
        else "article_5"
    )
    assert schedule["selection_type"] == (
        "face_amount_plan" if plan_required else "face_amount"
    )
    assert [option["value"] for option in schedule["plan_options"]] == (
        ["A", "B"] if plan_required else []
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "specific-critical-illness-benefit",
        "death-benefit",
        "disability-benefit",
    }
    assert [
        entries[entry_id]["rate_percent"]
        for entry_id in entries
    ] == [100, 100, 100]
    assert {
        entries[entry_id]["benefit_group_id"]
        for entry_id in entries
    } == {
        "cathay-group-one-year-critical-illness-terminal-benefit"
    }
    assert {
        entries[entry_id]["aggregation_rule"]
        for entry_id in entries
    } == {"choose_one"}
    assert (
        entries["disability-benefit"]["name"]
        == f"{expected_disability_term}保險金"
    )
    schedules[product_id] = schedule

assert (
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "204357M11AQD003"
    ]["source_document_sha256"]
    == CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "204357M11AQD004"
    ]["source_document_sha256"]
)
assert (
    schedules["204357M11AQD003"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["204357M11AQD004"]["version_characteristics"][
        "source_product_id"
    ]
)
assert (
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "204357M11AQD008"
    ]["source_document_sha256"]
    == CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "204357M11AQD009"
    ]["source_document_sha256"]
)

ocr_evidence = json.loads(
    OCR_EVIDENCE_PATH.read_text(encoding="utf-8")
)
assert ocr_evidence["product_id"] == "204357M11AQD006"
assert ocr_evidence["visual_verification"]["status"] == "verified"
assert ocr_evidence["normalized_text_sha256"] == (
    CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
        "204357M11AQD006"
    ]["source_text_sha256"]
)

wrong_definition = copy.deepcopy(
    schedules["204353MZ5BQD021A11Z10000010"]
)
wrong_definition["version_characteristics"][
    "critical_disease_definition_items"
] = CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_SEVERE_IMPAIRMENT_ITEMS
assert_invalid_schedule(
    wrong_definition,
    "version formula is invalid",
)

wrong_plan = copy.deepcopy(schedules["204357M11AQD007"])
wrong_plan["plan_options"][0]["label"] = (
    "計畫 A（重大疾病等待 90 日）"
)
assert_invalid_schedule(
    wrong_plan,
    "plan options are invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v236"
assert proposal_payload["proposal_count"] == 18
assert proposal_payload["proposed_count"] == 18
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        CATHAY_GROUP_ONE_YEAR_CRITICAL_ILLNESS_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "ocr_product_count": 1,
        "legacy_definition_versions": 11,
        "standardized_definition_versions": 7,
    }
)

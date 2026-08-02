from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_FINGERPRINT,
    PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_PRODUCT_IDS,
    PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_prudential_group_cancer_hospital_daily_policy_state,
    prudential_group_cancer_hospital_daily_semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-014"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-014-prudential-group-cancer-hospital-daily-v257.json"
)
PARSER_ID = (
    "prudential-group-cancer-hospital-daily-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_VERSIONS[
        product_id
    ]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
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


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            (
                "negative/tii-life-014/"
                "prudential-group-cancer-hospital-daily"
            ),
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Prudential cancer "
            "hospital daily schedule"
        )


assert EXTRACTOR_VERSION == "tii-plan-benefits-v257"
assert len(PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_PRODUCT_IDS) == 15

schedules: dict[str, dict] = {}
for product_id in sorted(
    PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_PRODUCT_IDS
):
    source_version = (
        PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_VERSIONS[product_id]
    )
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    schedule = (
        parse_prudential_group_cancer_hospital_daily_policy_state(
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
    assert version["family_fingerprint"] == (
        PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_FINGERPRINT
    )
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    assert version["semantic_phase"] == (
        prudential_group_cancer_hospital_daily_semantic_phase(
            revision
        )
    )
    assert version["cancer_waiting_days"] == 60
    assert version["cancer_coverage_starts_day"] == 61
    assert version["annual_hospitalization_day_limit"] == 365
    assert version["home_recovery_rate_percent"] == 60
    assert version["cancer_definition_revision"] == (
        "standardized_severe_cancer_13_exclusions"
        if revision >= 11
        else "legacy_malignant_tumor_definition"
    )
    assert version["waiting_period_start_wording"] == (
        "start_or_reinstatement"
        if revision <= 5
        else "effective_or_add_date"
    )
    assert version["waiting_period_early_diagnosis_effect"] == (
        "refund_and_void_from_inception"
        if revision >= 12
        else "refund_and_remove_insured_eligibility"
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "cancer-hospital-daily-benefit",
        "post-discharge-home-recovery-benefit",
    }
    assert entries["cancer-hospital-daily-benefit"][
        "quantity_cap"
    ] == 365
    assert entries["cancer-hospital-daily-benefit"][
        "unit_key"
    ] == "cancer_hospital_daily_amount"
    assert entries["post-discharge-home-recovery-benefit"][
        "rate_percent"
    ] == 60
    assert entries["post-discharge-home-recovery-benefit"][
        "quantity_state_key"
    ] == "cancer_hospitalization_days"
    schedules[product_id] = schedule


wrong_hash = copy.deepcopy(schedules["203327M11A00100"])
wrong_hash["version_characteristics"]["source_document_sha256"] = (
    "0" * 64
)
assert_invalid_schedule(wrong_hash, "version boundary is invalid")

wrong_rate = copy.deepcopy(schedules["203327M11A00100"])
wrong_rate["coverage_entries"][1]["rate_percent"] = 50
assert_invalid_schedule(wrong_rate, "exact entry contract is invalid")

wrong_cap = copy.deepcopy(
    schedules["203323MZ1A00121A11Z10000012"]
)
wrong_cap["coverage_entries"][0]["quantity_cap"] = 180
assert_invalid_schedule(wrong_cap, "exact entry contract is invalid")

bad_document, _ = source_document("203327M11A00100")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_prudential_group_cancer_hospital_daily_policy_state(
        bad_document
    )
    is None
)

wrong_name_document, _ = source_document("203327M11A00100")
wrong_name_document["file_name"] = "wrong.pdf"
assert (
    parse_prudential_group_cancer_hospital_daily_policy_state(
        wrong_name_document
    )
    is None
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
} == PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        PRUDENTIAL_GROUP_CANCER_HOSPITAL_DAILY_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "parser_id": PARSER_ID,
    }
)

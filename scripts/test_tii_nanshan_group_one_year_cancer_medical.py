from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_PRODUCT_IDS,
    NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_VERSIONS,
    complete_strict_source_document,
    nanshan_group_one_year_cancer_medical_semantic_phase,
    parse_nanshan_group_one_year_cancer_medical_policy_state,
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
    / "tii-life-032-nanshan-group-one-year-cancer-medical-v246.json"
)
PARSER_ID = (
    "nanshan-group-one-year-cancer-medical-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_VERSIONS[
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
            "negative/tii-life-032/nanshan-group-cancer-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan cancer schedule"
        )


schedules: dict[str, dict] = {}
documents: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_PRODUCT_IDS
):
    source_version = (
        NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_VERSIONS[
            product_id
        ]
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
        parse_nanshan_group_one_year_cancer_medical_policy_state(
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
    early_schedule = revision <= 5
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["semantic_phase"] == (
        nanshan_group_one_year_cancer_medical_semantic_phase(
            revision
        )
    )
    assert version["cancer_waiting_days"] == 30
    assert version["cancer_coverage_starts_day"] == 31
    assert version["surgery_benefit_rule"] == (
        "same_icd_detailed_code_once"
        if early_schedule
        else "per_surgery"
    )
    assert version["recovery_days_cap_per_discharge"] == (
        21 if early_schedule else None
    )
    assert version["required_policy_inputs"] == [
        "cancer_hospital_daily_amount",
        "cancer_hospitalization_days",
        "cancer_surgery_benefit_amount",
        "cancer_surgery_count",
        "cancer_death_benefit_amount",
        "cancer_recovery_daily_amount",
    ]
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "cancer-inpatient-daily-benefit",
        "cancer-surgery-treatment-benefit",
        "cancer-death-benefit",
        "cancer-post-discharge-recovery-benefit",
    }
    assert entries["cancer-inpatient-daily-benefit"][
        "quantity_state_key"
    ] == "cancer_hospitalization_days"
    assert entries["cancer-surgery-treatment-benefit"][
        "quantity_state_key"
    ] == "cancer_surgery_count"
    assert entries["cancer-post-discharge-recovery-benefit"].get(
        "quantity_cap"
    ) == (21 if early_schedule else None)
    schedules[product_id] = schedule
    documents[product_id] = document


assert (
    NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_VERSIONS[
        "206327M11A30108"
    ]["source_document_sha256"]
    == NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_VERSIONS[
        "206327M11A30109"
    ]["source_document_sha256"]
)
assert (
    schedules["206327M11A30108"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["206327M11A30109"]["version_characteristics"][
        "source_product_id"
    ]
)

tampered_source = copy.deepcopy(documents["206327M11A30100"])
tampered_source["source_document_sha256"] = "0" * 64
assert (
    parse_nanshan_group_one_year_cancer_medical_policy_state(
        tampered_source
    )
    is None
)
tampered_text = copy.deepcopy(documents["206327M11A30106"])
tampered_text["text"] += "來源文字遭修改"
assert (
    parse_nanshan_group_one_year_cancer_medical_policy_state(
        tampered_text
    )
    is None
)
wrong_batch = copy.deepcopy(documents["206323MZ1A30121A11Z10000013"])
wrong_batch["batch_id"] = "tii-life-033"
assert (
    parse_nanshan_group_one_year_cancer_medical_policy_state(
        wrong_batch
    )
    is None
)

wrong_phase = copy.deepcopy(schedules["206327M11A30105"])
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "legacy_cancer_disease_application_amounts"
)
assert_invalid_schedule(
    wrong_phase,
    "exact version formula is invalid",
)

wrong_recovery_cap = copy.deepcopy(schedules["206327M11A30100"])
for entry in wrong_recovery_cap["coverage_entries"]:
    if entry["id"] == "cancer-post-discharge-recovery-benefit":
        entry["quantity_cap"] = 30
assert_invalid_schedule(
    wrong_recovery_cap,
    "exact entry contract is invalid",
)

wrong_amount_key = copy.deepcopy(
    schedules["206323MZ1A30121A11Z10000015"]
)
for entry in wrong_amount_key["coverage_entries"]:
    if entry["id"] == "cancer-surgery-treatment-benefit":
        entry["policy_state_keys"] = [
            "cancer_hospital_daily_amount"
        ]
assert_invalid_schedule(
    wrong_amount_key,
    "exact entry contract is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v246"
)
assert proposal_payload["proposal_count"] == 16
assert proposal_payload["proposed_count"] == 16
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        NANSHAN_GROUP_ONE_YEAR_CANCER_MEDICAL_VERSIONS[
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

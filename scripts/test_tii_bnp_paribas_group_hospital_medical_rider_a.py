from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_PRODUCT_IDS,
    BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_VERSIONS,
    EXTRACTOR_VERSION,
    bnp_paribas_group_hospital_medical_d_semantic_phase,
    complete_strict_source_document,
    parse_bnp_paribas_group_hospital_medical_a_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-170"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-170-bnp-group-hospital-medical-rider-a-v255.json"
)
PARSER_ID = (
    "bnp-paribas-group-hospital-medical-rider-a-policy-state-v1"
)
REQUIRED_POLICY_INPUTS = [
    "hospital_daily_amount",
    "hospitalization_days",
    "cancer_hospitalization_days",
]


def source_document(product_id: str) -> tuple[dict, Path]:
    version = BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_VERSIONS[
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
            "negative/tii-life-170/bnp-group-hospital-medical-a",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid BNP Type A schedule"
        )


assert EXTRACTOR_VERSION == "tii-plan-benefits-v255"
schedules: dict[str, dict] = {}
for product_id in sorted(
    BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_PRODUCT_IDS
):
    source_version = BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_VERSIONS[
        product_id
    ]
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    schedule = parse_bnp_paribas_group_hospital_medical_a_policy_state(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["semantic_phase"] == (
        bnp_paribas_group_hospital_medical_d_semantic_phase(
            revision
        )
    )
    assert version["product_family"] == (
        "bnp-paribas-group-hospital-medical-rider-type-a"
    )
    assert version["coverage_type"] == "A"
    assert version["hospitalization_day_limit_per_benefit"] == 365
    assert version["required_policy_inputs"] == REQUIRED_POLICY_INPUTS
    assert version["claim_event_inputs"] == REQUIRED_POLICY_INPUTS[1:]
    assert version["newborn_screening_waiting_exception"] is (
        revision >= 5
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 6
    )
    assert version["day_hospital_excluded"] is (revision >= 7)
    assert version["cancer_definition_revision"] == (
        "malignant_tumor_or_in_situ"
        if revision >= 10
        else "legacy_malignant_tumor"
    )
    assert version["health_authority_wording"] == (
        "central_health_authority"
        if revision >= 11
        else "executive_yuan_department_of_health"
    )
    assert "intensive_care_daily_additional_multiplier" not in version
    assert "burn_unit_daily_additional_multiplier" not in version
    assert "specified_surgery_multiplier" not in version
    assert "outpatient_rate_percent" not in version
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "general-hospital-daily-benefit",
        "cancer-hospital-daily-additional-benefit",
    }
    assert all(
        entry["quantity_cap"] == 365
        for entry in entries.values()
    )
    assert entries["cancer-hospital-daily-additional-benefit"][
        "benefit_group_id"
    ] == "bnp-group-hospital-a-daily-additions"
    schedules[product_id] = schedule


wrong_cap = copy.deepcopy(schedules["267317R11A00100"])
wrong_cap["coverage_entries"][0]["quantity_cap"] = 90
assert_invalid_schedule(wrong_cap, "exact entry contract is invalid")

wrong_type = copy.deepcopy(
    schedules["267313RZ1A00121A11Z10000015"]
)
wrong_type["version_characteristics"]["coverage_type"] = "B"
assert_invalid_schedule(wrong_type, "version formula is invalid")

wrong_hash = copy.deepcopy(schedules["267317R11A00100"])
wrong_hash["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
assert_invalid_schedule(wrong_hash, "version formula is invalid")

bad_document, _ = source_document("267317R11A00100")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_bnp_paribas_group_hospital_medical_a_policy_state(
        bad_document
    )
    is None
)

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
assert proposal_payload["proposal_count"] == 16
assert proposal_payload["proposed_count"] == 16
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        BNP_PARIBAS_GROUP_HOSPITAL_MEDICAL_A_VERSIONS[
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

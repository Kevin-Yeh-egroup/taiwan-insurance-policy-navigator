from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_PRODUCT_IDS,
    FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_VERSIONS,
    complete_strict_source_document,
    farglory_group_anjia_hospital_medical_rider_a_semantic_phase,
    parse_farglory_group_anjia_hospital_medical_rider_a_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-080"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-080-farglory-group-anjia-hospital-medical-rider-a-v280.json"
)
PARSER_ID = (
    "farglory-group-anjia-hospital-medical-rider-a-policy-state-v1"
)
ENTRY_IDS = [
    "hospital-room-expense-benefit",
    "intensive-care-room-expense-benefit",
    "physician-examination-expense-benefit",
    "inpatient-medical-expense-benefit",
    "surgery-expense-benefit",
    "hospital-daily-cash-alternative",
]


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_VERSIONS[
            product_id
        ]
    )
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


schedules: dict[str, dict] = {}
for product_id in sorted(
    FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_PRODUCT_IDS
):
    source_version = (
        FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_VERSIONS[
            product_id
        ]
    )
    document, source_path = source_document(product_id)
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == (
        source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    schedule = (
        parse_farglory_group_anjia_hospital_medical_rider_a_policy_state(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    revision = int(source_version["revision"])
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["semantic_phase"] == (
        farglory_group_anjia_hospital_medical_rider_a_semantic_phase(
            revision
        )
    )
    assert version["family_fingerprint"] == (
        "2bc4bb711f6da8e75b908a60"
    )
    assert version["same_hospital_readmission_days"] == 14
    assert version["disease_waiting_days"] == 30
    assert version["non_nhi_reimbursement_rate_percent"] == 66
    assert version["intensive_care_limit_multiplier"] == 3
    assert version["intensive_care_day_limit"] == 7
    assert version["numeric_plan_table_in_terms"] is False
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 6
    )
    assert version["day_hospital_excluded"] is (revision >= 7)
    assert version["newborn_screening_exception"] is (
        5 <= revision <= 8
    )
    assert version["claim_medical_review_clause"] is (
        revision >= 10
    )
    assert version["multichannel_premium_notice"] is (
        revision >= 13
    )
    assert version["day_care_reference"] is (revision >= 15)
    assert [
        entry["id"] for entry in schedule["coverage_entries"]
    ] == ENTRY_IDS
    schedules[product_id] = schedule


revision7 = schedules["216312R12B62507"]
wrong_schedule = copy.deepcopy(revision7)
wrong_schedule["coverage_entries"][0]["rate_percent"] = 65
try:
    validate_plan_options(
        wrong_schedule,
        "negative/tii-life-080/farglory-anjia-a",
    )
except SystemExit as error:
    assert "exact entry contract is invalid" in str(error), str(error)
else:
    raise AssertionError("formal validator accepted an altered rate")

valid_source, _ = source_document("216312R12B62507")
for field, wrong_value in (
    ("source_document_sha256", "0" * 64),
    ("file_name", "216312R12B62507-F.pdf"),
    ("source_text_extractor", "windows_ocr"),
    ("page_count", 10),
    ("pages_parsed", 10),
):
    wrong_source = copy.deepcopy(valid_source)
    wrong_source[field] = wrong_value
    assert (
        parse_farglory_group_anjia_hospital_medical_rider_a_policy_state(
            wrong_source
        )
        is None
    ), field

tampered_text = copy.deepcopy(valid_source)
tampered_text["text"] += "\n錯置來源"
assert (
    parse_farglory_group_anjia_hospital_medical_rider_a_policy_state(
        tampered_text
    )
    is None
)

for wrong_product_id in (
    "216312R12B62502",
    "216312R12B62603",
):
    wrong_family = copy.deepcopy(valid_source)
    wrong_family["product_id"] = wrong_product_id
    assert (
        parse_farglory_group_anjia_hospital_medical_rider_a_policy_state(
            wrong_family
        )
        is None
    ), wrong_product_id

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v280"
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FARGLORY_GROUP_ANJIA_HOSPITAL_MEDICAL_RIDER_A_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "parser_id": PARSER_ID,
        "negative_source_cases": 8,
    }
)

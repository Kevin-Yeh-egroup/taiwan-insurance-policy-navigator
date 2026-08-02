from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_PLAN_MULTIPLIERS,
    PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_PRODUCT_IDS,
    PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_prudential_new_hospital_medical_limit_rider_plan,
    prudential_new_hospital_medical_limit_rider_semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-014"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-014-prudential-new-hospital-medical-limit-rider-v271.json"
)
PARSER_ID = "prudential-new-hospital-medical-limit-rider-plan-v1"
ENTRY_IDS = [
    "general-room-expense-reimbursement",
    "intensive-care-room-expense-reimbursement",
    "inpatient-surgery-expense-reimbursement",
    "inpatient-medical-expense-reimbursement",
    "pre-post-hospital-outpatient-reimbursement",
    "outpatient-surgery-fee-reimbursement",
    "outpatient-surgery-medical-reimbursement",
    "hospital-daily-cash-alternative",
]


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_VERSIONS[
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


def assert_invalid_schedule(schedule: dict) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-014/prudential-new-hospital",
        )
    except SystemExit as error:
        assert "exact entry contract is invalid" in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Prudential schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_PRODUCT_IDS
):
    source_version = (
        PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_VERSIONS[
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
        parse_prudential_new_hospital_medical_limit_rider_plan(
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
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["semantic_phase"] == (
        prudential_new_hospital_medical_limit_rider_semantic_phase(
            revision
        )
    )
    assert version["family_fingerprint"] == (
        "d89daa76da49b3c8ee012a5f"
    )
    assert version["plan_options"] == list(
        PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_PLAN_MULTIPLIERS
    )
    assert version["non_social_insurance_limit_rate_percent"] == (
        60 if revision == 0 else 65
    )
    assert version["six_hour_continuous_treatment_eligible"] is (
        revision <= 7
    )
    assert version["day_hospital_excluded"] is (revision >= 8)
    assert version["complete_impairment_wording"] is (
        revision >= 10
    )
    assert version["electronic_receipt_allowed"] is (
        revision >= 13
    )
    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert schedule.get("coverage_entries") in (None, [])
    assert [
        option["value"] for option in schedule["plan_options"]
    ] == ["I", "II", "III", "IV", "V", "VI"]
    for option in schedule["plan_options"]:
        assert [
            entry["id"] for entry in option["coverage_entries"]
        ] == ENTRY_IDS
    schedules[product_id] = schedule


revision0 = schedules["203311R11A00300"]
plan_vi_entries = {
    entry["id"]: entry
    for entry in revision0["plan_options"][-1]["coverage_entries"]
}
assert plan_vi_entries[
    "general-room-expense-reimbursement"
]["amount"] == 3_000
assert plan_vi_entries[
    "intensive-care-room-expense-reimbursement"
]["amount"] == 6_000
assert plan_vi_entries[
    "inpatient-surgery-expense-reimbursement"
]["amount"] == 150_000
assert plan_vi_entries[
    "inpatient-medical-expense-reimbursement"
]["amount_tiers"] == [
    {
        "label": "住院 30 日（含）以下",
        "min_quantity": 1,
        "max_quantity": 30,
        "amount": 90_000,
    },
    {
        "label": "住院 31 至 90 日",
        "min_quantity": 31,
        "max_quantity": 90,
        "amount": 135_000,
    },
    {
        "label": "住院 91 日（含）以上",
        "min_quantity": 91,
        "max_quantity": 365,
        "amount": 180_000,
    },
]
assert plan_vi_entries[
    "pre-post-hospital-outpatient-reimbursement"
]["amount"] == 1_500

wrong_amount = copy.deepcopy(revision0)
wrong_amount["plan_options"][0]["coverage_entries"][0][
    "amount"
] = 501
assert_invalid_schedule(wrong_amount)

wrong_source, _ = source_document("203311R11A00300")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_prudential_new_hospital_medical_limit_rider_plan(
        wrong_source
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v271"
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        PRUDENTIAL_NEW_HOSPITAL_MEDICAL_LIMIT_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"]["version_characteristics"][
        "source_product_id"
    ] == product_id

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "parser_id": PARSER_ID,
    }
)

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_FINGERPRINT,
    PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_PRODUCT_IDS,
    PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_prudential_group_hospital_medical_b_policy_state,
    prudential_group_hospital_medical_b_semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-014"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-014-prudential-group-hospital-medical-b-v256.json"
)
PARSER_ID = "prudential-group-hospital-medical-b-policy-state-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_VERSIONS[product_id]
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
            "negative/tii-life-014/prudential-group-hospital-medical-b",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Prudential Type B schedule"
        )


assert EXTRACTOR_VERSION == "tii-plan-benefits-v256"
assert len(PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_PRODUCT_IDS) == 15

schedules: dict[str, dict] = {}
for product_id in sorted(
    PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_PRODUCT_IDS
):
    source_version = PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_VERSIONS[
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
    schedule = parse_prudential_group_hospital_medical_b_policy_state(
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
    assert version["family_fingerprint"] == (
        PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_FINGERPRINT
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
        prudential_group_hospital_medical_b_semantic_phase(revision)
    )
    assert version["non_insurance_payment_rate_percent"] == (
        60 if revision <= 1 else 65
    )
    assert version["hospital_daily_day_limit"] == (
        None if revision <= 1 else 60
    )
    assert version["post_discharge_outpatient_measure"] == (
        "visits" if revision <= 1 else "days"
    )
    assert version["receipt_daily_cash_alternative"] is (
        revision >= 2
    )
    assert version["designated_physician_expense_covered"] is (
        2 <= revision <= 6
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 9
    )
    assert version["day_hospital_excluded"] is (revision >= 10)

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    expected_ids = {
        "hospital-room-daily-benefit",
        "surgery-expense-benefit",
        "inpatient-medical-expense-benefit",
        "post-discharge-outpatient-benefit",
    }
    if revision <= 1:
        expected_ids.add("hospitalization-total-benefit-limit")
    assert set(entries) == expected_ids
    assert entries["hospital-room-daily-benefit"].get(
        "quantity_cap"
    ) == (None if revision <= 1 else 60)
    assert entries["post-discharge-outpatient-benefit"][
        "quantity_state_key"
    ] == (
        "post_discharge_outpatient_visit_count"
        if revision <= 1
        else "post_discharge_outpatient_day_count"
    )
    for entry_id in (
        "surgery-expense-benefit",
        "inpatient-medical-expense-benefit",
    ):
        assert entries[entry_id]["rate_percent"] == (
            60 if revision <= 1 else 65
        )
        assert entries[entry_id].get("exclusion_state_key") == (
            None
            if revision <= 1
            else "medical_claim_receipt_status"
        )
    schedules[product_id] = schedule


wrong_hash = copy.deepcopy(schedules["203317M11A00200"])
wrong_hash["version_characteristics"]["source_document_sha256"] = "0" * 64
assert_invalid_schedule(wrong_hash, "version boundary is invalid")

wrong_limit_key = copy.deepcopy(schedules["203317M11A00202"])
wrong_limit_key["coverage_entries"][1]["unit_key"] = "reimbursement_limit"
assert_invalid_schedule(wrong_limit_key, "exact entry contract is invalid")

wrong_receipt_rule = copy.deepcopy(schedules["203317M11A00202"])
wrong_receipt_rule["coverage_entries"][1].pop("exclusion_state_key")
wrong_receipt_rule["coverage_entries"][1].pop("exclusion_values")
assert_invalid_schedule(
    wrong_receipt_rule,
    "exact entry contract is invalid",
)

bad_document, _ = source_document("203317M11A00200")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_prudential_group_hospital_medical_b_policy_state(
        bad_document
    )
    is None
)

wrong_name_document, _ = source_document("203317M11A00200")
wrong_name_document["file_name"] = "wrong.pdf"
assert (
    parse_prudential_group_hospital_medical_b_policy_state(
        wrong_name_document
    )
    is None
)

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        PRUDENTIAL_GROUP_HOSPITAL_MEDICAL_B_VERSIONS[
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

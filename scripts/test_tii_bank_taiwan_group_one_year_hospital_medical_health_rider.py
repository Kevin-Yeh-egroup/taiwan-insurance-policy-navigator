from __future__ import annotations

import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BANK_TAIWAN_GROUP_ONE_YEAR_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy,
    parse_plan_table_with_parser,
)
from tii_bank_taiwan_group_one_year_hospital_medical_health_rider import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-002"
PARSER_ID = (
    "bank-taiwan-group-one-year-hospital-medical-health-rider-v1"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-002-bank-taiwan-group-one-year-hospital-medical-health-rider-v290.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-002-bank-taiwan-group-one-year-hospital-medical-health-rider-v290"
    / "tii-life-002-bank-taiwan-group-one-year-hospital-medical-health-rider-v290-review-packet.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-002-bank-taiwan-group-one-year-hospital-medical-health-rider.json"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        BANK_TAIWAN_GROUP_ONE_YEAR_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    source_path = (
        ROOT
        / "work"
        / "tii-documents"
        / BATCH_ID
        / product_id
        / version["file_name"]
    )
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


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-002/bank-taiwan-group-hospital-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


schedules: dict[str, dict] = {}
for product_id in sorted(PRODUCT_IDS):
    source_version = (
        BANK_TAIWAN_GROUP_ONE_YEAR_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == "pypdf"
    assert document["page_count"] == source_version["page_count"]
    normalized_text = " ".join(
        unicodedata.normalize("NFKC", document["text"]).split()
    )
    assert hashlib.sha256(normalized_text.encode("utf-8")).hexdigest() == (
        source_version["source_text_sha256"]
    )

    schedule = (
        parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
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
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["terms_revision"] == f"partial_change_{revision}"
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source_version[
        "source_text_sha256"
    ]
    assert version["settlement_type_options"] == [
        "reimbursement",
        "daily",
    ]
    assert version["maximum_units_per_insured"] == 5
    assert version["same_hospital_readmission_days"] == 14
    assert version["hospital_daily_day_limit"] == 365
    assert version["social_insurance_wording"] is (revision == 1)
    assert version["original_receipt_required_for_reimbursement"] is (
        revision == 1
    )
    assert version["nhi_uncovered_payment_rate_percent"] == (
        None if revision == 1 else 70
    )
    assert version["designated_physician_expense_included"] is (
        revision <= 4
    )
    assert version["newborn_screening_waiting_exception"] is (
        revision >= 6
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 7
    )
    assert version["day_hospital_excluded"] is (revision >= 8)
    assert version["death_cash_benefit_available"] is False
    assert version["outpatient_medical_benefit_available"] is False

    options = schedule["plan_options"]
    assert [option["value"] for option in options] == [
        "reimbursement",
        "daily",
    ]
    reimbursement_entries = {
        item["id"]: item for item in options[0]["coverage_entries"]
    }
    assert reimbursement_entries[
        "daily-room-expense-reimbursement"
    ]["amount"] == 500
    assert reimbursement_entries[
        "inpatient-medical-expense-reimbursement"
    ]["amount"] == 10_000
    assert reimbursement_entries[
        "inpatient-surgery-expense-reimbursement"
    ]["amount"] == 10_000
    if revision == 1:
        assert reimbursement_entries[
            "daily-room-expense-reimbursement"
        ]["eligibility_state_key"] == (
            "bank_taiwan_legacy_reimbursement_eligibility_status"
        )
    else:
        assert reimbursement_entries[
            "daily-room-expense-reimbursement"
        ]["rate_percent"] == 70
    daily_entry = options[1]["coverage_entries"][0]
    assert daily_entry["amount"] == 500
    assert daily_entry["quantity_cap"] == 365
    schedules[product_id] = schedule


assert len(schedules) == 13

document, _ = source_document("201317R11A05A02")
wrong_batch = copy.deepcopy(document)
wrong_batch["batch_id"] = "tii-life-003"
assert (
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
        wrong_batch
    )
    is None
)

wrong_type = copy.deepcopy(document)
wrong_type["document_type"] = "summary"
assert (
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
        wrong_type
    )
    is None
)

wrong_sha = copy.deepcopy(document)
wrong_sha["source_document_sha256"] = "0" * 64
assert (
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
        wrong_sha
    )
    is None
)

wrong_text = copy.deepcopy(document)
wrong_text["text"] += "source mutation"
assert (
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
        wrong_text
    )
    is None
)

wrong_file = copy.deepcopy(document)
wrong_file["file_name"] = "201317R11A05A03-A.pdf"
assert (
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
        wrong_file
    )
    is None
)

cross_product = copy.deepcopy(document)
cross_product["product_id"] = "201317R11A05A03"
assert (
    parse_bank_taiwan_group_one_year_hospital_medical_health_rider_policy(
        cross_product
    )
    is None
)

wrong_amount = copy.deepcopy(schedules["201317R11A05A02"])
wrong_amount["plan_options"][0]["coverage_entries"][0]["amount"] = 501
assert_invalid_schedule(wrong_amount, "exact entry contract is invalid")

wrong_phase = copy.deepcopy(schedules["201317R11A05A07"])
wrong_phase["version_characteristics"]["day_hospital_excluded"] = True
assert_invalid_schedule(wrong_phase, "identity or version formula is invalid")

source_matrix = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert source_matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert source_matrix["product_count"] == 13
assert source_matrix["status_counts"] == {"readable": 13}
assert source_matrix["duplicate_source_sha_groups"] == {}
assert {
    row["product_id"] for row in source_matrix["rows"]
} == PRODUCT_IDS

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v290"
assert proposal_payload["proposal_count"] == 13
assert proposal_payload["proposed_count"] == 13
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"] for proposal in proposal_payload["proposals"]
} == PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        BANK_TAIWAN_GROUP_ONE_YEAR_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

review_packet = json.loads(REVIEW_PACKET_PATH.read_text(encoding="utf-8"))
assert review_packet["proposal_count"] == 13
assert review_packet["status_counts"] == {
    "ready_for_human_source_review": 13
}
assert all(
    item["review_packet_status"] == "ready_for_human_source_review"
    for item in review_packet["items"]
)

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phase_count": len(
            {item["version_characteristics"]["semantic_phase"] for item in schedules.values()}
        ),
        "ready_for_human_source_review": 13,
    }
)

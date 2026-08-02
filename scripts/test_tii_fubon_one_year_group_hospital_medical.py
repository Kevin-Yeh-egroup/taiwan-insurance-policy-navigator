from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    complete_strict_source_document,
    normalize_terms_text,
    parse_plan_table_with_parser,
)
from tii_fubon_one_year_group_hospital_medical import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    is_strict_source,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-050"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-one-year-group-hospital-medical-v299.json"
)
PARSER_ID = "fubon-one-year-group-hospital-medical-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
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
            "negative/tii-life-050/fubon-one-year-group-hospital",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("formal validator accepted an invalid schedule")


expected_common_ids = {
    "daily-room-reimbursement-benefit",
    "surgery-reimbursement-benefit",
    "hospital-misc-reimbursement-benefit",
    "hospital-deductible-reference",
}
schedules: dict[str, dict] = {}

for product_id in sorted(PRODUCT_IDS):
    source_contract = VERSIONS[product_id]
    revision = int(source_contract["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_contract["source_document_sha256"]
    )
    assert document["source_text_extractor"] == source_contract[
        "source_text_extractor"
    ]
    assert document["page_count"] == source_contract["page_count"]
    assert hashlib.sha256(
        normalize_terms_text(document["text"]).encode("utf-8")
    ).hexdigest() == source_contract["source_text_sha256"]

    schedule = parse_policy(document)
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
    assert version["source_document_sha256"] == source_contract[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source_contract[
        "source_text_sha256"
    ]
    assert version["daily_cash_choice_available"] is (revision <= 10)
    assert version["same_hospital_readmission_days"] == (
        90 if revision <= 5 else 14
    )
    assert version["day_hospital_excluded"] is (revision >= 3)
    assert version["electronic_receipt_document_accepted"] is (
        revision >= 12
    )
    assert version["benefit_entry_count"] == (5 if revision <= 10 else 4)

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    expected_ids = set(expected_common_ids)
    if revision <= 10:
        expected_ids.add("hospital-medical-daily-cash-alternative")
    assert set(entries) == expected_ids
    assert entries["surgery-reimbursement-benefit"][
        "calculation_basis"
    ] == "reimbursement_with_schedule_and_major_cap"
    assert entries["hospital-misc-reimbursement-benefit"][
        "calculation_basis"
    ] == "reimbursement_with_greater_of_daily_cap"
    assert entries["hospital-deductible-reference"]["amount_role"] == "reference"
    schedules[product_id] = schedule


base_product_id = "209313MZ1A00221A11Z10000015"
valid_document, _ = source_document(base_product_id)
invalid_hash_document = copy.deepcopy(valid_document)
invalid_hash_document["source_document_sha256"] = "0" * 64
assert not is_strict_source(invalid_hash_document)
assert parse_policy(invalid_hash_document) is None

invalid_text_document = copy.deepcopy(valid_document)
invalid_text_document["text"] += "非條款文字"
assert parse_policy(invalid_text_document) is None

invalid_file_document = copy.deepcopy(valid_document)
invalid_file_document["file_name"] = "neighbor-product-A.pdf"
assert not is_strict_source(invalid_file_document)
assert parse_policy(invalid_file_document) is None

wrong_source = copy.deepcopy(schedules[base_product_id])
wrong_source["version_characteristics"]["source_text_sha256"] = "0" * 64
assert_invalid_schedule(wrong_source, "identity is invalid")

wrong_phase = copy.deepcopy(schedules["209313MZ1A00221A11Z10000017"])
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "daily-choice-removed"
)
assert_invalid_schedule(wrong_phase, "identity is invalid")

wrong_formula = copy.deepcopy(schedules[base_product_id])
for entry in wrong_formula["coverage_entries"]:
    if entry["id"] == "surgery-reimbursement-benefit":
        entry["rate_threshold_percent"] = 99
assert_invalid_schedule(wrong_formula, "exact entry contract is invalid")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
assert proposal_payload["proposal_count"] == 13
assert proposal_payload["proposed_count"] == 13
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"] for proposal in proposal_payload["proposals"]
} == PRODUCT_IDS

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phases": sorted(
            {item["version_characteristics"]["semantic_phase"] for item in schedules.values()}
        ),
    }
)

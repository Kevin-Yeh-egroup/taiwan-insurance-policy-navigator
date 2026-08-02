from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
)
from tii_china_group_hospital_medical_limit import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-026"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-026-china-group-hospital-medical-limit-v297.json"
)
PARSER_ID = "china-group-hospital-medical-limit-v1"


def source_document(product_id: str) -> dict:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "source_document_sha256": version["source_document_sha256"],
            "text": "",
        },
        source_path,
    )


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-026/china-group-hospital-medical-limit",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("formal validator accepted an invalid schedule")


schedules: dict[str, dict] = {}
for product_id in sorted(PRODUCT_IDS):
    expected = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / expected["file_name"]
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == expected[
        "source_document_sha256"
    ]
    document = source_document(product_id)
    assert document["source_text_extractor"] == "pymupdf"
    assert document["page_count"] == expected["page_count"]
    assert document["pages_parsed"] == expected["page_count"]
    assert hashlib.sha256(document["text"].encode("utf-8")).hexdigest() == (
        expected["source_text_sha256"]
    )

    schedule = parse_policy(document)
    assert schedule is not None, product_id
    assert parse_plan_table_with_parser(document) == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    revision = int(expected["revision"])
    version = schedule["version_characteristics"]
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule["selection_source"] == "terms"
    assert schedule["selection_label"] == "保單記載總限額"
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == expected[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == expected["source_text_sha256"]
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["daily_room_meal_limit_percent"] == 3
    assert version["hospitalization_day_limit_in_terms"] is False
    assert version["outpatient_surgery_covered"] is (revision >= 5)
    assert version["emergency_observation_covered"] is (revision >= 5)
    assert version["original_receipt_required"] is (revision == 0)
    assert version["beneficiary_identity_document_required"] is (
        revision >= 9
    )
    assert version["medical_opinion_review_available"] is (revision >= 11)
    assert version["nhi_reduction_percent"] is None
    assert version["death_benefit_available"] is False
    assert version["premium_waiver_available"] is False

    assert len(schedule["coverage_entries"]) == 1
    entry = schedule["coverage_entries"][0]
    assert entry["id"] == "hospital-medical-reimbursement-benefit"
    assert (
        entry["calculation_basis"]
        == "reimbursement_with_total_and_daily_room_cap"
    )
    assert entry["basis"] == "policy_recorded_limit"
    assert entry["rate_percent"] == 3
    assert entry["unit_key"] == "china_group_hospital_medical_total_limit"
    assert entry["expense_state_key"] == (
        "china_group_hospital_medical_actual_expense"
    )
    assert entry["quantity_state_key"] == "hospitalization_days"
    assert entry["policy_state_keys"] == [
        "china_group_hospital_room_meal_expense"
    ]
    if revision >= 5:
        assert entry["eligibility_state_key"] == (
            "china_group_hospital_medical_event_type"
        )
    else:
        assert "eligibility_state_key" not in entry
    schedules[product_id] = schedule


valid_document = source_document("205317M11A07200")
wrong_sha = copy.deepcopy(valid_document)
wrong_sha["source_document_sha256"] = "0" * 64
assert parse_policy(wrong_sha) is None

wrong_product = copy.deepcopy(valid_document)
wrong_product["product_id"] = "205351R11A54800"
assert parse_policy(wrong_product) is None

wrong_file = copy.deepcopy(valid_document)
wrong_file["file_name"] = "205317M11A072-F.pdf"
assert parse_policy(wrong_file) is None

altered_text = copy.deepcopy(valid_document)
altered_text["text"] = altered_text["text"].replace("百分之三", "百分之四", 1)
assert parse_policy(altered_text) is None

wrong_rate = copy.deepcopy(schedules["205317M11A07200"])
wrong_rate["coverage_entries"][0]["rate_percent"] = 4
assert_invalid_schedule(
    wrong_rate,
    "coverage entry amount or calculable formula is invalid",
)

wrong_identity = copy.deepcopy(schedules["205317M11A07205"])
wrong_identity["version_characteristics"]["outpatient_surgery_covered"] = False
assert_invalid_schedule(wrong_identity, "identity is invalid")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v297"
assert proposal_payload["proposal_count"] == 13
assert proposal_payload["proposed_count"] == 13
assert proposal_payload["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal_payload["proposals"]
} == PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == VERSIONS[product_id][
        "source_document_sha256"
    ]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phase_count": len(
            {
                schedule["version_characteristics"]["semantic_phase"]
                for schedule in schedules.values()
            }
        ),
        "parser_id": PARSER_ID,
    }
)

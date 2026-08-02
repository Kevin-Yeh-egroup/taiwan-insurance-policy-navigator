from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_PRODUCT_IDS,
    NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_VERSIONS,
    complete_strict_source_document,
    nanshan_hospital_expense_benefit_rider_semantic_phase,
    parse_nanshan_hospital_expense_benefit_rider_policy_state,
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
    / "tii-life-032-nanshan-hospital-expense-benefit-rider-v275.json"
)
PARSER_ID = (
    "nanshan-hospital-expense-benefit-rider-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_VERSIONS[
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
            "negative/tii-life-032/nanshan-hospital-expense",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_PRODUCT_IDS
):
    source_version = (
        NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_VERSIONS[
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
        parse_nanshan_hospital_expense_benefit_rider_policy_state(
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
        nanshan_hospital_expense_benefit_rider_semantic_phase(
            revision
        )
    )
    assert version["required_policy_inputs"] == [
        "hospital_daily_amount",
        "hospitalization_days",
        "taiwan_inpatient_daily_event_status",
    ]
    assert version["disease_waiting_days"] == 30
    assert version["accident_waiting_period_exempt"] is True
    assert version["same_hospital_readmission_days"] == 14
    assert version["same_hospitalization_days_limit"] == 365
    assert version["family_member_coverage"] is (revision <= 1)
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 10
    )
    assert version["day_hospital_excluded"] is True
    assert version["night_only_hospitalization_excluded"] is (
        revision <= 9
    )
    assert version["reimbursement_benefit_present"] is False
    assert version["room_expense_benefit_present"] is False
    assert version["inpatient_medical_expense_benefit_present"] is (
        False
    )
    assert version["surgery_benefit_present"] is False
    assert version["outpatient_benefit_present"] is False
    assert version["receipt_required_for_payout"] is False
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    assert len(schedule["coverage_entries"]) == 1
    entry = schedule["coverage_entries"][0]
    assert entry["id"] == "hospital-daily-tiered-benefit"
    assert entry["calculation_basis"] == "tiered_or_stepped"
    assert entry["basis"] == "hospital_daily_amount"
    assert entry["quantity_state_key"] == "hospitalization_days"
    assert entry["quantity_cap"] == 365
    assert entry["eligibility_state_key"] == (
        "taiwan_inpatient_daily_event_status"
    )
    assert entry["ineligible_values"] == [
        "disease_within_waiting_period",
        "day_hospital_or_day_care",
    ]
    assert entry["uncertain_values"] == [
        "not_eligible_or_uncertain",
    ]
    assert entry["policy_state_keys"] == [
        "hospital_daily_amount",
        "hospitalization_days",
    ]
    assert [tier["multiplier"] for tier in entry["amount_tiers"]] == [
        1,
        1.25,
        1.5,
    ]
    schedules[product_id] = schedule


assert sum(
    version["source_text_extractor"] == "pymupdf"
    for version in (
        NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_VERSIONS.values()
    )
) == 3

wrong_phase = copy.deepcopy(schedules["206311R11A30302"])
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "wrong_phase"
)
assert_invalid_schedule(
    wrong_phase,
    "version contract is invalid",
)

wrong_extra_benefit = copy.deepcopy(schedules["206311R11A30310"])
wrong_extra_benefit["version_characteristics"][
    "reimbursement_benefit_present"
] = True
assert_invalid_schedule(
    wrong_extra_benefit,
    "version contract is invalid",
)

wrong_tier = copy.deepcopy(schedules["206311R11A30303"])
wrong_tier["coverage_entries"][0]["amount_tiers"][1][
    "multiplier"
] = 1.5
assert_invalid_schedule(
    wrong_tier,
    "exact entry contract is invalid",
)

wrong_cap = copy.deepcopy(schedules["206311R11A30309"])
wrong_cap["coverage_entries"][0]["quantity_cap"] = 366
assert_invalid_schedule(
    wrong_cap,
    "exact entry contract is invalid",
)

bad_document, _ = source_document("206311R11A30301")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_nanshan_hospital_expense_benefit_rider_policy_state(
        bad_document
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v275"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        NANSHAN_HOSPITAL_EXPENSE_BENEFIT_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "pymupdf_product_count": 3,
        "semantic_phase_count": len(
            {
                schedule["version_characteristics"][
                    "semantic_phase"
                ]
                for schedule in schedules.values()
            }
        ),
    }
)

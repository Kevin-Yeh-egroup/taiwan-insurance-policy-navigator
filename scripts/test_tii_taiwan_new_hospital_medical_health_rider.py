from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_PLAN_LIMITS,
    TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS,
    TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_new_hospital_medical_health_rider_plan,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-008"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-008-taiwan-new-hospital-medical-health-rider-v268.json"
)
PARSER_ID = "taiwan-new-hospital-medical-health-rider-plan-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
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
            "negative/tii-life-008/taiwan-new-hospital-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Taiwan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
):
    source_version = (
        TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
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
    schedule = parse_taiwan_new_hospital_medical_health_rider_plan(
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
    assert version["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    assert version["family_fingerprint"] == (
        "bd210e300e812df2cd9ff9ab"
    )
    assert version["required_policy_inputs"] == ["plan_name"]
    assert version["disease_waiting_days"] == 30
    assert version["accident_waiting_period_exempt"] is True
    assert version["same_hospital_readmission_days"] == 14
    assert version["same_hospitalization_day_limit"] is None
    assert version["non_health_insurance_payment_rate_percent"] == 65
    assert version["surgery_rate_min_percent"] == 1
    assert version["surgery_rate_max_percent"] == 400
    assert version["designated_physician_expense_included"] is (
        revision <= 5
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 8
    )
    assert version["day_hospital_excluded"] is (revision >= 9)
    assert version["mental_day_stay_excluded"] is (revision >= 9)
    assert version["outpatient_surgery_benefit_present"] is False
    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert schedule.get("coverage_entries") in (None, [])
    assert [
        option["value"] for option in schedule["plan_options"]
    ] == list(TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_PLAN_LIMITS)
    for option in schedule["plan_options"]:
        entries = {
            entry["id"]: entry
            for entry in option["coverage_entries"]
        }
        assert set(entries) == {
            "daily-room-expense-reimbursement",
            "inpatient-surgery-expense-reimbursement",
            "inpatient-medical-expense-reimbursement",
            "specific-surgery-discharge-recuperation-benefit",
            "hospital-daily-cash-alternative",
        }
        for entry in entries.values():
            assert entry["eligibility_state_key"] == (
                "taiwan_inpatient_daily_event_status"
            )
            assert entry["ineligible_values"][0] == (
                "disease_within_waiting_period"
            )
            assert entry["uncertain_values"][0] == (
                "not_eligible_or_uncertain"
            )
            if revision >= 9:
                assert "day_hospital_or_day_care" in (
                    entry["ineligible_values"]
                )
            else:
                assert "day_hospital_or_day_care" in (
                    entry["uncertain_values"]
                )
        specific = entries[
            "specific-surgery-discharge-recuperation-benefit"
        ]
        assert "rate_percent" not in specific
        assert "rate_condition_state_key" not in specific
        assert specific["quantity_state_key"] == (
            "specific_surgery_count"
        )
    schedules[product_id] = schedule


assert len(schedules) == 14
assert sum(
    version["source_text_extractor"] == "windows_ocr"
    for version in TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS.values()
) == 1
assert len(
    {
        schedule["version_characteristics"]["semantic_phase"]
        for schedule in schedules.values()
    }
) == 4

wrong_phase = copy.deepcopy(schedules["202311R11AG9A08"])
wrong_phase["version_characteristics"][
    "post_expiry_readmission_excluded"
] = False
assert_invalid_schedule(
    wrong_phase,
    "identity or formula is invalid",
)

wrong_plan = copy.deepcopy(schedules["202311R11AG9A01"])
wrong_plan["plan_options"][0]["coverage_entries"][0]["amount"] = 501
assert_invalid_schedule(
    wrong_plan,
    "exact entry contract is invalid",
)

wrong_eligibility = copy.deepcopy(schedules["202311R11AG9A09"])
wrong_eligibility["plan_options"][0]["coverage_entries"][0][
    "uncertain_values"
].append("day_hospital_or_day_care")
assert_invalid_schedule(
    wrong_eligibility,
    "eligibility contract is invalid",
)

bad_document, _ = source_document("202311R11AG9A01")
bad_document["source_document_sha256"] = "0" * 64
assert (
    parse_taiwan_new_hospital_medical_health_rider_plan(
        bad_document
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v268"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "plan_count": len(
            TAIWAN_NEW_HOSPITAL_MEDICAL_HEALTH_RIDER_PLAN_LIMITS
        ),
        "semantic_phase_count": 4,
    }
)

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_PLAN_LIMITS,
    TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS,
    TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_wenxin_hospital_medical_health_rider_plan,
    taiwan_wenxin_hospital_medical_health_rider_semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-008"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-008-taiwan-wenxin-hospital-medical-health-rider-v270.json"
)
PARSER_ID = "taiwan-wenxin-hospital-medical-health-rider-plan-v1"
ENTRY_IDS = [
    "daily-room-expense-reimbursement",
    "inpatient-medical-expense-reimbursement-standard",
    "inpatient-medical-expense-reimbursement-icu",
    "major-surgery-nursing-benefit",
    "outpatient-surgery-expense-reimbursement",
    "outpatient-surgery-fixed-benefit",
    "inpatient-daily-cash-benefit",
]


def source_document(product_id: str) -> tuple[dict, Path]:
    version = (
        TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
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


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-008/taiwan-wenxin",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Wenxin schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
):
    source_version = (
        TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
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
    schedule = parse_taiwan_wenxin_hospital_medical_health_rider_plan(
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
        taiwan_wenxin_hospital_medical_health_rider_semantic_phase(
            revision
        )
    )
    assert version["family_fingerprint"] == (
        "4cc62b886b3d1c16e3c833d5"
    )
    assert version["plan_options"] == ["M6", "M12", "M18"]
    assert version["no_claim_lookback_policy_years"] == 3
    assert version["no_claim_bonus_rate_percent"] == 30
    assert version["icu_inpatient_medical_limit_multiplier"] == 2
    assert version["outpatient_surgery_annual_count_limit"] == 6
    assert version["newborn_screening_exception"] is (
        revision >= 3
    )
    assert version["day_hospital_excluded"] is (revision >= 5)
    assert version["benefit_article_start"] == (
        9 if revision >= 13 else 8
    )
    assert version["original_receipt_required"] is (
        revision >= 13
    )
    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert schedule.get("coverage_entries") in (None, [])
    assert [
        option["value"] for option in schedule["plan_options"]
    ] == ["M6", "M12", "M18"]
    for option in schedule["plan_options"]:
        assert [
            entry["id"] for entry in option["coverage_entries"]
        ] == ENTRY_IDS
    schedules[product_id] = schedule


m12_entries = {
    entry["id"]: entry
    for entry in schedules["202311R11ABB100"]["plan_options"][1][
        "coverage_entries"
    ]
}
assert m12_entries["daily-room-expense-reimbursement"]["amount"] == (
    TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_PLAN_LIMITS[
        "M12"
    ]["room"]
)
assert m12_entries[
    "inpatient-medical-expense-reimbursement-icu"
]["limit_rate_percent"] == 200
assert m12_entries["inpatient-daily-cash-benefit"][
    "amount_tiers"
] == [
    {
        "label": "第 1 至 30 日",
        "min_quantity": 1,
        "max_quantity": 30,
        "amount": 1_500,
    },
    {
        "label": "第 31 至 365 日",
        "min_quantity": 31,
        "max_quantity": 365,
        "amount": 2_000,
    },
]

wrong_amount = copy.deepcopy(schedules["202311R11ABB100"])
wrong_amount["plan_options"][0]["coverage_entries"][0][
    "amount"
] = 601
assert_invalid_schedule(
    wrong_amount,
    "exact entry contract is invalid",
)

wrong_source, _ = source_document("202311R11ABB100")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_taiwan_wenxin_hospital_medical_health_rider_plan(
        wrong_source
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v270"
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        TAIWAN_WENXIN_HOSPITAL_MEDICAL_HEALTH_RIDER_VERSIONS[
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

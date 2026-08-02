from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_NEW_WHOLE_LIFE_MEDICAL_PRODUCT_IDS,
    NANSHAN_NEW_WHOLE_LIFE_MEDICAL_VERSIONS,
    complete_strict_source_document,
    nanshan_new_whole_life_medical_semantic_phase,
    parse_nanshan_new_whole_life_medical_face_amount,
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
    / "tii-life-032-nanshan-new-whole-life-medical-v259.json"
)
PARSER_ID = "nanshan-new-whole-life-medical-face-amount-v1"


def source_document(product_id: str) -> dict:
    version = NANSHAN_NEW_WHOLE_LIFE_MEDICAL_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_DIR / product_id / version["file_name"]
    )
    return complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "source_document_sha256": version[
                "source_document_sha256"
            ],
            "text": "",
        },
        source_path,
    )


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-032/nanshan-new-whole-life-medical",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan schedule"
        )


assert len(NANSHAN_NEW_WHOLE_LIFE_MEDICAL_PRODUCT_IDS) == 15
schedules: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_NEW_WHOLE_LIFE_MEDICAL_PRODUCT_IDS
):
    version_source = NANSHAN_NEW_WHOLE_LIFE_MEDICAL_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_DIR / product_id / version_source["file_name"]
    )
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == version_source["source_document_sha256"]
    )
    document = source_document(product_id)
    assert document["source_text_extractor"] == "pypdf"
    assert document["page_count"] == version_source["page_count"]
    assert document["pages_parsed"] == version_source["page_count"]
    assert (
        hashlib.sha256(
            document["text"].encode("utf-8")
        ).hexdigest()
        == version_source["source_text_sha256"]
    )

    schedule = parse_nanshan_new_whole_life_medical_face_amount(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    revision = int(version_source["revision"])
    characteristics = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "單位日額"
    assert schedule["face_amount_label"] == "單位日額"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == BATCH_ID
    assert characteristics["family_fingerprint"] == (
        "c75b9f9e987af609dd5943ce"
    )
    assert characteristics["source_document_sha256"] == (
        version_source["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version_source["source_text_sha256"]
    )
    assert characteristics["semantic_phase"] == (
        nanshan_new_whole_life_medical_semantic_phase(
            revision
        )
    )
    assert characteristics["hospital_daily_tiers"] == [
        {"min_day": 1, "max_day": 30, "multiplier": 1},
        {"min_day": 31, "max_day": 90, "multiplier": 2},
        {"min_day": 91, "max_day": 365, "multiplier": 3},
    ]
    assert characteristics[
        "emergency_transport_benefit_present"
    ] is (revision <= 6)
    assert characteristics[
        "emergency_room_benefit_present"
    ] is (revision <= 6)
    assert characteristics[
        "legacy_cancer_and_critical_definitions"
    ] is (revision <= 8)
    assert characteristics["severe_critical_definition"] is (
        revision >= 9
    )
    assert characteristics["disability_term"] == (
        "失能" if revision >= 11 else "殘廢"
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert entries["hospital-daily-tiered-benefit"][
        "amount_tiers"
    ][1]["multiplier"] == 2
    assert entries["hospital-daily-tiered-benefit"][
        "amount_tiers"
    ][2]["multiplier"] == 3
    assert entries["icu-burn-center-daily-benefit"][
        "quantity_state_key"
    ] == "intensive_care_or_burn_unit_days"
    assert entries["inpatient-surgery-benefit"][
        "quantity_state_key"
    ] == "inpatient_surgery_count"
    assert entries["health-increment-benefit"][
        "rate_state_key"
    ] == "health_increment_rate_percent"
    assert entries["remaining-lifetime-benefit-cap"][
        "multiplier"
    ] == 3000
    assert entries["remaining-lifetime-benefit-cap"][
        "cumulative_paid_state_key"
    ] == "cumulative_medical_benefit_paid_amount"
    assert entries["maturity-benefit"]["rate_percent"] == 105
    assert entries["death-or-funeral-benefit"][
        "calculation_basis"
    ] == "death_or_funeral_percentage_of_policy_state_amount"
    assert (
        "emergency-medical-transport-benefit" in entries
    ) is (revision <= 6)
    assert ("emergency-room-benefit" in entries) is (
        revision <= 6
    )
    assert ("major-cancer-benefit" in entries) is (
        revision <= 8
    )
    assert ("mild-cancer-benefit" in entries) is (
        revision >= 9
    )
    assert ("minor-paid-premium-refund" in entries) is (
        revision >= 7
    )
    schedules[product_id] = schedule


wrong_source = source_document("206391M12B30200")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_nanshan_new_whole_life_medical_face_amount(
        wrong_source
    )
    is None
)
wrong_product = source_document("206391M12B30200")
wrong_product["product_id"] = "206391M12B39999"
assert (
    parse_nanshan_new_whole_life_medical_face_amount(
        wrong_product
    )
    is None
)

wrong_tier = copy.deepcopy(schedules["206391M12B30200"])
wrong_tier["coverage_entries"][1]["amount_tiers"][1][
    "multiplier"
] = 1.5
assert_invalid_schedule(
    wrong_tier,
    "hospital tiers are invalid",
)

wrong_phase = copy.deepcopy(
    schedules["206391MZ1B30123A11Z10000011"]
)
wrong_phase["version_characteristics"][
    "disability_term"
] = "殘廢"
assert_invalid_schedule(
    wrong_phase,
    "version formula is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v259"
)
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == NANSHAN_NEW_WHOLE_LIFE_MEDICAL_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        NANSHAN_NEW_WHOLE_LIFE_MEDICAL_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "ocr_product_count": 0,
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

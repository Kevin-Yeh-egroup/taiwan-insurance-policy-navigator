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
from tii_nanshan_new_group_medical_benefit import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    SURGERY_SCHEDULE_PERCENT_OPTIONS,
    VERSIONS,
    expected_entry_contracts,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-032"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-032-nanshan-new-group-medical-benefit-v298.json"
)
PARSER_ID = "nanshan-new-group-medical-benefit-v1"


def source_document(product_id: str) -> dict:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
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


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-032/nanshan-new-group-medical-benefit",
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
    assert document["source_text_extractor"] == "pypdf"
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
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == expected[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == expected[
        "source_text_sha256"
    ]
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["hospitalization_day_limit"] == 365
    assert version["icu_multiplier"] == 2
    assert version["icu_multiplier_day_limit"] == 7
    assert version["surgery_stay_multiplier"] == 1.5
    assert version["accident_emergency_sublimit"] == 5_000
    assert version["surgery_schedule_percent_options"] == list(
        SURGERY_SCHEDULE_PERCENT_OPTIONS
    )
    assert version[
        "surgery_schedule_100_percent_special_cap_percent"
    ] == 400
    assert version["beneficiary_identity_document_required"] is (
        revision >= 6
    )
    assert version["nhi_covered_amount_excluded"] is (revision >= 9)
    assert version["medical_opinion_review_available"] is (
        revision >= 10
    )
    assert version["original_receipt_required"] is False
    assert version["death_benefit_available"] is False
    assert version["premium_waiver_available"] is False

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == set(expected_entry_contracts())
    assert len(entries) == 11
    assert entries["icu-daily-room-reimbursement-limit"][
        "limit_rate_percent"
    ] == 200
    assert entries["surgery-stay-daily-room-reimbursement-limit"][
        "limit_rate_percent"
    ] == 150
    assert entries["accident-emergency-fixed-sublimit"]["amount"] == 5_000
    assert entries["surgery-schedule-limit"]["rate_min_percent"] == 3
    assert entries["surgery-schedule-limit"]["rate_max_percent"] == 400
    assert entries["accident-accessory-aggregate-limit"][
        "limit_rate_percent"
    ] == 1000
    schedules[product_id] = schedule


valid_document = source_document("206317M11A30200")
wrong_sha = copy.deepcopy(valid_document)
wrong_sha["source_document_sha256"] = "0" * 64
assert parse_policy(wrong_sha) is None

wrong_product = copy.deepcopy(valid_document)
wrong_product["product_id"] = "206317M11A07600"
assert parse_policy(wrong_product) is None

wrong_file = copy.deepcopy(valid_document)
wrong_file["file_name"] = "206317M11A30200-F.pdf"
assert parse_policy(wrong_file) is None

altered_text = copy.deepcopy(valid_document)
altered_text["text"] += "source mutation"
assert parse_policy(altered_text) is None

wrong_rate = copy.deepcopy(schedules["206317M11A30200"])
wrong_rate["coverage_entries"][1]["limit_rate_percent"] = 250
assert_invalid_schedule(wrong_rate, "exact entry contract is invalid")

wrong_identity = copy.deepcopy(schedules["206313M11A30306"])
wrong_identity["version_characteristics"][
    "beneficiary_identity_document_required"
] = False
assert_invalid_schedule(wrong_identity, "identity is invalid")

assert PROPOSAL_PATH.exists(), PROPOSAL_PATH
proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v298"
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

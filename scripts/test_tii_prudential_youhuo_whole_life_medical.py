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
    parse_plan_table_with_parser,
)
from tii_prudential_youhuo_whole_life_medical import (
    FAMILY_FINGERPRINT,
    PLAN_ROWS,
    PRODUCT_IDS,
    VERSIONS,
    normalize_text,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-014"
PARSER_ID = "prudential-youhuo-whole-life-medical-v1"
PROPOSAL_STEM = "tii-life-014-prudential-youhuo-whole-life-medical-v293"
PROPOSAL_PATH = (
    ROOT / "work" / "tii-benefit-proposals" / f"{PROPOSAL_STEM}.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / PROPOSAL_STEM
    / f"{PROPOSAL_STEM}-review-packet.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-014-prudential-youhuo-whole-life-medical.json"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = VERSIONS[product_id]
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
            "negative/tii-life-014/prudential-youhuo",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


schedules: dict[str, dict] = {}
for product_id in sorted(PRODUCT_IDS):
    source_version = VERSIONS[product_id]
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == (
        source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert document["page_count"] == source_version["page_count"]
    assert document["pages_parsed"] == source_version["page_count"]
    assert hashlib.sha256(
        normalize_text(document["text"]).encode("utf-8")
    ).hexdigest() == source_version["source_text_sha256"]

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
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source_version[
        "source_text_sha256"
    ]
    assert version["newborn_screening_waiting_exception"] is (
        revision >= 3
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 4
    )
    assert version["emergency_transport_benefit_available"] is (
        revision <= 5
    )
    assert version["major_disease_reinstatement_waiting_days"] == (
        0 if revision >= 9 else 90
    )
    assert version["same_stay_surgery_cap_multiplier"] == (
        60 if revision <= 7 else 98
    )
    assert version["surgery_schedule_rate_max_percent"] == (
        300 if revision <= 7 else 490
    )
    assert version["medical_review_wording"] is (revision >= 12)

    if revision <= 7:
        assert schedule["selection_type"] == "plan"
        assert [item["value"] for item in schedule["plan_options"]] == [
            row[0] for row in PLAN_ROWS
        ]
        for option, row in zip(schedule["plan_options"], PLAN_ROWS):
            entries = {
                item["id"]: item
                for item in option["coverage_entries"]
            }
            daily_amount = row[2]
            assert entries["hospital-daily-benefit"]["amount"] == daily_amount
            assert entries["intensive-care-additional-benefit"][
                "multiplier"
            ] == 2
            assert entries["inpatient-surgery-benefit"]["amount"] == (
                daily_amount * 20
            )
            assert entries["inpatient-surgery-aggregate-cap"][
                "amount"
            ] == daily_amount * 60
            assert entries["remaining-lifetime-medical-cap"]["amount"] == (
                daily_amount * 3_000
            )
            assert (
                "emergency-medical-transport-benefit" in entries
            ) is (revision <= 5)
    else:
        assert schedule["selection_type"] == "unit"
        assert schedule["selection_label"] == "保險計劃數"
        entries = {
            item["id"]: item for item in schedule["coverage_entries"]
        }
        assert entries["hospital-daily-benefit"]["amount"] == 100
        assert entries["hospital-daily-benefit"]["basis"] == "daily_per_unit"
        assert entries["inpatient-surgery-benefit"]["amount"] == 2_000
        assert entries["inpatient-surgery-benefit"][
            "maximum_multiplier"
        ] == 4.9
        assert entries["inpatient-surgery-aggregate-cap"]["amount"] == 9_800
        assert entries["remaining-lifetime-medical-cap"]["amount"] == 300_000
        assert "emergency-medical-transport-benefit" not in entries
    schedules[product_id] = schedule

assert len(schedules) == 13

document, _ = source_document("203311M11A00200")
for field, value in (
    ("batch_id", "tii-life-015"),
    ("document_type", "summary"),
    ("source_document_sha256", "0" * 64),
    ("file_name", "203311M11A00201-A.pdf"),
    ("product_id", "203311M11A00100"),
):
    invalid = copy.deepcopy(document)
    invalid[field] = value
    assert parse_policy(invalid) is None, field

wrong_text = copy.deepcopy(document)
wrong_text["text"] += "source mutation"
assert parse_policy(wrong_text) is None

wrong_old_amount = copy.deepcopy(schedules["203311M11A00200"])
wrong_old_amount["plan_options"][0]["coverage_entries"][0][
    "amount"
] += 1
assert_invalid_schedule(wrong_old_amount, "exact entry contract is invalid")

wrong_old_emergency = copy.deepcopy(schedules["203311M11A00200"])
wrong_old_emergency["plan_options"][0]["coverage_entries"] = [
    entry
    for entry in wrong_old_emergency["plan_options"][0]["coverage_entries"]
    if entry["id"] != "emergency-medical-transport-benefit"
]
assert_invalid_schedule(wrong_old_emergency, "exact entry set is invalid")

wrong_modern_rate = copy.deepcopy(
    schedules["203311MZ1A00123A11Z10000012"]
)
modern_entries = {
    item["id"]: item
    for item in wrong_modern_rate["coverage_entries"]
}
modern_entries["inpatient-surgery-benefit"]["maximum_multiplier"] = 3
assert_invalid_schedule(wrong_modern_rate, "exact entry contract is invalid")

wrong_phase = copy.deepcopy(
    schedules["203311MZ1A00123A11Z10000009"]
)
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "dhcl-plan-number-modern-surgery-table"
)
assert_invalid_schedule(wrong_phase, "identity or version formula is invalid")

source_matrix = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert source_matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert source_matrix["product_count"] == 13
assert source_matrix["status_counts"] == {"readable": 13}
assert source_matrix["duplicate_source_sha_groups"] == {}
assert {row["product_id"] for row in source_matrix["rows"]} == PRODUCT_IDS

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
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
    assert candidate["source_document_sha256"] == VERSIONS[product_id][
        "source_document_sha256"
    ]
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
            {
                schedule["version_characteristics"]["semantic_phase"]
                for schedule in schedules.values()
            }
        ),
        "ready_for_human_source_review": 13,
    }
)

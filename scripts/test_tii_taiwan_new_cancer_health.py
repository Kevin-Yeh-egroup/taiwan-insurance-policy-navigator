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
from tii_taiwan_new_cancer_health import (
    EVENT_STATE_KEY,
    EVENT_VALUES,
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    normalize_text,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-008"
PARSER_ID = "taiwan-new-cancer-health-unit-v1"
PROPOSAL_STEM = "tii-life-008-taiwan-new-cancer-health-v291"
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
    / "tii-life-008-taiwan-new-cancer-health.json"
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
            "negative/tii-life-008/taiwan-new-cancer-health",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


expected_entry_ids = {
    "cancer-hospital-daily",
    "cancer-home-recovery",
    "cancer-death",
    "waiting-period-premium-refund",
    "non-cancer-death-current-year-premium-refund",
}
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
    assert version["terms_revision"] == f"partial_change_{revision}"
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source_version[
        "source_text_sha256"
    ]
    assert version["maximum_units_per_insured"] == 2
    assert version["hospital_daily_amount_per_unit"] == 2_500
    assert version["hospital_daily_day_limit"] is None
    assert version["home_recovery_amount_per_unit"] == 15_000
    assert version["home_recovery_minimum_hospital_days"] == 6
    assert version["home_recovery_annual_claim_limit"] == 3
    assert version["cancer_death_amount_per_unit"] == 180_000
    assert version["cancer_reinstatement_waiting_days"] == (
        10 if 1 <= revision <= 7 else 0
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 3
    )
    assert version["medical_corporation_hospital_wording"] is (
        revision >= 4
    )
    assert version["inclusive_disability_wording"] is (revision >= 9)
    assert version["modern_cancer_definition"] is (revision >= 10)
    assert version["medical_review_wording"] is (revision >= 11)

    entries = {
        item["id"]: item for item in schedule["coverage_entries"]
    }
    assert set(entries) == expected_entry_ids
    assert entries["cancer-hospital-daily"]["amount"] == 2_500
    assert entries["cancer-hospital-daily"]["quantity_state_key"] == (
        "cancer_hospitalization_days"
    )
    assert "quantity_cap" not in entries["cancer-hospital-daily"]
    assert entries["cancer-home-recovery"]["amount"] == 15_000
    assert entries["cancer-home-recovery"]["minimum_multiplier"] == 6
    assert entries["cancer-home-recovery"]["quantity_cap"] == 3
    assert entries["cancer-death"]["amount"] == 180_000
    assert entries["waiting-period-premium-refund"]["amount"] is None
    assert entries["non-cancer-death-current-year-premium-refund"][
        "rate_percent"
    ] == 50
    for item in entries.values():
        assert item["exclusion_state_key"] == EVENT_STATE_KEY
        assert set(item["exclusion_values"]) < EVENT_VALUES
    schedules[product_id] = schedule

assert len(schedules) == 13

document, _ = source_document("202321M11A68100")
for field, value in (
    ("batch_id", "tii-life-009"),
    ("document_type", "summary"),
    ("source_document_sha256", "0" * 64),
    ("file_name", "202321M11A68101-A.pdf"),
    ("product_id", "202321M11A68101"),
):
    invalid = copy.deepcopy(document)
    invalid[field] = value
    assert parse_policy(invalid) is None, field

wrong_text = copy.deepcopy(document)
wrong_text["text"] += "source mutation"
assert parse_policy(wrong_text) is None

wrong_amount = copy.deepcopy(schedules["202321M11A68100"])
wrong_amount["coverage_entries"][0]["amount"] = 2_501
assert_invalid_schedule(wrong_amount, "exact entry contract is invalid")

wrong_phase = copy.deepcopy(
    schedules["202321MZ1A68121A11Z10000008"]
)
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "reinstatement-ten-day-waiting"
)
assert_invalid_schedule(wrong_phase, "identity or version formula is invalid")

wrong_refund = copy.deepcopy(schedules["202321M11A68100"])
wrong_refund["coverage_entries"][-1]["rate_percent"] = 60
assert_invalid_schedule(wrong_refund, "exact entry contract is invalid")

wrong_minimum = copy.deepcopy(schedules["202321M11A68100"])
wrong_minimum["coverage_entries"][1]["minimum_multiplier"] = 5
assert_invalid_schedule(wrong_minimum, "exact entry contract is invalid")

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

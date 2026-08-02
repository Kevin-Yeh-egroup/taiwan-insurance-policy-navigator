from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_global_health_rider_plan,
    parse_plan_table_with_parser,
)
from tii_global_health_rider import (
    GLOBAL_HEALTH_RIDER_PRODUCT_IDS,
    GLOBAL_HEALTH_RIDER_VERSIONS,
    PLAN_ROWS,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-164"
PARSER_ID = "global-health-rider-plan-v1"
PROPOSAL_PATH = ROOT / "work" / "tii-benefit-proposals" / "tii-life-164-global-health-rider-v288.json"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = GLOBAL_HEALTH_RIDER_VERSIONS[product_id]
    path = ROOT / "work" / "tii-documents" / BATCH_ID / product_id / version["file_name"]
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
        path,
    )
    return document, path


def assert_invalid(schedule: dict, expected: str) -> None:
    try:
        validate_plan_options(schedule, "negative/global-health-rider")
    except SystemExit as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted invalid Global health rider data")


schedules: dict[str, dict] = {}
for product_id in sorted(GLOBAL_HEALTH_RIDER_PRODUCT_IDS):
    version = GLOBAL_HEALTH_RIDER_VERSIONS[product_id]
    document, path = source_document(product_id)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == version["source_document_sha256"]
    assert document["source_text_extractor"] == version["source_text_extractor"]
    schedule = parse_global_health_rider_plan(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None and integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")
    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == version["source_document_sha256"]
    assert characteristics["source_text_sha256"] == version["source_text_sha256"]
    assert characteristics["newborn_screening_waiting_exception"] is (revision >= 6)
    assert characteristics["day_hospital_excluded"] is (revision >= 8)
    assert characteristics["disability_terminology"] == ("喪失工作能力" if revision >= 10 else "失能")
    assert [option["value"] for option in schedule["plan_options"]] == [row[0] for row in PLAN_ROWS]
    for option, row in zip(schedule["plan_options"], PLAN_ROWS):
        entries = {entry["id"]: entry for entry in option["coverage_entries"]}
        assert entries["hospital-daily-benefit"]["amount"] == row[2]
        assert entries["intensive-care-daily-benefit"]["amount"] == row[3]
        assert entries["surgery-fixed-benefit"]["amount"] == row[4]
        assert entries["major-surgery-additional-benefit"]["amount"] == row[5]
        assert entries["misc-medical-daily-benefit"]["amount"] == row[6]
        assert entries["surgery-aggregate-cap"]["amount"] == row[4] * 3
    schedules[product_id] = schedule

assert len(schedules) == 14
assert schedules["264391R11AHIR00"]["version_characteristics"]["semantic_phase"] == "original_same_insurance_accident_90_day_readmission"
assert schedules["264391R11AHIR02"]["version_characteristics"]["readmission_rule_days"] == 14
assert schedules["264391R11AHIR06"]["version_characteristics"]["newborn_screening_waiting_exception"] is True
assert schedules["264311R11AHIR08"]["version_characteristics"]["day_hospital_excluded"] is True

document, _ = source_document("264311R11AHIR08")
for field, value in (
    ("source_document_sha256", "0" * 64),
    ("file_name", "264311R11AMIR08-A.pdf"),
    ("product_id", "264311R11AMIR08"),
    ("batch_id", "tii-life-999"),
):
    mutated = copy.deepcopy(document)
    mutated[field] = value
    assert parse_global_health_rider_plan(mutated) is None
mutated = copy.deepcopy(document)
mutated["text"] += " source mutation"
assert parse_global_health_rider_plan(mutated) is None

wrong_amount = copy.deepcopy(schedules["264311R11AHIR08"])
wrong_amount["plan_options"][0]["coverage_entries"][0]["amount"] = 501
assert_invalid(wrong_amount, "exact entry contract is invalid")
wrong_phase = copy.deepcopy(schedules["264391R11AHIR05"])
wrong_phase["version_characteristics"]["newborn_screening_waiting_exception"] = True
assert_invalid(wrong_phase, "identity is invalid")

payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert payload["extractor_version"] == "tii-plan-benefits-v288"
assert payload["proposal_count"] == payload["proposed_count"] == 14
assert payload["manual_review_count"] == 0
assert {item["product_id"] for item in payload["proposals"]} == GLOBAL_HEALTH_RIDER_PRODUCT_IDS
for proposal in payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    assert proposal["candidates"][0]["parser_id"] == PARSER_ID

print({"status": "ok", "batch_id": BATCH_ID, "product_count": len(schedules), "semantic_phase_count": 6})

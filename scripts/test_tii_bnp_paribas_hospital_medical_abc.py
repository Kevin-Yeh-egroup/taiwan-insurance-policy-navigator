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
from tii_bnp_paribas_hospital_medical_abc import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-170"
PARSER_ID = "bnp-paribas-hospital-medical-abc-policy-state-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-170-bnp-paribas-hospital-medical-abc-v289.json"
)
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-170-bnp-paribas-hospital-medical-abc.json"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = VERSIONS[product_id]
    path = (
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
            "file_name": path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": hashlib.sha256(
                path.read_bytes()
            ).hexdigest(),
        },
        path,
    )
    return document, path


def assert_invalid(schedule: dict, expected: str) -> None:
    try:
        validate_plan_options(schedule, "negative/bnp-hospital-abc")
    except SystemExit as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted invalid ABC schedule")


assert EXTRACTOR_VERSION == "tii-plan-benefits-v289"
matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert matrix["status_counts"] == {"readable": 14}
assert {row["product_id"] for row in matrix["rows"]} == PRODUCT_IDS

schedules: dict[str, dict] = {}
for product_id in sorted(PRODUCT_IDS):
    expected_source = VERSIONS[product_id]
    revision = int(expected_source["revision"])
    document, path = source_document(product_id)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        expected_source["source_document_sha256"]
    )
    assert document["source_text_extractor"] == "pypdf"
    schedule = parse_policy(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None and integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == (
        expected_source["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        expected_source["source_text_sha256"]
    )
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["benefit_article"] == (5 if revision == 13 else 4)
    assert version["newborn_screening_waiting_exception"] is (
        revision >= 5
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 6
    )
    assert version["day_hospital_excluded"] is (revision >= 7)
    assert version["preacceptance_liability_rule_added"] is (
        revision == 13
    )
    assert [option["value"] for option in schedule["plan_options"]] == [
        "A",
        "B",
        "C",
    ]
    assert [
        len(option["coverage_entries"])
        for option in schedule["plan_options"]
    ] == [2, 4, 8]
    c_entries = {
        entry["id"]: entry
        for entry in schedule["plan_options"][2]["coverage_entries"]
    }
    assert c_entries["inpatient-surgery-medical-benefit"]["multiplier"] == 3
    assert c_entries[
        "inpatient-treatment-procedure-medical-benefit"
    ]["multiplier"] == 3
    assert c_entries["post-discharge-convalescence-benefit"][
        "rate_percent"
    ] == 50
    assert c_entries["pre-post-hospital-outpatient-benefit"][
        "rate_percent"
    ] == 25
    schedules[product_id] = schedule

assert len(schedules) == 14

document, _ = source_document("267391M11A00207")
for field, value in (
    ("source_document_sha256", "0" * 64),
    ("file_name", "267391M11A00207-F.pdf"),
    ("product_id", "267317R11A00207"),
    ("batch_id", "tii-life-999"),
):
    mutated = copy.deepcopy(document)
    mutated[field] = value
    assert parse_policy(mutated) is None
mutated = copy.deepcopy(document)
mutated["text"] += " source mutation"
assert parse_policy(mutated) is None

wrong_plan = copy.deepcopy(schedules["267391M11A00200"])
wrong_plan["plan_options"][1]["coverage_entries"][3]["multiplier"] = 3
assert_invalid(wrong_plan, "exact entry contract is invalid")
wrong_source = copy.deepcopy(schedules["267391M11A00200"])
wrong_source["version_characteristics"]["source_document_sha256"] = "0" * 64
assert_invalid(wrong_source, "identity or version formula is invalid")
wrong_family = copy.deepcopy(schedules["267391M11A00200"])
wrong_family["version_characteristics"]["product_family"] = (
    "bnp-paribas-group-hospital-medical-rider-type-b"
)
assert_invalid(wrong_family, "identity or version formula is invalid")

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == EXTRACTOR_VERSION
assert proposal["proposal_count"] == proposal["proposed_count"] == 14
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == PRODUCT_IDS
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["schedule"] == schedules[item["product_id"]]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "plan_entry_counts": [2, 4, 8],
    }
)

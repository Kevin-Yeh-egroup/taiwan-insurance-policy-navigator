from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_PRODUCT_IDS,
    CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_VERSIONS,
    cathay_group_quanyi_hospital_medical_limit_semantic_phase,
    complete_strict_source_document,
    parse_cathay_group_quanyi_hospital_medical_limit_plan,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-020"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-020-cathay-group-quanyi-hospital-medical-limit-health-rider-v272.json"
)
PARSER_ID = (
    "cathay-group-quanyi-hospital-medical-limit-health-rider-plan-v1"
)
ENTRY_IDS = [
    "daily-room-expense-benefit",
    "inpatient-medical-expense-benefit",
]


def source_document(product_id: str) -> tuple[dict, Path]:
    version = CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_VERSIONS[
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


schedules: dict[str, dict] = {}
for product_id in sorted(
    CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_PRODUCT_IDS
):
    source_version = (
        CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_VERSIONS[
            product_id
        ]
    )
    document, source_path = source_document(product_id)
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == (
        source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    schedule = parse_cathay_group_quanyi_hospital_medical_limit_plan(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    revision = int(source_version["revision"])
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["semantic_phase"] == (
        cathay_group_quanyi_hospital_medical_limit_semantic_phase(
            revision
        )
    )
    assert version["family_fingerprint"] == (
        "f0c258d6ac8d4a1738a86682"
    )
    assert version["newborn_screening_exception_count"] == (
        0 if revision < 4 else 11 if revision < 8 else 21
    )
    assert version["designated_physician_expense_included"] is (
        revision <= 2
    )
    assert version["day_hospital_excluded"] is (revision >= 6)
    assert schedule["selection_type"] == "plan"
    assert schedule.get("coverage_entries") in (None, [])
    assert [
        option["value"] for option in schedule["plan_options"]
    ] == ["A", "B"]
    for option in schedule["plan_options"]:
        assert [
            entry["id"] for entry in option["coverage_entries"]
        ] == ENTRY_IDS
        assert not any(
            "手術" in entry["name"] or "門診" in entry["name"]
            for entry in option["coverage_entries"]
        )
    schedules[product_id] = schedule


revision0 = schedules["204317R11AWAA00"]
wrong_schedule = copy.deepcopy(revision0)
wrong_schedule["plan_options"][0]["coverage_entries"][0][
    "rate_percent"
] = 70
try:
    validate_plan_options(
        wrong_schedule,
        "negative/tii-life-020/cathay-quanyi",
    )
except SystemExit as error:
    assert "exact entry contract is invalid" in str(error), str(error)
else:
    raise AssertionError("formal validator accepted an altered rate")

wrong_source, _ = source_document("204317R11AWAA00")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_cathay_group_quanyi_hospital_medical_limit_plan(
        wrong_source
    )
    is None
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v272"
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        CATHAY_GROUP_QUANYI_HOSPITAL_MEDICAL_LIMIT_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "parser_id": PARSER_ID,
    }
)

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS,
    MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_VERSIONS,
    complete_strict_source_document,
    parse_mercantile_evergreen_hospital_medical_rider_face_amount,
    parse_mercantile_new_hospital_medical_rider_plan,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-062"
FAMILY_FINGERPRINT = "8bc99ce40a87d65117a5a397"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-062-mercantile-evergreen-hospital-medical-rider.json"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-062-mercantile-evergreen-hospital-medical-rider-v278.json"
)
PARSER_ID = (
    "mercantile-evergreen-hospital-medical-rider-face-amount-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
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
            "negative/tii-life-062/mercantile-evergreen",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid evergreen schedule"
        )


matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert matrix["product_count"] == 14
assert matrix["status_counts"] == {"readable": 14}
assert {
    row["product_id"] for row in matrix["rows"]
} == MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS

schedules: dict[str, dict] = {}
for product_id in sorted(
    MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS
):
    expected = (
        MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
            product_id
        ]
    )
    revision = int(expected["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == expected["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        expected["source_text_extractor"]
    )
    schedule = (
        parse_mercantile_evergreen_hospital_medical_rider_face_amount(
            document
        )
    )
    assert schedule is not None, product_id
    assert parse_mercantile_new_hospital_medical_rider_plan(
        document
    ) is None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == (
        expected["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        expected["source_text_sha256"]
    )
    assert version["source_page_count"] == expected["page_count"]
    assert version["same_hospital_readmission_days"] == (
        90 if revision <= 1 else 14
    )
    assert version["same_hospital_required"] is (revision >= 2)
    assert version["annual_benefit_caps"] is (revision >= 2)
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 8
    )
    assert version["day_hospital_excluded"] is (revision >= 9)

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "hospital-daily-benefit",
        "intensive-care-additional-benefit",
        "surgery-benefit",
        "discharge-recuperation-benefit",
    }
    assert entries["hospital-daily-benefit"]["multiplier"] == 1
    assert entries["hospital-daily-benefit"]["quantity_cap"] == 365
    assert entries["intensive-care-additional-benefit"][
        "amount_tiers"
    ] == [
        {
            "label": "第 1 至 30 日",
            "multiplier": 0.5,
            "min_quantity": 1,
            "max_quantity": 30,
        },
        {
            "label": "第 31 至 60 日",
            "multiplier": 1,
            "min_quantity": 31,
            "max_quantity": 60,
        },
    ]
    assert entries["surgery-benefit"]["multiplier_state_key"] == (
        "surgery_benefit_multiplier_decimal"
    )
    assert entries["discharge-recuperation-benefit"][
        "quantity_cap"
    ] == 120
    schedules[product_id] = schedule

assert (
    MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        "211311RZ1A00721A11Z10000010"
    ]["source_document_sha256"]
    == MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
        "211311RZ1A00721A11Z10000011"
    ]["source_document_sha256"]
)
assert (
    schedules["211311RZ1A00721A11Z10000010"][
        "version_characteristics"
    ]["source_product_id"]
    != schedules["211311RZ1A00721A11Z10000011"][
        "version_characteristics"
    ]["source_product_id"]
)

wrong_fingerprint = copy.deepcopy(schedules["211311R11A00709"])
wrong_fingerprint["version_characteristics"]["family_fingerprint"] = (
    "wrong-family"
)
assert_invalid_schedule(wrong_fingerprint, "identity or input mode")

wrong_icu_tier = copy.deepcopy(schedules["211311R11A00708"])
wrong_icu_tier["coverage_entries"][1]["amount_tiers"][0][
    "multiplier"
] = 1
assert_invalid_schedule(wrong_icu_tier, "exact entry contract")

wrong_source, source_path = source_document("211311R11A00709")
wrong_source["source_document_sha256"] = "0" * 64
assert (
    parse_mercantile_evergreen_hospital_medical_rider_face_amount(
        wrong_source
    )
    is None
)
wrong_file = copy.deepcopy(wrong_source)
wrong_file["source_document_sha256"] = hashlib.sha256(
    source_path.read_bytes()
).hexdigest()
wrong_file["file_name"] = "211311R11A00609-A.pdf"
assert (
    parse_mercantile_evergreen_hospital_medical_rider_face_amount(
        wrong_file
    )
    is None
)
neighbor_document, _ = source_document("211311R11A00709")
neighbor_document["product_id"] = "211311R11A00609"
neighbor_document["file_name"] = "211311R11A00609-A.pdf"
assert (
    parse_mercantile_evergreen_hospital_medical_rider_face_amount(
        neighbor_document
    )
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["extractor_version"] == "tii-plan-benefits-v278"
assert proposal["proposal_count"] == 14
assert proposal["proposed_count"] == 14
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_PRODUCT_IDS
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        MERCANTILE_EVERGREEN_HOSPITAL_MEDICAL_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_count": len(schedules),
        "source_gap_count": 0,
        "semantic_phase_count": 5,
    }
)

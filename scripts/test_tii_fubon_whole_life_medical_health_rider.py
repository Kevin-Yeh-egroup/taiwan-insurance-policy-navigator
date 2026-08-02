from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_PRODUCT_IDS,
    FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    fubon_whole_life_medical_health_rider_semantic_phase,
    is_fubon_whole_life_medical_health_rider_strict_source,
    parse_fubon_whole_life_medical_health_rider_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-050"
FAMILY_FINGERPRINT = "e8f04c6086eb051a16ce4cf5"
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-050-fubon-whole-life-medical-health-rider.json"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-whole-life-medical-health-rider-v277.json"
)
PARSER_ID = (
    "fubon-whole-life-medical-health-rider-face-amount-v1"
)


def source_document(product_id: str) -> dict:
    version = FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / str(version["file_name"])
    )
    document = {
        "batch_id": BATCH_ID,
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-050/fubon-whole-life-medical-rider",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Fubon rider schedule"
        )


matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == BATCH_ID
assert matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert matrix["product_count"] == 14
assert matrix["status_counts"] == {"readable": 14}
assert {
    row["product_id"] for row in matrix["rows"]
} == FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_PRODUCT_IDS

schedules: dict[str, dict] = {}
for product_id in sorted(
    FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
):
    version = FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_VERSIONS[
        product_id
    ]
    revision = int(version["revision"])
    document = source_document(product_id)
    schedule = (
        parse_fubon_whole_life_medical_health_rider_face_amount(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID, product_id
    assert integrated[1] == schedule, product_id
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["product_family"] == (
        "fubon-whole-life-medical-health-rider"
    )
    assert characteristics["family_fingerprint"] == (
        FAMILY_FINGERPRINT
    )
    assert characteristics["source_document_sha256"] == (
        version["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version["source_text_sha256"]
    )
    assert characteristics["source_text_extractor"] == (
        version["source_text_extractor"]
    )
    assert characteristics["source_page_count"] == (
        version["page_count"]
    )
    assert characteristics["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{revision}"
    )
    assert characteristics["semantic_phase"] == (
        fubon_whole_life_medical_health_rider_semantic_phase(
            revision
        )
    )
    assert characteristics["waiver_disability_grade_max"] == (
        3 if revision <= 2 else 6
    )
    assert characteristics[
        "minor_paid_premium_interest_refund"
    ] == (revision >= 10)
    assert characteristics["cancer_benefit_present"] is False
    assert (
        characteristics["critical_illness_benefit_present"]
        is False
    )
    assert characteristics["maturity_benefit_present"] is False

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert entries["remaining-lifetime-benefit-cap"][
        "multiplier"
    ] == 1000
    assert entries["hospital-daily-tiered-benefit"][
        "amount_tiers"
    ] == [
        {
            "label": "第 1 至 30 日",
            "multiplier": 1,
            "min_quantity": 1,
            "max_quantity": 30,
        },
        {
            "label": "第 31 至 365 日",
            "multiplier": 2,
            "min_quantity": 31,
            "max_quantity": 365,
        },
    ]
    assert entries["intensive-care-additional-benefit"][
        "multiplier"
    ] == 2
    assert entries["burn-center-additional-benefit"][
        "multiplier"
    ] == 3
    assert entries["discharge-recuperation-benefit"][
        "multiplier"
    ] == 0.5
    assert entries["pre-post-hospital-outpatient-benefit"][
        "multiplier"
    ] == 0.25
    assert entries["inpatient-surgery-benefit"][
        "multiplier"
    ] == 30
    assert entries["inpatient-surgery-benefit"][
        "rate_max_percent"
    ] == 500
    assert entries["death-or-funeral-benefit"][
        "multiplier"
    ] == 1000
    assert (
        "minor-death-premium-interest-refund" in entries
    ) == (revision >= 10)
    schedules[product_id] = schedule


assert (
    FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_VERSIONS[
        "209311R12B00107"
    ]["source_document_sha256"]
    == FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_VERSIONS[
        "209311R12B00108"
    ]["source_document_sha256"]
)
assert (
    schedules["209311R12B00107"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["209311R12B00108"]["version_characteristics"][
        "source_product_id"
    ]
)

wrong_boundary = copy.deepcopy(schedules["209311R12B00113"])
wrong_boundary["version_characteristics"][
    "family_fingerprint"
] = "24ec31ced739d3fa72b0935e"
assert_invalid_schedule(wrong_boundary, "version formula is invalid")

wrong_formula = copy.deepcopy(schedules["209311R12B00100"])
for entry in wrong_formula["coverage_entries"]:
    if entry["id"] == "hospital-daily-tiered-benefit":
        entry["amount_tiers"][1]["multiplier"] = 3
assert_invalid_schedule(
    wrong_formula,
    "exact entry contract is invalid",
)

base_document = source_document("209311R12B00100")
assert parse_fubon_whole_life_medical_health_rider_face_amount(
    {**base_document, "batch_id": "tii-life-049"}
) is None
assert parse_fubon_whole_life_medical_health_rider_face_amount(
    {**base_document, "file_name": "209311R12B001-F.doc"}
) is None
assert parse_fubon_whole_life_medical_health_rider_face_amount(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_fubon_whole_life_medical_health_rider_face_amount(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "終身醫療健康保險附約",
            "終身醫療健康保險",
            1,
        ),
    }
) is None
assert not is_fubon_whole_life_medical_health_rider_strict_source(
    {
        **base_document,
        "product_id": "209311M12B00100",
        "file_name": "209311M12B001-A.pdf",
    }
)
assert parse_fubon_whole_life_medical_health_rider_face_amount(
    {
        **base_document,
        "product_id": "209311M12B00100",
        "file_name": "209311M12B001-A.pdf",
    }
) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["extractor_version"] == "tii-plan-benefits-v277"
assert proposal["proposal_count"] == 14
assert proposal["proposed_count"] == 14
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_PRODUCT_IDS
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FUBON_WHOLE_LIFE_MEDICAL_HEALTH_RIDER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]


print(
    "TII Fubon whole-life medical health rider parser tests passed."
)

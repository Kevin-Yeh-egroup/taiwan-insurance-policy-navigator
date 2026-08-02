from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    FUBON_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS,
    complete_strict_source_document,
    parse_fubon_whole_life_medical_health_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-050"
PARSER_ID = "fubon-whole-life-medical-health-face-amount-v1"


def source_document(product_id: str) -> dict:
    version = FUBON_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / str(version["file_name"])
    )
    document = {
        "batch_id": "tii-life-050",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


for product_id, version in (
    FUBON_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS.items()
):
    document = source_document(product_id)
    schedule = parse_fubon_whole_life_medical_health_face_amount(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == (
        version["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version["source_text_sha256"]
    )
    assert characteristics["source_text_extractor"] == (
        version["source_text_extractor"]
    )
    assert characteristics["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{revision}"
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
        "rate_state_key"
    ] == "surgery_total_benefit_rate_percent"
    assert entries["inpatient-surgery-benefit"][
        "rate_max_percent"
    ] == 500
    assert entries["death-or-funeral-benefit"][
        "calculation_basis"
    ] == "death_or_funeral_multiplier_of_face_amount"
    assert entries["death-or-funeral-benefit"][
        "multiplier"
    ] == 1000
    assert (
        "minor-death-premium-interest-refund" in entries
    ) == (revision >= 10)


base_document = source_document("209311M12B00100")
assert parse_fubon_whole_life_medical_health_face_amount(
    {**base_document, "batch_id": "tii-life-049"}
) is None
assert parse_fubon_whole_life_medical_health_face_amount(
    {**base_document, "file_name": "209311M12B00100-F.pdf"}
) is None
assert parse_fubon_whole_life_medical_health_face_amount(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_fubon_whole_life_medical_health_face_amount(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "一百五十倍",
            "一百四十倍",
            1,
        ),
    }
) is None


print(
    "TII Fubon whole-life medical health parser tests passed."
)

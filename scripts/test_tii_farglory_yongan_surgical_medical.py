from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    FARGLORY_YONGAN_SURGICAL_MEDICAL_VERSIONS,
    complete_strict_source_document,
    farglory_yongan_semantic_phase,
    parse_farglory_yongan_surgical_medical_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-080"
PARSER_ID = "farglory-yongan-surgical-medical-face-amount-v1"


def source_document(product_id: str) -> dict:
    source_path = DOCUMENTS_ROOT / product_id / f"{product_id}-A.pdf"
    document = {
        "batch_id": "tii-life-080",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(FARGLORY_YONGAN_SURGICAL_MEDICAL_VERSIONS) == 17
for product_id, version in (
    FARGLORY_YONGAN_SURGICAL_MEDICAL_VERSIONS.items()
):
    document = source_document(product_id)
    assert document["source_text_extractor"] == "pymupdf"
    schedule = parse_farglory_yongan_surgical_medical_face_amount(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-080:{product_id}")

    revision = version["revision"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_batch_id"] == "tii-life-080"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "dense_text_sha256"
    ]
    assert characteristics["source_text_extractor"] == "pymupdf"
    assert characteristics["source_page_count"] == version["page_count"]
    assert characteristics["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{revision}"
    )
    assert characteristics["semantic_phase"] == (
        farglory_yongan_semantic_phase(revision)
    )
    assert characteristics["surgery_table_item_count"] == 1461
    assert characteristics["surgery_schedule_revision"] == (
        "original"
        if revision <= 8
        else "item_252_253_revision"
    )
    assert characteristics["outpatient_surgery_separate_benefit"] is False
    assert characteristics["cumulative_medical_cap_multiplier"] == 1200
    assert characteristics["premium_total_rate_percent"] == 110
    assert characteristics["newborn_screening_waiting_exception"] is (
        revision >= 11
    )
    assert characteristics[
        "newborn_screening_exception_requires_issue_age_zero"
    ] is (revision >= 11)
    assert characteristics["premium_waiver_benefit_present"] is False

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert entries["surgery-medical-benefit"][
        "multiplier_state_key"
    ] == "surgery_benefit_multiplier"
    assert entries["inpatient-surgery-recuperation-benefit"][
        "multiplier"
    ] == 3
    assert entries["inpatient-surgery-recuperation-benefit"][
        "aggregation_rule"
    ] == "conditional_additive"
    assert entries["inpatient-surgery-recuperation-benefit"][
        "exclusion_values"
    ] == ["outpatient"]
    assert entries["major-surgery-consolation-benefit"][
        "minimum_multiplier"
    ] == 60
    assert entries["major-surgery-consolation-benefit"][
        "rate_percent"
    ] == 50
    assert entries["remaining-lifetime-medical-benefit-cap"][
        "cumulative_paid_state_key"
    ] == "cumulative_medical_benefit_paid_amount"
    assert entries["maturity-benefit"][
        "cumulative_paid_state_key"
    ] == "cumulative_medical_benefit_paid_amount"
    assert entries["death-or-funeral-benefit"][
        "calculation_basis"
    ] == "death_or_funeral_percentage_of_policy_state_amount"
    assert (
        "minor-paid-premium-refund-or-death-benefit" in entries
    ) == (revision >= 1)
    assert len(entries) == (9 if revision >= 1 else 8)


base_document = source_document("216311M12B10300")
assert parse_farglory_yongan_surgical_medical_face_amount(
    {**base_document, "batch_id": "tii-life-081"}
) is None
assert parse_farglory_yongan_surgical_medical_face_amount(
    {**base_document, "file_name": "216311M12B10300-F.pdf"}
) is None
assert parse_farglory_yongan_surgical_medical_face_amount(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_farglory_yongan_surgical_medical_face_amount(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "一千二百倍",
            "一千一百倍",
            1,
        ),
    }
) is None


print("TII Farglory Yongan surgical medical parser tests passed.")

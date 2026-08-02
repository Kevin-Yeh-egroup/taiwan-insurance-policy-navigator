from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    FARGLORY_HEALTH_JIUJIU_SURGICAL_MEDICAL_VERSIONS,
    complete_strict_source_document,
    parse_farglory_health_jiujiu_surgical_medical_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-080"
PARSER_ID = (
    "farglory-health-jiujiu-surgical-medical-face-amount-v1"
)


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_ROOT / product_id / f"{product_id}-A.pdf"
    )
    document = {
        "batch_id": "tii-life-080",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(FARGLORY_HEALTH_JIUJIU_SURGICAL_MEDICAL_VERSIONS) == 19
for (
    product_id,
    version,
) in FARGLORY_HEALTH_JIUJIU_SURGICAL_MEDICAL_VERSIONS.items():
    document = source_document(product_id)
    schedule = (
        parse_farglory_health_jiujiu_surgical_medical_face_amount(
            document
        )
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule

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
    assert characteristics["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    assert characteristics["source_page_count"] == version[
        "page_count"
    ]
    assert characteristics["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{revision}"
    )
    assert characteristics["disability_term"] == (
        "完全失能" if revision >= 11 else "全殘廢"
    )
    assert characteristics["funeral_status_rule"] == (
        "guardianship_declaration"
        if revision >= 11
        else "mental_incapacity"
        if revision >= 2
        else "minor_under_14_or_mental_incapacity"
    )
    assert characteristics["surgery_table_item_count"] == 1464
    assert characteristics["surgery_table_multiplier_min"] == 1
    assert characteristics["surgery_table_multiplier_max"] == 100
    assert characteristics["cumulative_medical_cap_multiplier"] == 1200
    assert characteristics["premium_total_rate_percent"] == 110

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert entries["inpatient-surgery-benefit"][
        "multiplier_state_key"
    ] == "surgery_benefit_multiplier"
    assert entries["outpatient-surgery-benefit"][
        "multiplier_state_key"
    ] == "surgery_benefit_multiplier"
    assert entries["surgery-benefit-lifetime-cap"][
        "multiplier"
    ] == 1200
    assert entries["maturity-benefit"][
        "cumulative_paid_state_key"
    ] == "cumulative_surgery_benefit_paid_amount"
    assert entries["death-or-funeral-benefit"][
        "calculation_basis"
    ] == "death_or_funeral_percentage_of_policy_state_amount"
    assert (
        "minor-paid-premium-refund-or-death-benefit" in entries
    ) == (revision >= 2)
    assert len(entries) == (6 if revision >= 2 else 5)


base_document = source_document("216311R12B08900")
assert parse_farglory_health_jiujiu_surgical_medical_face_amount(
    {**base_document, "batch_id": "tii-life-081"}
) is None
assert parse_farglory_health_jiujiu_surgical_medical_face_amount(
    {**base_document, "file_name": "216311R12B08900-F.pdf"}
) is None
assert parse_farglory_health_jiujiu_surgical_medical_face_amount(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_farglory_health_jiujiu_surgical_medical_face_amount(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "一千二百倍",
            "一千一百倍",
            1,
        ),
    }
) is None


print(
    "TII Farglory Health Jiujiu surgical medical parser tests "
    "passed."
)

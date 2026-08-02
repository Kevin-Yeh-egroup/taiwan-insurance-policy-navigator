from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    FUBON_WHOLE_CARE_HEALTH_MINOR_REFUND_REVISIONS,
    FUBON_WHOLE_CARE_HEALTH_VERSIONS,
    complete_strict_source_document,
    parse_fubon_whole_care_health_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-050"
PARSER_ID = "fubon-whole-care-health-face-amount-v1"


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    document = {
        "batch_id": "tii-life-050",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


for product_id, version in FUBON_WHOLE_CARE_HEALTH_VERSIONS.items():
    document = source_document(product_id)
    schedule = parse_fubon_whole_care_health_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule

    revision = version["revision"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{revision}"
    )
    assert characteristics["disability_term"] == (
        "完全失能" if revision >= 8 else "全殘"
    )
    assert characteristics["specific_disease_definition_revision"] == (
        "standardized_severe_terms"
        if revision >= 8
        else "legacy_terms"
    )
    assert characteristics["minor_death_paid_premium_with_interest_refund"] == (
        revision in FUBON_WHOLE_CARE_HEALTH_MINOR_REFUND_REVISIONS
    )
    assert characteristics["minor_refund_interest_rate_percent"] == (
        1.75
        if revision >= 14
        else 2.0
        if revision in FUBON_WHOLE_CARE_HEALTH_MINOR_REFUND_REVISIONS
        else None
    )
    assert characteristics["death_benefit_formula"] == (
        "annual_insured_amount"
        if revision >= 16
        else "annual_premium_total_times_1_05_minus_paid_and_unpaid_specific_benefits"
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert entries[
        "specific-disease-total-disability-recurring-benefit"
    ]["rate_percent"] == 100
    assert entries[
        "specific-disease-total-disability-care-benefit"
    ]["rate_percent"] == 600
    assert entries[
        "death-or-funeral-net-premium-benefit"
    ]["rate_percent"] == 105
    assert entries["maturity-net-premium-benefit"]["rate_percent"] == 105
    assert (
        "minor-death-paid-premium-with-interest-refund" in entries
    ) == (
        revision in FUBON_WHOLE_CARE_HEALTH_MINOR_REFUND_REVISIONS
    )


base_document = source_document("209351M12B00700")
assert parse_fubon_whole_care_health_face_amount(
    {**base_document, "batch_id": "tii-life-049"}
) is None
assert parse_fubon_whole_care_health_face_amount(
    {**base_document, "file_name": "209351M12B00700-F.pdf"}
) is None
assert parse_fubon_whole_care_health_face_amount(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_fubon_whole_care_health_face_amount(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "當時保險金額的六倍給付",
            "當時保險金額的五倍給付",
            1,
        ),
    }
) is None


print("TII Fubon whole-care health parser tests passed.")

from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    FARGLORY_PREMIUM_WAIVER_RIDER_VERSIONS,
    complete_strict_source_document,
    farglory_premium_waiver_rider_file_name,
    parse_farglory_premium_waiver_rider_policy_state,
    parse_plan_table_with_parser,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-080"
PARSER_ID = "farglory-premium-waiver-rider-policy-state-v1"


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / farglory_premium_waiver_rider_file_name(product_id)
    )
    document = {
        "batch_id": "tii-life-080",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(FARGLORY_PREMIUM_WAIVER_RIDER_VERSIONS) == 19
for product_id, version in FARGLORY_PREMIUM_WAIVER_RIDER_VERSIONS.items():
    document = source_document(product_id)
    schedule = parse_farglory_premium_waiver_rider_policy_state(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_batch_id"] == "tii-life-080"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    assert characteristics["source_page_count"] == version["page_count"]
    assert characteristics["terms_revision"] == (
        "original" if revision == 0 else f"partial_change_{revision}"
    )
    assert characteristics["disease_waiting_days"] == 30
    assert characteristics["waiver_is_non_cash_effect"] is True
    assert characteristics["premium_waiver_disability_levels"] == (
        "1-3" if revision <= 1 else "1-6"
    )
    assert characteristics["disability_term"] == (
        "殘廢" if revision <= 13 else "失能"
    )

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    waiver = entries["future-premium-waiver"]
    assert waiver["calculation_basis"] == "waiver"
    assert waiver["amount_role"] == "premium_waiver"
    assert waiver["unit_key"] == "remaining_premium_amount"
    assert waiver["policy_state_keys"] == ["remaining_premium_amount"]
    assert waiver["result_kind"] == "non_cash_effect"
    assert waiver["amount_stage"] == "non_cash_estimate"

    if revision == 18:
        assert len(entries) == 3
        assert characteristics[
            "current_unexpired_premium_refund_available"
        ] is True
        assert characteristics[
            "overlapping_waiver_settlement_available"
        ] is True
        assert characteristics["required_policy_inputs"] == [
            "remaining_premium_amount",
            "unexpired_premium_refund_amount",
            "overlapping_waiver_settlement_amount",
        ]
        assert entries["current-unexpired-premium-refund"][
            "unit_key"
        ] == "unexpired_premium_refund_amount"
        assert entries["overlapping-waiver-cash-settlement"][
            "unit_key"
        ] == "overlapping_waiver_settlement_amount"
    else:
        assert len(entries) == 1
        assert characteristics[
            "current_unexpired_premium_refund_available"
        ] is False
        assert characteristics[
            "overlapping_waiver_settlement_available"
        ] is False
        assert characteristics["required_policy_inputs"] == [
            "remaining_premium_amount"
        ]

    if product_id == "216341R12B02607":
        assert document["source_text_extractor"] == "windows_ocr"
        assert (
            characteristics["source_text_quality"]
            == "verified_windows_ocr_exact_hash"
        )
        assert characteristics["ocr_evidence_path"].endswith(
            "216341R12B02607-ocr-evidence.json"
        )


base_document = source_document("216341R12B02600")
assert parse_farglory_premium_waiver_rider_policy_state(
    {**base_document, "batch_id": "tii-life-081"}
) is None
assert parse_farglory_premium_waiver_rider_policy_state(
    {**base_document, "file_name": "216341R12B02600-F.pdf"}
) is None
assert parse_farglory_premium_waiver_rider_policy_state(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_farglory_premium_waiver_rider_policy_state(
    {**base_document, "text": f"{base_document['text']}變更"}
) is None


print("TII Farglory premium waiver rider parser tests passed.")

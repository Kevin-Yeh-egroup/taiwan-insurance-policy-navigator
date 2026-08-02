from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    PRUDENTIAL_CONCERN_PREMIUM_WAIVER_96_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_prudential_anjia_premium_waiver_96_policy_state,
    parse_prudential_concern_premium_waiver_96_policy_state,
    prudential_concern_premium_waiver_96_semantic_phase,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-014"
PARSER_ID = "prudential-concern-premium-waiver-96-policy-state-v1"


def source_document(product_id: str) -> dict:
    version = PRUDENTIAL_CONCERN_PREMIUM_WAIVER_96_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_ROOT / product_id / version["file_name"]
    )
    document = {
        "batch_id": "tii-life-014",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(PRUDENTIAL_CONCERN_PREMIUM_WAIVER_96_VERSIONS) == 16
for product_id, version in (
    PRUDENTIAL_CONCERN_PREMIUM_WAIVER_96_VERSIONS.items()
):
    document = source_document(product_id)
    assert (
        document["source_text_extractor"]
        == version["source_text_extractor"]
    )
    schedule = (
        parse_prudential_concern_premium_waiver_96_policy_state(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    assert (
        parse_prudential_anjia_premium_waiver_96_policy_state(
            document
        )
        is None
    )
    validate_plan_options(schedule, f"tii-life-014:{product_id}")

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    disability_term = "殘廢" if revision <= 10 else "失能"
    cancer_term = "癌症" if revision <= 8 else "癌症(重度)"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == "tii-life-014"
    assert characteristics["terms_revision"] == (
        f"partial_change_{revision}"
    )
    assert characteristics["semantic_phase"] == (
        prudential_concern_premium_waiver_96_semantic_phase(
            revision
        )
    )
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_page_count"] == version[
        "page_count"
    ]
    assert characteristics["specific_disease_item_count"] == 18
    assert characteristics["cancer_term"] == cancer_term
    assert (
        characteristics["termination_definition_term"]
        == disability_term
    )
    assert (
        characteristics[
            "specific_disease_waiting_period_explicit"
        ]
        is (revision >= 9)
    )
    assert characteristics[
        "specific_disease_waiting_days_first_7"
    ] == (90 if revision >= 9 else None)
    assert characteristics[
        "specific_disease_waiting_days_last_11"
    ] == (30 if revision >= 9 else None)
    assert characteristics[
        "specific_disease_waiting_start_first_7"
    ] == (
        "effective_or_reinstatement_date"
        if revision == 9
        else "effective_date"
        if revision >= 10
        else None
    )
    assert characteristics[
        "specific_disease_waiting_start_last_11"
    ] == ("effective_date" if revision >= 9 else None)
    assert characteristics[
        "accidental_waiting_exception"
    ] is (revision >= 9)
    assert characteristics["death_is_waiver_trigger"] is False
    assert (
        characteristics[
            "disability_or_impairment_is_waiver_trigger"
        ]
        is False
    )
    assert (
        characteristics[
            "first_policy_year_cash_benefit_available"
        ]
        is False
    )
    assert characteristics["premium_waiver_event_triggers"] == [
        "specified_disease_18_items"
    ]
    assert characteristics["required_policy_inputs"] == [
        "remaining_premium_amount",
        "unexpired_premium_refund_amount",
    ]

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "specified-disease-future-premium-waiver",
        "current-unexpired-premium-refund",
    }
    waiver_entry = entries[
        "specified-disease-future-premium-waiver"
    ]
    assert waiver_entry["calculation_basis"] == "waiver"
    assert waiver_entry["amount_role"] == "premium_waiver"
    assert waiver_entry["aggregation_rule"] == "choose_one"
    assert waiver_entry["result_kind"] == "non_cash_effect"
    assert waiver_entry["policy_state_keys"] == [
        "remaining_premium_amount"
    ]
    refund_entry = entries["current-unexpired-premium-refund"]
    assert refund_entry["aggregation_rule"] == (
        "conditional_additive"
    )
    assert refund_entry["applies_to_entry_ids"] == [
        "specified-disease-future-premium-waiver"
    ]
    assert refund_entry["policy_state_keys"] == [
        "unexpired_premium_refund_amount"
    ]
    assert not any(
        token in entry_id
        for entry_id in entries
        for token in (
            "death",
            "disability",
            "impairment",
            "first-policy-year",
            "triple",
        )
    )


base_document = source_document("203341R11A00301")
assert (
    parse_prudential_concern_premium_waiver_96_policy_state(
        {**base_document, "batch_id": "tii-life-015"}
    )
    is None
)
assert (
    parse_prudential_concern_premium_waiver_96_policy_state(
        {**base_document, "file_name": "203341R11A00301-F.PDF"}
    )
    is None
)
assert (
    parse_prudential_concern_premium_waiver_96_policy_state(
        {**base_document, "source_document_sha256": "0" * 64}
    )
    is None
)
assert (
    parse_prudential_concern_premium_waiver_96_policy_state(
        {**base_document, "text": f"{base_document['text']}\nTAMPER"}
    )
    is None
)


print(
    "TII Prudential Concern premium waiver 96 parser tests passed."
)

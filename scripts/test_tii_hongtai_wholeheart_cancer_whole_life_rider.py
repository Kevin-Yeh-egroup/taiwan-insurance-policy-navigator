from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    HONGTAI_WHOLEHEART_CANCER_RIDER_VERSIONS,
    complete_strict_source_document,
    hongtai_wholeheart_cancer_semantic_phase,
    parse_hongtai_wholeheart_cancer_rider_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-086"
PARSER_ID = (
    "hongtai-wholeheart-cancer-whole-life-rider-face-amount-v1"
)


def source_document(product_id: str) -> dict:
    version = HONGTAI_WHOLEHEART_CANCER_RIDER_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_ROOT / product_id / version["file_name"]
    )
    document = {
        "batch_id": "tii-life-086",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert EXTRACTOR_VERSION == "tii-plan-benefits-v255"
assert len(HONGTAI_WHOLEHEART_CANCER_RIDER_VERSIONS) == 16

for product_id, version in (
    HONGTAI_WHOLEHEART_CANCER_RIDER_VERSIONS.items()
):
    document = source_document(product_id)
    assert document["source_text_extractor"] == "pypdf"
    schedule = parse_hongtai_wholeheart_cancer_rider_face_amount(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-086:{product_id}")

    revision = version["revision"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == "tii-life-086"
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_page_count"] == version[
        "page_count"
    ]
    assert characteristics["semantic_phase"] == (
        hongtai_wholeheart_cancer_semantic_phase(revision)
    )
    assert characteristics["reinstatement_waiting_days"] == (
        90 if revision <= 6 else 0
    )
    assert characteristics[
        "reinstatement_immediate_coverage"
    ] is (revision >= 7)
    assert characteristics["disability_term"] == (
        "殘廢" if revision <= 7 else "失能"
    )
    assert characteristics[
        "living_support_discount_rate_percent"
    ] == (
        2.25 if revision <= 5 else 2 if revision <= 11 else 1.75
    )
    assert characteristics[
        "living_support_anniversary_survival_wording"
    ] is (revision <= 2)
    assert characteristics["medical_opinion_review_clause"] is (
        revision >= 11
    )
    assert characteristics["early_cancer_term"] == (
        "低侵襲性癌症"
        if revision <= 8
        else "癌症（初期、輕度）"
    )
    assert characteristics["severe_cancer_term"] == (
        "侵襲性癌症"
        if revision <= 8
        else "癌症（重度）"
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "initial-early-cancer-benefit",
        "initial-severe-cancer-benefit",
        "cancer-living-support-anniversary-benefit",
        "discounted-cancer-living-support-balance",
        "future-premium-waiver",
        "current-unexpired-premium-refund",
    }
    assert entries["initial-early-cancer-benefit"][
        "rate_percent"
    ] == 5
    assert entries["initial-severe-cancer-benefit"][
        "amount_tiers"
    ] == [
        {
            "label": "第 1 保單年度",
            "multiplier": 0.10,
            "min_quantity": 1,
            "max_quantity": 1,
        },
        {
            "label": "第 2 保單年度",
            "multiplier": 0.20,
            "min_quantity": 2,
            "max_quantity": 2,
        },
        {
            "label": "第 3 保單年度起",
            "multiplier": 0.40,
            "min_quantity": 3,
            "max_quantity": None,
        },
    ]
    assert entries["cancer-living-support-anniversary-benefit"][
        "quantity_state_key"
    ] == "cancer_living_support_anniversary_count"
    assert entries["cancer-living-support-anniversary-benefit"][
        "quantity_cap"
    ] == 5
    assert entries["discounted-cancer-living-support-balance"][
        "policy_state_keys"
    ] == ["discounted_cancer_living_support_balance_amount"]
    assert entries["future-premium-waiver"]["result_kind"] == (
        "non_cash_effect"
    )


duplicate_a = HONGTAI_WHOLEHEART_CANCER_RIDER_VERSIONS[
    "217321R11A00403"
]
duplicate_b = HONGTAI_WHOLEHEART_CANCER_RIDER_VERSIONS[
    "217321R11A00404"
]
assert (
    duplicate_a["source_document_sha256"]
    == duplicate_b["source_document_sha256"]
)
assert "217321R11A00403" != "217321R11A00404"

base_document = source_document("217321R11A00400")
assert (
    parse_hongtai_wholeheart_cancer_rider_face_amount(
        {**base_document, "batch_id": "tii-life-087"}
    )
    is None
)
assert (
    parse_hongtai_wholeheart_cancer_rider_face_amount(
        {
            **base_document,
            "file_name": "217321R11A00400-F.pdf",
        }
    )
    is None
)
assert (
    parse_hongtai_wholeheart_cancer_rider_face_amount(
        {
            **base_document,
            "source_document_sha256": "0" * 64,
        }
    )
    is None
)
assert (
    parse_hongtai_wholeheart_cancer_rider_face_amount(
        {**base_document, "text": f"{base_document['text']}\nTAMPER"}
    )
    is None
)

print(
    "TII Hongtai Wholeheart cancer whole-life rider parser tests passed."
)

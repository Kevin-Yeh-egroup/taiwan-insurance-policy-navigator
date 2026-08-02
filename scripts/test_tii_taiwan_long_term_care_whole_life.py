#!/usr/bin/env python3
"""Verify exact-source Taiwan Life long-term-care whole-life formulas."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    EXTRACTOR_VERSION,
    TAIWAN_LIFE_LONG_TERM_CARE_WHOLE_LIFE_PRODUCT_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_long_term_care_whole_life_formula,
)
from validate_data import validate_plan_options  # noqa: E402


BATCH_ID = "tii-life-009"
PARSER_ID = "taiwan-long-term-care-whole-life-formula-v2"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-009-taiwan-long-term-care-whole-life-v215.json"
)
EXPECTED_SOURCE_SHA256 = {
    "202191MZ6G84423A11Z10000000":
        "65baeeaefec19e442b568d3deed8747d1100cd0c7a50df85fc8d7603f3eb875d",
    "202191MZ6G84423A11Z10000001":
        "9c2544aab5940ba926df80974f53479f8c8c41963343df8fa5d9ac16353076e8",
}


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_DIR / product_id / f"{product_id}-A.pdf"
    )
    return complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
        },
        source_path,
    )


schedules: dict[str, dict] = {}
for product_id, version in (
    TAIWAN_LIFE_LONG_TERM_CARE_WHOLE_LIFE_PRODUCT_VERSIONS.items()
):
    source_path = (
        DOCUMENTS_DIR / product_id / f"{product_id}-A.pdf"
    )
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == EXPECTED_SOURCE_SHA256[product_id]
    )
    document = source_document(product_id)
    assert document["page_count"] == 10
    assert document["pages_parsed"] == 10
    schedule = parse_taiwan_long_term_care_whole_life_formula(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == version["terms_revision"]
    assert characteristics["filing_number"] == version["filing_number"]
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["long_term_care_adl_impairments_required"] == 3
    assert characteristics["long_term_care_cdr_min"] == 2
    assert characteristics["long_term_care_persistence_months"] == 3

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert len(entries) == 7
    assert (
        entries["long-term-care-benefit"]["calculation_basis"]
        == "policy_year_tiered_premium_or_face_amount"
    )
    assert entries["long-term-care-benefit"]["rate_percent"] == 50
    assert entries["long-term-care-benefit"]["policy_year_cutoff"] == 3
    assert (
        entries["long-term-care-benefit"]["eligibility_rule"]["type"]
        == "long_term_care_state"
    )
    assert (
        entries["long-term-care-benefit"]["eligibility_rule"][
            "medical_confirmation_status_key"
        ]
        == "long_term_care_medical_confirmation_status"
    )
    assert (
        entries["long-term-care-benefit"]["eligibility_rule"][
            "previous_claim_status_key"
        ]
        == "long_term_care_previous_claim_status"
    )
    assert (
        entries["long-term-care-benefit"]["eligibility_rule"][
            "cognitive_diagnosis_status_key"
        ]
        == "cognitive_icd_diagnosis_status"
    )
    assert (
        entries["long-term-care-benefit"]["amount_stage"]
        == "gross_contract_benefit"
    )
    assert (
        entries["death-or-funeral-benefit"]["calculation_basis"]
        == "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset"
    )
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 106
    assert entries["death-or-funeral-benefit"]["event_key"] == "death"
    assert (
        entries["accidental-death-additional-benefit"]["calculation_basis"]
        == "death_or_funeral_face_amount"
    )
    assert (
        entries["accidental-death-additional-benefit"][
            "applies_to_entry_ids"
        ]
        == ["death-or-funeral-benefit"]
    )
    assert (
        entries["accidental-death-additional-benefit"][
            "conditional_event_key"
        ]
        == "accidental-death"
    )
    assert (
        entries["total-disability-benefit"]["calculation_basis"]
        == "policy_year_greater_of_face_reserve_premium_with_offset"
    )
    assert entries["total-disability-benefit"]["event_key"] == "total-disability"
    assert (
        entries["maturity-benefit"]["calculation_basis"]
        == "maturity_greater_of_face_and_premium_with_offset"
    )
    assert entries["maturity-benefit"]["event_key"] == "maturity"
    assert entries["premium-waiver"]["calculation_basis"] == "waiver"
    assert entries["premium-waiver"]["amount_role"] == "premium_waiver"
    assert entries["premium-waiver"]["result_kind"] == "non_cash_effect"
    assert (
        entries["premium-waiver"]["amount_stage"]
        == "non_cash_estimate"
    )
    assert (
        entries["premium-waiver"]["eligibility_rule"][
            "payment_period_status_key"
        ]
        == "premium_payment_period_status"
    )
    assert (
        entries["installment-periodic-benefit"]["result_kind"]
        == "payment_method"
    )
    assert (
        entries["installment-periodic-benefit"]["calculation_basis"]
        == "policy_state_amount"
    )
    assert (
        entries["installment-periodic-benefit"]["policy_state_keys"]
        == ["installment_periodic_amount"]
    )
    assert (
        entries["installment-periodic-benefit"]["amount_stage"]
        == "insurer_quoted_amount"
    )
    assert any(
        "36,000" in condition
        for condition in entries["installment-periodic-benefit"][
            "conditions"
        ]
    )
    schedules[product_id] = schedule


reference = source_document(next(iter(EXPECTED_SOURCE_SHA256)))
assert (
    parse_taiwan_long_term_care_whole_life_formula(
        {**reference, "batch_id": "tii-life-008"}
    )
    is None
)
assert (
    parse_taiwan_long_term_care_whole_life_formula(
        {
            **reference,
            "file_name": (
                f"{reference['product_id']}-F.pdf"
            ),
        }
    )
    is None
)
assert (
    parse_taiwan_long_term_care_whole_life_formula(
        {**reference, "page_count": 9}
    )
    is None
)
corrupted = copy.deepcopy(reference)
corrupted["text"] = corrupted["text"].replace(
    "不分紅保險單",
    "分紅保險單",
)
assert (
    parse_taiwan_long_term_care_whole_life_formula(corrupted)
    is None
)

assert EXTRACTOR_VERSION == "tii-plan-benefits-v217"
assert set(schedules) == set(EXPECTED_SOURCE_SHA256)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["extractor_version"] == "tii-plan-benefits-v215"
assert proposal["proposal_count"] == 2
assert proposal["proposed_count"] == 2
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == set(EXPECTED_SOURCE_SHA256)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert (
        candidate["source_document_sha256"]
        == EXPECTED_SOURCE_SHA256[item["product_id"]]
    )
    assert candidate["schedule"] == schedules[item["product_id"]]

print(
    json.dumps(
        {
            "status": "ok",
            "batch_id": BATCH_ID,
            "extractor_version": EXTRACTOR_VERSION,
            "product_count": len(schedules),
            "coverage_entry_count": sum(
                len(schedule["coverage_entries"])
                for schedule in schedules.values()
            ),
        },
        ensure_ascii=False,
        indent=2,
    )
)

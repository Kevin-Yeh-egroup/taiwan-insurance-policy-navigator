from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    PRUDENTIAL_BAILE_VARIABLE_LIFE_PRODUCT_IDS,
    PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS,
    PRUDENTIAL_LEGACY_INVESTMENT_LIFE_PRODUCT_IDS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_prudential_baile_variable_life,
)
from build_tii_proposal_review_packet import semantic_schedule_sha256
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-017"
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-017-prudential-baile-variable-life-v213.json"
)
SOURCE_GAP_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-017-prudential-baile-variable-life-source-gaps.json"
)
OCR_EVIDENCE_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-017-prudential-baile-variable-life-"
        "203141M31A01001-ocr-evidence.json"
    )
)
SOURCE_PENDING_PRODUCT_ID = "203141M31A01001"


assert len(PRUDENTIAL_BAILE_VARIABLE_LIFE_PRODUCT_IDS) == 31
assert SOURCE_PENDING_PRODUCT_ID in PRUDENTIAL_BAILE_VARIABLE_LIFE_PRODUCT_IDS
assert (
    "203131MV1A00223A11Z90000030"
    not in PRUDENTIAL_LEGACY_INVESTMENT_LIFE_PRODUCT_IDS
)
assert (
    PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS["203141M31A01008"][
        "source_document_sha256"
    ]
    == PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS["203141M31A01009"][
        "source_document_sha256"
    ]
)


def exact_document(product_id: str) -> dict:
    version = PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS[product_id]
    file_name = f"{product_id}-A.pdf"
    source_path = DOCUMENTS_ROOT / BATCH_ID / product_id / file_name
    document = {
        "batch_id": BATCH_ID,
        "product_id": product_id,
        "file_name": file_name,
        "document_type": "policy_terms",
        "source_document_sha256": version["source_document_sha256"],
    }
    return complete_strict_source_document(document, source_path)


schedules = {}
for product_id in sorted(PRUDENTIAL_BAILE_VARIABLE_LIFE_PRODUCT_IDS):
    schedule = parse_prudential_baile_variable_life(
        exact_document(product_id)
    )
    assert schedule is not None, product_id
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")
    revision = schedule["version_characteristics"]["terms_revision_number"]
    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "disability-premium-waiver",
    }
    assert (
        entries["disability-premium-waiver"]["calculation_basis"]
        == "waiver"
    )
    assert entries["disability-premium-waiver"]["policy_state_keys"] == [
        "remaining_premium_amount"
    ]
    if revision <= 4:
        assert (
            schedule["version_characteristics"]["semantic_phase"]
            == "basic_premium_account_value"
        )
        assert (
            "benefit_valuation_basic_premium_policy_account_value"
            in entries["death-or-funeral-benefit"]["policy_state_keys"]
        )
        assert (
            "maturity_basic_premium_policy_account_value"
            in entries["maturity-benefit"]["policy_state_keys"]
        )
    elif revision <= 25:
        assert (
            schedule["version_characteristics"]["semantic_phase"]
            == "full_policy_account_value"
        )
        assert schedule["face_amount_label"] == "保險金額"
    else:
        assert (
            schedule["version_characteristics"]["semantic_phase"]
            == "basic_amount_plus_policy_account_value"
        )
        assert schedule["face_amount_label"] == "基本保額"
        assert (
            schedule["version_characteristics"]["maturity_benefit_name"]
            == "祝壽保險金"
        )
        assert (
            schedule["version_characteristics"]["premium_waiver_basis"]
            == "目標保險費"
        )
    common_offset_entries = [
        entries["maturity-benefit"],
        entries["death-or-funeral-benefit"],
        entries["total-disability-benefit"],
    ]
    for entry in common_offset_entries:
        assert "unpaid_policy_charge_amount" in entry["policy_state_keys"]
        assert (
            "policy_loan_and_interest_amount"
            in entry["policy_state_keys"]
        ) is (revision >= 8)
    for entry_id in (
        "death-or-funeral-benefit",
        "total-disability-benefit",
    ):
        assert (
            "post_event_insurance_cost_refund_amount"
            in entries[entry_id]["policy_state_keys"]
        )
        assert (
            "policy_values_converted_to_twd"
            not in entries[entry_id]["policy_state_keys"]
        )
        assert (
            entries[entry_id].get("minor_account_value_return_age") == 15
        ) is (revision >= 10)
    assert (
        schedule["version_characteristics"][
            "insurance_cost_refund_after_event"
        ]
        is True
    )
    assert (
        schedule["version_characteristics"][
            "post_event_insurance_cost_state_key"
        ]
        == "post_event_insurance_cost_refund_amount"
    )
    assert not any(
        "事故日後已收取之保險成本" in condition
        for condition in entries["maturity-benefit"]["conditions"]
    )
    assert any(
        "事故日後已收取之保險成本" in condition
        for condition in entries["death-or-funeral-benefit"]["conditions"]
    )
    assert (
        schedule["version_characteristics"][
            "policy_values_converted_to_twd_required"
        ]
        is False
    )
    schedules[product_id] = schedule

assert (
    schedules["203141M31A01001"]["version_characteristics"][
        "source_text_quality"
    ]
    == "verified_windows_ocr_exact_hash"
)
assert (
    schedules["203131MV1A00223A11Z90000029"]["version_characteristics"][
        "valuation_reference"
    ]
    == "next_asset_valuation_date_after_complete_claim_documents"
)
assert (
    schedules["203131MV1A00223A11Z90000030"]["version_characteristics"][
        "valuation_reference"
    ]
    == "document_received_date_with_appendix_4_asset_redemption_timing"
)
assert (
    schedules["203131MV1A00223A11Z90000029"]["version_characteristics"][
        "premium_waiver_disability_schedule_ref"
    ]
    == "附表四"
)
assert (
    schedules["203131MV1A00223A11Z90000030"]["version_characteristics"][
        "premium_waiver_disability_schedule_ref"
    ]
    == "附表五"
)
assert semantic_schedule_sha256(
    schedules["203131MV1A00223A11Z90000029"]
) != semantic_schedule_sha256(
    schedules["203131MV1A00223A11Z90000030"]
)


wrong_batch = exact_document("203141M31A01000")
wrong_batch["batch_id"] = "tii-life-018"
assert parse_prudential_baile_variable_life(wrong_batch) is None

wrong_hash = exact_document("203141M31A01000")
wrong_hash["source_document_sha256"] = "0" * 64
assert parse_prudential_baile_variable_life(wrong_hash) is None

tampered_text = copy.deepcopy(exact_document("203141M31A01026"))
tampered_text["text"] += "tampered"
assert parse_prudential_baile_variable_life(tampered_text) is None

wrong_file = exact_document("203131MV1A00223A11Z90000030")
wrong_file["file_name"] = "203131MV1A00223A11Z90000029-A.pdf"
assert parse_prudential_baile_variable_life(wrong_file) is None

swapped_source = copy.deepcopy(
    exact_document("203131MV1A00223A11Z90000029")
)
version_30_document = exact_document("203131MV1A00223A11Z90000030")
for field in (
    "source_document_sha256",
    "source_text_extractor",
    "page_count",
    "pages_parsed",
    "text",
):
    swapped_source[field] = version_30_document[field]
assert parse_prudential_baile_variable_life(swapped_source) is None

parser_id, version_30_schedule = parse_plan_table_with_parser(
    exact_document("203131MV1A00223A11Z90000030")
)
assert parser_id == "prudential-baile-variable-life-v1"
assert (
    version_30_schedule["version_characteristics"][
        "terms_revision_number"
    ]
    == 30
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["proposal_count"] == 31
assert proposal["proposed_count"] == 31
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == set(
    PRUDENTIAL_BAILE_VARIABLE_LIFE_PRODUCT_IDS
)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    assert candidate["parser_id"] == "prudential-baile-variable-life-v1"
    assert candidate["schedule"] == schedules[item["product_id"]]

source_gap = json.loads(SOURCE_GAP_PATH.read_text(encoding="utf-8"))
assert source_gap["gap_count"] == 0
assert source_gap["gaps"] == []
assert source_gap["resolved_gap_count"] == 1
assert source_gap["resolved_gaps"][0]["product_id"] == SOURCE_PENDING_PRODUCT_ID
assert (
    source_gap["resolved_gaps"][0]["resolution_code"]
    == "verified_windows_ocr_exact_hash"
)
ocr_evidence = json.loads(OCR_EVIDENCE_PATH.read_text(encoding="utf-8"))
assert ocr_evidence["source_document_sha256"] == (
    PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS[
        SOURCE_PENDING_PRODUCT_ID
    ]["source_document_sha256"]
)
assert ocr_evidence["normalized_text_sha256"] == (
    PRUDENTIAL_BAILE_VARIABLE_LIFE_VERSIONS[
        SOURCE_PENDING_PRODUCT_ID
    ]["normalized_text_sha256"]
)
assert ocr_evidence["ocr_language"] == "zh-Hant-TW"
assert ocr_evidence["page_numbers"] == list(range(1, 21))
assert all(
    len(page["png_sha256"]) == 64
    and len(page["ocr_text_sha256"]) == 64
    for page in ocr_evidence["pages"]
)

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "proposed_product_count": len(schedules),
        "source_pending_product_ids": [],
    }
)

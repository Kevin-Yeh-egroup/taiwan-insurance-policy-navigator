from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    FUBON_JIXIANG_VARIABLE_DEFERRED_ANNUITY_VERSIONS,
    complete_strict_source_document,
    parse_fubon_jixiang_variable_deferred_annuity,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-054"
PARSER_ID = "fubon-jixiang-variable-deferred-annuity-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-054-fubon-jixiang-variable-deferred-annuity-v232.json"
)
OCR_PRODUCT_IDS = {
    "209421M31A00301",
    "209421M31A00335",
    "209421M31A00337",
    "209421M31A00342",
}


def source_document(product_id: str) -> dict:
    version = FUBON_JIXIANG_VARIABLE_DEFERRED_ANNUITY_VERSIONS[product_id]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-054",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


assert EXTRACTOR_VERSION == "tii-plan-benefits-v232"
versions = FUBON_JIXIANG_VARIABLE_DEFERRED_ANNUITY_VERSIONS
assert len(versions) == 24

schedules = {}
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    document = source_document(product_id)
    assert document["page_count"] == source_version["page_count"]
    assert document["pages_parsed"] == source_version["page_count"]
    assert (
        document["source_text_extractor"]
        == source_version["source_text_extractor"]
    )

    schedule = parse_fubon_jixiang_variable_deferred_annuity(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-054/{product_id}")

    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert [item["value"] for item in schedule["plan_options"]] == [
        "年給付",
        "半年給付",
        "季給付",
        "月給付",
    ]
    expected_entries = {
        "periodic-annuity-or-low-amount-lump-sum",
        "excess-account-value-return-at-annuity-start",
        "account-value-return-before-annuity-start-death",
        "unpaid-annuity-balance-after-death",
    }
    for option in schedule["plan_options"]:
        assert {
            entry["id"] for entry in option["coverage_entries"]
        } == expected_entries

    characteristics = schedule["version_characteristics"]
    assert characteristics["source_batch_id"] == "tii-life-054"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["terms_revision"] == (
        f"partial-change-{source_version['revision']}"
    )
    assert characteristics["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == source_version[
        "normalized_text_sha256"
    ]
    assert characteristics["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert characteristics["source_page_count"] == source_version[
        "page_count"
    ]
    assert characteristics["guarantee_period_options_years"] == [
        10,
        15,
        20,
    ]
    assert characteristics["payment_frequency_options"] == [
        "annual",
        "semiannual",
        "quarterly",
        "monthly",
    ]
    assert characteristics["minimum_annual_annuity_amount"] == 5_000
    assert characteristics["maximum_annual_annuity_amount"] == 1_200_000
    assert characteristics["annuity_payment_quote_required"] is True
    schedules[product_id] = schedule

reference = source_document("209421M31A00327")
for corrupted in (
    {**reference, "batch_id": "tii-life-053"},
    {**reference, "file_name": "209421M31A00327-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 11},
    {**reference, "source_text_extractor": "pypdf"},
):
    assert parse_fubon_jixiang_variable_deferred_annuity(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "富邦人壽吉祥變額遞延年金保險",
    "其他商品",
    1,
)
assert parse_fubon_jixiang_variable_deferred_annuity(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == EXTRACTOR_VERSION
assert proposal["batch_id"] == "tii-life-054"
assert proposal["proposal_count"] == 24
assert proposal["proposed_count"] == 20
assert proposal["manual_review_count"] == 4
assert {item["product_id"] for item in proposal["proposals"]} == set(
    versions
)
for item in proposal["proposals"]:
    product_id = item["product_id"]
    assert item["candidate_count"] == 1
    assert item["status"] == (
        "manual_review_required"
        if product_id in OCR_PRODUCT_IDS
        else "proposed"
    )
    assert (
        "manual_source_review_required" in item["review_reasons"]
    ) is (product_id in OCR_PRODUCT_IDS)
    candidate = item["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == versions[product_id][
        "source_document_sha256"
    ]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-054",
        "product_count": len(schedules),
        "proposed_count": 20,
        "manual_source_review_count": len(OCR_PRODUCT_IDS),
    }
)

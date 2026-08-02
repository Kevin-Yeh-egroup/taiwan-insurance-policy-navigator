from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    HONGTAI_LEHUO_VARIABLE_ANNUITY_VERSIONS,
    complete_strict_source_document,
    parse_hongtai_lehuo_variable_annuity,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-090"
PARSER_ID = "hongtai-lehuo-variable-annuity-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-090-hongtai-lehuo-variable-annuity-v222.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-090-hongtai-lehuo-variable-annuity-exact-source-matrix.json"
)
SOURCE_GAPS_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-090-hongtai-lehuo-variable-annuity-source-gaps.json"
)


def source_document(product_id: str) -> dict:
    version = HONGTAI_LEHUO_VARIABLE_ANNUITY_VERSIONS[product_id]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-090",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


versions = HONGTAI_LEHUO_VARIABLE_ANNUITY_VERSIONS
assert len(versions) == 21

source_matrix = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert source_matrix["product_count"] == 42
assert source_matrix["status_counts"] == {
    "source_pending": 21,
    "readable": 21,
}
assert {
    row["product_id"]
    for row in source_matrix["rows"]
    if row["status"] == "readable"
} == set(versions)

source_gaps = json.loads(SOURCE_GAPS_PATH.read_text(encoding="utf-8"))
assert source_gaps["gap_count"] == 21
assert {
    item["product_id"] for item in source_gaps["gaps"]
} == {
    row["product_id"]
    for row in source_matrix["rows"]
    if row["status"] == "source_pending"
}

schedules = {}
semantic_groups = Counter()
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    revision = source_version["revision"]
    document = source_document(product_id)
    assert document["page_count"] == source_version["page_count"]
    assert document["pages_parsed"] == source_version["page_count"]
    assert (
        document["source_text_extractor"]
        == source_version["source_text_extractor"]
    )
    schedule = parse_hongtai_lehuo_variable_annuity(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-090/{product_id}")

    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert [item["value"] for item in schedule["plan_options"]] == [
        "一次給付",
        "分期給付",
    ]
    once_entries = {
        entry["id"]
        for entry in schedule["plan_options"][0]["coverage_entries"]
    }
    installment_entries = {
        entry["id"]
        for entry in schedule["plan_options"][1]["coverage_entries"]
    }
    assert once_entries == {
        "annuity-start-lump-sum",
        "account-value-return-before-annuity-start-death",
    }
    assert installment_entries == {
        "annual-annuity-or-low-amount-lump-sum",
        "excess-account-value-return-at-annuity-start",
        "account-value-return-before-annuity-start-death",
        "unpaid-annuity-balance-after-death",
    }

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert version["guarantee_period_options_years"] == [10, 15, 20]
    assert version["minimum_annual_annuity_amount"] == 10_000
    assert version["maximum_annual_annuity_amount"] == 1_200_000
    assert version["annuity_start_payment_deadline_days"] == (
        15 if revision >= 28 else None
    )
    assert version["annuity_start_delay_interest_rule"] is (
        revision >= 28
    )
    semantic_groups[version["semantic_phase"]] += 1
    schedules[product_id] = schedule

assert semantic_groups == {
    "legacy-annuity-payment-articles": 8,
    "modern-annuity-notice-and-payment-articles": 13,
}

reference = source_document("217421MV1A00123A11Z90000041")
for corrupted in (
    {**reference, "batch_id": "tii-life-091"},
    {**reference, "file_name": "217421MV1A00123A11Z90000041-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 11},
):
    assert parse_hongtai_lehuo_variable_annuity(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "宏泰人壽樂活人生變額年金保險",
    "其他商品",
    1,
)
assert parse_hongtai_lehuo_variable_annuity(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-090"
assert proposal["proposal_count"] == 21
assert proposal["proposed_count"] == 21
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == set(
    versions
)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == versions[product_id][
        "source_document_sha256"
    ]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-090",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": source_gaps["gap_count"],
    }
)

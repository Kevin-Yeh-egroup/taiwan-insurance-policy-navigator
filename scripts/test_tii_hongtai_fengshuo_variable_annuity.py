from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    HONGTAI_FENGSHUO_VARIABLE_ANNUITY_VERSIONS,
    complete_strict_source_document,
    parse_hongtai_fengshuo_variable_annuity,
    parse_plan_table_with_parser,
)
from validate_data import (
    validate_hongtai_fengshuo_variable_annuity_contract,
    validate_plan_options,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-090"
PARSER_ID = "hongtai-fengshuo-variable-annuity-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-090-hongtai-fengshuo-variable-annuity-v223.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-090-hongtai-fengshuo-variable-annuity-exact-source-matrix.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-090-hongtai-fengshuo-variable-annuity-v223"
    / "tii-life-090-hongtai-fengshuo-variable-annuity-v223-review-packet.json"
)


def source_document(product_id: str) -> dict:
    version = HONGTAI_FENGSHUO_VARIABLE_ANNUITY_VERSIONS[product_id]
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


versions = HONGTAI_FENGSHUO_VARIABLE_ANNUITY_VERSIONS
assert len(versions) == 31
assert {version["revision"] for version in versions.values()} == set(
    range(31)
)

source_matrix = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert source_matrix["product_count"] == 31
assert source_matrix["status_counts"] == {"readable": 31}
assert source_matrix["duplicate_source_sha_groups"] == {}
assert {row["product_id"] for row in source_matrix["rows"]} == set(
    versions
)

schedules = {}
semantic_groups = Counter()
maximum_start_age_groups = Counter()
minimum_accumulation_groups = Counter()
maximum_annual_annuity_groups = Counter()
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    revision = source_version["revision"]
    document = source_document(product_id)
    assert document["page_count"] == source_version["page_count"]
    assert document["pages_parsed"] == source_version["page_count"]
    assert document["source_text_extractor"] == "pypdf"
    schedule = parse_hongtai_fengshuo_variable_annuity(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-090/{product_id}")
    validate_hongtai_fengshuo_variable_annuity_contract(
        schedule,
        schedule["version_characteristics"],
        f"tii-life-090/{product_id}",
    )

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
    expected_installment_entries = {
        "annual-annuity-or-low-amount-lump-sum",
        "account-value-return-before-annuity-start-death",
        "unpaid-annuity-balance-after-death",
        *(
            {"excess-account-value-return-at-annuity-start"}
            if revision >= 12
            else set()
        ),
    }
    assert installment_entries == expected_installment_entries

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["terms_revision"] == (
        "initial" if revision == 0 else f"partial-change-{revision}"
    )
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["guarantee_period_options_years"] == [10, 15, 20]
    assert version["minimum_annual_annuity_amount"] == 10_000
    assert version["maximum_annual_annuity_amount"] == (
        1_200_000 if revision >= 12 else None
    )
    assert version["annuity_start_payment_deadline_days"] == (
        15 if revision >= 12 else None
    )
    assert version["annuity_start_delay_interest_rule"] is (
        revision >= 12
    )
    semantic_groups[version["semantic_phase"]] += 1
    maximum_start_age_groups[version["max_annuity_start_age"]] += 1
    minimum_accumulation_groups[
        version["minimum_accumulation_period_years"]
    ] += 1
    maximum_annual_annuity_groups[
        version["maximum_annual_annuity_amount"]
    ] += 1
    schedules[product_id] = schedule

assert semantic_groups == {
    "legacy-annuity-payment-articles": 12,
    "modern-annuity-notice-and-payment-articles": 19,
}
assert maximum_start_age_groups == {80: 14, 85: 13, 95: 4}
assert minimum_accumulation_groups == {10: 26, 6: 5}
assert maximum_annual_annuity_groups == {None: 12, 1_200_000: 19}

reference = source_document("217421MV1A00223A11Z90000030")
for corrupted in (
    {**reference, "batch_id": "tii-life-091"},
    {**reference, "file_name": "217421MV1A00223A11Z90000030-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 7},
):
    assert parse_hongtai_fengshuo_variable_annuity(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "宏泰人壽豐碩年年變額年金保險",
    "其他商品",
    1,
)
assert parse_hongtai_fengshuo_variable_annuity(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-090"
assert proposal["proposal_count"] == 31
assert proposal["proposed_count"] == 31
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

review_packet = json.loads(REVIEW_PACKET_PATH.read_text(encoding="utf-8"))
assert review_packet["proposal_count"] == 31
assert review_packet["status_counts"] == {
    "ready_for_human_source_review": 31
}
assert review_packet["error_counts"] == {}

print(
    {
        "status": "ok",
        "batch_id": "tii-life-090",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "maximum_start_age_group_count": len(maximum_start_age_groups),
        "source_gap_count": 0,
    }
)

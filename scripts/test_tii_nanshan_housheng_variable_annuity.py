from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_HOUSHENG_VARIABLE_ANNUITY_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_housheng_variable_annuity,
    parse_plan_table_with_parser,
)
from validate_data import (
    validate_nanshan_housheng_variable_annuity_contract,
    validate_plan_options,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-036"
PARSER_ID = "nanshan-housheng-variable-annuity-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-036-nanshan-housheng-variable-annuity-v228.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-036-nanshan-housheng-variable-annuity-exact-source-matrix.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-036-nanshan-housheng-variable-annuity-v228"
    / "tii-life-036-nanshan-housheng-variable-annuity-v228-review-packet.json"
)


def source_document(product_id: str) -> dict:
    version = NANSHAN_HOUSHENG_VARIABLE_ANNUITY_VERSIONS[product_id]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-036",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        DOCUMENT_ROOT / product_id / version["file_name"],
    )


versions = NANSHAN_HOUSHENG_VARIABLE_ANNUITY_VERSIONS
assert len(versions) == 26
assert {version["revision"] for version in versions.values()} == set(
    range(26)
)
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 26

source_matrix = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert source_matrix["batch_id"] == "tii-life-036"
assert source_matrix["product_count"] == 26
assert source_matrix["status_counts"] == {"readable": 26}
assert source_matrix["duplicate_source_sha_groups"] == {}
assert {row["product_id"] for row in source_matrix["rows"]} == set(
    versions
)

schedules = {}
semantic_groups = Counter()
max_start_age_groups = Counter()
annual_limit_groups = Counter()
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    revision = source_version["revision"]
    document = source_document(product_id)
    assert document["page_count"] == source_version["page_count"]
    assert document["pages_parsed"] == source_version["page_count"]
    assert document["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    schedule = parse_nanshan_housheng_variable_annuity(document)
    assert schedule is not None, product_id
    assert parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    ) == (PARSER_ID, schedule)
    context = f"tii-life-036/{product_id}"
    validate_plan_options(schedule, context)
    validate_nanshan_housheng_variable_annuity_contract(
        schedule,
        schedule["version_characteristics"],
        context,
    )

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert [option["value"] for option in schedule["plan_options"]] == [
        "10年",
        "15年",
        "20年",
    ]
    version = schedule["version_characteristics"]
    assert version["source_batch_id"] == "tii-life-036"
    assert version["source_product_id"] == product_id
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["guarantee_period_options_years"] == [10, 15, 20]
    assert version["minimum_monthly_annuity_amount"] == 3_000
    assert version["max_annuity_payment_age"] == 110
    assert version["max_annuity_start_age"] == (
        85 if revision <= 4 else 80
    )
    assert version["maximum_annual_annuity_amount"] == (
        None if revision <= 19 else 1_200_000
    )
    assert version["policy_loan_offset_applies"] is (revision >= 7)
    assert version["other_unpaid_amount_offset_applies"] is (
        revision >= 20
    )
    assert version["maturity_claim_documents_required"] is (
        revision >= 22
    )
    semantic_groups[version["semantic_phase"]] += 1
    max_start_age_groups[version["max_annuity_start_age"]] += 1
    annual_limit_groups[version["maximum_annual_annuity_rule"]] += 1

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "allocated-death-benefit-before-annuity-start",
        "preallocation-death-benefit",
        "delayed-claim-death-benefit-after-accumulation-maturity",
        "exclusion-account-value-return",
        "monthly-annuity-payment",
        "account-value-withdrawal-at-annuity-start",
        "low-monthly-annuity-lump-sum",
        "unpaid-annuity-balance",
        "excess-annuity-account-value-return",
    }
    assert entries["allocated-death-benefit-before-annuity-start"][
        "calculation_basis"
    ] == "protected_amount_plus_policy_account_value"
    assert entries["preallocation-death-benefit"][
        "calculation_basis"
    ] == "net_premium_factor_plus_additional_premium"
    assert entries["preallocation-death-benefit"][
        "rate_percent"
    ] == 101
    assert entries[
        "delayed-claim-death-benefit-after-accumulation-maturity"
    ]["calculation_basis"] == (
        "face_amount_plus_account_value_minus_paid_annuity_and_offsets"
    )
    assert entries["monthly-annuity-payment"][
        "calculation_basis"
    ] == "account_value_annuity_factor"
    assert entries["account-value-withdrawal-at-annuity-start"][
        "unit_key"
    ] == "annuity_start_policy_account_value"
    assert entries["unpaid-annuity-balance"]["unit_key"] == (
        "unpaid_annuity_balance"
    )
    assert entries["excess-annuity-account-value-return"][
        "unit_key"
    ] == "excess_annuity_reserve_return_amount"
    schedules[product_id] = schedule

assert semantic_groups == {
    "legacy-total-account-value-max-age-85": 3,
    "basic-premium-max-age-85": 2,
    "basic-premium-max-age-80-before-loan-offset": 2,
    "basic-premium-with-loan-offset": 13,
    "target-premium-fixed-cap-written-notice": 1,
    "target-premium-fixed-cap-agreed-notice": 1,
    "target-premium-maturity-document-receipt": 4,
}
assert max_start_age_groups == {85: 5, 80: 21}
assert annual_limit_groups == {
    "legal_limit_at_annuity_start": 20,
    "fixed_1200000_twd": 6,
}

reference = source_document("206421MV1A30123A11Z90000025")
for corrupted in (
    {**reference, "batch_id": "tii-life-037"},
    {
        **reference,
        "file_name": "206421MV1A30123A11Z90000025-F.pdf",
    },
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 20},
):
    assert parse_nanshan_housheng_variable_annuity(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "南山人壽厚生變額年金保險",
    "其他商品",
    1,
)
assert parse_nanshan_housheng_variable_annuity(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-036"
assert proposal["proposal_count"] == 26
assert proposal["proposed_count"] == 26
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
assert review_packet["proposal_count"] == 26
assert review_packet["status_counts"] == {
    "ready_for_human_source_review": 26
}
assert review_packet["error_counts"] == {}

print(
    {
        "status": "ok",
        "batch_id": "tii-life-036",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": 0,
    }
)

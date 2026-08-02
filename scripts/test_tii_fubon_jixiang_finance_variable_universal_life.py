from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FUBON_JIXIANG_FINANCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    PLAN_TABLE_PARSERS,
    complete_strict_source_document,
    parse_fubon_jixiang_finance_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-053"
PARSER_ID = "fubon-jixiang-finance-variable-universal-life-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-053-fubon-jixiang-finance-variable-universal-life-v224.json"
)
SOURCE_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-053-fubon-jixiang-finance-variable-universal-life-exact-source-matrix.json"
)
SOURCE_GAP_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / "tii-life-053-fubon-jixiang-finance-variable-universal-life-source-gaps.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-053-fubon-jixiang-finance-variable-universal-life-v224"
    / "tii-life-053-fubon-jixiang-finance-variable-universal-life-v224-review-packet.json"
)
SOURCE_GAP_PRODUCT_IDS = {
    "209141M31A00904",
    "209191MV1A00323A11Z90000024",
    "209191MV1A00323A11Z90000025",
    "209191MV1A00323A11Z90000026",
}


def source_document(product_id: str) -> dict:
    version = FUBON_JIXIANG_FINANCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
        product_id
    ]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-053",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


versions = FUBON_JIXIANG_FINANCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 36
assert {version["revision"] for version in versions.values()} == (
    set(range(40)) - {4, 24, 25, 26}
)
assert not SOURCE_GAP_PRODUCT_IDS & set(versions)
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 36

source_matrix = json.loads(SOURCE_MATRIX_PATH.read_text(encoding="utf-8"))
assert source_matrix["product_count"] == 40
assert source_matrix["status_counts"] == {
    "readable": 36,
    "source_pending": 4,
}
assert source_matrix["duplicate_source_sha_groups"] == {}
assert {row["product_id"] for row in source_matrix["rows"]} == (
    set(versions) | SOURCE_GAP_PRODUCT_IDS
)

source_gaps = json.loads(SOURCE_GAP_PATH.read_text(encoding="utf-8"))
assert source_gaps["gap_count"] == 4
assert {item["product_id"] for item in source_gaps["gaps"]} == (
    SOURCE_GAP_PRODUCT_IDS
)

schedules = {}
semantic_groups = Counter()
maturity_age_groups = Counter()
funeral_eligibility_groups = Counter()
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    revision = source_version["revision"]
    document = source_document(product_id)
    assert document["page_count"] == source_version["page_count"]
    assert document["pages_parsed"] == source_version["page_count"]
    assert document["source_text_extractor"] == "pypdf"

    schedule = parse_fubon_jixiang_finance_variable_universal_life(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    parser_matches = [
        parser_id
        for parser_id, parser in PLAN_TABLE_PARSERS
        if parser(document) is not None
    ]
    assert parser_matches == [PARSER_ID], (
        product_id,
        parser_matches,
    )
    validate_plan_options(schedule, f"tii-life-053/{product_id}")

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert [item["value"] for item in schedule["plan_options"]] == [
        "A型",
        "B型",
    ]
    assert schedule["version_characteristics"][
        "required_policy_inputs"
    ] == [
        "face_amount",
        "policy_type",
        "benefit_valuation_policy_account_value",
        "insured_age_at_event",
        "death_benefit_status",
        "remaining_funeral_benefit_limit",
        "maturity_policy_account_value",
    ]

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "maturity_policy_account_value"
    )
    for entry_id in (
        "death-or-funeral-benefit",
        "total-disability-benefit",
    ):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        assert entry["policy_state_keys"] == [
            "benefit_valuation_policy_account_value"
        ]
        assert entry["minor_account_value_return_age"] == 15
    assert entries["death-or-funeral-benefit"][
        "funeral_limit_plan_options"
    ] == ["A型", "B型"]

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["source_text_quality"] == (
        "machine_readable_exact_hash"
    )
    if revision <= 19:
        semantic_groups["direct_greater_or_sum"] += 1
        assert schedule["face_amount_label"] == "保險金額"
        assert version["terms_formula_representation"] == (
            "direct_greater_or_sum"
        )
        assert version["disability_term"] == "完全殘廢"
    elif revision <= 33:
        semantic_groups["net_risk_legacy_funeral"] += 1
        assert schedule["face_amount_label"] == "基本保額"
        assert version["terms_formula_representation"] == (
            "net_amount_at_risk_plus_account_value"
        )
        assert version["disability_term"] == "完全殘廢"
    else:
        semantic_groups["net_risk_guardianship"] += 1
        assert schedule["face_amount_label"] == "基本保額"
        assert version["disability_term"] == "完全失能"

    maturity_age_groups[version["maturity_age"]] += 1
    funeral_eligibility_groups[
        version["funeral_eligibility_rule"]
    ] += 1
    schedules[product_id] = schedule

assert semantic_groups == {
    "direct_greater_or_sum": 19,
    "net_risk_legacy_funeral": 11,
    "net_risk_guardianship": 6,
}
assert maturity_age_groups == {111: 19, 110: 17}
assert funeral_eligibility_groups == {
    "mental_capacity_definition": 30,
    "guardianship_declaration": 6,
}

reference = source_document("209191MV1A00323A11Z90000039")
for corrupted in (
    {**reference, "batch_id": "tii-life-054"},
    {**reference, "file_name": "209191MV1A00323A11Z90000039-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 33},
):
    assert (
        parse_fubon_jixiang_finance_variable_universal_life(corrupted)
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] += "\ncorrupted-source-text"
assert (
    parse_fubon_jixiang_finance_variable_universal_life(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-053"
assert proposal["proposal_count"] == 36
assert proposal["proposed_count"] == 36
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

review_packet = json.loads(
    REVIEW_PACKET_PATH.read_text(encoding="utf-8")
)
assert review_packet["proposal_count"] == 36
assert review_packet["status_counts"] == {
    "ready_for_human_source_review": 36
}
assert review_packet["semantic_schedule_group_count"] == 3
assert review_packet["error_counts"] == {}

print(
    {
        "status": "ok",
        "batch_id": "tii-life-053",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": len(SOURCE_GAP_PRODUCT_IDS),
    }
)

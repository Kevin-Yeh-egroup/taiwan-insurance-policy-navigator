from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    KANGJIAN_JINZHUN_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_kangjian_jinzhun_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-137"
PARSER_ID = "kangjian-jinzhun-variable-universal-life-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-137-kangjian-jinzhun-variable-universal-life-v223.json"
)


def source_document(product_id: str) -> dict:
    version = KANGJIAN_JINZHUN_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
        product_id
    ]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-137",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


versions = KANGJIAN_JINZHUN_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 28
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 28

schedules: dict[str, dict] = {}
semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    document = source_document(product_id)
    schedule = parse_kangjian_jinzhun_variable_universal_life(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-137/{product_id}")

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["plan_options"] == [
        {"value": "甲型", "label": "甲型"}
    ]
    version = schedule["version_characteristics"]
    assert version["source_batch_id"] == "tii-life-137"
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert version["source_text_quality"] == (
        "machine_readable_exact_hash"
    )
    assert version["maturity_age"] == 101
    assert version["policy_type_options"] == ["甲型"]
    semantic_groups[version["semantic_phase"]] += 1

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
    assert entries["death-or-funeral-benefit"][
        "calculation_basis"
    ] == "net_amount_at_risk_plus_policy_account_value"
    assert entries["total-disability-benefit"][
        "calculation_basis"
    ] == "net_amount_at_risk_plus_policy_account_value"
    schedules[product_id] = schedule

assert semantic_groups == {
    "legacy_greater_of_basic_or_account": 1,
    "age_ratio_without_policy_loan": 2,
    "age_ratio_with_policy_loan": 12,
    "age_ratio_funeral_limit": 2,
    "minor_return_collected_cost_period": 5,
    "minor_return_death_to_next_policy_month": 6,
}

for revision in range(28):
    product_id = f"256191M31A001{revision:02d}"
    schedule = schedules[product_id]
    version = schedule["version_characteristics"]
    death_entry = next(
        entry
        for entry in schedule["coverage_entries"]
        if entry["id"] == "death-or-funeral-benefit"
    )
    disability_entry = next(
        entry
        for entry in schedule["coverage_entries"]
        if entry["id"] == "total-disability-benefit"
    )
    assert version["policy_loan_offset_required"] is (
        revision >= 3
    )
    assert version[
        "minor_death_before_age_15_account_value_rule"
    ] is (revision >= 17)
    assert version[
        "minor_disability_before_age_15_account_value_rule"
    ] is (revision >= 17)
    assert death_entry.get("minor_account_value_return_age") == (
        15 if revision >= 17 else None
    )
    assert disability_entry.get(
        "minor_account_value_return_age"
    ) == (15 if revision >= 17 else None)
    assert death_entry.get("funeral_limit_plan_options") == (
        ["甲型"] if revision >= 15 else None
    )
    assert (
        "unexpired_premium_refund_amount"
        in death_entry.get("policy_state_keys", [])
    ) is (revision >= 17)
    assert (
        "policy_loan_and_interest_amount"
        in death_entry["policy_state_keys"]
    ) is (revision >= 3)

reference = source_document("256191M31A00127")
for corrupted in (
    {**reference, "batch_id": "tii-life-136"},
    {**reference, "file_name": "256191M31A00127-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 16},
    {**reference, "source_text_extractor": "pymupdf"},
):
    assert (
        parse_kangjian_jinzhun_variable_universal_life(corrupted)
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "百分之一百三十",
    "百分之一百三十一",
    1,
)
assert (
    parse_kangjian_jinzhun_variable_universal_life(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-137"
assert proposal["proposal_count"] == 28
assert proposal["proposed_count"] == 28
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == set(versions)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == versions[
        product_id
    ]["source_document_sha256"]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-137",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "promoted_product_count": 0,
    }
)

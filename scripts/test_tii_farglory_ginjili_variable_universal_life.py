from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FARGLORY_GINJILI_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_farglory_ginjili_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-083"
PARSER_ID = "farglory-ginjili-variable-universal-life-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-083-farglory-ginjili-variable-universal-life-v222.json"
)
SOURCE_GAP_PRODUCT_IDS = {
    "216121M31A03113",
    "216121M31A03115",
    "216121M31A03116",
    "216121M31A03117",
    "216121M31A03118",
    "216121M31A03119",
    "216121M31A03121",
    "216121M31A03122",
    "216121M31A03123",
    "216121M31A03124",
}


def source_document(product_id: str) -> dict:
    version = FARGLORY_GINJILI_VARIABLE_UNIVERSAL_LIFE_VERSIONS[product_id]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-083",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version["source_document_sha256"],
        },
        source_path,
    )


versions = FARGLORY_GINJILI_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 59
assert not SOURCE_GAP_PRODUCT_IDS & set(versions)

hash_to_products: dict[str, list[str]] = {}
for product_id, version in versions.items():
    hash_to_products.setdefault(
        version["source_document_sha256"],
        [],
    ).append(product_id)
assert len(hash_to_products) == 58
assert sorted(
    sorted(product_ids)
    for product_ids in hash_to_products.values()
    if len(product_ids) > 1
) == [["216121M31A03111", "216121M31A03112"]]

schedules = {}
semantic_groups = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_farglory_ginjili_variable_universal_life(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-083/{product_id}")

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["face_amount_label"] == "當年度保險金額"
    assert [item["value"] for item in schedule["plan_options"]] == [
        "甲型",
        "乙型",
        "丙型",
    ]

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert version["source_text_quality"] == (
        "machine_readable_exact_hash_pymupdf_recovery"
        if source_version["source_text_extractor"] == "pymupdf"
        else "machine_readable_exact_hash"
    )
    assert version["insurance_deduction_amount_policy_type_options"] == [
        "甲型",
        "丙型",
    ]
    assert version["maturity_age"] == 106
    assert version["annual_insurance_amount_input_required"] is True
    assert version["benefit_valuation_policy_account_value_required"] is True
    assert version["maturity_policy_account_value_required"] is True

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert entries["maturity-benefit"]["policy_state_keys"] == [
        "maturity_policy_account_value"
    ]
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

    semantic_groups[version["semantic_phase"]] += 1
    expected_minor_rule = 20 <= revision <= 51
    assert version["minor_death_before_age_15_account_value_rule"] is (
        expected_minor_rule
    )
    assert version["minor_disability_before_age_15_account_value_rule"] is (
        expected_minor_rule
    )
    for entry_id in (
        "death-or-funeral-benefit",
        "total-disability-benefit",
    ):
        assert (
            entries[entry_id].get("minor_account_value_return_age")
            == (15 if expected_minor_rule else None)
        )

    assert entries["death-or-funeral-benefit"][
        "funeral_limit_plan_options"
    ] == ["乙型"]
    assert version["funeral_limit_policy_type_options"] == ["乙型"]
    assert version["funeral_benefit_excludes_account_value"] is True
    assert version["terms_formula_representation"] == (
        "direct_greater_or_sum"
        if revision <= 33
        else "net_amount_at_risk_plus_account_value"
    )
    assert version["disability_term"] == (
        "完全殘廢" if revision <= 45 else "完全失能"
    )
    assert version["maturity_interest_applies"] is (revision >= 54)
    schedules[product_id] = schedule

assert semantic_groups == {
    "legacy_direct_child_funeral_under14": 11,
    "legacy_direct_under15_mental_capacity": 10,
    "net_risk_under15_mental_capacity": 12,
    "net_risk_under15_guardianship": 6,
    "net_risk_guardianship_no_minor_rule": 2,
    "net_risk_guardianship_no_minor_rule_maturity_interest": 18,
}

reference = source_document("216131MV1A03123A11C30000070")
for corrupted in (
    {**reference, "batch_id": "tii-life-084"},
    {**reference, "file_name": "216131MV1A03123A11C30000070-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 21},
):
    assert (
        parse_farglory_ginjili_variable_universal_life(corrupted)
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "遠雄人壽金吉利變額萬能壽險",
    "其他商品",
    1,
)
assert (
    parse_farglory_ginjili_variable_universal_life(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-083"
assert proposal["proposal_count"] == 59
assert proposal["proposed_count"] == 59
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
    assert candidate["source_document_sha256"] == versions[product_id][
        "source_document_sha256"
    ]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-083",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": len(SOURCE_GAP_PRODUCT_IDS),
    }
)

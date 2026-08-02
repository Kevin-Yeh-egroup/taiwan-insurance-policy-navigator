from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    HONGTAI_HONGYUAN_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_hongtai_hongyuan_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-089"
PARSER_ID = "hongtai-hongyuan-variable-universal-life-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-089-hongtai-hongyuan-variable-universal-life-v222.json"
)
SOURCE_GAP_PRODUCT_IDS = {
    "217141M31A00100",
    "217141M31A00103",
    "217141M31A00104",
    "217141M31A00105",
    "217141M31A00106",
    "217141M31A00107",
    "217141M31A00108",
    "217141M31A00116",
    "217141M31A00117",
    "217121MV1A00123A11Z90000029",
}


def source_document(product_id: str) -> dict:
    version = HONGTAI_HONGYUAN_VARIABLE_UNIVERSAL_LIFE_VERSIONS[product_id]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-089",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version["source_document_sha256"],
        },
        source_path,
    )


versions = HONGTAI_HONGYUAN_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 35
assert not SOURCE_GAP_PRODUCT_IDS & set(versions)
assert len({item["source_document_sha256"] for item in versions.values()}) == 35

schedules = {}
semantic_groups = Counter()
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_hongtai_hongyuan_variable_universal_life(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-089/{product_id}")

    expected_face_label = "保險金額" if revision <= 22 else "基本保額"
    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["face_amount_label"] == expected_face_label
    assert [item["value"] for item in schedule["plan_options"]] == [
        "甲型",
        "乙型",
    ]

    version = schedule["version_characteristics"]
    assert version["product_family"] == (
        "hongtai-hongyuan-variable-universal-life"
    )
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["source_text_extractor"] == "pypdf"
    assert version["source_text_quality"] == "machine_readable_exact_hash"
    assert version["policy_type_options"] == ["甲型", "乙型"]
    assert version["face_amount_label"] == expected_face_label
    assert version["maturity_age"] == 100
    assert version["maturity_interest_applies"] is (revision >= 37)
    assert version["unexpired_insurance_cost_refund_rule"] == (
        "type_a_when_account_value_exceeds_face_amount_type_b_always"
        if revision <= 22
        else "always"
    )
    assert version["funeral_limit_policy_type_options"] == ["乙型"]
    assert version["funeral_benefit_excludes_account_value"] is True

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "disability-benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "sum_policy_state_amounts"
        if revision >= 37
        else "policy_state_amount"
    )
    assert entries["maturity-benefit"]["policy_state_keys"] == (
        ["maturity_policy_account_value", "maturity_interest_amount"]
        if revision >= 37
        else ["maturity_policy_account_value"]
    )
    for entry_id in ("death-or-funeral-benefit", "disability-benefit"):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        assert entry["policy_state_keys"] == [
            "benefit_valuation_policy_account_value",
            "unexpired_premium_refund_amount",
        ]

    assert entries["death-or-funeral-benefit"][
        "funeral_limit_plan_options"
    ] == ["乙型"]
    semantic_groups[version["semantic_phase"]] += 1
    schedules[product_id] = schedule

assert semantic_groups == {
    "direct_first_degree_disability_legacy_funeral": 2,
    "direct_total_disability_mental_capacity": 7,
    "direct_total_disability_mental_capacity_later": 5,
    "net_risk_complete_disability_mental_capacity": 6,
    "net_risk_complete_disability_guardianship": 5,
    "net_risk_guardianship_seven_age_thresholds": 2,
    "net_risk_guardianship_maturity_interest": 8,
}

reference = source_document("217121MV1A00123A11Z90000037")
for corrupted in (
    {**reference, "batch_id": "tii-life-090"},
    {**reference, "file_name": "217121MV1A00123A11Z90000037-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 12},
):
    assert parse_hongtai_hongyuan_variable_universal_life(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "宏泰人壽宏願人生變額萬能壽險",
    "其他商品",
    1,
)
assert parse_hongtai_hongyuan_variable_universal_life(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-089"
assert proposal["proposal_count"] == 35
assert proposal["proposed_count"] == 35
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == set(versions)
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
        "batch_id": "tii-life-089",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": len(SOURCE_GAP_PRODUCT_IDS),
    }
)

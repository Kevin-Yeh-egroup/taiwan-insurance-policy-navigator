from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FUBON_NEW_LUCKY_VARIABLE_UNIVERSAL_LIFE_EARLY_VERSIONS,
    FUBON_NEW_LUCKY_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_fubon_new_lucky_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-053"
PARSER_ID = "fubon-new-lucky-variable-universal-life-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-053-fubon-new-lucky-variable-universal-life-v221.json"
)
EARLY_PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-053-fubon-new-lucky-variable-universal-life-early-v227.json"
)
EARLY_REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-053-fubon-new-lucky-variable-universal-life-early-v227"
    / "tii-life-053-fubon-new-lucky-variable-universal-life-early-v227-review-packet.json"
)
SOURCE_GAP_PRODUCT_IDS = {
    "209141M31A00140",
    "209141M31A00156",
}


def source_document(product_id: str) -> dict:
    version = FUBON_NEW_LUCKY_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENT_ROOT / product_id / version["file_name"]
    )
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


versions = FUBON_NEW_LUCKY_VARIABLE_UNIVERSAL_LIFE_VERSIONS
early_versions = FUBON_NEW_LUCKY_VARIABLE_UNIVERSAL_LIFE_EARLY_VERSIONS
late_product_ids = set(versions) - set(early_versions)
assert len(versions) == 64
assert len(early_versions) == 27
assert len(late_product_ids) == 37
assert not SOURCE_GAP_PRODUCT_IDS & set(versions)
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 64

schedules = {}
semantic_groups = {
    "legacy_under14_b_funeral_maturity105": 0,
    "base_terms_without_funeral_endorsement": 0,
    "legacy_under14_b_funeral": 0,
    "under15_account_value_return": 0,
    "net_risk_legacy_funeral": 0,
    "net_risk_guardianship": 0,
}
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_fubon_new_lucky_variable_universal_life(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-053/{product_id}")

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert [item["value"] for item in schedule["plan_options"]] == [
        "A型",
        "B型",
    ]
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["source_text_quality"] == (
        "verified_windows_ocr_exact_hash"
        if source_version["source_text_extractor"] == "windows_ocr"
        else "machine_readable_exact_hash"
    )
    assert version["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert version["maturity_age"] == (
        105 if revision == 10 else 110
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    death_entry_id = (
        "death-benefit"
        if revision == 11
        else "death-or-funeral-benefit"
    )
    assert set(entries) == {
        "maturity-benefit",
        death_entry_id,
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "maturity_policy_account_value"
    )
    for entry_id in (
        death_entry_id,
        "total-disability-benefit",
    ):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        assert entry["policy_state_keys"] == [
            "benefit_valuation_policy_account_value"
        ]
        if revision >= 29:
            assert entry["minor_account_value_return_age"] == 15
        else:
            assert "minor_account_value_return_age" not in entry

    if revision == 10:
        expected_semantic_phase = (
            "legacy_under14_b_funeral_maturity105"
        )
    elif revision == 11:
        expected_semantic_phase = (
            "base_terms_without_funeral_endorsement"
        )
    elif revision <= 28:
        expected_semantic_phase = "legacy_under14_b_funeral"
    elif revision <= 55:
        expected_semantic_phase = "under15_account_value_return"
    elif revision <= 71:
        expected_semantic_phase = "net_risk_legacy_funeral"
    else:
        expected_semantic_phase = "net_risk_guardianship"
    semantic_groups[expected_semantic_phase] += 1
    assert version["semantic_phase"] == expected_semantic_phase
    assert version[
        "minor_death_before_age_15_account_value_rule"
    ] is (revision >= 29)
    assert version[
        "minor_disability_before_age_15_account_value_rule"
    ] is (revision >= 29)
    assert version["funeral_benefit_excludes_account_value"] is (
        revision != 11
    )

    if revision <= 55:
        assert schedule["face_amount_label"] == "保單所載保險金額"
        assert version["terms_formula_representation"] == (
            "direct_greater_or_sum"
        )
        assert version["disability_term"] == "全殘廢"
        if revision == 11:
            assert version["funeral_eligibility_rule"] == (
                "not_stated_in_exact_source_document"
            )
            assert version["funeral_limit_policy_type_options"] == []
            assert "funeral_limit_plan_options" not in entries[
                death_entry_id
            ]
        else:
            assert version["funeral_eligibility_rule"] == (
                "under_14_or_mental_incapacity"
                if revision <= 28
                else "mental_capacity_definition"
            )
            assert entries[death_entry_id][
                "funeral_limit_plan_options"
            ] == ["B型"]
    elif revision <= 71:
        assert schedule["face_amount_label"] == "基本保額"
        assert version["terms_formula_representation"] == (
            "net_amount_at_risk_plus_account_value"
        )
        assert version["disability_term"] == "完全殘廢"
        assert version["funeral_eligibility_rule"] == (
            "mental_capacity_definition"
        )
        assert entries["death-or-funeral-benefit"][
            "funeral_limit_plan_options"
        ] == ["A型", "B型"]
    else:
        assert schedule["face_amount_label"] == "基本保額"
        assert version["disability_term"] == "完全失能"
        assert version["funeral_eligibility_rule"] == (
            "guardianship_declaration"
        )
        assert entries["death-or-funeral-benefit"][
            "funeral_limit_plan_options"
        ] == ["A型", "B型"]
    schedules[product_id] = schedule

assert semantic_groups == {
    "legacy_under14_b_funeral_maturity105": 1,
    "base_terms_without_funeral_endorsement": 1,
    "legacy_under14_b_funeral": 17,
    "under15_account_value_return": 26,
    "net_risk_legacy_funeral": 15,
    "net_risk_guardianship": 4,
}

reference = source_document("209141M31A00155")
for corrupted in (
    {**reference, "batch_id": "tii-life-054"},
    {**reference, "file_name": "209141M31A00155-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 21},
):
    assert (
        parse_fubon_new_lucky_variable_universal_life(corrupted)
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "富邦人壽新吉祥變額萬能終身壽險",
    "其他商品",
    1,
)
assert (
    parse_fubon_new_lucky_variable_universal_life(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-053"
assert proposal["proposal_count"] == 37
assert proposal["proposed_count"] == 37
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == late_product_ids
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == versions[
        product_id
    ]["source_document_sha256"]
    validate_plan_options(
        candidate["schedule"],
        f"tii-life-053/{product_id}/historical-v221",
    )

early_proposal = json.loads(
    EARLY_PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert early_proposal["batch_id"] == "tii-life-053"
assert early_proposal["proposal_count"] == len(early_versions)
assert early_proposal["proposed_count"] == len(early_versions)
assert early_proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in early_proposal["proposals"]
} == set(early_versions)
for item in early_proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == early_versions[
        product_id
    ]["source_document_sha256"]
    assert candidate["schedule"] == schedules[product_id]

early_review_packet = json.loads(
    EARLY_REVIEW_PACKET_PATH.read_text(encoding="utf-8")
)
assert early_review_packet["proposal_count"] == len(early_versions)
assert early_review_packet["status_counts"] == {
    "ready_for_human_source_review": len(early_versions)
}
assert early_review_packet["semantic_schedule_group_count"] == 4
assert early_review_packet["error_counts"] == {}

print(
    {
        "status": "ok",
        "batch_id": "tii-life-053",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": len(SOURCE_GAP_PRODUCT_IDS),
    }
)

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    GLOBAL_EXCELLENCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_global_excellence_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-167"
PARSER_ID = "global-excellence-variable-universal-life-v1"
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-167-global-excellence-variable-universal-life-"
        "exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / (
        "tii-life-167-global-excellence-variable-universal-life-"
        "v225.json"
    )
)


def source_document(product_id: str) -> dict:
    version = GLOBAL_EXCELLENCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
        product_id
    ]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-167",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


versions = GLOBAL_EXCELLENCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 29
assert set(versions) == {
    f"264141M31AVUL{revision:02d}"
    for revision in range(29)
}
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 29

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == "tii-life-167"
assert matrix["product_count"] == 29
assert matrix["status_counts"] == {"readable": 29}
assert matrix["duplicate_source_sha_groups"] == {}

schedules = {}
semantic_groups = {
    "fixed_110_percent": 0,
    "age_bands_130_115_101": 0,
    "age_bands_15_floor_130_115_101": 0,
}
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_global_excellence_variable_universal_life(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-167/{product_id}")

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["face_amount_label"] == "基本保額"
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
        "machine_readable_exact_hash"
    )
    assert version["maturity_age"] == 95
    assert version["disability_term"] == "全殘廢"

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "maturity_policy_account_value"
    )
    for entry_id in ("death-benefit", "total-disability-benefit"):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        assert entry["policy_state_keys"] == [
            "benefit_valuation_policy_account_value"
        ]
        assert "minor_account_value_return_age" not in entry

    semantic_phase = version["semantic_phase"]
    semantic_groups[semantic_phase] += 1
    if revision <= 6:
        assert version["minimum_benefit_formula_age"] == 0
        assert version["threshold_factor_schedule"] == []
        assert "insured_age_at_event" not in version[
            "required_policy_inputs"
        ]
    elif revision <= 19:
        assert version["minimum_benefit_formula_age"] == 0
        assert version["threshold_factor_schedule"][0] == {
            "min_age": 0,
            "max_age": 40,
            "factor": 1.3,
        }
        assert "insured_age_at_event" in version[
            "required_policy_inputs"
        ]
    else:
        assert version["minimum_benefit_formula_age"] == 15
        assert version["threshold_factor_schedule"][0] == {
            "min_age": 15,
            "max_age": 40,
            "factor": 1.3,
        }
        assert "insured_age_at_event" in version[
            "required_policy_inputs"
        ]
    schedules[product_id] = schedule

assert semantic_groups == {
    "fixed_110_percent": 7,
    "age_bands_130_115_101": 13,
    "age_bands_15_floor_130_115_101": 9,
}

reference = source_document("264141M31AVUL20")
for corrupted in (
    {**reference, "batch_id": "tii-life-168"},
    {**reference, "file_name": "264141M31AVUL20-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 32},
):
    assert (
        parse_global_excellence_variable_universal_life(corrupted)
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "卓越變額萬能壽險",
    "其他商品",
    1,
)
assert (
    parse_global_excellence_variable_universal_life(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-167"
assert proposal["proposal_count"] == 29
assert proposal["proposed_count"] == 29
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
        "batch_id": "tii-life-167",
        "product_count": len(schedules),
        "semantic_review_group_count": len(semantic_groups),
        "source_gap_count": 0,
    }
)

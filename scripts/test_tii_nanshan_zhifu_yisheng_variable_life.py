from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_ZHIFU_YISHENG_VARIABLE_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_zhifu_yisheng_variable_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-035"
PARSER_ID = "nanshan-zhifu-yisheng-variable-life-v1"
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-035-nanshan-zhifu-yisheng-variable-life-"
        "exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-035-nanshan-zhifu-yisheng-variable-life-v1.json"
)


def source_document(product_id: str) -> dict:
    version = NANSHAN_ZHIFU_YISHENG_VARIABLE_LIFE_VERSIONS[product_id]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-035",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


versions = NANSHAN_ZHIFU_YISHENG_VARIABLE_LIFE_VERSIONS
assert len(versions) == 27
assert set(versions) == {
    *(f"206141M31A310{revision:02d}" for revision in range(19)),
    *(
        f"206131MV1A30223A11Z900000{revision:02d}"
        for revision in range(19, 27)
    ),
}

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == "tii-life-035"
assert matrix["product_count"] == 27
assert matrix["status_counts"] == {"readable": 27}
assert len(matrix["duplicate_source_sha_groups"]) == 1

schedules: dict[str, dict] = {}
semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_nanshan_zhifu_yisheng_variable_life(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-035/{product_id}")

    expected_face_label = (
        "基本保險金額" if revision <= 17 else "基本保額"
    )
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["face_amount_label"] == expected_face_label
    assert not schedule.get("plan_options")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["maturity_age"] == 100
    assert version["unallocated_net_premium_included"] is (
        revision <= 17
    )
    assert version["funeral_limit_applies"] is True
    assert version[
        "minor_death_before_age_15_account_value_rule"
    ] is (9 <= revision <= 24)
    assert version["maturity_interest_applies"] is (revision == 26)
    assert version["funeral_limit_basis"] == (
        "supervisory_fixed_cap"
        if revision <= 8
        else "estate_tax_funeral_deduction_half"
    )
    semantic_groups[version["semantic_phase"]] += 1

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "nanshan-zhifu-yisheng-maturity",
        "nanshan-zhifu-yisheng-death",
        "nanshan-zhifu-yisheng-disability",
    }
    assert entries["nanshan-zhifu-yisheng-maturity"][
        "calculation_basis"
    ] == "maturity_policy_account_value"
    for entry_id in (
        "nanshan-zhifu-yisheng-death",
        "nanshan-zhifu-yisheng-disability",
    ):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "protected_amount_plus_policy_account_value"
        )
        assert entry["policy_state_keys"][:3] == [
            "policy_effect_status_at_event",
            "benefit_valuation_policy_account_value",
            "policy_values_converted_to_twd",
        ]
        assert (
            "investment_allocation_status"
            in entry["policy_state_keys"]
        ) is (revision <= 17)
        assert (
            "policy_loan_and_interest_amount"
            in entry["policy_state_keys"]
        ) is True
        assert (
            "unpaid_policy_charge_amount"
            in entry["policy_state_keys"]
        ) is (revision >= 18)
        assert (
            entry.get("minor_account_value_return_age") == 15
        ) is (9 <= revision <= 24)
    assert "death_benefit_status" in entries[
        "nanshan-zhifu-yisheng-death"
    ]["policy_state_keys"]
    assert "death_benefit_status" not in entries[
        "nanshan-zhifu-yisheng-disability"
    ]["policy_state_keys"]
    schedules[product_id] = schedule

assert semantic_groups == Counter(
    {
        "legacy_under14_fixed_funeral_pending_premium": 9,
        "legacy_minor15_estate_funeral_pending_premium": 9,
        "minor15_mental_capacity_complete_disability": 3,
        "minor15_guardianship_complete_impairment": 4,
        "guardianship_complete_impairment": 1,
        "guardianship_complete_impairment_maturity_interest": 1,
    }
)

reference_id = "206141M31A31018"
reference = source_document(reference_id)
for corrupted in (
    {**reference, "batch_id": "tii-life-036"},
    {**reference, "product_id": "206141M31A31017"},
    {**reference, "file_name": "206141M31A31018-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": reference["page_count"] + 1},
    {**reference, "source_text_extractor": "other"},
):
    assert parse_nanshan_zhifu_yisheng_variable_life(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "南山人壽致富一生變額壽險",
    "其他商品",
    1,
)
assert parse_nanshan_zhifu_yisheng_variable_life(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-035"
assert proposal["proposal_count"] == 27
assert proposal["proposed_count"] == 27
assert proposal["manual_review_count"] == 0
assert proposal.get("promoted_count", 0) == 0
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
    json.dumps(
        {
            "status": "ok",
            "exact_versions": len(versions),
            "semantic_groups": len(semantic_groups),
            "proposed": proposal["proposed_count"],
            "promoted": proposal.get("promoted_count", 0),
        },
        ensure_ascii=False,
        indent=2,
    )
)

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_SUPERIOR_LIFE_VARIABLE_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_superior_life_variable_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-035"
PARSER_ID = "nanshan-superior-life-variable-life-v1"
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-035-nanshan-superior-life-variable-life-"
        "exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-035-nanshan-superior-life-variable-life-v1.json"
)


def source_document(product_id: str) -> dict:
    version = NANSHAN_SUPERIOR_LIFE_VARIABLE_LIFE_VERSIONS[product_id]
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


versions = NANSHAN_SUPERIOR_LIFE_VARIABLE_LIFE_VERSIONS
assert len(versions) == 24
assert set(versions) == {
    *(f"206141M31A317{revision:02d}" for revision in range(0, 13)),
    *(
        f"206131MV1A30323A11Z900000{revision:02d}"
        for revision in range(13, 24)
    ),
}

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == "tii-life-035"
assert matrix["product_count"] == 24
assert matrix["status_counts"] == {"readable": 24}
matrix_rows = {
    row["product_id"]: row
    for row in matrix["rows"]
}
assert set(versions).issubset(matrix_rows)
for product_id, version in versions.items():
    row = matrix_rows[product_id]
    assert row["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert row["extractors"]["pypdf"]["page_count"] == version[
        "page_count"
    ]
    assert row["extractors"]["pypdf"]["normalized_text_sha256"] == (
        version["normalized_text_sha256"]
    )

schedules: dict[str, dict] = {}
semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_nanshan_superior_life_variable_life(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-035/{product_id}")

    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["face_amount_label"] == "基本保額"
    assert not schedule.get("plan_options")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["maturity_age"] == 100
    assert version[
        "policy_account_value_includes_unallocated_amount"
    ] is (revision >= 12)
    assert version["claim_time_bar_account_value_return"] is (
        revision >= 12
    )
    assert version["account_value_return_on_exclusion"] is True
    assert version["insured_age_accuracy_status_required"] is True
    assert version["funeral_limit_applies"] is True
    assert version["funeral_excess_insurance_cost_refund"] is True
    assert version[
        "minor_death_before_age_15_account_value_rule"
    ] is (revision != 0)
    assert version[
        "minor_disability_before_age_15_account_value_rule"
    ] is (revision != 0)
    assert version["value_addition_available"] is True
    assert version["value_addition_start_policy_year"] == 6
    assert version["value_addition_rate_schedule"] == [
        {"policy_years": "6-10", "rate_percent": 0.2},
        {"policy_years": "11-15", "rate_percent": 0.3},
        {"policy_years": "16+", "rate_percent": 0.4},
    ]
    semantic_groups[version["semantic_phase"]] += 1

    disability_term = (
        "殘廢"
        if revision <= 11
        else ("完全殘廢" if revision <= 18 else "完全失能")
    )
    assert version["disability_term"] == disability_term
    assert version["funeral_eligibility_rule"] == (
        "mental_incapacity_at_issue"
        if revision <= 18
        else "guardianship_declaration_not_revoked_at_issue"
    )
    if revision <= 11:
        assert version["unallocated_net_premium_included"] is True
        assert version[
            "unallocated_net_premium_return_on_exclusion"
        ] is True
        assert version["minor_age_rule"] == (
            "legacy_no_minor_age_rule"
            if revision == 0
            else (
                "legacy_actual_age_minor15"
                if revision == 1
                else "legacy_issue_age_minor15"
            )
        )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "nanshan-superior-life-maturity",
        "nanshan-superior-life-death",
        "nanshan-superior-life-disability",
        "nanshan-superior-life-value-addition",
    }
    assert entries["nanshan-superior-life-maturity"][
        "calculation_basis"
    ] == "maturity_policy_account_value"
    for entry_id in (
        "nanshan-superior-life-death",
        "nanshan-superior-life-disability",
    ):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "protected_amount_plus_policy_account_value"
        )
        assert entry.get("minor_account_value_return_age") == (
            15 if revision != 0 else None
        )
        assert "claim_time_status" in entry["policy_state_keys"]
        assert "benefit_exclusion_status" in entry["policy_state_keys"]
        assert "insured_age_accuracy_status" in entry[
            "policy_state_keys"
        ]
        assert "policy_loan_and_interest_amount" in entry[
            "policy_state_keys"
        ]
        assert "unpaid_policy_charge_amount" in entry[
            "policy_state_keys"
        ]
        assert (
            "investment_allocation_status"
            in entry["policy_state_keys"]
        ) is (revision <= 11)
    if 1 <= revision <= 11:
        assert entries["nanshan-superior-life-death"][
            "minor_unallocated_net_premium_return"
        ] is False
        assert entries["nanshan-superior-life-disability"][
            "minor_unallocated_net_premium_return"
        ] is True
    death = entries["nanshan-superior-life-death"]
    assert "death_benefit_status" in death["policy_state_keys"]
    assert "funeral_excess_insurance_cost_refund_status" in death[
        "policy_state_keys"
    ]
    disability = entries["nanshan-superior-life-disability"]
    assert disability["name"] == f"{disability_term}保險金"
    assert "total_disability_qualification_status" in disability[
        "policy_state_keys"
    ]
    value_addition = entries["nanshan-superior-life-value-addition"]
    expected_average_key = (
        "average_basic_premium_account_value"
        if revision <= 11
        else "average_target_premium_account_value"
    )
    assert value_addition["calculation_basis"] == (
        "policy_year_average_basic_premium_account_value_addition"
        if revision <= 11
        else "policy_year_average_target_premium_account_value_addition"
    )
    assert value_addition["policy_state_keys"] == [
        "policy_effect_status_at_event",
        "policy_year",
        expected_average_key,
    ]
    schedules[product_id] = schedule

assert semantic_groups == Counter(
    {
        "legacy_no_minor_age_rule": 1,
        "legacy_actual_age_minor15": 1,
        "legacy_issue_age_minor15": 10,
        "minor15_mental_incapacity_complete_disability": 7,
        "minor15_guardianship_complete_impairment": 5,
    }
)

reference_id = "206141M31A31712"
reference = source_document(reference_id)
for corrupted in (
    {**reference, "batch_id": "tii-life-036"},
    {**reference, "product_id": "206131MV1A30323A11Z90000013"},
    {**reference, "file_name": "206141M31A31712-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": reference["page_count"] + 1},
    {**reference, "source_text_extractor": "other"},
):
    assert parse_nanshan_superior_life_variable_life(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "南山人壽優越人生變額壽險",
    "其他商品",
    1,
)
assert parse_nanshan_superior_life_variable_life(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-035"
assert proposal["proposal_count"] == 24
assert proposal["proposed_count"] == 24
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

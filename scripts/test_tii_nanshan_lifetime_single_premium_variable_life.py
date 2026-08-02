from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_LIFETIME_SINGLE_PREMIUM_VARIABLE_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_lifetime_single_premium_variable_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-035"
PARSER_ID = "nanshan-lifetime-single-premium-variable-life-v1"
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-035-nanshan-lifetime-single-premium-variable-life-"
        "exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / (
        "tii-life-035-nanshan-lifetime-single-premium-variable-life-"
        "v1.json"
    )
)


def source_document(product_id: str) -> dict:
    version = NANSHAN_LIFETIME_SINGLE_PREMIUM_VARIABLE_LIFE_VERSIONS[
        product_id
    ]
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


versions = NANSHAN_LIFETIME_SINGLE_PREMIUM_VARIABLE_LIFE_VERSIONS
assert len(versions) == 35
assert set(versions) == {
    *(f"206141M31A301{revision:02d}" for revision in range(28)),
    *(
        f"206131MV1A30423A11Z900000{revision:02d}"
        for revision in range(28, 35)
    ),
}
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 35

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == "tii-life-035"
assert matrix["product_count"] == 35
assert matrix["status_counts"] == {"readable": 35}
assert matrix["duplicate_source_sha_groups"] == {}

schedules: dict[str, dict] = {}
semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_nanshan_lifetime_single_premium_variable_life(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-035/{product_id}")

    expected_face_label = (
        "基本保險金額" if revision <= 26 else "基本保額"
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
        revision <= 26
    )
    assert version["funeral_limit_applies"] is (
        2 <= revision <= 13 or revision >= 19
    )
    assert version[
        "minor_death_before_age_15_account_value_rule"
    ] is (19 <= revision <= 32)
    assert version["maturity_interest_applies"] is (revision == 34)
    semantic_groups[version["semantic_phase"]] += 1

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "nanshan-lifetime-maturity",
        "nanshan-lifetime-death",
        "nanshan-lifetime-disability",
    }
    assert entries["nanshan-lifetime-maturity"][
        "calculation_basis"
    ] == "maturity_policy_account_value"
    for entry_id in (
        "nanshan-lifetime-death",
        "nanshan-lifetime-disability",
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
        ) is (revision <= 26)
        assert (
            "policy_loan_and_interest_amount"
            in entry["policy_state_keys"]
        ) is (revision >= 10)
        assert (
            "unpaid_policy_charge_amount"
            in entry["policy_state_keys"]
        ) is (revision >= 27)
        assert (
            entry.get("minor_account_value_return_age") == 15
        ) is (19 <= revision <= 32)
    assert (
        "death_benefit_status"
        in entries["nanshan-lifetime-death"]["policy_state_keys"]
    ) is (2 <= revision <= 13 or revision >= 19)
    assert (
        "death_benefit_status"
        in entries["nanshan-lifetime-disability"][
            "policy_state_keys"
        ]
    ) is False
    schedules[product_id] = schedule

assert semantic_groups == Counter(
    {
        "legacy_fifth_valuation": 1,
        "legacy_second_trading_day": 1,
        "legacy_funeral_200m": 8,
        "legacy_funeral_200m_loan": 2,
        "legacy_funeral_threshold_excludes_pending": 1,
        "legacy_funeral_threshold_includes_pending": 1,
        "legacy_no_funeral_loan": 5,
        "legacy_minor15_funeral_loan": 8,
        "account_value_minor15_disability": 3,
        "account_value_minor15_impairment_guardianship": 3,
        "account_value_guardianship": 1,
        "account_value_guardianship_maturity_interest": 1,
    }
)

reference_id = "206141M31A30119"
reference = source_document(reference_id)
for corrupted in (
    {**reference, "batch_id": "tii-life-036"},
    {**reference, "product_id": "206141M31A30120"},
    {**reference, "file_name": "206141M31A30119-F.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": reference["page_count"] + 1},
    {**reference, "source_text_extractor": "other"},
):
    assert (
        parse_nanshan_lifetime_single_premium_variable_life(
            corrupted
        )
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "伴我一生躉繳變額壽險",
    "其他商品",
    1,
)
assert (
    parse_nanshan_lifetime_single_premium_variable_life(
        corrupted_text
    )
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-035"
assert proposal["proposal_count"] == 35
assert proposal["proposed_count"] == 35
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

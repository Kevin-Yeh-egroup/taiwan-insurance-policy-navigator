from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    SHINKONG_JINMANYI_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_shinkong_jinmanyi_variable_universal_life,
)
from validate_data import validate_plan_options  # noqa: E402


BATCH_ID = "tii-life-047"
PARSER_ID = "shinkong-jinmanyi-variable-universal-life-v1"
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-047-shinkong-jinmanyi-variable-universal-life-"
        "exact-source-matrix.json"
    )
)


def source_document(product_id: str) -> dict:
    version = SHINKONG_JINMANYI_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
        product_id
    ]
    return complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        DOCUMENT_ROOT / product_id / version["file_name"],
    )


versions = SHINKONG_JINMANYI_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 24
assert set(versions) == {
    f"208121M31A007{revision:02d}"
    for revision in range(24)
}
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 24
assert {
    version["source_text_extractor"]
    for version in versions.values()
} == {"pypdf"}

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == BATCH_ID
assert matrix["product_count"] == 24
assert matrix["status_counts"] == {"readable": 24}
assert matrix["duplicate_source_sha_groups"] == {}

semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_shinkong_jinmanyi_variable_universal_life(
        document
    )
    assert schedule is not None, product_id
    assert parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    ) == (PARSER_ID, schedule)
    assert parse_plan_table_with_parser(document) == (
        PARSER_ID,
        schedule,
    )
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["face_amount_label"] == "保險金額"
    assert not schedule.get("plan_options")
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_batch_id"] == BATCH_ID
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_extractor"] == "pypdf"
    assert characteristics["source_page_count"] == source_version[
        "page_count"
    ]
    assert characteristics["product_family"] == (
        "shinkong-jinmanyi-variable-universal-life"
    )
    assert characteristics["maturity_age"] == 100
    assert characteristics[
        "risk_amount_actual_age_threshold"
    ] == (14 if revision <= 12 else 15)
    assert characteristics["minor_risk_amount"] == (
        None if revision <= 12 else 0
    )
    assert characteristics["age15_recalculation_applies"] is (
        revision >= 13
    )
    assert characteristics[
        "minor_exclusion_account_value_return_clause"
    ] is (revision >= 14)
    assert characteristics["risk_coefficient_appendix"] == (
        4 if revision >= 22 else 5
    )
    assert characteristics[
        "death_requires_before_maturity"
    ] is (revision >= 13)
    assert characteristics[
        "total_disability_requires_before_maturity"
    ] is (revision >= 18)
    semantic_groups[characteristics["semantic_phase"]] += 1

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "total-disability-benefit",
    }
    assert {
        entry["unit_key"]
        for entry in entries.values()
    } == {
        "shinkong_jinmanyi_maturity_benefit",
        "shinkong_jinmanyi_death_benefit",
        "shinkong_jinmanyi_total_disability_benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "maturity_policy_account_value"
    )
    for entry_id in ("death-benefit", "total-disability-benefit"):
        assert entries[entry_id]["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        assert (
            "insured_age_at_event"
            in entries[entry_id]["policy_state_keys"]
        ) is (revision >= 13)
    assert entries["death-benefit"].get(
        "minor_account_value_return_age"
    ) == (15 if revision >= 13 else None)
    assert (
        "event_before_policy_maturity_status"
        in entries["death-benefit"]["policy_state_keys"]
    ) is (revision >= 13)
    assert (
        "event_before_policy_maturity_status"
        in entries["total-disability-benefit"]["policy_state_keys"]
    ) is (revision >= 18)
    minor_exclusion_condition = (
        "未滿十五足歲因條款除外責任死亡時，依身故條款返還保單帳戶價值。"
    )
    assert (
        minor_exclusion_condition
        in entries["death-benefit"]["conditions"]
    ) is (revision >= 14)

assert semantic_groups == Counter(
    {
        "age14-risk-threshold-appendix5": 13,
        "age15-minor-return-death-before-maturity-appendix5": 1,
        (
            "age15-minor-return-death-before-maturity-"
            "minor-exclusion-clause-appendix5"
        ): 4,
        (
            "age15-minor-return-all-events-before-maturity-"
            "minor-exclusion-clause-appendix5"
        ): 4,
        (
            "age15-minor-return-all-events-before-maturity-"
            "minor-exclusion-clause-appendix4"
        ): 2,
    }
)

reference = source_document("208121M31A00723")
tampered_sha = copy.deepcopy(reference)
tampered_sha["source_document_sha256"] = "0" * 64
assert (
    parse_shinkong_jinmanyi_variable_universal_life(tampered_sha)
    is None
)
tampered_text = copy.deepcopy(reference)
tampered_text["text"] += " altered"
assert (
    parse_shinkong_jinmanyi_variable_universal_life(tampered_text)
    is None
)
wrong_product = copy.deepcopy(reference)
wrong_product["product_id"] = "208121M31A00722"
assert (
    parse_shinkong_jinmanyi_variable_universal_life(wrong_product)
    is None
)

print(
    "TII Shinkong Jinmanyi variable universal life parser test "
    f"passed ({len(versions)} exact versions)"
)

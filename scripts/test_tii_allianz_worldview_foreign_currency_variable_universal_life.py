from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    ALLIANZ_WORLDVIEW_FOREIGN_CURRENCY_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    EXTRACTOR_VERSION,
    complete_strict_source_document,
    parse_allianz_worldview_foreign_currency_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options  # noqa: E402


BATCH_ID = "tii-life-095"
PARSER_ID = (
    "allianz-worldview-foreign-currency-variable-universal-life-v1"
)
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-095-allianz-worldview-foreign-currency-"
        "variable-universal-life-exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / (
        "tii-life-095-allianz-worldview-foreign-currency-"
        "variable-universal-life-v229.json"
    )
)


def source_document(product_id: str) -> dict:
    version = (
        ALLIANZ_WORLDVIEW_FOREIGN_CURRENCY_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
            product_id
        ]
    )
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


versions = (
    ALLIANZ_WORLDVIEW_FOREIGN_CURRENCY_VARIABLE_UNIVERSAL_LIFE_VERSIONS
)
assert EXTRACTOR_VERSION == "tii-plan-benefits-v230"
assert len(versions) == 26
assert set(versions) == {
    f"218141M31A011{revision:02d}"
    for revision in range(9, 35)
}
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 26

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == BATCH_ID
assert matrix["product_count"] == 26
assert matrix["status_counts"] == {"readable": 26}
assert matrix["duplicate_source_sha_groups"] == {}

schedules: dict[str, dict] = {}
semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = (
        parse_allianz_worldview_foreign_currency_variable_universal_life(
            document
        )
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

    expected_types = (
        ["甲型", "乙型", "丙型"]
        if revision <= 10
        else ["A型", "B型", "C型"]
        + (["D型"] if revision >= 12 else [])
    )
    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["face_amount_label"] == (
        "基本保險金額" if revision <= 10 else "保險金額"
    )
    assert schedule["plan_options"] == [
        {"value": value, "label": value}
        for value in expected_types
    ]

    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == BATCH_ID
    assert characteristics["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_extractor"] == "pypdf"
    assert characteristics["source_page_count"] == source_version[
        "page_count"
    ]
    assert characteristics["policy_type_options"] == expected_types
    assert set(characteristics["formula_by_type"]) == set(expected_types)
    assert characteristics["contract_currency_required"] is True
    assert (
        characteristics["contract_currency_code_format"]
        == "iso_4217_alpha3"
    )
    assert characteristics["same_currency_amount_inputs_required"] is True
    assert characteristics["money_decimal_places"] == 4
    assert characteristics["maturity_age"] == 111
    assert characteristics["threshold_factor_schedule"] == (
        []
        if revision <= 10
        else [
            {
                "min_age": 15 if revision >= 25 else 0,
                "max_age": 40,
                "factor": 1.3,
            },
            {"min_age": 41, "max_age": 70, "factor": 1.15},
            {"min_age": 71, "max_age": 130, "factor": 1.01},
        ]
    )
    assert characteristics[
        "minor_death_before_age_15_account_value_rule"
    ] is (revision >= 25)
    assert characteristics[
        "minor_disability_before_age_15_account_value_rule"
    ] is (revision >= 25)
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
    for entry in entries.values():
        assert entry["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        assert entry["currency_state_key"] == "contract_currency"
    assert entries["maturity-benefit"]["policy_state_keys"][0] == (
        "maturity_policy_account_value"
    )
    for entry_id in ("death-benefit", "total-disability-benefit"):
        assert entries[entry_id]["policy_state_keys"][0] == (
            "benefit_valuation_policy_account_value"
        )
        assert (
            entries[entry_id].get("minor_account_value_return_age")
            == 15
        ) is (revision >= 25)
        assert (
            "post_event_insurance_cost_refund_amount"
            in entries[entry_id]["policy_state_keys"]
        )
        assert (
            "post_event_insurance_cost_refund_status"
            in entries[entry_id]["policy_state_keys"]
        )
    schedules[product_id] = schedule

assert semantic_groups == Counter(
    {
        "legacy-annual-insurance-amount-abc": 2,
        "preservation-multiplier-abc": 1,
        "preservation-multiplier-abcd": 13,
        "preservation-multiplier-abcd-minor-account-value-return": 10,
    }
)

reference_id = "218141M31A01125"
reference = source_document(reference_id)
for corrupted in (
    {**reference, "batch_id": "tii-life-096"},
    {**reference, "product_id": "218141M31A01124"},
    {**reference, "file_name": "218141M31A01125-F.PDF"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": reference["page_count"] + 1},
    {**reference, "source_text_extractor": "other"},
):
    assert (
        parse_allianz_worldview_foreign_currency_variable_universal_life(
            corrupted
        )
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "安聯人壽世界觀外幣變額萬能壽險",
    "其他商品",
    1,
)
assert (
    parse_allianz_worldview_foreign_currency_variable_universal_life(
        corrupted_text
    )
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["proposal_count"] == 26
assert proposal["proposed_count"] == 26
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
            "semantic_groups": dict(semantic_groups),
            "proposed": proposal["proposed_count"],
            "promoted": proposal.get("promoted_count", 0),
        },
        ensure_ascii=False,
        indent=2,
    )
)

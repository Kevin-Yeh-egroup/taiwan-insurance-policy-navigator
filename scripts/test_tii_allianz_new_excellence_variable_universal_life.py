from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    ALLIANZ_NEW_EXCELLENCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    EXTRACTOR_VERSION,
    complete_strict_source_document,
    parse_allianz_new_excellence_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import (  # noqa: E402
    validate_allianz_new_excellence_variable_universal_life_contract,
    validate_plan_options,
)


BATCH_ID = "tii-life-095"
PARSER_ID = "allianz-new-excellence-variable-universal-life-v1"
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-095-allianz-new-excellence-variable-universal-life-"
        "exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / (
        "tii-life-095-allianz-new-excellence-variable-universal-life-"
        "v230.json"
    )
)


def source_document(product_id: str) -> dict:
    version = ALLIANZ_NEW_EXCELLENCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
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


versions = ALLIANZ_NEW_EXCELLENCE_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert EXTRACTOR_VERSION == "tii-plan-benefits-v230"
assert len(versions) == 26
assert set(versions) == {
    f"218141M31A014{revision:02d}"
    for revision in range(5, 31)
}
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 25
assert (
    versions["218141M31A01428"]["source_document_sha256"]
    == versions["218141M31A01429"]["source_document_sha256"]
)

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == BATCH_ID
assert matrix["product_count"] == 26
assert matrix["status_counts"] == {"readable": 26}
assert matrix["duplicate_source_sha_groups"] == {
    "0b7a2fe88fd227cb3f1d1204a9ba9a85feac46bcc6b0e1e4b80d8c2ff2d8f0e3": [
        "218141M31A01428",
        "218141M31A01429",
    ]
}

schedules: dict[str, dict] = {}
semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_allianz_new_excellence_variable_universal_life(
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
    validate_allianz_new_excellence_variable_universal_life_contract(
        {
            "product_id": product_id,
            "source_document_sha256": source_version[
                "source_document_sha256"
            ],
            **schedule,
        },
        schedule["version_characteristics"],
        f"{BATCH_ID}/{product_id}",
    )

    expected_types = (
        ["甲型", "乙型", "丙型"]
        if revision <= 6
        else ["A型", "B型", "C型"]
        + (["D型"] if revision >= 8 else [])
    )
    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["face_amount_label"] == (
        "基本保險金額" if revision <= 6 else "保險金額"
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
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["foreign_currency_policy"] is False
    assert characteristics["contract_currency_required"] is False
    assert characteristics["money_decimal_places"] == 0
    assert characteristics["money_rounding_rule_available"] is False
    assert characteristics[
        "fractional_formula_requires_insurer_confirmation"
    ] is True
    assert characteristics[
        "insurer_provided_twd_policy_account_value_required"
    ] is True
    assert characteristics["fund_unit_self_calculation_supported"] is False
    assert characteristics[
        "maturity_account_value_valuation_date_defined"
    ] is (revision >= 6)
    assert characteristics[
        "maturity_account_value_valuation_date_basis"
    ] == (
        "first_asset_valuation_date_of_policy_year"
        if revision >= 6
        else "not_explicit_in_terms_use_insurer_provided_value"
    )
    assert characteristics["policy_type_options"] == expected_types
    assert set(characteristics["formula_by_type"]) == set(expected_types)
    assert characteristics["maturity_age"] == 111
    assert characteristics["threshold_factor_schedule"] == (
        []
        if revision <= 6
        else [
            {
                "min_age": 15 if revision >= 20 else 0,
                "max_age": 40,
                "factor": 1.3,
            },
            {"min_age": 41, "max_age": 70, "factor": 1.15},
            {"min_age": 71, "max_age": 130, "factor": 1.01},
        ]
    )
    assert characteristics[
        "minor_death_before_age_15_account_value_rule"
    ] is (revision >= 20)
    assert characteristics[
        "minor_disability_before_age_15_account_value_rule"
    ] is (revision >= 20)
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
        assert "currency_state_key" not in entry
    assert entries["maturity-benefit"]["policy_state_keys"][0] == (
        "maturity_policy_account_value"
    )
    maturity_conditions = entries["maturity-benefit"]["conditions"]
    assert (
        "保單價值總額採該保單年度第一個資產評估日計算結果。"
        in maturity_conditions
    ) is (revision >= 6)
    assert (
        any("未明定祝壽帳戶價值的資產評估日" in item for item in maturity_conditions)
    ) is (revision == 5)
    for entry_id in ("death-benefit", "total-disability-benefit"):
        entry = entries[entry_id]
        assert entry["policy_state_keys"][0] == (
            "benefit_valuation_policy_account_value"
        )
        assert (
            entry.get("minor_account_value_return_age") == 15
        ) is (revision >= 20)
        assert (
            "post_event_insurance_cost_refund_status"
            in entry["policy_state_keys"]
        )
        assert (
            "post_event_insurance_cost_refund_amount"
            in entry["policy_state_keys"]
        )
        assert "claim_time_status" in entry["policy_state_keys"]
        assert "benefit_exclusion_status" in entry["policy_state_keys"]
    assert (
        "total_disability_qualification_status"
        in entries["total-disability-benefit"]["policy_state_keys"]
    )
    assert (
        "total_disability_qualification_status"
        not in entries["death-benefit"]["policy_state_keys"]
    )
    schedules[product_id] = schedule

assert semantic_groups == Counter(
    {
        "legacy-annual-insurance-amount-abc": 2,
        "preservation-multiplier-abc": 1,
        "preservation-multiplier-abcd": 12,
        "preservation-multiplier-abcd-minor-account-value-return": 11,
    }
)

reference = source_document("218141M31A01420")
for corrupted in (
    {**reference, "batch_id": "tii-life-096"},
    {**reference, "product_id": "218141M31A01421"},
    {**reference, "file_name": "218141M31A01420-F.PDF"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": reference["page_count"] + 1},
    {**reference, "source_text_extractor": "other"},
):
    assert (
        parse_allianz_new_excellence_variable_universal_life(
            corrupted
        )
        is None
    )
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "安聯人壽新卓越變額萬能壽險",
    "其他商品",
    1,
)
assert (
    parse_allianz_new_excellence_variable_universal_life(
        corrupted_text
    )
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["extractor_version"] == EXTRACTOR_VERSION
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

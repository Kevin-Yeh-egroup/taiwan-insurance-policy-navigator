from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_HENGFU_CURRENT_AMOUNT_PRODUCT_IDS,
    BNP_PARIBAS_HENGFU_FORMULA_PRODUCT_IDS,
    BNP_PARIBAS_HENGFU_MISSING_REFERENCED_APPENDIX_PRODUCT_IDS,
    BNP_PARIBAS_HENGFU_VARIABLE_LIFE_PRODUCT_IDS,
    BNP_PARIBAS_HENGFU_VARIABLE_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_bnp_paribas_hengfu_variable_life,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
TEXT_FIXTURE = json.loads(
    (ROOT / "work" / "tii-document-text" / "tii-life-173-text.json").read_text(
        encoding="utf-8"
    )
)["documents"]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-173"


def document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    fixture = next(
        item
        for item in TEXT_FIXTURE
        if item.get("product_id") == product_id and item.get("file_name") == file_name
    )
    return {**fixture, "batch_id": "tii-life-173"}


def completed_document(product_id: str) -> dict:
    source_document = document(product_id)
    source_path = (
        DOCUMENT_ROOT / product_id / source_document["file_name"]
    )
    return complete_strict_source_document(
        {
            **source_document,
            "source_document_sha256": sha256_file(source_path),
        },
        source_path,
    )


PRODUCT_IDS = [f"267191M31A003{version:02d}" for version in range(12)]
FORMULA_PRODUCT_IDS = set(PRODUCT_IDS[:4])
CURRENT_AMOUNT_PRODUCT_IDS = set(PRODUCT_IDS[4:])
MISSING_REFERENCED_APPENDIX_PRODUCT_IDS = {"267191M31A00303"}

assert BNP_PARIBAS_HENGFU_VARIABLE_LIFE_PRODUCT_IDS == set(PRODUCT_IDS)
assert BNP_PARIBAS_HENGFU_FORMULA_PRODUCT_IDS == FORMULA_PRODUCT_IDS
assert BNP_PARIBAS_HENGFU_CURRENT_AMOUNT_PRODUCT_IDS == CURRENT_AMOUNT_PRODUCT_IDS
assert (
    BNP_PARIBAS_HENGFU_MISSING_REFERENCED_APPENDIX_PRODUCT_IDS
    == MISSING_REFERENCED_APPENDIX_PRODUCT_IDS
)


for product_id in PRODUCT_IDS:
    source_document = completed_document(product_id)
    schedule = parse_bnp_paribas_hengfu_variable_life(source_document)
    if product_id in MISSING_REFERENCED_APPENDIX_PRODUCT_IDS:
        assert schedule is None
        continue
    assert schedule is not None, product_id
    validate_plan_options(schedule, f"tii-life-173/{product_id}")
    assert schedule["plan_options"] == [
        {"value": "甲型", "label": "甲型"},
        {"value": "乙型", "label": "乙型"},
    ]

    uses_current_amount = product_id in CURRENT_AMOUNT_PRODUCT_IDS
    modern_funeral_rule = product_id >= "267191M31A00308"
    assert schedule["selection_type"] == (
        "face_amount_plan" if uses_current_amount else "paid_premium_factor_plan"
    )
    assert schedule["input_mode"] == schedule["selection_type"]
    assert ("face_amount_label" in schedule) is uses_current_amount
    if uses_current_amount:
        assert schedule["face_amount_label"] == "事故時有效保險金額"

    characteristics = schedule["version_characteristics"]
    version = BNP_PARIBAS_HENGFU_VARIABLE_LIFE_VERSIONS[product_id]
    assert characteristics["source_batch_id"] == "tii-life-173"
    assert characteristics["source_product_id"] == product_id
    assert (
        characteristics["source_document_sha256"]
        == version["source_document_sha256"]
    )
    assert (
        characteristics["source_text_sha256"]
        == version["normalized_text_sha256"]
    )
    assert characteristics["source_page_count"] == version["page_count"]
    assert characteristics["source_text_quality"] == "verified_full_text"
    assert characteristics["product_family"] == (
        "bnp-paribas-hengfu-variable-life"
    )
    assert characteristics["company_group"] == "bnp_paribas_cardif_life"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["variable_life_policy"] is True
    assert characteristics["variable_universal_life_policy"] is False
    assert characteristics["policy_type_options"] == ["甲型", "乙型"]
    assert characteristics["insurance_amount_change_rules_present"] is (
        uses_current_amount
    )
    assert characteristics["insurance_amount_source"] == (
        "latest_policy_record_or_endorsement"
        if uses_current_amount
        else "paid_premium_formula"
    )
    assert characteristics["minor_account_value_return"] is False
    assert characteristics["account_value_return_on_time_bar"] is True
    assert characteristics["account_value_return_on_exclusion"] is True
    assert characteristics["insured_age_accuracy_status_required"] is True
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["funeral_limit_plan_options"] == (
        ["甲型", "乙型"] if modern_funeral_rule else ["乙型"]
    )

    if uses_current_amount:
        assert characteristics["version_group"] == (
            "current_effective_insurance_amount"
        )
        assert characteristics["required_policy_inputs"][:3] == [
            "current_effective_insurance_amount",
            "policy_type",
            "benefit_valuation_policy_account_value",
        ]
        assert characteristics["formula_by_type"] == {
            "甲型": "max(current_effective_insurance_amount, benefit_valuation_policy_account_value)",
            "乙型": "current_effective_insurance_amount + benefit_valuation_policy_account_value",
        }
        assert characteristics["specified_factor_unit_fixed"] is None
        assert (
            characteristics["age_based_minimum_rate_adjustment_applies"]
            is True
        )
        assert characteristics["age_based_minimum_rate_schedule"][0] == {
            "min_age": 15 if modern_funeral_rule else 0,
            "max_age": 40,
            "factor": 1.3,
        }
        expected_formula_basis = (
            "net_amount_at_risk_plus_policy_account_value"
        )
    else:
        assert characteristics["version_group"] == "paid_premium_formula"
        assert characteristics["required_policy_inputs"][:5] == [
            "policy_type",
            "paid_premium_total",
            "partial_termination_amount_total",
            "specified_percent_or_multiplier",
            "benefit_valuation_policy_account_value",
        ]
        assert characteristics["formula_by_type"] == {
            "甲型": "max((paid_premium_total - partial_termination_amount_total) * (specified_percent / 100), benefit_valuation_policy_account_value)",
            "乙型": "(paid_premium_total - partial_termination_amount_total) * (specified_percent / 100) + benefit_valuation_policy_account_value",
        }
        assert characteristics["specified_factor_unit_fixed"] == "percent"
        assert (
            characteristics["age_based_minimum_rate_adjustment_applies"]
            is False
        )
        expected_formula_basis = "paid_premium_factor_account_value_formula"

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert (
        entries["maturity-benefit"]["calculation_basis"]
        == "maturity_policy_account_value"
    )
    assert (
        entries["maturity-benefit"]["policy_state_keys"]
        == [
            "maturity_policy_account_value",
            "policy_effect_status_at_event",
        ]
    )
    assert (
        entries["death-or-funeral-benefit"]["calculation_basis"]
        == expected_formula_basis
    )
    assert (
        entries["death-or-funeral-benefit"]["funeral_limit_plan_options"]
        == characteristics["funeral_limit_plan_options"]
    )
    assert "death_benefit_status" in (
        entries["death-or-funeral-benefit"]["policy_state_keys"]
    )
    assert "insured_age_accuracy_status" in (
        entries["death-or-funeral-benefit"]["policy_state_keys"]
    )
    assert (
        entries["total-disability-benefit"]["calculation_basis"]
        == expected_formula_basis
    )
    assert "total_disability_qualification_status" in (
        entries["total-disability-benefit"]["policy_state_keys"]
    )
    assert all(
        entry.get("minor_account_value_return_age") is None
        for entry in entries.values()
    )


for product_id in [
    "267191M31A00300",
    "267191M31A00304",
    "267191M31A00311",
]:
    source_document = completed_document(product_id)
    schedule = parse_bnp_paribas_hengfu_variable_life(source_document)
    integrated = parse_plan_table_with_parser(source_document)
    assert integrated is not None
    assert integrated[0] == "bnp-paribas-hengfu-variable-life-v2"
    assert integrated[1] == schedule


assert (
    parse_bnp_paribas_hengfu_variable_life(
        completed_document("267191M31A00303")
    )
    is None
)
assert parse_bnp_paribas_hengfu_variable_life(document("267191M31A00300", "F")) is None
wrong_batch = completed_document("267191M31A00300")
wrong_batch["batch_id"] = "tii-life-172"
assert parse_bnp_paribas_hengfu_variable_life(wrong_batch) is None
wrong_hash = completed_document("267191M31A00300")
wrong_hash["source_document_sha256"] = "0" * 64
assert parse_bnp_paribas_hengfu_variable_life(wrong_hash) is None
for product_id in ["267191M31A00225", "267191M31A00400"]:
    assert parse_bnp_paribas_hengfu_variable_life(document(product_id)) is None

missing_formula = completed_document("267191M31A00300")
missing_formula["text"] = missing_formula["text"].replace(
    "要保人於要保書中所指定之百分比", "要保書另載"
)
assert parse_bnp_paribas_hengfu_variable_life(missing_formula) is None


print(
    {
        "status": "ok",
        "source_product_count": len(PRODUCT_IDS),
        "proposed_product_count": (
            len(PRODUCT_IDS)
            - len(MISSING_REFERENCED_APPENDIX_PRODUCT_IDS)
        ),
        "source_gap_count": len(MISSING_REFERENCED_APPENDIX_PRODUCT_IDS),
    }
)

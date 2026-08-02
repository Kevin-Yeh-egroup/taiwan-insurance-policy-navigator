from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_bnp_paribas_variable_life_net_risk_account_value,
    parse_bnp_paribas_variable_universal_life_net_risk_account_value,
    parse_plan_table_with_parser,
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


EXPECTED = {
    "267131MV1A02623A11C90000003": {
        "currency_basis": "twd",
        "disability_term": "殘廢",
        "minor_death": True,
        "redemption_fee_adjusts_account_value": False,
    },
    "267131MV1A02723Z11C90000005": {
        "currency_basis": "foreign_currency",
        "disability_term": "失能",
        "minor_death": True,
        "redemption_fee_adjusts_account_value": False,
    },
    "267131MV1A02723Z11C90000008": {
        "currency_basis": "foreign_currency",
        "disability_term": "失能",
        "minor_death": False,
        "redemption_fee_adjusts_account_value": False,
    },
    "267131MV1A07323A11Z90000001": {
        "currency_basis": "twd",
        "disability_term": "失能",
        "minor_death": True,
        "redemption_fee_adjusts_account_value": True,
    },
    "267141M31A02402": {
        "currency_basis": "twd",
        "disability_term": "殘廢",
        "minor_death": True,
        "redemption_fee_adjusts_account_value": False,
    },
}
VARIABLE_LIFE_EXPECTED = {
    "267131MV1A00423A11C90000019": {
        "currency_basis": "twd",
        "disability_term": "殘廢",
        "minor_rule": True,
    },
    "267131MV1A00623Z11C90000018": {
        "currency_basis": "foreign_currency",
        "disability_term": "殘廢",
        "minor_rule": True,
    },
    "267131MV1A00923A11C90000012": {
        "currency_basis": "twd",
        "disability_term": "失能",
        "minor_rule": False,
    },
    "267131MV1A01423Z11C90000012": {
        "currency_basis": "foreign_currency",
        "disability_term": "失能",
        "minor_rule": False,
    },
}


for product_id, expected in VARIABLE_LIFE_EXPECTED.items():
    source_document = document(product_id)
    schedule = parse_bnp_paribas_variable_life_net_risk_account_value(
        source_document
    )
    assert schedule is not None, product_id
    validate_plan_options(schedule, f"tii-life-173/{product_id}")
    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["plan_options"] == [
        {"value": "甲型", "label": "甲型"},
        {"value": "乙型", "label": "乙型"},
    ]

    characteristics = schedule["version_characteristics"]
    is_foreign_currency = expected["currency_basis"] == "foreign_currency"
    assert characteristics["currency_basis"] == expected["currency_basis"]
    assert characteristics["contract_currency_required"] is is_foreign_currency
    assert characteristics["disability_term"] == expected["disability_term"]
    assert (
        characteristics["minor_death_before_age_15_account_value_rule"]
        is expected["minor_rule"]
    )
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is expected["minor_rule"]
    )
    expected_inputs = [
        "basic_face_amount",
        "policy_type",
        "policy_account_value",
    ]
    if is_foreign_currency:
        expected_inputs.append("contract_currency")
    if expected["minor_rule"]:
        expected_inputs.append("insured_age_at_event")
    assert characteristics["required_policy_inputs"] == expected_inputs

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    for entry in entries.values():
        assert (
            entry.get("currency_state_key") == "contract_currency"
        ) is is_foreign_currency
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert entries["total-disability-benefit"]["calculation_basis"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert (
        entries["death-or-funeral-benefit"].get(
            "minor_account_value_return_age"
        )
        == 15
    ) is expected["minor_rule"]
    assert (
        entries["total-disability-benefit"].get(
            "minor_account_value_return_age"
        )
        == 15
    ) is expected["minor_rule"]


for product_id, expected in EXPECTED.items():
    source_document = document(product_id)
    schedule = parse_bnp_paribas_variable_universal_life_net_risk_account_value(
        source_document
    )
    assert schedule is not None, product_id
    validate_plan_options(schedule, f"tii-life-173/{product_id}")
    integrated = parse_plan_table_with_parser(source_document)
    assert integrated is not None
    assert integrated[0] == (
        "bnp-paribas-variable-universal-life-net-risk-account-value-v1"
    )
    assert integrated[1] == schedule

    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["selection_label"] == "基本保額與保險型態"
    assert schedule["plan_options"] == [
        {"value": "甲型", "label": "甲型"},
        {"value": "乙型", "label": "乙型"},
    ]

    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "bnp-paribas-variable-universal-life-net-risk-account-value"
    )
    assert characteristics["company_group"] == "bnp_paribas_cardif_life"
    assert characteristics["currency_basis"] == expected["currency_basis"]
    is_foreign_currency = expected["currency_basis"] == "foreign_currency"
    assert characteristics["contract_currency_required"] is is_foreign_currency
    assert characteristics["variable_universal_life_policy"] is True
    assert characteristics["policy_type_options"] == ["甲型", "乙型"]
    expected_inputs = [
        "basic_face_amount",
        "policy_type",
        "policy_account_value",
    ]
    if is_foreign_currency:
        expected_inputs.append("contract_currency")
    if expected["minor_death"]:
        expected_inputs.append("insured_age_at_event")
    assert characteristics["required_policy_inputs"] == expected_inputs
    assert characteristics["net_amount_at_risk_formula_by_type"] == {
        "甲型": "max(basic_face_amount - policy_account_value, 0)",
        "乙型": "basic_face_amount",
    }
    assert characteristics["death_benefit_formula"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["maturity_benefit_formula"] == (
        "policy_account_value_at_first_asset_valuation_date_after_maturity"
    )
    assert (
        characteristics["redemption_fee_adjusts_account_value"]
        is expected["redemption_fee_adjusts_account_value"]
    )
    assert characteristics["disability_term"] == expected["disability_term"]
    assert (
        characteristics["minor_death_before_age_15_account_value_rule"]
        is expected["minor_death"]
    )

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["calculation_basis"] == "account_value"
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert entries["death-or-funeral-benefit"]["unit_key"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert entries["total-disability-benefit"]["calculation_basis"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    for entry in entries.values():
        assert (
            entry.get("currency_state_key") == "contract_currency"
        ) is is_foreign_currency
    assert (
        entries["death-or-funeral-benefit"].get(
            "minor_account_value_return_age"
        )
        == 15
    ) is expected["minor_death"]

    source_path = DOCUMENT_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in source_document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = indexed_document["text"][:2000]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_bnp_paribas_variable_universal_life_net_risk_account_value(
            completed_document
        )
        == schedule
    )


assert (
    parse_bnp_paribas_variable_universal_life_net_risk_account_value(
        document("267131MV1A02623A11C90000003", "F")
    )
    is None
)
assert (
    parse_bnp_paribas_variable_universal_life_net_risk_account_value(
        document("267131MV1A00423A11C90000019")
    )
    is None
)
assert (
    parse_bnp_paribas_variable_life_net_risk_account_value(
        document("267131MV1A02623A11C90000003")
    )
    is None
)

print({"status": "ok", "product_count": len(EXPECTED)})

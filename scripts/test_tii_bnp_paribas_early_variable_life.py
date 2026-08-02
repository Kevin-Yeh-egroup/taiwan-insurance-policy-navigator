from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_EARLY_VARIABLE_LIFE_PRODUCT_IDS,
    BNP_PARIBAS_EARLY_VARIABLE_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_bnp_paribas_early_variable_life_paid_premium_factor,
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
        DOCUMENT_ROOT
        / product_id
        / source_document["file_name"]
    )
    return complete_strict_source_document(
        {
            **source_document,
            "source_document_sha256": sha256_file(source_path),
        },
        source_path,
    )


POSITIVE_PRODUCT_IDS = [
    *[
        f"267191M31A002{version:02d}"
        for version in range(26)
        if version != 3
    ],
    *[f"267191M31A004{version:02d}" for version in range(18)],
    *[f"267191M31A005{version:02d}" for version in range(17)],
    *[f"267191M31A006{version:02d}" for version in range(17)],
    *[f"267191M31A007{version:02d}" for version in range(6)],
]
REPRESENTATIVE_PRODUCT_IDS = [
    "267191M31A00225",
    "267191M31A00400",
    "267191M31A00417",
    "267191M31A00516",
    "267191M31A00705",
]
FOREIGN_CURRENCY_PRODUCT_IDS = {
    f"267191M31A006{version:02d}" for version in range(17)
}
MINOR_ACCOUNT_VALUE_RETURN_PRODUCT_IDS = {
    "267191M31A00225",
    *[f"267191M31A004{version:02d}" for version in range(12, 18)],
    *[f"267191M31A005{version:02d}" for version in range(11, 17)],
    *[f"267191M31A006{version:02d}" for version in range(11, 17)],
    *[f"267191M31A007{version:02d}" for version in range(6)],
}


for product_id in POSITIVE_PRODUCT_IDS:
    source_document = completed_document(product_id)
    schedule = parse_bnp_paribas_early_variable_life_paid_premium_factor(
        source_document
    )
    assert schedule is not None, product_id
    validate_plan_options(schedule, f"tii-life-173/{product_id}")

    assert schedule["selection_type"] == "paid_premium_factor_plan"
    assert schedule["input_mode"] == "paid_premium_factor_plan"
    assert schedule["plan_options"] == [
        {"value": "甲型", "label": "甲型"},
        {"value": "乙型", "label": "乙型"},
    ]

    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "bnp-paribas-early-variable-life-paid-premium-factor"
    )
    assert characteristics["source_batch_id"] == "tii-life-173"
    assert characteristics["source_product_id"] == product_id
    assert (
        characteristics["source_document_sha256"]
        == BNP_PARIBAS_EARLY_VARIABLE_LIFE_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert (
        characteristics["source_text_sha256"]
        == BNP_PARIBAS_EARLY_VARIABLE_LIFE_VERSIONS[
            product_id
        ]["normalized_text_sha256"]
    )
    assert characteristics["company_group"] == "bnp_paribas_cardif_life"
    assert characteristics["variable_life_policy"] is True
    assert characteristics["variable_universal_life_policy"] is False
    assert characteristics["policy_type_options"] == ["甲型", "乙型"]
    assert characteristics["formula_by_type"] == {
        "甲型": "max((paid_premium_total - partial_termination_amount_total) * specified_factor, benefit_valuation_policy_account_value)",
        "乙型": "(paid_premium_total - partial_termination_amount_total) * specified_factor + benefit_valuation_policy_account_value",
    }
    assert characteristics["required_policy_inputs"][:8] == [
        "policy_type",
        "paid_premium_total",
        "partial_termination_amount_total",
        "specified_percent_or_multiplier",
        "specified_factor_unit",
        "benefit_valuation_policy_account_value",
        "current_benefit_amount_status",
        "current_death_disability_benefit_amount",
    ]
    assert characteristics["specified_factor_unit_required"] is True
    assert characteristics["policy_effect_status_required"] is True
    assert characteristics["claim_time_status_required"] is True
    assert characteristics["benefit_exclusion_status_required"] is True
    assert (
        characteristics[
            "total_disability_qualification_status_required"
        ]
        is True
    )
    assert characteristics["insurance_amount_adjustment_applies"] is True
    is_foreign_currency = product_id in FOREIGN_CURRENCY_PRODUCT_IDS
    is_minor_account_value_return = (
        product_id in MINOR_ACCOUNT_VALUE_RETURN_PRODUCT_IDS
    )
    assert characteristics["foreign_currency_policy"] is is_foreign_currency
    assert characteristics["contract_currency_required"] is is_foreign_currency
    assert (
        "contract_currency" in characteristics["required_policy_inputs"]
    ) is is_foreign_currency
    assert (
        characteristics["minor_account_value_return"]
        is is_minor_account_value_return
    )
    assert (
        "insured_age_at_event" in characteristics["required_policy_inputs"]
    ) is is_minor_account_value_return

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
        entries["maturity-benefit"]["unit_key"]
        == "maturity_policy_account_value"
    )
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == (
        "paid_premium_factor_account_value_formula"
    )
    assert entries["total-disability-benefit"]["calculation_basis"] == (
        "paid_premium_factor_account_value_formula"
    )
    for entry in entries.values():
        assert (
            entry.get("currency_state_key") == "contract_currency"
        ) is is_foreign_currency
    for entry_id in ["death-or-funeral-benefit", "total-disability-benefit"]:
        assert "benefit_valuation_policy_account_value" in (
            entries[entry_id]["policy_state_keys"]
        )
        assert "current_benefit_amount_status" in (
            entries[entry_id]["policy_state_keys"]
        )
        assert (
            entries[entry_id].get("minor_account_value_return_age") == 15
        ) is is_minor_account_value_return

assert set(POSITIVE_PRODUCT_IDS) == set(
    BNP_PARIBAS_EARLY_VARIABLE_LIFE_PRODUCT_IDS
)


for product_id in REPRESENTATIVE_PRODUCT_IDS:
    source_document = completed_document(product_id)
    schedule = parse_bnp_paribas_early_variable_life_paid_premium_factor(
        source_document
    )
    integrated = parse_plan_table_with_parser(source_document)
    assert integrated is not None
    assert integrated[0] == "bnp-paribas-early-variable-life-paid-premium-factor-v2"
    assert integrated[1] == schedule

    source_path = DOCUMENT_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in source_document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = indexed_document["text"][:2000]
    recovered_document = complete_strict_source_document(
        indexed_document,
        source_path,
    )
    assert (
        parse_bnp_paribas_early_variable_life_paid_premium_factor(
            recovered_document
        )
        == schedule
    )


for product_id in [
    "267191M31A00300",
    "267191M31A00418",
    "267191M31A00617",
    "267191M31A00706",
    "267191M32A00100",
    "267131MV1A02623A11C90000003",
]:
    assert (
        parse_bnp_paribas_early_variable_life_paid_premium_factor(
            document(product_id)
        )
        is None
    ), product_id


print({"status": "ok", "product_count": len(POSITIVE_PRODUCT_IDS)})

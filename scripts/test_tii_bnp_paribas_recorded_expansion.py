from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS,
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_VERSIONS,
    BNP_PARIBAS_WEALTH_EXPERT_FOREIGN_VARIABLE_ANNUITY_VERSIONS,
    complete_strict_source_document,
    parse_bnp_paribas_legacy_recorded_variable_life,
    parse_plan_table_with_parser,
    parse_variable_annuity_account_value_formula,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-173"
TEXT_PATH = ROOT / "work" / "tii-document-text" / f"{BATCH_ID}-text.json"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
LIFE_PARSER_ID = "bnp-paribas-legacy-recorded-variable-life-v1"
ANNUITY_PARSER_ID = "variable-annuity-account-value-formula-v1"
EXPANSION_PREFIXES = {
    "267191M31A008": 5,
    "267191M31A010": 5,
    "267191M31A013": 4,
    "267191M31A015": 4,
    "267191M31A016": 4,
    "267191M31A017": 5,
    "267191M31A018": 5,
}
EXPANSION_LIFE_IDS = {
    f"{prefix}{revision:02d}"
    for prefix, revision_count in EXPANSION_PREFIXES.items()
    for revision in range(revision_count)
}
ANNUITY_ID = "267191M31A01504"


payload = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
source_documents = {
    document["product_id"]: document
    for document in payload["documents"]
    if (
        document.get("product_id") in EXPANSION_LIFE_IDS | {ANNUITY_ID}
        and str(document.get("file_name") or "").lower()
        == f"{str(document.get('product_id') or '').lower()}-a.pdf"
    )
}
assert set(source_documents) == EXPANSION_LIFE_IDS | {ANNUITY_ID}
assert EXPANSION_LIFE_IDS.issubset(
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS
)
assert ANNUITY_ID not in BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS


def completed_document(product_id: str) -> dict:
    source = source_documents[product_id]
    source_path = DOCUMENTS_DIR / product_id / source["file_name"]
    document = {
        **source,
        "batch_id": BATCH_ID,
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


for product_id in sorted(EXPANSION_LIFE_IDS):
    document = completed_document(product_id)
    version_contract = (
        BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_VERSIONS[product_id]
    )
    schedule = parse_bnp_paribas_legacy_recorded_variable_life(document)
    assert schedule is not None, product_id
    assert parse_plan_table_with_parser(
        document,
        parser_id_filter=LIFE_PARSER_ID,
    ) == (LIFE_PARSER_ID, schedule)
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert (
        version["source_document_sha256"]
        == version_contract["source_document_sha256"]
    )
    assert (
        version["source_text_sha256"]
        == version_contract["normalized_text_sha256"]
    )
    assert version["source_text_extractor"] == "pypdf"
    assert version["source_page_count"] == version_contract["page_count"]
    assert version["input_formula_variant"] == "paid_premium_factor"
    assert version["specified_factor_unit_required"] is True
    assert version["maturity_trigger"] == "age_110_policy_anniversary"
    assert version["policy_type_options"] == ["甲型", "乙型"]
    assert version["currency_basis"] == (
        "foreign_currency"
        if product_id[:-2] in {
            "267191M31A013",
            "267191M31A016",
            "267191M31A018",
        }
        else "twd"
    )

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert (
        entries["death-or-funeral-benefit"][
            "minor_account_value_return_age"
        ]
        == 15
    )
    assert (
        entries["death-or-funeral-benefit"][
            "funeral_limit_plan_options"
        ]
        == ["甲型", "乙型"]
    )
    assert entries["death-or-funeral-benefit"]["policy_state_keys"] == [
        "benefit_valuation_policy_account_value",
        "policy_effect_status_at_event",
        "policy_loan_and_interest_amount",
        "unpaid_policy_charge_amount",
        "claim_time_status",
        "benefit_exclusion_status",
        "death_benefit_status",
        "remaining_funeral_benefit_limit",
        "funeral_excess_insurance_cost_refund_status",
        "funeral_excess_insurance_cost_refund_amount",
        *(
            ["remittance_fee_amount"]
            if version["currency_basis"] == "foreign_currency"
            else []
        ),
    ]
    assert entries["total-disability-benefit"]["policy_state_keys"] == [
        "benefit_valuation_policy_account_value",
        "policy_effect_status_at_event",
        "policy_loan_and_interest_amount",
        "unpaid_policy_charge_amount",
        "claim_time_status",
        "benefit_exclusion_status",
        "total_disability_qualification_status",
        *(
            ["remittance_fee_amount"]
            if version["currency_basis"] == "foreign_currency"
            else []
        ),
    ]


base_document = completed_document("267191M31A00800")
for mutation in [
    {"batch_id": "tii-life-172"},
    {"product_id": "267191M31A00899"},
    {"file_name": "wrong.pdf"},
    {"document_type": "product_summary"},
    {"source_document_sha256": "0" * 64},
    {"source_text_extractor": "pymupdf"},
    {"page_count": 99},
    {"text": f"{base_document['text']} wrong"},
]:
    invalid = copy.deepcopy(base_document)
    invalid.update(mutation)
    assert parse_bnp_paribas_legacy_recorded_variable_life(invalid) is None


annuity_document = completed_document(ANNUITY_ID)
annuity_contract = (
    BNP_PARIBAS_WEALTH_EXPERT_FOREIGN_VARIABLE_ANNUITY_VERSIONS[ANNUITY_ID]
)
annuity_schedule = parse_variable_annuity_account_value_formula(
    annuity_document
)
assert annuity_schedule is not None
assert parse_plan_table_with_parser(
    annuity_document,
    parser_id_filter=ANNUITY_PARSER_ID,
) == (ANNUITY_PARSER_ID, annuity_schedule)
validate_plan_options(annuity_schedule, f"{BATCH_ID}/{ANNUITY_ID}")
annuity_version = annuity_schedule["version_characteristics"]
for field in [
    "source_document_sha256",
    "source_text_sha256",
    "source_text_extractor",
    "source_page_count",
    "product_family_key",
    "terms_revision",
]:
    assert annuity_version[field] == annuity_contract[field]
assert annuity_version["source_product_id"] == ANNUITY_ID
assert annuity_version["source_batch_id"] == BATCH_ID
assert annuity_version["annuity_policy"] is True
assert annuity_version["currency_basis"] == "foreign_currency"
assert annuity_version["company_group"] == "bnp_paribas_cardif_life"
assert annuity_version["payment_frequency_options"] == ["annual"]
assert annuity_version["guarantee_period_options_years"] == [10, 15, 20]
assert annuity_version["minimum_accumulation_period_years"] == 10
assert annuity_version["minimum_annual_annuity_amount"] == 5_000
assert annuity_version["maximum_annual_annuity_amount"] == 1_200_000
assert annuity_version["annuity_payment_quote_required"] is True
assert annuity_version["annual_annuity_adjustment_formula"] == (
    "(1 + prior_anniversary_declared_rate) / (1 + assumed_interest_rate)"
)
assert annuity_version["default_annuity_start_age"] == 70
assert annuity_version["max_annuity_start_age"] == 80
assert annuity_version["max_annuity_payment_age"] == 110
assert annuity_version["account_value_full_withdrawal_at_annuity_start"] is True
assert annuity_version["non_participating_policy"] is True

annuity_entries = {
    entry["id"]: entry for entry in annuity_schedule["coverage_entries"]
}
assert set(annuity_entries) == {
    "annuity-payment",
    "account-value-return-before-annuity-start",
    "unpaid-annuity-balance",
    "full-account-value-withdrawal-at-annuity-start",
    "excess-account-value-return-at-annuity-start",
}
assert (
    annuity_entries["annuity-payment"]["calculation_basis"]
    == "annuity_amount_or_lump_sum"
)
assert annuity_entries["annuity-payment"]["policy_state_keys"] == [
    "annuity_payment_amount",
    "annuity_start_policy_account_value",
]
assert (
    annuity_entries["annuity-payment"]["minimum_annual_annuity_amount"]
    == 5_000
)
assert (
    annuity_entries["annuity-payment"]["maximum_annual_annuity_amount"]
    == 1_200_000
)
assert (
    annuity_entries["unpaid-annuity-balance"]["calculation_basis"]
    == "policy_state_amount"
)
assert (
    annuity_entries["full-account-value-withdrawal-at-annuity-start"][
        "calculation_basis"
    ]
    == "policy_state_amount"
)
assert (
    annuity_entries["excess-account-value-return-at-annuity-start"][
        "calculation_basis"
    ]
    == "policy_state_amount"
)

for mutation in [
    {"batch_id": "tii-life-172"},
    {"file_name": "wrong.pdf"},
    {"source_document_sha256": "0" * 64},
    {"source_text_extractor": "pymupdf"},
    {"page_count": 99},
    {"text": f"{annuity_document['text']} wrong"},
]:
    invalid = copy.deepcopy(annuity_document)
    invalid.update(mutation)
    assert parse_variable_annuity_account_value_formula(invalid) is None


print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "life_product_count": len(EXPANSION_LIFE_IDS),
        "annuity_product_count": 1,
        "exact_source_product_count": len(EXPANSION_LIFE_IDS) + 1,
    }
)

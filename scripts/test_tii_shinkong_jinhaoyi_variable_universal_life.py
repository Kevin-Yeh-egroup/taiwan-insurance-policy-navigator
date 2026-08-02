from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    SHINKONG_JINHAOYI_VARIABLE_UNIVERSAL_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_shinkong_jinhaoyi_variable_universal_life,
)
from validate_data import validate_plan_options  # noqa: E402


BATCH_ID = "tii-life-047"
PARSER_ID = "shinkong-jinhaoyi-variable-universal-life-v1"
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-047-shinkong-jinhaoyi-variable-universal-life-"
        "exact-source-matrix.json"
    )
)


def source_document(product_id: str) -> dict:
    version = SHINKONG_JINHAOYI_VARIABLE_UNIVERSAL_LIFE_VERSIONS[
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


versions = SHINKONG_JINHAOYI_VARIABLE_UNIVERSAL_LIFE_VERSIONS
assert len(versions) == 25
assert set(versions) == {
    f"208121M31A006{revision:02d}"
    for revision in range(25)
}
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 25

matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["batch_id"] == BATCH_ID
assert matrix["product_count"] == 25
assert matrix["status_counts"] == {"readable": 25}
assert matrix["duplicate_source_sha_groups"] == {}

semantic_groups: Counter[str] = Counter()
for product_id, source_version in sorted(versions.items()):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_shinkong_jinhaoyi_variable_universal_life(
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
    assert characteristics["source_text_extractor"] == source_version[
        "source_text_extractor"
    ]
    assert characteristics["source_page_count"] == source_version[
        "page_count"
    ]
    assert characteristics["maturity_age"] == 100
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["money_decimal_places"] == 0
    assert characteristics[
        "fractional_formula_requires_insurer_confirmation"
    ] is True
    assert characteristics[
        "risk_amount_actual_age_threshold"
    ] == (14 if revision <= 13 else 15)
    assert characteristics["minor_risk_amount"] == (
        None if revision <= 13 else 0
    )
    assert characteristics["age15_recalculation_applies"] is (
        revision >= 14
    )
    assert characteristics["risk_coefficient_appendix"] == (
        4 if revision >= 23 else 5
    )
    assert characteristics[
        "insured_age_error_adjustment_applies"
    ] is True
    assert characteristics[
        "death_requires_before_maturity"
    ] is (revision >= 14)
    assert characteristics[
        "total_disability_requires_before_maturity"
    ] is (revision >= 19)
    assert characteristics[
        "funeral_excess_insurance_cost_refund_applies"
    ] is True
    assert characteristics["risk_coefficient_schedule"] == [
        {
            "min_insurance_age": 14,
            "max_insurance_age": 40,
            "factor": 0.3,
        },
        {
            "min_insurance_age": 41,
            "max_insurance_age": 70,
            "factor": 0.15,
        },
        {
            "min_insurance_age": 71,
            "max_insurance_age": 130,
            "factor": 0.01,
        },
    ]
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
    assert entries["maturity-benefit"]["calculation_basis"] == (
        "maturity_policy_account_value"
    )
    assert entries["maturity-benefit"]["policy_state_keys"] == [
        "maturity_policy_account_value",
        "policy_effect_status_at_event",
        "policy_loan_and_interest_amount",
        "unpaid_policy_charge_amount",
    ]
    for entry_id in ("death-benefit", "total-disability-benefit"):
        entry = entries[entry_id]
        assert entry["calculation_basis"] == (
            "net_amount_at_risk_plus_policy_account_value"
        )
        for required_key in (
            "benefit_valuation_policy_account_value",
            "risk_amount_source",
            "risk_calculation_actual_age",
            "risk_calculation_insurance_age",
            "insured_age_accuracy_status",
            "risk_calculation_stage",
            "risk_calculation_policy_account_value",
            "risk_calculation_net_premium_amount",
            "risk_amount_effective_status",
            "insurer_confirmed_current_risk_amount",
            "policy_effect_status_at_event",
            "policy_loan_and_interest_amount",
            "unpaid_policy_charge_amount",
            "claim_time_status",
            "benefit_exclusion_status",
            "post_event_insurance_cost_refund_status",
            "post_event_insurance_cost_refund_amount",
        ):
            assert required_key in entry["policy_state_keys"]
        assert (
            "insured_age_at_event" in entry["policy_state_keys"]
        ) is (revision >= 14)
    assert (
        entries["death-benefit"].get(
            "minor_account_value_return_age"
        )
        == (15 if revision >= 14 else None)
    )
    assert "death_benefit_status" in entries[
        "death-benefit"
    ]["policy_state_keys"]
    assert "remaining_funeral_benefit_limit" in entries[
        "death-benefit"
    ]["policy_state_keys"]
    assert "funeral_excess_insurance_cost_refund_status" in entries[
        "death-benefit"
    ]["policy_state_keys"]
    assert "funeral_excess_insurance_cost_refund_amount" in entries[
        "death-benefit"
    ]["policy_state_keys"]
    assert (
        "event_before_policy_maturity_status"
        in entries["death-benefit"]["policy_state_keys"]
    ) is (revision >= 14)
    assert (
        "event_before_policy_maturity_status"
        in entries["total-disability-benefit"]["policy_state_keys"]
    ) is (revision >= 19)
    assert "total_disability_qualification_status" in entries[
        "total-disability-benefit"
    ]["policy_state_keys"]

assert semantic_groups == Counter(
    {
        "age14-risk-threshold-appendix5": 14,
        "age15-minor-return-death-before-maturity-appendix5": 5,
        "age15-minor-return-all-events-before-maturity-appendix5": 4,
        "age15-minor-return-all-events-before-maturity-appendix4": 2,
    }
)
assert versions["208121M31A00603"]["source_text_extractor"] == (
    "pymupdf"
)
assert source_document("208121M31A00603")[
    "source_text_extractor"
] == "pymupdf"

reference = source_document("208121M31A00623")
tampered_sha = copy.deepcopy(reference)
tampered_sha["source_document_sha256"] = "0" * 64
assert (
    parse_shinkong_jinhaoyi_variable_universal_life(tampered_sha)
    is None
)
tampered_text = copy.deepcopy(reference)
tampered_text["text"] += " altered"
assert (
    parse_shinkong_jinhaoyi_variable_universal_life(tampered_text)
    is None
)
wrong_product = copy.deepcopy(reference)
wrong_product["product_id"] = "208121M31A00622"
assert (
    parse_shinkong_jinhaoyi_variable_universal_life(wrong_product)
    is None
)

print(
    "TII Shinkong Jinhaoyi variable universal life parser test "
    f"passed ({len(versions)} exact versions)"
)

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_QIKAIDESHENG_VARIABLE_LIFE_PRODUCT_IDS,
    BNP_PARIBAS_QIKAIDESHENG_VARIABLE_LIFE_REVISIONS,
    parse_bnp_paribas_qikaidesheng_variable_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
TEXT_PATH = ROOT / "work" / "tii-document-text" / "tii-life-173-text.json"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-173-bnp-qikaidesheng-three-way-v211.json"
)
PARSER_ID = "bnp-paribas-qikaidesheng-three-way-variable-life-v1"
EXPECTED_SOURCE_IDS = BNP_PARIBAS_QIKAIDESHENG_VARIABLE_LIFE_PRODUCT_IDS
VALUE_ADDITION_INPUTS = [
    "target_premium_cumulative_count",
    "target_premium_new_count",
    "cumulative_paid_target_premium_total",
    "value_addition_qualification_status",
]


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/tii-life-173/qikaidesheng")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Qikaidesheng schedule"
        )


payload = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
policy_terms = {
    document["product_id"]: document
    for document in payload["documents"]
    if document["product_id"] in EXPECTED_SOURCE_IDS
    and document["file_name"].lower()
    == f"{document['product_id'].lower()}-a.pdf"
}
assert set(policy_terms) == EXPECTED_SOURCE_IDS

schedules: dict[str, dict] = {}
for product_id in sorted(EXPECTED_SOURCE_IDS):
    revision = BNP_PARIBAS_QIKAIDESHENG_VARIABLE_LIFE_REVISIONS[product_id]
    document = {**policy_terms[product_id], "batch_id": "tii-life-173"}
    schedule = parse_bnp_paribas_qikaidesheng_variable_life(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-173/{product_id}")

    legacy_formula = revision <= 4
    version = schedule["version_characteristics"]
    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    assert version["source_product_id"] == product_id
    assert version["terms_revision"] == (
        "original" if revision == 0 else f"partial_change_{revision}"
    )
    assert version["insurance_type"] == "丙型"
    assert version["current_policy_amount_required"] is legacy_formula
    assert version["threshold_face_amount_required"] is not legacy_formula
    assert version["threshold_face_amount_must_be_user_entered"] is (
        not legacy_formula
    )
    assert version["maturity_interest_crediting"] is False
    assert version["insured_age_at_event_required"] is False
    assert version["disability_term"] == "殘廢"
    assert version["amount_multiplier_age_bands"] == [
        {"age_range": "18-40", "multiplier_percent": 130},
        {"age_range": "41-70", "multiplier_percent": 115},
        {"age_range": "71歲以上", "multiplier_percent": 101},
    ]
    assert version["value_addition_rate_bands"] == [
        {"count_range": "1-24", "rate_percent": 0},
        {"count_range": "25-60", "rate_percent": 10},
        {"count_range": "61-72", "rate_percent": 15},
        {"count_range": "73-84", "rate_percent": 30},
        {"count_range": "85+", "rate_percent": 0},
    ]
    assert version["value_addition_required_inputs"] == VALUE_ADDITION_INPUTS
    assert (
        version[
            "value_addition_already_reflected_in_account_value_after_credit"
        ]
        is True
    )

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "value-added-benefit",
    }
    expected_death_keys = (
        [
            "current_policy_amount",
            "basic_face_amount",
            "benefit_valuation_policy_account_value",
        ]
        if legacy_formula
        else [
            "basic_face_amount",
            "current_threshold_face_amount",
            "benefit_valuation_policy_account_value",
        ]
    )
    assert (
        entries["death-or-funeral-benefit"]["policy_state_keys"]
        == expected_death_keys
    )
    assert (
        entries["total-disability-benefit"]["policy_state_keys"]
        == expected_death_keys
    )
    assert entries["maturity-benefit"]["policy_state_keys"] == [
        "maturity_policy_account_value"
    ]
    value_addition = entries["value-added-benefit"]
    assert (
        value_addition["calculation_basis"]
        == "target_premium_count_value_addition"
    )
    assert value_addition["policy_state_keys"] == VALUE_ADDITION_INPUTS
    assert value_addition["amount_role"] == "reference"
    schedules[product_id] = schedule

product_summary = next(
    document
    for document in payload["documents"]
    if document["product_id"] == "267141M31A02000"
    and document["file_name"].endswith("-F.pdf")
)
assert (
    parse_bnp_paribas_qikaidesheng_variable_life(
        {**product_summary, "batch_id": "tii-life-173"}
    )
    is None
)
assert (
    parse_bnp_paribas_qikaidesheng_variable_life(
        {
            **policy_terms["267141M31A02000"],
            "batch_id": "tii-life-172",
        }
    )
    is None
)
assert (
    parse_bnp_paribas_qikaidesheng_variable_life(
        {
            **policy_terms["267141M31A02000"],
            "batch_id": "tii-life-173",
            "text": policy_terms["267141M31A02000"]["text"].replace(
                "期開得勝",
                "其他商品",
            ),
        }
    )
    is None
)
assert (
    parse_bnp_paribas_qikaidesheng_variable_life(
        {
            **policy_terms["267141M31A02005"],
            "batch_id": "tii-life-173",
            "text": policy_terms["267141M31A02005"]["text"].replace(
                "第 73 次-第 84 次 30%",
                "第 73 次-第 84 次 20%",
            ),
        }
    )
    is None
)

wrong_formula = copy.deepcopy(schedules["267141M31A02005"])
wrong_formula["version_characteristics"]["death_benefit_formula"] = (
    "max(current_policy_amount,basic_face_amount,"
    "benefit_valuation_policy_account_value)"
)
assert_invalid_schedule(wrong_formula, "version formula is invalid")

missing_value_addition_input = copy.deepcopy(schedules["267141M31A02000"])
missing_value_addition_input["version_characteristics"][
    "required_policy_inputs"
].remove("target_premium_new_count")
assert_invalid_schedule(
    missing_value_addition_input,
    "required inputs are invalid",
)

wrong_value_addition_contract = copy.deepcopy(
    schedules["267141M31A02000"]
)
next(
    entry
    for entry in wrong_value_addition_contract["coverage_entries"]
    if entry["id"] == "value-added-benefit"
)["unit_key"] = "wrong_value_addition_formula"
assert_invalid_schedule(
    wrong_value_addition_contract,
    "exact entry contract is invalid",
)

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == "tii-life-173"
assert proposal_payload["proposal_count"] == len(EXPECTED_SOURCE_IDS)
for proposal in proposal_payload["proposals"]:
    product_id = proposal["product_id"]
    assert product_id in EXPECTED_SOURCE_IDS
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_file"].lower() == f"{product_id.lower()}-a.pdf"
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-173",
        "product_count": len(schedules),
        "version_range": [0, 6],
    }
)

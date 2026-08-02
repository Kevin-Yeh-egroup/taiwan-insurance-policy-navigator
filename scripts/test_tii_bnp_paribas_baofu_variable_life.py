from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_BAOFU_VARIABLE_LIFE_PRODUCT_IDS,
    parse_bnp_paribas_baofu_variable_life,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
TEXT_PATH = ROOT / "work" / "tii-document-text" / "tii-life-173-text.json"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-173-bnp-baofu-variable-life-v207.json"
)
assert "267191M32A00110" not in BNP_PARIBAS_BAOFU_VARIABLE_LIFE_PRODUCT_IDS
EXPECTED_SOURCE_IDS = BNP_PARIBAS_BAOFU_VARIABLE_LIFE_PRODUCT_IDS


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/tii-life-173/baofu")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("formal validator accepted an invalid Baofu schedule")


payload = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
policy_terms = {
    document["product_id"]: document
    for document in payload["documents"]
    if document["product_id"] in BNP_PARIBAS_BAOFU_VARIABLE_LIFE_PRODUCT_IDS
    and document["file_name"].lower()
    == f"{document['product_id'].lower()}-a.pdf"
}
assert set(policy_terms) == EXPECTED_SOURCE_IDS

schedules = {}
for product_id in sorted(EXPECTED_SOURCE_IDS):
    schedule = parse_bnp_paribas_baofu_variable_life(
        {
            **policy_terms[product_id],
            "batch_id": "tii-life-173",
        }
    )
    assert schedule is not None, product_id
    validate_plan_options(schedule, f"tii-life-173/{product_id}")
    assert schedule["selection_type"] == "policy_state"
    assert schedule["version_characteristics"]["required_policy_inputs"] == [
        "maturity_policy_account_value",
        "policy_value_component",
        "general_death_disability_insurance_amount",
        "accidental_death_disability_insurance_amount",
        "policy_values_converted_to_twd",
    ]
    assert len(schedule["coverage_entries"]) == 5
    schedules[product_id] = schedule

product_summary = next(
    document
    for document in payload["documents"]
    if document["product_id"] == "267191M32A00100"
    and document["file_name"].endswith("-F.pdf")
)
assert (
    parse_bnp_paribas_baofu_variable_life(
        {
            **product_summary,
            "batch_id": "tii-life-173",
        }
    )
    is None
)

wrong_batch = {
    **policy_terms["267191M32A00100"],
    "batch_id": "tii-life-172",
}
assert parse_bnp_paribas_baofu_variable_life(wrong_batch) is None

missing_input = copy.deepcopy(schedules["267191M32A00100"])
missing_input["version_characteristics"]["required_policy_inputs"].pop()
assert_invalid_schedule(missing_input, "Baofu required inputs are invalid")

wrong_formula = copy.deepcopy(schedules["267191M32A00100"])
wrong_formula["coverage_entries"][2][
    "calculation_basis"
] = "policy_value_plus_general_insurance_amount"
assert_invalid_schedule(wrong_formula, "exact entry contract is invalid")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == "tii-life-173"
assert proposal_payload["proposal_count"] == len(EXPECTED_SOURCE_IDS)
assert len(proposal_payload["proposals"]) == len(EXPECTED_SOURCE_IDS)
for proposal in proposal_payload["proposals"]:
    product_id = proposal["product_id"]
    assert product_id in EXPECTED_SOURCE_IDS
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    assert candidate["parser_id"] == "bnp-paribas-baofu-variable-life-v1"
    assert candidate["source_file"].lower() == f"{product_id.lower()}-a.pdf"
    assert candidate["schedule"] == schedules[product_id]
    validate_plan_options(candidate["schedule"], f"proposal/tii-life-173/{product_id}")

print(
    {
        "status": "ok",
        "batch_id": "tii-life-173",
        "product_count": len(schedules),
        "source_pending_product_ids": ["267191M32A00110"],
    }
)

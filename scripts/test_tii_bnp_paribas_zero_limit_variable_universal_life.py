from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_ZERO_LIMIT_VARIABLE_UNIVERSAL_LIFE_PRODUCT_IDS,
    BNP_PARIBAS_ZERO_LIMIT_VARIABLE_UNIVERSAL_LIFE_REVISIONS,
    parse_bnp_paribas_zero_limit_variable_universal_life,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
TEXT_PATH = ROOT / "work" / "tii-document-text" / "tii-life-173-text.json"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-173-bnp-zero-limit-variable-universal-life-v208.json"
)
PARSER_ID = "bnp-paribas-zero-limit-variable-universal-life-v1"
EXPECTED_SOURCE_IDS = (
    BNP_PARIBAS_ZERO_LIMIT_VARIABLE_UNIVERSAL_LIFE_PRODUCT_IDS
)


def revision_for(product_id: str) -> int:
    return BNP_PARIBAS_ZERO_LIMIT_VARIABLE_UNIVERSAL_LIFE_REVISIONS[
        product_id
    ]


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/tii-life-173/zero-limit")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid zero-limit schedule"
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

schedules = {}
for product_id in sorted(EXPECTED_SOURCE_IDS):
    revision = revision_for(product_id)
    document = {
        **policy_terms[product_id],
        "batch_id": "tii-life-173",
    }
    schedule = parse_bnp_paribas_zero_limit_variable_universal_life(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-173/{product_id}")

    assert schedule["selection_type"] == "policy_state"
    assert schedule["input_mode"] == "policy_state"
    assert schedule.get("plan_options") in (None, [])
    version = schedule["version_characteristics"]
    assert version["terms_revision"] == (
        "original" if revision == 0 else f"partial_change_{revision}"
    )
    assert version["source_product_id"] == product_id
    assert version["insurance_type"] == "丙型"
    assert version["maturity_interest_crediting"] is (revision >= 10)
    assert version["insured_age_at_event_required"] is (revision <= 8)
    assert version["disability_term"] == (
        "殘廢" if revision <= 5 else "失能"
    )
    assert version["threshold_face_amount_required"] is (revision > 0)
    assert version["current_policy_amount_required"] is (revision == 0)

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    expected_death_keys = (
        [
            "current_policy_amount",
            "basic_face_amount",
            "benefit_valuation_policy_account_value",
        ]
        if revision == 0
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
    assert entries["death-or-funeral-benefit"].get(
        "minor_account_value_return_age"
    ) == (15 if revision <= 8 else None)
    assert entries["maturity-benefit"]["policy_state_keys"] == (
        ["maturity_policy_account_value", "maturity_interest_amount"]
        if revision >= 10
        else ["maturity_policy_account_value"]
    )
    schedules[product_id] = schedule

product_summary = next(
    document
    for document in payload["documents"]
    if document["product_id"] == "267141M31A03800"
    and document["file_name"].endswith("-F.pdf")
)
assert (
    parse_bnp_paribas_zero_limit_variable_universal_life(
        {**product_summary, "batch_id": "tii-life-173"}
    )
    is None
)
assert (
    parse_bnp_paribas_zero_limit_variable_universal_life(
        {
            **policy_terms["267141M31A03800"],
            "batch_id": "tii-life-172",
        }
    )
    is None
)
assert (
    parse_bnp_paribas_zero_limit_variable_universal_life(
        {
            **policy_terms["267141M31A03801"],
            "batch_id": "tii-life-173",
            "text": policy_terms["267141M31A03801"]["text"].replace(
                "門檻保額",
                "其他金額",
            ),
        }
    )
    is None
)

missing_threshold_key = copy.deepcopy(schedules["267141M31A03801"])
missing_threshold_key["coverage_entries"][1]["policy_state_keys"].remove(
    "current_threshold_face_amount"
)
assert_invalid_schedule(
    missing_threshold_key,
    "exact entry contract is invalid",
)

wrong_maturity_input = copy.deepcopy(
    schedules["267131MV1A03823A11C90000013"]
)
wrong_maturity_input["coverage_entries"][0]["policy_state_keys"] = [
    "maturity_policy_account_value",
    "basic_face_amount",
]
assert_invalid_schedule(
    wrong_maturity_input,
    "exact entry contract is invalid",
)

wrong_product_revision = copy.deepcopy(schedules["267141M31A03800"])
wrong_product_revision["version_characteristics"][
    "source_product_id"
] = "267131MV1A03823A11C90000013"
assert_invalid_schedule(
    wrong_product_revision,
    "product revision is invalid",
)

old_schedule_text = policy_terms["267141M31A03801"]["text"]
assert (
    parse_bnp_paribas_zero_limit_variable_universal_life(
        {
            **policy_terms["267141M31A03801"],
            "batch_id": "tii-life-173",
            "text": old_schedule_text.replace(
                "百分之一百零 一",
                "百分之一百零 二",
            ),
        }
    )
    is None
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
    assert candidate["source_file"].lower() == (
        f"{product_id.lower()}-a.pdf"
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-173",
        "product_count": len(schedules),
        "version_range": [0, 13],
    }
)

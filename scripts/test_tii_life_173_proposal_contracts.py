from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_FILES = {
    "bnp-paribas-early-variable-life-paid-premium-factor-v2": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-early-variable-life-paid-premium-v204-combined.json",
        83,
    ),
    "bnp-paribas-variable-life-net-risk-account-value-v1": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-variable-life-net-risk-v205.json",
        49,
    ),
    "bnp-paribas-variable-universal-life-net-risk-account-value-v1": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-variable-universal-life-net-risk-v205.json",
        563,
    ),
    "bnp-paribas-hengfu-variable-life-v2": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-hengfu-variable-life-v206.json",
        11,
    ),
    "bnp-paribas-zero-limit-variable-universal-life-v1": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-zero-limit-variable-universal-life-v208.json",
        14,
    ),
    "bnp-paribas-qimandeli-threshold-face-amount-variable-universal-life-v1": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-qimandeli-threshold-face-amount-v210.json",
        7,
    ),
    "bnp-paribas-qikaidesheng-three-way-variable-life-v1": (
        "work/tii-benefit-proposals/"
        "tii-life-173-bnp-qikaidesheng-three-way-v211.json",
        7,
    ),
}


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/tii-life-173")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("formal validator accepted an invalid tii-life-173 schedule")


product_ids: set[str] = set()
representatives: dict[str, dict] = {}
product_schedules: dict[str, dict] = {}

for expected_parser_id, (relative_path, expected_count) in PROPOSAL_FILES.items():
    payload = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    assert payload["batch_id"] == "tii-life-173"
    assert payload["proposal_count"] == expected_count
    assert len(payload["proposals"]) == expected_count

    for proposal in payload["proposals"]:
        product_id = proposal["product_id"]
        assert product_id not in product_ids, product_id
        product_ids.add(product_id)
        assert proposal["status"] == "proposed"
        assert proposal["candidate_count"] == 1
        candidate = proposal["candidates"][0]
        assert candidate["parser_id"] == expected_parser_id
        assert candidate["source_file"].lower() == f"{product_id.lower()}-a.pdf"
        validate_plan_options(
            candidate["schedule"],
            f"tii-life-173/{product_id}",
        )
        representatives.setdefault(expected_parser_id, candidate["schedule"])
        product_schedules[product_id] = candidate["schedule"]

assert len(product_ids) == 734

hengfu_source_gaps = json.loads(
    (
        ROOT
        / "work"
        / "tii-benefit-candidates"
        / "tii-life-173-bnp-hengfu-variable-life-source-gaps.json"
    ).read_text(encoding="utf-8")
)
assert hengfu_source_gaps["gap_count"] == 1
assert [item["product_id"] for item in hengfu_source_gaps["gaps"]] == [
    "267191M31A00303"
]
assert (
    hengfu_source_gaps["gaps"][0]["reason_code"]
    == "referenced_total_disability_appendix_missing"
)

early = copy.deepcopy(
    representatives["bnp-paribas-early-variable-life-paid-premium-factor-v2"]
)
early["plan_options"][0]["value"] = "丙型"
assert_invalid_schedule(early, "policy-type option values are invalid")

variable_life = copy.deepcopy(
    representatives["bnp-paribas-variable-life-net-risk-account-value-v1"]
)
variable_life["coverage_entries"].pop()
assert_invalid_schedule(variable_life, "exact entry set is invalid")

variable_life_false_required_flag = copy.deepcopy(
    representatives["bnp-paribas-variable-life-net-risk-account-value-v1"]
)
variable_life_false_required_flag["version_characteristics"][
    "policy_account_value_required"
] = False
assert_invalid_schedule(
    variable_life_false_required_flag,
    "variable life required flag is invalid",
)

variable_universal = copy.deepcopy(
    representatives[
        "bnp-paribas-variable-universal-life-net-risk-account-value-v1"
    ]
)
variable_universal["coverage_entries"][1]["limit_scope"] = "annual"
assert_invalid_schedule(variable_universal, "exact entry contract is invalid")

variable_universal_false_required_flag = copy.deepcopy(
    representatives[
        "bnp-paribas-variable-universal-life-net-risk-account-value-v1"
    ]
)
variable_universal_false_required_flag["version_characteristics"][
    "policy_type_required"
] = False
assert_invalid_schedule(
    variable_universal_false_required_flag,
    "variable universal life required flag is invalid",
)

early_minor_disability = copy.deepcopy(product_schedules["267191M31A00225"])
early_minor_disability_entry = next(
    entry
    for entry in early_minor_disability["coverage_entries"]
    if entry["id"] == "total-disability-benefit"
)
early_minor_disability_entry.pop("minor_account_value_return_age")
assert_invalid_schedule(
    early_minor_disability,
    "exact entry contract is invalid",
)

hengfu = copy.deepcopy(
    representatives["bnp-paribas-hengfu-variable-life-v2"]
)
hengfu["version_characteristics"]["required_policy_inputs"].pop()
assert_invalid_schedule(hengfu, "required inputs are invalid")

hengfu_current_effective = copy.deepcopy(product_schedules["267191M31A00304"])
hengfu_current_effective.pop("face_amount_label")
assert_invalid_schedule(
    hengfu_current_effective,
    "face amount label is invalid",
)

zero_limit = copy.deepcopy(
    representatives[
        "bnp-paribas-zero-limit-variable-universal-life-v1"
    ]
)
zero_limit["coverage_entries"][1]["policy_state_keys"].pop()
assert_invalid_schedule(zero_limit, "minor account value rule is invalid")

print(
    {
        "status": "ok",
        "batch_id": "tii-life-173",
        "product_count": len(product_ids),
        "parser_family_count": len(PROPOSAL_FILES),
    }
)

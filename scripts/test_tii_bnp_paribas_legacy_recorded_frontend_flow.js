const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-173-bnp-legacy-recorded-variable-life-v212.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 24);
assert.equal(proposal.proposed_count, 24);
assert.equal(proposal.manual_review_count, 0);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (proposalItem) => proposalItem.product_id === productId,
  ).candidates[0].schedule;
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(schedule, entryId, policyState, planName) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    plan_name: planName,
    policy_state: policyState,
  });
}

const topPlayer = scheduleFor("267191M31A00900");
const directState = {
  paid_premium_total: 1_000_000,
  partial_termination_amount_total: 100_000,
  specified_percent_or_multiplier: 130,
  specified_factor_unit: "percent",
  benefit_valuation_policy_account_value: 800_000,
  insured_age_at_event: 40,
  policy_effect_status_at_event: "active",
  claim_time_status: "within_claim_period",
  benefit_exclusion_status: "none_confirmed",
  total_disability_qualification_status:
    "confirmed_first_level_item",
  policy_loan_and_interest_amount: 50_000,
  unpaid_policy_charge_amount: 10_000,
  death_benefit_status: "standard_death",
  remaining_funeral_benefit_limit: 0,
  funeral_excess_insurance_cost_refund_status:
    "confirmed_none",
  funeral_excess_insurance_cost_refund_amount: 0,
  maturity_policy_account_value: 900_000,
};

const typeA = valueFor(
  topPlayer,
  "death-or-funeral-benefit",
  directState,
  "甲型",
);
assert.equal(typeA.value, 1_110_000);
assert.equal(typeA.state, "death_or_funeral_amount");
assert.equal(typeA.paid_premium_basis, 900_000);
assert.equal(typeA.paid_premium_factor_amount, 1_170_000);
assert.equal(typeA.gross_value_before_offsets, 1_170_000);

const typeB = valueFor(
  topPlayer,
  "total-disability-benefit",
  {
    ...directState,
    specified_percent_or_multiplier: 1.3,
    specified_factor_unit: "multiplier",
  },
  "乙型",
);
assert.equal(typeB.value, 1_910_000);
assert.equal(typeB.state, "calculated");

const directMinor = valueFor(
  topPlayer,
  "death-or-funeral-benefit",
  { ...directState, insured_age_at_event: 14 },
  "甲型",
);
assert.equal(directMinor.value, 740_000);
assert.equal(directMinor.state, "account_value_return");

const directFuneral = valueFor(
  topPlayer,
  "death-or-funeral-benefit",
  {
    ...directState,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 200_000,
  },
  "甲型",
);
assert.equal(directFuneral.protected_amount, 370_000);
assert.equal(directFuneral.capped_protected_amount, 200_000);
assert.equal(directFuneral.gross_value_before_offsets, 1_000_000);
assert.equal(directFuneral.value, 940_000);

const directInactive = valueFor(
  topPlayer,
  "total-disability-benefit",
  { ...directState, policy_effect_status_at_event: "suspended_or_lapsed" },
  "甲型",
);
assert.equal(directInactive.state, "needs_insurer_confirmation");
assert.equal(
  directInactive.confirmation_reason,
  "contract_not_confirmed_active",
);

const directOverOffset = valueFor(
  topPlayer,
  "total-disability-benefit",
  {
    ...directState,
    policy_loan_and_interest_amount: 2_000_000,
  },
  "甲型",
);
assert.equal(directOverOffset.state, "needs_insurer_confirmation");
assert.equal(
  directOverOffset.confirmation_reason,
  "offsets_exceed_gross_benefit",
);

const foreignTopPlayer = scheduleFor("267191M31A01405");
const foreignMissingCurrency = valueFor(
  foreignTopPlayer,
  "total-disability-benefit",
  {
    ...directState,
    remittance_fee_amount: 5_000,
  },
  "甲型",
);
assert.equal(foreignMissingCurrency.state, "needs_policy_state");
assert.ok(
  foreignMissingCurrency.required_fields.includes("contract_currency"),
);
const foreignCalculated = valueFor(
  foreignTopPlayer,
  "total-disability-benefit",
  {
    ...directState,
    contract_currency: "ZAR",
    remittance_fee_amount: 5_000,
  },
  "甲型",
);
assert.equal(foreignCalculated.value, 1_105_000);
assert.equal(foreignCalculated.currency_label, "ZAR");
assert.equal(foreignCalculated.remittance_fee_amount, 5_000);

const value100 = scheduleFor("267191M31A01905");
const value100State = {
  current_policy_amount: 1_500_000,
  basic_face_amount: 1_100_000,
  benefit_valuation_policy_account_value: 800_000,
  insured_age_at_event: 40,
  policy_effect_status_at_event: "active",
  policy_loan_and_interest_amount: 50_000,
  unpaid_policy_charge_amount: 10_000,
  death_benefit_status: "standard_death",
  remaining_funeral_benefit_limit: 0,
  maturity_policy_account_value: 900_000,
  installment_premium_frequency: "annual",
  previous_installment_premium_cumulative_count: 60,
  current_installment_premium_cumulative_count: 72,
  previous_installment_premium_average_amount: 10_000,
  value_addition_qualification_status: "eligible",
};
const value100Death = valueFor(
  value100,
  "death-or-funeral-benefit",
  value100State,
);
assert.equal(value100Death.value, 1_440_000);
assert.equal(value100Death.gross_value_before_offsets, 1_500_000);
assert.equal(
  valueFor(
    value100,
    "total-disability-benefit",
    value100State,
  ).value,
  1_440_000,
);
assert.equal(
  valueFor(
    value100,
    "maturity-benefit",
    value100State,
  ).value,
  840_000,
);

const value100Minor = valueFor(
  value100,
  "death-or-funeral-benefit",
  { ...value100State, insured_age_at_event: 14 },
);
assert.equal(value100Minor.value, 740_000);
assert.equal(value100Minor.state, "account_value_return");

const value100Funeral = valueFor(
  value100,
  "death-or-funeral-benefit",
  {
    ...value100State,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 200_000,
  },
);
assert.equal(value100Funeral.account_value_return, 800_000);
assert.equal(value100Funeral.protected_amount, 700_000);
assert.equal(value100Funeral.capped_protected_amount, 200_000);
assert.equal(value100Funeral.value, 940_000);

const annualCross61 = valueFor(
  value100,
  "value-added-benefit",
  value100State,
);
assert.equal(annualCross61.value, 1_200);
assert.equal(annualCross61.formula_type, "annual_first_crossing_61");

const annualCross121 = valueFor(
  value100,
  "value-added-benefit",
  {
    ...value100State,
    previous_installment_premium_cumulative_count: 116,
    current_installment_premium_cumulative_count: 128,
  },
);
assert.equal(annualCross121.value, 2_000);
assert.equal(annualCross121.formula_type, "annual_first_crossing_121");

const monthly121 = valueFor(
  value100,
  "value-added-benefit",
  {
    ...value100State,
    installment_premium_frequency: "monthly",
    previous_installment_premium_cumulative_count: 120,
    current_installment_premium_cumulative_count: 121,
  },
);
assert.equal(monthly121.value, 200);
assert.equal(monthly121.formula_type, "monthly_current_count_rate");

const ineligible = valueFor(
  value100,
  "value-added-benefit",
  {
    ...value100State,
    value_addition_qualification_status: "ineligible",
  },
);
assert.equal(ineligible.value, 0);
assert.equal(ineligible.formula_type, "qualification_lost");

const invalidCounts = valueFor(
  value100,
  "value-added-benefit",
  {
    ...value100State,
    previous_installment_premium_cumulative_count: 72,
    current_installment_premium_cumulative_count: 60,
  },
);
assert.equal(invalidCounts.state, "needs_policy_state");

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  product_count: proposal.proposal_count,
  direct_formula_versions: 18,
  value100_versions: 6,
  user_flow_cases: 17,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");

function loadProposal(fileName) {
  return JSON.parse(
    fs.readFileSync(
      path.join(ROOT, "work/tii-benefit-proposals", fileName),
      "utf8",
    ),
  );
}

const lifeProposal = loadProposal(
  "tii-life-173-bnp-legacy-recorded-variable-life-expansion-v230.json",
);
const annuityProposal = loadProposal(
  "tii-life-173-bnp-wealth-expert-foreign-variable-annuity-v230.json",
);

assert.equal(lifeProposal.proposal_count, 32);
assert.equal(lifeProposal.proposed_count, 32);
assert.equal(lifeProposal.manual_review_count, 0);
assert.equal(annuityProposal.proposal_count, 1);
assert.equal(annuityProposal.proposed_count, 1);
assert.equal(annuityProposal.manual_review_count, 0);

function scheduleFor(proposal, productId) {
  const item = proposal.proposals.find(
    (proposalItem) => proposalItem.product_id === productId,
  );
  assert(item, productId);
  return item.candidates[0].schedule;
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

const policyState = {
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

const twdLife = scheduleFor(lifeProposal, "267191M31A00800");
const twdDeath = valueFor(
  twdLife,
  "death-or-funeral-benefit",
  policyState,
  "甲型",
);
assert.equal(twdDeath.value, 1_110_000);
assert.equal(twdDeath.state, "death_or_funeral_amount");

const twdTypeB = valueFor(
  twdLife,
  "total-disability-benefit",
  {
    ...policyState,
    specified_percent_or_multiplier: 1.3,
    specified_factor_unit: "multiplier",
  },
  "乙型",
);
assert.equal(twdTypeB.value, 1_910_000);

const twdMinor = valueFor(
  twdLife,
  "death-or-funeral-benefit",
  { ...policyState, insured_age_at_event: 14 },
  "甲型",
);
assert.equal(twdMinor.value, 740_000);
assert.equal(twdMinor.state, "account_value_return");

const timeBarred = valueFor(
  twdLife,
  "death-or-funeral-benefit",
  {
    ...policyState,
    claim_time_status: "time_barred",
  },
  "甲型",
);
assert.equal(timeBarred.value, 740_000);
assert.equal(timeBarred.state, "account_value_return");
assert.equal(
  timeBarred.formula_type,
  "time_barred_account_value_return",
);

const exclusionUncertain = valueFor(
  twdLife,
  "death-or-funeral-benefit",
  {
    ...policyState,
    benefit_exclusion_status: "may_apply",
  },
  "甲型",
);
assert.equal(
  exclusionUncertain.state,
  "needs_insurer_confirmation",
);
assert.equal(
  exclusionUncertain.confirmation_reason,
  "benefit_exclusion_may_apply",
);

const disabilityUnconfirmed = valueFor(
  twdLife,
  "total-disability-benefit",
  {
    ...policyState,
    total_disability_qualification_status: "not_confirmed",
  },
  "甲型",
);
assert.equal(
  disabilityUnconfirmed.state,
  "needs_insurer_confirmation",
);
assert.equal(
  disabilityUnconfirmed.confirmation_reason,
  "total_disability_not_confirmed",
);

const overWithdrawal = valueFor(
  twdLife,
  "total-disability-benefit",
  {
    ...policyState,
    partial_termination_amount_total: 1_000_001,
  },
  "甲型",
);
assert.equal(
  overWithdrawal.confirmation_reason,
  "partial_termination_exceeds_paid_premium",
);

const fractionalFormula = valueFor(
  twdLife,
  "total-disability-benefit",
  {
    ...policyState,
    paid_premium_total: 1_001,
    partial_termination_amount_total: 0,
  },
  "甲型",
);
assert.equal(
  fractionalFormula.confirmation_reason,
  "specified_factor_rounding_rule_missing",
);

const missingFactorUnit = valueFor(
  twdLife,
  "total-disability-benefit",
  {
    ...policyState,
    specified_factor_unit: "",
  },
  "甲型",
);
assert.equal(missingFactorUnit.state, "needs_policy_state");
assert(
  missingFactorUnit.required_fields.includes(
    "specified_factor_unit",
  ),
);

const funeralNeedsRefundConfirmation = valueFor(
  twdLife,
  "death-or-funeral-benefit",
  {
    ...policyState,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 200_000,
    funeral_excess_insurance_cost_refund_status: "unknown",
  },
  "甲型",
);
assert.equal(
  funeralNeedsRefundConfirmation.confirmation_reason,
  "funeral_excess_insurance_cost_refund_unknown",
);

const funeralWithRefund = valueFor(
  twdLife,
  "death-or-funeral-benefit",
  {
    ...policyState,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 200_000,
    funeral_excess_insurance_cost_refund_status:
      "confirmed_amount",
    funeral_excess_insurance_cost_refund_amount: 30_000,
  },
  "甲型",
);
assert.equal(funeralWithRefund.value, 970_000);
assert.equal(
  funeralWithRefund.funeral_excess_insurance_cost_refund_amount,
  30_000,
);

const foreignLife = scheduleFor(lifeProposal, "267191M31A01300");
const foreignMissingCurrency = valueFor(
  foreignLife,
  "total-disability-benefit",
  { ...policyState, remittance_fee_amount: 5_000 },
  "甲型",
);
assert.equal(foreignMissingCurrency.state, "needs_policy_state");
assert(
  foreignMissingCurrency.required_fields.includes("contract_currency"),
);

const foreignCalculated = valueFor(
  foreignLife,
  "total-disability-benefit",
  {
    ...policyState,
    contract_currency: "USD",
    remittance_fee_amount: 5_000,
  },
  "甲型",
);
assert.equal(foreignCalculated.value, 1_105_000);
assert.equal(foreignCalculated.currency_label, "USD");

const annuity = scheduleFor(annuityProposal, "267191M31A01504");
const annuityEntries = entriesFor(annuity);
assert.deepEqual(Object.keys(annuityEntries).sort(), [
  "account-value-return-before-annuity-start",
  "annuity-payment",
  "excess-account-value-return-at-annuity-start",
  "full-account-value-withdrawal-at-annuity-start",
  "unpaid-annuity-balance",
]);

const annuityBase = {
  annuity_payment_amount: 9_000,
  annuity_start_policy_account_value: 500_000,
};
const annuityPayment = valueFor(
  annuity,
  "annuity-payment",
  annuityBase,
);
assert.equal(annuityPayment.value, 9_000);
assert.equal(annuityPayment.state, "policy_state_value");
assert.equal(
  annuityPayment.formula_type,
  "insurer_quoted_annual_annuity",
);

const lowAnnuity = valueFor(
  annuity,
  "annuity-payment",
  {
    annuity_payment_amount: 4_999,
    annuity_start_policy_account_value: 500_000,
  },
);
assert.equal(lowAnnuity.value, 500_000);
assert.equal(lowAnnuity.state, "account_value_return");
assert.equal(lowAnnuity.formula_type, "low_annual_annuity_lump_sum");

const missingQuote = valueFor(
  annuity,
  "annuity-payment",
  { annuity_start_policy_account_value: 500_000 },
);
assert.equal(missingQuote.state, "needs_policy_state");
assert(missingQuote.required_fields.includes("annuity_payment_amount"));

assert.equal(
  valueFor(
    annuity,
    "full-account-value-withdrawal-at-annuity-start",
    { annuity_start_policy_account_value: 500_000 },
  ).value,
  500_000,
);
assert.equal(
  valueFor(
    annuity,
    "excess-account-value-return-at-annuity-start",
    { excess_annuity_reserve_return_amount: 120_000 },
  ).value,
  120_000,
);
assert.equal(
  valueFor(
    annuity,
    "unpaid-annuity-balance",
    { unpaid_annuity_balance: 45_000 },
  ).value,
  45_000,
);
assert.equal(
  valueFor(
    annuity,
    "account-value-return-before-annuity-start",
    { policy_account_value: 480_000 },
  ).value,
  480_000,
);

const requiredFields = model
  .policyStateRequirements({
    ...annuity,
    policy_state: {},
  })
  .fields.map((field) => field.key);
for (const requiredField of [
  "annuity_payment_amount",
  "annuity_start_policy_account_value",
  "excess_annuity_reserve_return_amount",
  "unpaid_annuity_balance",
  "policy_account_value",
]) {
  assert(requiredFields.includes(requiredField), requiredField);
}

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  life_product_count: 32,
  annuity_product_count: 1,
  user_flow_cases: 20,
});

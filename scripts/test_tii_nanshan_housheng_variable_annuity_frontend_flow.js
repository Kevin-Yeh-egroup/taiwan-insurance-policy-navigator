const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const proposalPath = path.join(
  __dirname,
  "..",
  "work",
  "tii-benefit-proposals",
  "tii-life-036-nanshan-housheng-variable-annuity-v228.json",
);
const proposal = JSON.parse(fs.readFileSync(proposalPath, "utf8"));

function scheduleFor(productId) {
  const item = proposal.proposals.find(
    (candidate) => candidate.product_id === productId,
  );
  assert(item, productId);
  return item.candidates[0].schedule;
}

function entry(schedule, entryId) {
  const result = schedule.coverage_entries.find(
    (candidate) => candidate.id === entryId,
  );
  assert(result, entryId);
  return result;
}

function valueFor(schedule, entryId, selection) {
  return model.coverageValue(entry(schedule, entryId), {
    ...schedule,
    ...selection,
  });
}

function deathState(overrides = {}) {
  return {
    policy_effect_status_at_event: "active",
    benefit_valuation_policy_account_value: 1_000_000,
    policy_values_converted_to_twd: true,
    investment_allocation_status: "allocated",
    policy_loan_and_interest_amount: 0,
    unpaid_policy_charge_amount: 0,
    ...overrides,
  };
}

for (const [productId, expectedValue] of [
  ["206421M32C30100", 1_050_000],
  ["206421M32C30103", 1_050_000],
  ["206421M32C30120", 1_043_000],
]) {
  const schedule = scheduleFor(productId);
  const result = valueFor(
    schedule,
    "allocated-death-benefit-before-annuity-start",
    {
      face_amount: 50_000,
      plan_name: "20年",
      policy_state: deathState({
        policy_loan_and_interest_amount:
          productId === "206421M32C30120" ? 5_000 : 0,
        unpaid_policy_charge_amount:
          productId === "206421M32C30120" ? 2_000 : 0,
      }),
    },
  );
  assert.equal(result.state, "calculated");
  assert.equal(result.value, expectedValue);
  assert.equal(result.protected_amount, 50_000);
}

const revision20 = scheduleFor("206421M32C30120");
for (const [productId, policyState, expectedValue] of [
  [
    "206421M32C30100",
    {
      policy_effect_status_at_event: "active",
      investment_allocation_status: "awaiting_allocation",
      net_primary_premium_amount: 100_000,
    },
    101_000,
  ],
  [
    "206421M32C30103",
    {
      policy_effect_status_at_event: "active",
      investment_allocation_status: "awaiting_allocation",
      net_primary_premium_amount: 100_000,
      net_additional_premium_amount: 20_000,
    },
    121_000,
  ],
  [
    "206421M32C30120",
    {
      policy_effect_status_at_event: "active",
      investment_allocation_status: "awaiting_allocation",
      net_primary_premium_amount: 100_000,
      net_additional_premium_amount: 20_000,
      policy_loan_and_interest_amount: 5_000,
      unpaid_policy_charge_amount: 2_000,
    },
    114_000,
  ],
]) {
  const schedule = scheduleFor(productId);
  const result = valueFor(
    schedule,
    "preallocation-death-benefit",
    {
      face_amount: 50_000,
      plan_name: "20年",
      policy_state: policyState,
    },
  );
  assert.equal(result.state, "calculated");
  assert.equal(result.value, expectedValue);
  assert.equal(result.premium_factor, 1.01);
}

const missingAdditionalPremium = valueFor(
  revision20,
  "preallocation-death-benefit",
  {
    face_amount: 50_000,
    plan_name: "20年",
    policy_state: {
      policy_effect_status_at_event: "active",
      investment_allocation_status: "awaiting_allocation",
      net_primary_premium_amount: 100_000,
      policy_loan_and_interest_amount: 0,
      unpaid_policy_charge_amount: 0,
    },
  },
);
assert.equal(missingAdditionalPremium.state, "needs_policy_state");
assert(missingAdditionalPremium.required_fields.includes(
  "net_additional_premium_amount",
));

const inactiveContract = valueFor(
  revision20,
  "allocated-death-benefit-before-annuity-start",
  {
    face_amount: 50_000,
    plan_name: "20年",
    policy_state: deathState({
      policy_effect_status_at_event: "suspended_or_lapsed",
    }),
  },
);
assert.equal(inactiveContract.state, "needs_insurer_confirmation");
assert.equal(
  inactiveContract.confirmation_reason,
  "contract_not_confirmed_active",
);

const delayedDeath = valueFor(
  revision20,
  "delayed-claim-death-benefit-after-accumulation-maturity",
  {
    face_amount: 50_000,
    plan_name: "20年",
    policy_state: {
      policy_effect_status_at_event: "active",
      annuity_start_policy_account_value: 2_000_000,
      annuity_paid_total_amount: 100_000,
      policy_values_converted_to_twd: true,
      policy_loan_and_interest_amount: 5_000,
      unpaid_policy_charge_amount: 2_000,
    },
  },
);
assert.equal(delayedDeath.state, "calculated");
assert.equal(delayedDeath.value, 1_943_000);

const annuityQuoted = valueFor(
  revision20,
  "monthly-annuity-payment",
  {
    face_amount: 50_000,
    plan_name: "15年",
    policy_state: {
      policy_account_value: 2_000_000,
      annuity_payment_amount: 9_000,
    },
  },
);
assert.equal(annuityQuoted.state, "policy_state_value");
assert.equal(annuityQuoted.value, 9_000);
assert.equal(annuityQuoted.reference_amount, 2_000_000);

const needsAnnuityQuote = valueFor(
  revision20,
  "monthly-annuity-payment",
  {
    face_amount: 50_000,
    plan_name: "10年",
    policy_state: {
      policy_account_value: 2_000_000,
    },
  },
);
assert.equal(needsAnnuityQuote.state, "needs_annuity_factor");
assert.deepEqual(needsAnnuityQuote.required_fields, [
  "annuity_payment_amount",
]);

const stateAmountCases = [
  [
    "exclusion-account-value-return",
    "exclusion_account_value_return_amount",
    410_000,
  ],
  [
    "account-value-withdrawal-at-annuity-start",
    "annuity_start_policy_account_value",
    2_000_000,
  ],
  [
    "low-monthly-annuity-lump-sum",
    "annuity_start_policy_account_value",
    2_000_000,
  ],
  ["unpaid-annuity-balance", "unpaid_annuity_balance", 320_000],
  [
    "excess-annuity-account-value-return",
    "excess_annuity_reserve_return_amount",
    180_000,
  ],
];
for (const [entryId, stateKey, amount] of stateAmountCases) {
  const result = valueFor(revision20, entryId, {
    face_amount: 50_000,
    plan_name: "20年",
    policy_state: { [stateKey]: amount },
  });
  assert.equal(result.state, "policy_state_value");
  assert.equal(result.value, amount);
}

const requirements = model.policyStateRequirements({
  ...revision20,
  face_amount: 50_000,
  plan_name: "20年",
  policy_state: deathState(),
});
const requirementKeys = requirements.fields.map((field) => field.key);
for (const requiredKey of [
  "annuity_payment_amount",
  "annuity_start_policy_account_value",
  "annuity_paid_total_amount",
  "exclusion_account_value_return_amount",
  "unpaid_annuity_balance",
  "excess_annuity_reserve_return_amount",
]) {
  assert(requirementKeys.includes(requiredKey), requiredKey);
}
assert.equal(requirementKeys.includes("net_primary_premium_amount"), false);
assert.equal(
  requirementKeys.includes("net_additional_premium_amount"),
  false,
);

const awaitingRequirements = model.policyStateRequirements({
  ...revision20,
  face_amount: 50_000,
  plan_name: "20年",
  policy_state: deathState({
    investment_allocation_status: "awaiting_allocation",
  }),
});
const awaitingRequirementKeys = awaitingRequirements.fields.map(
  (field) => field.key,
);
assert(awaitingRequirementKeys.includes("net_primary_premium_amount"));
assert(awaitingRequirementKeys.includes("net_additional_premium_amount"));
assert.equal(
  awaitingRequirementKeys.includes(
    "benefit_valuation_policy_account_value",
  ),
  false,
);

console.log({
  status: "ok",
  batch_id: "tii-life-036",
  product_versions_tested: 3,
  user_flow_cases: 15,
});

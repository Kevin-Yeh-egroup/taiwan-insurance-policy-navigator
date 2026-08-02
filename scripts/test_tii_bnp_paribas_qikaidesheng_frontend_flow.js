const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-173-bnp-qikaidesheng-three-way-v211.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 7);

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

function valueFor(schedule, entryId, policyState) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    policy_state: policyState,
  });
}

const original = scheduleFor("267141M31A02000");
assert.equal(model.selectionRequirements(original).mode, "policy_state");
assert.deepEqual(
  model.policyStateRequirements(original).fields.map((field) => field.key),
  [
    "maturity_policy_account_value",
    "current_policy_amount",
    "basic_face_amount",
    "benefit_valuation_policy_account_value",
    "death_benefit_status",
    "target_premium_cumulative_count",
    "target_premium_new_count",
    "cumulative_paid_target_premium_total",
    "value_addition_qualification_status",
  ],
);

const originalState = {
  maturity_policy_account_value: 900_000,
  current_policy_amount: 1_100_000,
  basic_face_amount: 1_500_000,
  benefit_valuation_policy_account_value: 800_000,
  death_benefit_status: "standard_death",
  target_premium_cumulative_count: 36,
  target_premium_new_count: 12,
  cumulative_paid_target_premium_total: 360_000,
  value_addition_qualification_status: "eligible",
};
const originalDeath = valueFor(
  original,
  "death-or-funeral-benefit",
  originalState,
);
assert.equal(originalDeath.value, 1_500_000);
assert.equal(originalDeath.state, "greater_of");
assert.equal(
  valueFor(original, "total-disability-benefit", originalState).value,
  1_500_000,
);
assert.equal(
  valueFor(original, "maturity-benefit", originalState).value,
  900_000,
);

const originalValueAddition = valueFor(
  original,
  "value-added-benefit",
  originalState,
);
assert.equal(originalValueAddition.value, 12_000);
assert.equal(
  originalValueAddition.state,
  "value_added_account_credit",
);
assert.equal(originalValueAddition.average_target_premium, 10_000);
assert.ok(
  Math.abs(originalValueAddition.applicable_rate_sum - 1.2) < 1e-9,
);

const current = scheduleFor("267141M31A02005");
const currentState = {
  maturity_policy_account_value: 1_000_000,
  basic_face_amount: 1_100_000,
  current_threshold_face_amount: 1_500_000,
  benefit_valuation_policy_account_value: 800_000,
  death_benefit_status: "standard_death",
  target_premium_cumulative_count: 65,
  target_premium_new_count: 12,
  cumulative_paid_target_premium_total: 650_000,
  value_addition_qualification_status: "eligible",
};
assert.equal(
  valueFor(current, "death-or-funeral-benefit", currentState).value,
  1_500_000,
);
assert.equal(
  valueFor(current, "total-disability-benefit", currentState).value,
  1_500_000,
);
const crossingBand = valueFor(
  current,
  "value-added-benefit",
  currentState,
);
assert.equal(crossingBand.value, 14_500);
assert.ok(Math.abs(crossingBand.applicable_rate_sum - 1.45) < 1e-9);

const upperBand = valueFor(
  current,
  "value-added-benefit",
  {
    ...currentState,
    target_premium_cumulative_count: 86,
    target_premium_new_count: 12,
    cumulative_paid_target_premium_total: 860_000,
  },
);
assert.equal(upperBand.value, 30_000);
assert.ok(Math.abs(upperBand.applicable_rate_sum - 3) < 1e-9);

const ineligible = valueFor(
  current,
  "value-added-benefit",
  {
    ...currentState,
    value_addition_qualification_status: "ineligible",
  },
);
assert.equal(ineligible.value, 0);
assert.equal(ineligible.formula_type, "qualification_lost");

const invalidCounts = valueFor(
  current,
  "value-added-benefit",
  {
    ...currentState,
    target_premium_cumulative_count: 6,
    target_premium_new_count: 12,
  },
);
assert.equal(invalidCounts.value, null);
assert.equal(invalidCounts.state, "needs_policy_state");

const missingValueAdditionState = valueFor(
  current,
  "value-added-benefit",
  {
    target_premium_cumulative_count: 36,
    target_premium_new_count: 12,
  },
);
assert.equal(missingValueAdditionState.value, null);
assert.deepEqual(missingValueAdditionState.required_fields, [
  "cumulative_paid_target_premium_total",
  "value_addition_qualification_status",
]);

const funeralLimited = valueFor(
  current,
  "death-or-funeral-benefit",
  {
    ...currentState,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 200_000,
  },
);
assert.equal(funeralLimited.value, 1_000_000);
assert.equal(funeralLimited.gross_value_before_funeral_cap, 1_500_000);
assert.equal(funeralLimited.protected_amount, 700_000);
assert.equal(funeralLimited.capped_protected_amount, 200_000);
assert.equal(funeralLimited.account_value_return, 800_000);

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  product_count: proposal.proposal_count,
  user_flow_cases: 25,
});

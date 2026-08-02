const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const proposalPath = path.join(
  __dirname,
  "..",
  "work",
  "tii-benefit-proposals",
  "tii-life-090-hongtai-fengshuo-variable-annuity-v223.json",
);
const proposal = JSON.parse(fs.readFileSync(proposalPath, "utf8"));

function scheduleFor(productId) {
  const item = proposal.proposals.find(
    (candidate) => candidate.product_id === productId,
  );
  assert(item, productId);
  assert.equal(item.candidate_count, 1);
  return item.candidates[0].schedule;
}

function policy(schedule, policyState) {
  return {
    ...schedule,
    plan_name: "分期給付",
    policy_state: policyState,
  };
}

const legacySchedule = scheduleFor("217421M31A00200");
const legacyPolicy = policy(legacySchedule, {
  annuity_payment_amount: 9_999,
  annuity_start_policy_account_value: 500_000,
});
const legacyEntries = model.effectiveCoverageEntries(legacyPolicy);
assert.deepEqual(
  legacyEntries.map((entry) => entry.id),
  [
    "annual-annuity-or-low-amount-lump-sum",
    "account-value-return-before-annuity-start-death",
    "unpaid-annuity-balance-after-death",
  ],
);
const legacyAnnuityEntry = legacyEntries[0];
assert.equal(
  legacyAnnuityEntry.maximum_annual_annuity_amount,
  null,
);
const legacyLowResult = model.coverageValue(
  legacyAnnuityEntry,
  legacyPolicy,
);
assert.equal(legacyLowResult.value, 500_000);
assert.equal(legacyLowResult.state, "account_value_return");
assert.equal(
  legacyLowResult.maximum_annual_annuity_amount,
  null,
);
const legacyRequiredFields = model
  .policyStateRequirements(legacyPolicy)
  .fields.map((field) => field.key);
assert(!legacyRequiredFields.includes(
  "excess_annuity_reserve_return_amount",
));

const legacyAnnualResult = model.coverageValue(
  legacyAnnuityEntry,
  policy(legacySchedule, {
    annuity_payment_amount: 15_000,
    annuity_start_policy_account_value: 500_000,
  }),
);
assert.equal(legacyAnnualResult.value, 15_000);
assert.equal(legacyAnnualResult.state, "policy_state_value");

const modernSchedule = scheduleFor(
  "217421MV1A00223A11Z90000030",
);
const modernPolicy = policy(modernSchedule, {
  annuity_payment_amount: 15_000,
  annuity_start_policy_account_value: 500_000,
  excess_annuity_reserve_return_amount: 0,
});
const modernEntries = model.effectiveCoverageEntries(modernPolicy);
assert.equal(modernEntries.length, 4);
assert(
  modernEntries.some(
    (entry) =>
      entry.id ===
      "excess-account-value-return-at-annuity-start",
  ),
);
assert.equal(
  modernEntries[0].maximum_annual_annuity_amount,
  1_200_000,
);
assert(
  model
    .policyStateRequirements(modernPolicy)
    .fields.some(
      (field) =>
        field.key ===
        "excess_annuity_reserve_return_amount",
    ),
);

console.log({
  status: "ok",
  product_family: "hongtai-fengshuo-variable-annuity",
  legacy_version_count: 12,
  modern_version_count: 19,
  source_gap_count: 0,
});

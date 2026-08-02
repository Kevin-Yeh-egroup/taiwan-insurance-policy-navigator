const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-173-bnp-zero-limit-variable-universal-life-v208.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 14);

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

const original = scheduleFor("267141M31A03800");
assert.equal(model.selectionRequirements(original).mode, "policy_state");
assert.deepEqual(
  model.policyStateRequirements(original).fields.map((field) => field.key),
  [
    "maturity_policy_account_value",
    "current_policy_amount",
    "basic_face_amount",
    "benefit_valuation_policy_account_value",
    "insured_age_at_event",
    "death_benefit_status",
  ],
);
assert.equal(
  model
    .policyStateRequirements({
      ...original,
      policy_state: { death_benefit_status: "funeral_limited" },
    })
    .fields.at(-1).key,
  "remaining_funeral_benefit_limit",
);
const originalState = {
  maturity_policy_account_value: 900_000,
  current_policy_amount: 1_100_000,
  basic_face_amount: 1_300_000,
  benefit_valuation_policy_account_value: 800_000,
  death_benefit_status: "standard_death",
  insured_age_at_event: 40,
};
assert.equal(
  valueFor(
    original,
    "death-or-funeral-benefit",
    originalState,
  ).value,
  1_300_000,
);
assert.equal(
  valueFor(
    original,
    "total-disability-benefit",
    originalState,
  ).value,
  1_300_000,
);
assert.equal(
  valueFor(original, "maturity-benefit", originalState).value,
  900_000,
);
const originalMinor = valueFor(
  original,
  "death-or-funeral-benefit",
  { ...originalState, insured_age_at_event: 14 },
);
assert.equal(originalMinor.value, 800_000);
assert.equal(originalMinor.state, "account_value_return");
const originalNewborn = valueFor(
  original,
  "death-or-funeral-benefit",
  {
    ...originalState,
    benefit_valuation_policy_account_value: 0,
    insured_age_at_event: 0,
  },
);
assert.equal(originalNewborn.value, 0);
assert.equal(originalNewborn.state, "account_value_return");

const funeralLimited = valueFor(
  original,
  "death-or-funeral-benefit",
  {
    ...originalState,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 200_000,
  },
);
assert.equal(funeralLimited.value, 1_000_000);
assert.equal(funeralLimited.protected_amount, 500_000);
assert.equal(funeralLimited.account_value_return, 800_000);

const expandedThreshold = scheduleFor(
  "267131MV1A03823A11C90000008",
);
const thresholdState = {
  maturity_policy_account_value: 950_000,
  basic_face_amount: 1_000_000,
  current_threshold_face_amount: 1_500_000,
  benefit_valuation_policy_account_value: 800_000,
  death_benefit_status: "standard_death",
  insured_age_at_event: 40,
};
const thresholdDeath = valueFor(
  expandedThreshold,
  "death-or-funeral-benefit",
  thresholdState,
);
assert.equal(thresholdDeath.value, 1_500_000);
assert.equal(thresholdDeath.state, "greater_of");
assert.deepEqual(
  thresholdDeath.candidates.map((candidate) => candidate.key),
  [
    "basic_face_amount",
    "current_threshold_face_amount",
    "benefit_valuation_policy_account_value",
  ],
);
assert.equal(
  valueFor(
    expandedThreshold,
    "total-disability-benefit",
    { ...thresholdState, insured_age_at_event: 14 },
  ).value,
  800_000,
);
const missingThreshold = valueFor(
  expandedThreshold,
  "death-or-funeral-benefit",
  {
    basic_face_amount: 1_000_000,
    benefit_valuation_policy_account_value: 800_000,
    death_benefit_status: "standard_death",
    insured_age_at_event: 40,
  },
);
assert.equal(missingThreshold.value, null);
assert.equal(missingThreshold.state, "needs_policy_state");
assert.deepEqual(missingThreshold.required_fields, [
  "current_threshold_face_amount",
]);

const adultOnly = scheduleFor("267131MV1A03823A11C90000009");
assert.deepEqual(
  model.policyStateRequirements(adultOnly).fields.map(
    (field) => field.key,
  ),
  [
    "maturity_policy_account_value",
    "basic_face_amount",
    "current_threshold_face_amount",
    "benefit_valuation_policy_account_value",
    "death_benefit_status",
  ],
);

const interestMaturity = scheduleFor(
  "267131MV1A03823A11C90000013",
);
assert.deepEqual(
  model.policyStateRequirements(interestMaturity).fields.map(
    (field) => field.key,
  ),
  [
    "maturity_policy_account_value",
    "maturity_interest_amount",
    "basic_face_amount",
    "current_threshold_face_amount",
    "benefit_valuation_policy_account_value",
    "death_benefit_status",
  ],
);
const interestState = {
  maturity_policy_account_value: 1_000_000,
  maturity_interest_amount: 25_000,
  basic_face_amount: 1_000_000,
  current_threshold_face_amount: 1_200_000,
  benefit_valuation_policy_account_value: 900_000,
  death_benefit_status: "standard_death",
};
const maturityValue = valueFor(
  interestMaturity,
  "maturity-benefit",
  interestState,
);
assert.equal(maturityValue.value, 1_025_000);
assert.equal(maturityValue.state, "policy_state_value");
assert.equal(
  maturityValue.components[1].key,
  "maturity_interest_amount",
);

assert.equal(
  model.POLICY_STATE_FIELDS.current_threshold_face_amount.label,
  "目前門檻保額",
);
assert.match(
  model.POLICY_STATE_FIELDS.current_threshold_face_amount.guidance,
  /不可用目前年齡與目前帳戶價值自行回推/,
);
assert.equal(
  model.POLICY_STATE_FIELDS.maturity_interest_amount.label,
  "保險公司列示之祝壽金利息",
);

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  product_count: proposal.proposal_count,
  user_flow_cases: 31,
});

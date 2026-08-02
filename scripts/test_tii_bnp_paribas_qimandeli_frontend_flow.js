const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-173-bnp-qimandeli-threshold-face-amount-v210.json",
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

const original = scheduleFor("267131MV1A07823A11Z90000000");
assert.equal(model.selectionRequirements(original).mode, "policy_state");
assert.deepEqual(
  model.policyStateRequirements(original).fields.map((field) => field.key),
  [
    "maturity_policy_account_value",
    "basic_face_amount",
    "current_threshold_face_amount",
    "benefit_valuation_policy_account_value",
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
  basic_face_amount: 1_100_000,
  current_threshold_face_amount: 1_500_000,
  benefit_valuation_policy_account_value: 800_000,
  death_benefit_status: "standard_death",
};
const death = valueFor(
  original,
  "death-or-funeral-benefit",
  originalState,
);
assert.equal(death.value, 1_500_000);
assert.equal(death.state, "greater_of");
assert.deepEqual(
  death.candidates.map((candidate) => candidate.key),
  [
    "basic_face_amount",
    "current_threshold_face_amount",
    "benefit_valuation_policy_account_value",
  ],
);
assert.equal(
  valueFor(original, "total-disability-benefit", originalState).value,
  1_500_000,
);
assert.equal(
  valueFor(original, "maturity-benefit", originalState).value,
  900_000,
);

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
assert.equal(funeralLimited.gross_value_before_funeral_cap, 1_500_000);
assert.equal(funeralLimited.protected_amount, 700_000);
assert.equal(funeralLimited.capped_protected_amount, 200_000);
assert.equal(funeralLimited.account_value_return, 800_000);

const missingThreshold = valueFor(
  original,
  "death-or-funeral-benefit",
  {
    basic_face_amount: 1_100_000,
    benefit_valuation_policy_account_value: 800_000,
    death_benefit_status: "standard_death",
  },
);
assert.equal(missingThreshold.value, null);
assert.equal(missingThreshold.state, "needs_policy_state");
assert.deepEqual(missingThreshold.required_fields, [
  "current_threshold_face_amount",
]);

const accountValueHighest = valueFor(
  original,
  "total-disability-benefit",
  {
    basic_face_amount: 1_100_000,
    current_threshold_face_amount: 1_500_000,
    benefit_valuation_policy_account_value: 1_800_000,
  },
);
assert.equal(accountValueHighest.value, 1_800_000);

const interestMaturity = scheduleFor(
  "267131MV1A07823A11Z90000005",
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
  interestMaturity.version_characteristics
    .insured_age_at_event_required,
  false,
);
assert.equal(
  model.policyStateRequirements(interestMaturity).fields.some(
    (field) => field.key === "insured_age_at_event",
  ),
  false,
);

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  product_count: proposal.proposal_count,
  user_flow_cases: 22,
});

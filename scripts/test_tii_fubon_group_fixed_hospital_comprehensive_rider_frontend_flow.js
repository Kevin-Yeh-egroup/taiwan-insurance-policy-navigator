const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-group-fixed-hospital-comprehensive-rider-v262.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

function scheduleFor(productId, planName) {
  const product = proposal.proposals.find(
    (item) => item.product_id === productId,
  );
  assert(product, productId);
  return {
    ...product.candidates[0].schedule,
    product_id: productId,
    plan_name: planName,
  };
}

function entriesById(selection) {
  return Object.fromEntries(
    model
      .effectiveCoverageEntries(selection)
      .map((entry) => [entry.id, entry]),
  );
}

function value(selection, entryId, policyState) {
  return model.coverageValue(entriesById(selection)[entryId], {
    ...selection,
    policy_state: policyState,
  });
}

const productId = "209313RZ1A00221A11Z10000014";
const noPlan = scheduleFor(productId, "");
assert.equal(model.selectionRequirements(noPlan).mode, "plan");
assert.deepEqual(
  model.selectionRequirements(noPlan).plan_options.map(
    (option) => option.value,
  ),
  ["A", "B", "C", "D", "E"],
);
assert.equal(model.effectiveCoverageEntries(noPlan).length, 0);

const planA = scheduleFor(productId, "A");
assert.deepEqual(
  model.policyStateRequirements(planA).fields.map(
    (field) => field.key,
  ),
  [
    "hospital_daily_amount",
    "hospitalization_days",
    "hospitalization_day_limit_per_stay",
    "intensive_care_days",
    "burn_unit_days",
  ],
);
const planAState = {
  hospital_daily_amount: 2_000,
  hospitalization_days: 45,
  hospitalization_day_limit_per_stay: 30,
  intensive_care_days: 35,
  burn_unit_days: 4,
};
assert.equal(
  value(
    planA,
    "general-hospital-benefit",
    planAState,
  ).value,
  60_000,
);
assert.equal(
  value(
    planA,
    "intensive-care-additional-benefit",
    planAState,
  ).value,
  120_000,
);
assert.equal(
  value(
    planA,
    "burn-unit-additional-benefit",
    planAState,
  ).value,
  24_000,
);

const planB = scheduleFor(productId, "B");
assert.equal(
  value(planB, "inpatient-nursing-benefit", {
    inpatient_nursing_daily_amount: 1_200,
    hospitalization_days: 12,
    hospitalization_day_limit_per_stay: 10,
  }).value,
  12_000,
);

const planC = scheduleFor(productId, "C");
assert.equal(
  value(planC, "post-discharge-recuperation-benefit", {
    discharge_recuperation_daily_amount: 800,
    hospitalization_days: 12,
    hospitalization_day_limit_per_stay: 10,
  }).value,
  8_000,
);

const planD = scheduleFor(productId, "D");
const surgery = value(planD, "surgery-benefit", {
  surgery_fixed_amount: 10_000,
  surgery_total_benefit_rate_percent: 165,
});
assert.equal(surgery.state, "policy_state_percentage");
assert.equal(surgery.value, 16_500);
const missingSurgeryRate = value(
  planD,
  "surgery-benefit",
  { surgery_fixed_amount: 10_000 },
);
assert.equal(
  missingSurgeryRate.state,
  "needs_policy_state",
);
assert.deepEqual(missingSurgeryRate.required_fields, [
  "surgery_total_benefit_rate_percent",
]);
const excessiveSurgeryRate = value(
  planD,
  "surgery-benefit",
  {
    surgery_fixed_amount: 10_000,
    surgery_total_benefit_rate_percent: 550,
  },
);
assert.equal(
  excessiveSurgeryRate.state,
  "needs_policy_state",
);
assert.deepEqual(excessiveSurgeryRate.required_fields, [
  "surgery_total_benefit_rate_percent",
]);

const planE = scheduleFor(productId, "E");
assert.equal(
  value(planE, "surgery-nursing-benefit", {
    surgery_nursing_fixed_amount: 5_000,
    surgery_benefit_rate_percent: 65,
  }).value,
  3_250,
);

for (const [key, type] of [
  ["inpatient_nursing_daily_amount", "money"],
  ["discharge_recuperation_daily_amount", "money"],
  ["surgery_fixed_amount", "money"],
  ["surgery_nursing_fixed_amount", "money"],
  ["surgery_total_benefit_rate_percent", "rate"],
]) {
  assert.equal(model.POLICY_STATE_FIELDS[key].type, type);
}

console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: 12,
});

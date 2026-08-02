const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals",
      "tii-life-080-farglory-xiong-health-surgery-medical-v283.json",
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

function selection(schedule, policyState, unitCount = 3) {
  return {
    ...schedule,
    unit_count: unitCount,
    policy_state: policyState,
  };
}

function valueFor(
  schedule,
  entryId,
  policyState,
  unitCount = 3,
) {
  return model.coverageValue(
    entriesFor(schedule)[entryId],
    selection(schedule, policyState, unitCount),
  );
}

const schedule = scheduleFor("216311R11A07200");
assert.equal(model.selectionRequirements(schedule).mode, "unit");

const inpatientState = {
  surgery_care_setting: "inpatient",
  surgery_benefit_multiplier: 20,
  cumulative_surgery_benefit_paid_amount: 100_000,
};
const requiredKeys = model
  .policyStateRequirements(selection(schedule, inpatientState))
  .fields.map((field) => field.key);
assert.deepEqual(requiredKeys, [
  "surgery_care_setting",
  "surgery_benefit_multiplier",
  "cumulative_surgery_benefit_paid_amount",
]);

const inpatient = valueFor(
  schedule,
  "inpatient-surgery-medical-benefit",
  inpatientState,
);
assert.equal(inpatient.state, "policy_state_multiplier");
assert.equal(inpatient.gross_value, 1_500);
assert.equal(inpatient.value, 1_500);
assert.equal(inpatient.aggregate_limit, 150_000);
assert.equal(inpatient.remaining_aggregate_limit, 50_000);
assert.equal(
  valueFor(
    schedule,
    "outpatient-surgery-medical-benefit",
    inpatientState,
  ).state,
  "not_eligible",
);
assert.equal(
  valueFor(
    schedule,
    "remaining-lifetime-surgery-medical-cap",
    inpatientState,
  ).value,
  50_000,
);

const outpatientState = {
  ...inpatientState,
  surgery_care_setting: "outpatient",
};
const outpatient = valueFor(
  schedule,
  "outpatient-surgery-medical-benefit",
  outpatientState,
);
assert.equal(outpatient.gross_value, 6_000);
assert.equal(outpatient.value, 6_000);
assert.equal(
  valueFor(
    schedule,
    "inpatient-surgery-medical-benefit",
    outpatientState,
  ).state,
  "not_eligible",
);

const nearCap = valueFor(
  schedule,
  "outpatient-surgery-medical-benefit",
  {
    ...outpatientState,
    cumulative_surgery_benefit_paid_amount: 149_000,
  },
);
assert.equal(nearCap.gross_value, 6_000);
assert.equal(nearCap.remaining_aggregate_limit, 1_000);
assert.equal(nearCap.value, 1_000);

const atCap = valueFor(
  schedule,
  "outpatient-surgery-medical-benefit",
  {
    ...outpatientState,
    cumulative_surgery_benefit_paid_amount: 150_000,
  },
);
assert.equal(atCap.remaining_aggregate_limit, 0);
assert.equal(atCap.value, 0);

assert.equal(
  valueFor(
    schedule,
    "inpatient-surgery-medical-benefit",
    {
      surgery_care_setting: "inpatient",
      cumulative_surgery_benefit_paid_amount: 0,
    },
  ).state,
  "needs_policy_state",
);
assert.equal(
  valueFor(
    schedule,
    "inpatient-surgery-medical-benefit",
    {
      surgery_care_setting: "inpatient",
      surgery_benefit_multiplier: 20,
    },
  ).state,
  "needs_policy_state",
);
assert.equal(
  valueFor(
    schedule,
    "inpatient-surgery-medical-benefit",
    inpatientState,
    null,
  ).state,
  "needs_unit_count",
);

const revision13 = scheduleFor(
  "216311RZ1A07223A11Z10000013",
);
assert.equal(
  revision13.version_characteristics.semantic_phase,
  "constant_unit_multiplier_benefit_model",
);
assert.equal(
  revision13.version_characteristics.lifetime_cap_per_unit,
  50_000,
);

console.log({
  status: "ok",
  batch_id: "tii-life-080",
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

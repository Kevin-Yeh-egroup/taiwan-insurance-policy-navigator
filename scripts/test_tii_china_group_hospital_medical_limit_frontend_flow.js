const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-026-china-group-hospital-medical-limit-v297.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function valueFor(schedule, policyState = {}) {
  return model.coverageValue(schedule.coverage_entries[0], {
    ...schedule,
    policy_state: policyState,
  });
}

const revision0 = scheduleFor("205317M11A07200");
assert.equal(model.selectionRequirements(revision0).mode, "policy_state");
assert.deepEqual(
  model.policyStateRequirements(revision0).fields.map((field) => field.key),
  [
    "china_group_hospital_medical_total_limit",
    "china_group_hospital_medical_actual_expense",
    "hospitalization_days",
    "china_group_hospital_room_meal_expense",
  ],
);

const inpatient = {
  china_group_hospital_medical_total_limit: 100_000,
  china_group_hospital_medical_actual_expense: 80_000,
  hospitalization_days: 3,
  china_group_hospital_room_meal_expense: 20_000,
};
const inpatientValue = valueFor(revision0, inpatient);
assert.equal(inpatientValue.state, "calculated");
assert.equal(inpatientValue.daily_room_meal_limit, 3_000);
assert.equal(inpatientValue.room_meal_limit, 9_000);
assert.equal(inpatientValue.eligible_room_meal_expense, 9_000);
assert.equal(inpatientValue.eligible_expense, 69_000);
assert.equal(inpatientValue.value, 69_000);

const totalCap = valueFor(revision0, {
  ...inpatient,
  china_group_hospital_medical_actual_expense: 200_000,
  china_group_hospital_room_meal_expense: 9_000,
});
assert.equal(totalCap.value, 100_000);

const invalidBreakdown = valueFor(revision0, {
  ...inpatient,
  china_group_hospital_medical_actual_expense: 10_000,
  china_group_hospital_room_meal_expense: 20_000,
});
assert.equal(invalidBreakdown.state, "needs_policy_state");
assert.equal(
  invalidBreakdown.invalid_reason,
  "room_meal_expense_exceeds_actual_expense",
);

const revision5 = scheduleFor("205317M11A07205");
assert.deepEqual(
  model.policyStateRequirements(revision5).fields.map((field) => field.key),
  [
    "china_group_hospital_medical_total_limit",
    "china_group_hospital_medical_event_type",
  ],
);

const outpatientState = {
  china_group_hospital_medical_event_type: "outpatient_surgery",
};
assert.deepEqual(
  model
    .policyStateRequirements({
      ...revision5,
      policy_state: outpatientState,
    })
    .fields.map((field) => field.key),
  [
    "china_group_hospital_medical_total_limit",
    "china_group_hospital_medical_event_type",
    "china_group_hospital_medical_actual_expense",
  ],
);
const outpatient = valueFor(revision5, {
  ...outpatientState,
  china_group_hospital_medical_total_limit: 100_000,
  china_group_hospital_medical_actual_expense: 120_000,
});
assert.equal(outpatient.state, "calculated");
assert.equal(outpatient.value, 100_000);
assert.equal(outpatient.event_type, "outpatient_surgery");

const emergency = valueFor(revision5, {
  china_group_hospital_medical_event_type: "emergency_observation",
  china_group_hospital_medical_total_limit: 100_000,
  china_group_hospital_medical_actual_expense: 35_000,
});
assert.equal(emergency.value, 35_000);

assert.deepEqual(
  model
    .policyStateRequirements({
      ...revision5,
      policy_state: {
        china_group_hospital_medical_event_type: "inpatient",
      },
    })
    .fields.map((field) => field.key),
  [
    "china_group_hospital_medical_total_limit",
    "china_group_hospital_medical_event_type",
    "china_group_hospital_medical_actual_expense",
    "hospitalization_days",
    "china_group_hospital_room_meal_expense",
  ],
);

const uncertain = valueFor(revision5, {
  china_group_hospital_medical_event_type: "uncertain",
});
assert.equal(uncertain.state, "needs_insurer_confirmation");

const ineligible = valueFor(revision5, {
  china_group_hospital_medical_event_type: "confirmed_not_eligible",
});
assert.equal(ineligible.state, "not_eligible");
assert.equal(ineligible.value, 0);

console.log({
  status: "ok",
  batch_id: "tii-life-026",
  product_count: proposal.proposal_count,
  user_flow_cases: 13,
});

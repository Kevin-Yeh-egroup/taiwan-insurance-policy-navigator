const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-020-cathay-group-hospital-medical-limit-ab-v294.json",
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

function selected(schedule, planName, policyState = {}) {
  return {
    ...schedule,
    plan_name: planName,
    policy_state: { ...policyState },
  };
}

function result(item, entryId) {
  const entry = model
    .effectiveCoverageEntries(item)
    .find((candidate) => candidate.id === entryId);
  return model.coverageValue(entry, item);
}

const revision0 = scheduleFor("204317R11AMAA00");
assert.equal(model.selectionRequirements(revision0).mode, "plan");
assert.deepEqual(
  revision0.plan_options.map((option) => option.value),
  ["A", "B"],
);

const common = {
  cathay_group_quanyi_event_status:
    "eligible_disease_after_waiting",
  cathay_group_quanyi_nhi_status: "nhi_covered",
  cathay_group_quanyi_daily_room_limit: 1000,
  cathay_group_quanyi_max_hospital_days: 30,
  cathay_group_quanyi_inpatient_medical_limit: 50000,
  hospitalization_days: 40,
  hospital_room_expense: 50000,
  inpatient_medical_expense: 80000,
};

const planA = selected(revision0, "A", common);
assert.equal(result(planA, "daily-room-expense-benefit").value, 30000);
assert.equal(
  result(planA, "inpatient-medical-expense-benefit").value,
  50000,
);

const nonNhi = selected(revision0, "A", {
  ...common,
  cathay_group_quanyi_nhi_status: "not_nhi_covered",
  hospital_room_expense: 40000,
  inpatient_medical_expense: 60000,
});
assert.equal(result(nonNhi, "daily-room-expense-benefit").value, 26000);
assert.equal(
  result(nonNhi, "inpatient-medical-expense-benefit").value,
  39000,
);

const missingLimit = selected(revision0, "A", { ...common });
delete missingLimit.policy_state.cathay_group_quanyi_max_hospital_days;
assert.equal(
  result(missingLimit, "daily-room-expense-benefit").state,
  "needs_policy_state",
);

const planAWaiting = selected(revision0, "A", {
  ...common,
  cathay_group_quanyi_event_status: "disease_waiting_not_met",
});
assert.equal(
  result(planAWaiting, "daily-room-expense-benefit").state,
  "not_eligible",
);

const planBWaiting = selected(revision0, "B", {
  ...common,
  cathay_group_quanyi_event_status: "disease_waiting_not_met",
});
assert.equal(
  result(planBWaiting, "daily-room-expense-benefit").value,
  30000,
);

const oldNewborn = selected(revision0, "A", {
  ...common,
  cathay_group_quanyi_event_status:
    "eligible_newborn_screening_exception",
});
assert.equal(
  result(oldNewborn, "daily-room-expense-benefit").state,
  "needs_insurer_confirmation",
);

const revision4 = scheduleFor("204317R11AMAA04");
const newNewborn = selected(revision4, "A", {
  ...common,
  cathay_group_quanyi_event_status:
    "eligible_newborn_screening_exception",
});
assert.equal(result(newNewborn, "daily-room-expense-benefit").value, 30000);

const revision6 = scheduleFor("204313R11AMAA06");
const dayHospital = selected(revision6, "B", {
  ...common,
  cathay_group_quanyi_event_status: "day_hospital_or_day_stay",
});
assert.equal(
  result(dayHospital, "daily-room-expense-benefit").state,
  "not_eligible",
);

console.log({
  status: "ok",
  batch_id: "tii-life-020",
  product_count: proposal.proposal_count,
  user_flow_cases: 12,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-020-cathay-group-quanyi-hospital-medical-limit-health-rider-v272.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, planName, policyState = {}) {
  return {
    ...schedule,
    plan_name: planName,
    policy_state: { ...policyState },
  };
}

function coverageResult(item, entryId) {
  const entry = model
    .effectiveCoverageEntries(item)
    .find((candidate) => candidate.id === entryId);
  return model.coverageValue(entry, item);
}

const revision0 = scheduleFor("204317R11AWAA00");
assert.equal(model.selectionRequirements(revision0).mode, "plan");
assert.deepEqual(
  revision0.plan_options.map((option) => option.value),
  ["A", "B"],
);

const commonState = {
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
const planA = selectedSchedule(revision0, "A", commonState);
const room = coverageResult(planA, "daily-room-expense-benefit");
assert.equal(room.value, 30000);
assert.equal(room.eligible_quantity, 30);
assert.equal(room.policy_quantity_cap, 30);
assert.equal(
  coverageResult(planA, "inpatient-medical-expense-benefit").value,
  50000,
);

const nonNhi = selectedSchedule(revision0, "A", {
  ...commonState,
  cathay_group_quanyi_nhi_status: "not_nhi_covered",
  hospital_room_expense: 40000,
  inpatient_medical_expense: 60000,
});
assert.equal(
  coverageResult(nonNhi, "daily-room-expense-benefit").value,
  26000,
);
assert.equal(
  coverageResult(nonNhi, "inpatient-medical-expense-benefit").value,
  39000,
);

const missingLimit = selectedSchedule(revision0, "A", {
  ...commonState,
});
delete missingLimit.policy_state.cathay_group_quanyi_max_hospital_days;
assert.equal(
  coverageResult(missingLimit, "daily-room-expense-benefit").state,
  "needs_policy_state",
);

const waitingNotMet = selectedSchedule(revision0, "A", {
  ...commonState,
  cathay_group_quanyi_event_status: "disease_waiting_not_met",
});
assert.equal(
  coverageResult(waitingNotMet, "daily-room-expense-benefit").state,
  "not_eligible",
);

const oldNewbornException = selectedSchedule(revision0, "A", {
  ...commonState,
  cathay_group_quanyi_event_status:
    "eligible_newborn_screening_exception",
});
assert.equal(
  coverageResult(
    oldNewbornException,
    "daily-room-expense-benefit",
  ).state,
  "needs_insurer_confirmation",
);

const revision8 = scheduleFor(
  "204313RZ1AWA321A11Z10000008",
);
const newNewbornException = selectedSchedule(revision8, "A", {
  ...commonState,
  cathay_group_quanyi_event_status:
    "eligible_newborn_screening_exception",
});
assert.equal(
  coverageResult(
    newNewbornException,
    "daily-room-expense-benefit",
  ).value,
  30000,
);

assert.deepEqual(
  model.POLICY_STATE_FIELDS
    .cathay_group_quanyi_nhi_status.options.map(
      (option) => option.value,
    ),
  ["nhi_covered", "not_nhi_covered"],
);

console.log({
  status: "ok",
  batch_id: "tii-life-020",
  product_count: proposal.proposal_count,
  plan_count: 2,
  user_flow_cases: 11,
});

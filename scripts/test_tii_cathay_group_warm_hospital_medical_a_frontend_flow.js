const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-020-cathay-group-warm-hospital-medical-a-v295.json",
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

const revision0 = scheduleFor("204317R11AMLA00");
assert.equal(model.selectionRequirements(revision0).mode, "plan");
assert.deepEqual(
  revision0.plan_options.map((option) => option.value),
  Array.from({ length: 21 }, (_, index) => `M${index + 10}`),
);

const reimbursementState = {
  cathay_group_warm_event_status: "eligible_disease_waiting_met",
  cathay_group_warm_benefit_choice: "reimbursement",
  cathay_group_warm_nhi_status: "nhi_covered",
  cathay_group_warm_icu_limit_rate: "100",
  hospitalization_days: 10,
  hospital_room_expense: 12_000,
  inpatient_medical_expense: 250_000,
};

const m10 = selected(revision0, "M10", reimbursementState);
assert.equal(result(m10, "daily-room-expense-benefit").value, 10_000);
assert.equal(
  result(m10, "inpatient-medical-expense-benefit").value,
  100_000,
);
assert.equal(result(m10, "hospital-daily-benefit").state, "not_eligible");

const icu = selected(revision0, "M10", {
  ...reimbursementState,
  cathay_group_warm_icu_limit_rate: "200",
});
assert.equal(
  result(icu, "inpatient-medical-expense-benefit").value,
  200_000,
);

const nonNhi = selected(revision0, "M10", {
  ...reimbursementState,
  cathay_group_warm_nhi_status: "not_nhi_covered",
  hospital_room_expense: 8_000,
  inpatient_medical_expense: 120_000,
});
assert.equal(result(nonNhi, "daily-room-expense-benefit").value, 5_200);
assert.equal(
  result(nonNhi, "inpatient-medical-expense-benefit").value,
  78_000,
);

const daily = selected(revision0, "M10", {
  cathay_group_warm_event_status: "eligible_accident",
  cathay_group_warm_benefit_choice: "daily_cash",
  hospitalization_days: 10,
});
assert.equal(result(daily, "hospital-daily-benefit").value, 13_000);
assert.equal(result(daily, "daily-room-expense-benefit").state, "not_eligible");
assert.equal(
  result(daily, "inpatient-medical-expense-benefit").state,
  "not_eligible",
);

const m30Daily = selected(revision0, "M30", {
  cathay_group_warm_event_status: "eligible_accident",
  cathay_group_warm_benefit_choice: "daily_cash",
  hospitalization_days: 400,
});
assert.equal(result(m30Daily, "hospital-daily-benefit").value, 1_204_500);

const missingChoice = selected(revision0, "M10", {
  cathay_group_warm_event_status: "eligible_accident",
  hospitalization_days: 10,
});
assert.equal(
  result(missingChoice, "hospital-daily-benefit").state,
  "needs_policy_state",
);

const waiting = selected(revision0, "M10", {
  ...reimbursementState,
  cathay_group_warm_event_status: "disease_waiting_not_met",
});
assert.equal(result(waiting, "daily-room-expense-benefit").state, "not_eligible");

const oldNewborn = selected(revision0, "M10", {
  ...reimbursementState,
  cathay_group_warm_event_status: "eligible_newborn_screening_exception",
});
assert.equal(
  result(oldNewborn, "daily-room-expense-benefit").state,
  "needs_insurer_confirmation",
);

const revision4 = scheduleFor("204317R11AMLA04");
const newNewborn = selected(revision4, "M10", {
  ...reimbursementState,
  cathay_group_warm_event_status: "eligible_newborn_screening_exception",
});
assert.equal(result(newNewborn, "daily-room-expense-benefit").value, 10_000);

const revision6 = scheduleFor("204313R11AMLA06");
const dayHospital = selected(revision6, "M10", {
  ...reimbursementState,
  cathay_group_warm_event_status: "day_hospital_or_day_stay",
});
assert.equal(
  result(dayHospital, "daily-room-expense-benefit").state,
  "not_eligible",
);

console.log({
  status: "ok",
  batch_id: "tii-life-020",
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

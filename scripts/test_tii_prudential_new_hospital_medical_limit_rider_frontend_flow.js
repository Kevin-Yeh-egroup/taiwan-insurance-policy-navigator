const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-014-prudential-new-hospital-medical-limit-rider-v271.json",
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
    policy_state: policyState,
  };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [
      entry.id,
      entry,
    ]),
  );
}

function coverageResult(item, entryId) {
  return model.coverageValue(entriesFor(item)[entryId], item);
}

const revision0 = scheduleFor("203311R11A00300");
assert.equal(model.selectionRequirements(revision0).mode, "plan");
assert.deepEqual(
  revision0.plan_options.map((option) => option.value),
  ["I", "II", "III", "IV", "V", "VI"],
);

const commonState = {
  prudential_new_hospital_event_status:
    "eligible_formal_hospitalization",
  reimbursement_or_daily_cash_choice: "reimbursement",
  hospitalization_days: 40,
  general_ward_days: 35,
  intensive_care_days: 5,
  hospital_room_expense: 100_000,
  intensive_care_room_expense: 20_000,
  inpatient_surgery_expense: 80_000,
  inpatient_medical_expense: 100_000,
  outpatient_visit_count: 10,
  outpatient_medical_expense: 8_000,
  outpatient_surgery_expense: 40_000,
  outpatient_surgery_medical_expense: 30_000,
  surgery_benefit_rate_percent: 100,
  prudential_new_hospital_social_insurance_factor_60_percent: "100",
};
const planII = selectedSchedule(revision0, "II", commonState);

assert.equal(
  coverageResult(
    planII,
    "general-room-expense-reimbursement",
  ).value,
  35_000,
);
assert.equal(
  coverageResult(
    planII,
    "intensive-care-room-expense-reimbursement",
  ).value,
  10_000,
);
assert.equal(
  coverageResult(
    planII,
    "inpatient-surgery-expense-reimbursement",
  ).value,
  50_000,
);
const tieredMedical = coverageResult(
  planII,
  "inpatient-medical-expense-reimbursement",
);
assert.equal(tieredMedical.value, 45_000);
assert.deepEqual(tieredMedical.selected_amount_tier, {
  label: "住院 31 至 90 日",
  amount: 45_000,
});
assert.equal(
  coverageResult(
    planII,
    "pre-post-hospital-outpatient-reimbursement",
  ).value,
  5_000,
);
assert.equal(
  coverageResult(
    planII,
    "outpatient-surgery-fee-reimbursement",
  ).value,
  40_000,
);
assert.equal(
  coverageResult(
    planII,
    "outpatient-surgery-medical-reimbursement",
  ).value,
  30_000,
);
assert.equal(
  coverageResult(
    planII,
    "hospital-daily-cash-alternative",
  ).value,
  0,
);

const scenarios = model
  .coverageEventScenarios(planII)
  .filter(
    (scenario) =>
      scenario.benefit_group_id ===
      "prudential-new-hospital-reimbursement-or-daily-cash",
  );
assert.deepEqual(
  scenarios.map((scenario) => [scenario.event_key, scenario.value]),
  [
    ["reimbursement", 215_000],
    ["daily_cash", 0],
  ],
);

const reducedLimit = selectedSchedule(revision0, "II", {
  ...commonState,
  prudential_new_hospital_social_insurance_factor_60_percent: "60",
});
assert.equal(
  coverageResult(
    reducedLimit,
    "inpatient-medical-expense-reimbursement",
  ).value,
  27_000,
);
assert.equal(
  coverageResult(
    reducedLimit,
    "inpatient-surgery-expense-reimbursement",
  ).value,
  30_000,
);

const dailyCash = selectedSchedule(revision0, "II", {
  ...commonState,
  reimbursement_or_daily_cash_choice: "daily_cash",
});
assert.equal(
  coverageResult(
    dailyCash,
    "general-room-expense-reimbursement",
  ).value,
  0,
);
assert.equal(
  coverageResult(
    dailyCash,
    "hospital-daily-cash-alternative",
  ).value,
  40_000,
);

const revision8 = scheduleFor("203311R11A00308");
const excludedSixHour = selectedSchedule(revision8, "I", {
  ...commonState,
  prudential_new_hospital_event_status:
    "eligible_six_hour_continuous_treatment",
  prudential_new_hospital_nhi_factor_65_percent: "100",
});
assert.equal(
  coverageResult(
    excludedSixHour,
    "general-room-expense-reimbursement",
  ).state,
  "not_eligible",
);

const earlyDayHospital = selectedSchedule(revision0, "I", {
  ...commonState,
  prudential_new_hospital_event_status:
    "day_hospital_or_day_care",
});
assert.equal(
  coverageResult(
    earlyDayHospital,
    "general-room-expense-reimbursement",
  ).state,
  "needs_insurer_confirmation",
);

assert.deepEqual(
  model.POLICY_STATE_FIELDS
    .prudential_new_hospital_social_insurance_factor_60_percent
    .options.map((option) => option.value),
  ["100", "60"],
);
assert.deepEqual(
  model.POLICY_STATE_FIELDS
    .prudential_new_hospital_nhi_factor_65_percent
    .options.map((option) => option.value),
  ["100", "65"],
);

console.log({
  status: "ok",
  batch_id: "tii-life-014",
  product_count: proposal.proposal_count,
  plan_count: 6,
  user_flow_cases: 19,
});

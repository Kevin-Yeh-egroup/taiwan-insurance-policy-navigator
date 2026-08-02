const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-086-hongtai-hospital-medical-rider-v238.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 18);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, planName, policyState = {}) {
  return {
    ...schedule,
    plan_name: planName,
    unit_count: 10,
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

const revision0 = scheduleFor("217311R11A00100");
assert.equal(
  model.selectionRequirements(revision0).mode,
  "plan_unit",
);
assert.equal(
  revision0.version_characteristics.social_insurance_wording,
  true,
);

const planA = selectedSchedule(revision0, "A", {
  hospitalization_days: 5,
  intensive_care_days: 2,
  hospital_room_expense: 8_000,
  intensive_care_room_expense: 9_000,
  inpatient_medical_expense: 40_000,
  inpatient_surgery_expense: 20_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 50,
});
const planAEntries = entriesFor(planA);
assert.equal(Object.keys(planAEntries).length, 6);
assert.equal(
  model.coverageValue(
    planAEntries["daily-room-expense-reimbursement"],
    planA,
  ).value,
  5_000,
);
assert.equal(
  model.coverageValue(
    planAEntries["icu-room-expense-reimbursement"],
    planA,
  ).value,
  4_000,
);
assert.equal(
  model.coverageValue(
    planAEntries["post-icu-therapy-daily"],
    planA,
  ).value,
  2_000,
);
assert.equal(
  model.coverageValue(
    planAEntries[
      "inpatient-medical-expense-reimbursement"
    ],
    planA,
  ).value,
  30_000,
);
assert.equal(
  model.coverageValue(
    planAEntries[
      "inpatient-surgery-expense-reimbursement"
    ],
    planA,
  ).value,
  15_000,
);
assert.equal(
  model.coverageValue(
    planAEntries["plan-a-daily-cash-alternative"],
    planA,
  ).value,
  6_100,
);

const nonCoveredPlanA = selectedSchedule(revision0, "A", {
  hospitalization_days: 5,
  intensive_care_days: 2,
  hospital_room_expense: 8_000,
  intensive_care_room_expense: 9_000,
  inpatient_medical_expense: 40_000,
  inpatient_surgery_expense: 20_000,
  national_health_insurance_payment_status: "not_covered",
  surgery_benefit_rate_percent: 50,
});
const nonCoveredEntries = entriesFor(nonCoveredPlanA);
assert.equal(
  model.coverageValue(
    nonCoveredEntries[
      "inpatient-medical-expense-reimbursement"
    ],
    nonCoveredPlanA,
  ).value,
  28_000,
);
assert.equal(
  model.coverageValue(
    nonCoveredEntries[
      "inpatient-surgery-expense-reimbursement"
    ],
    nonCoveredPlanA,
  ).value,
  14_000,
);

const planB = selectedSchedule(revision0, "B", {
  hospitalization_days: 5,
});
const planBEntries = entriesFor(planB);
assert.deepEqual(Object.keys(planBEntries), [
  "plan-b-hospital-daily",
]);
assert.equal(
  model.coverageValue(
    planBEntries["plan-b-hospital-daily"],
    planB,
  ).value,
  5_000,
);

const missingDays = selectedSchedule(revision0, "A", {
  hospital_room_expense: 8_000,
  national_health_insurance_payment_status: "covered",
});
const missingDaysResult = model.coverageValue(
  entriesFor(missingDays)[
    "daily-room-expense-reimbursement"
  ],
  missingDays,
);
assert.equal(missingDaysResult.state, "needs_policy_state");
assert.deepEqual(missingDaysResult.required_fields, [
  "hospitalization_days",
]);

const missingSurgeryRate = selectedSchedule(revision0, "A", {
  inpatient_surgery_expense: 20_000,
  national_health_insurance_payment_status: "covered",
});
const missingSurgeryRateResult = model.coverageValue(
  entriesFor(missingSurgeryRate)[
    "inpatient-surgery-expense-reimbursement"
  ],
  missingSurgeryRate,
);
assert.equal(
  missingSurgeryRateResult.state,
  "needs_policy_state",
);
assert.deepEqual(missingSurgeryRateResult.required_fields, [
  "surgery_benefit_rate_percent",
]);

assert.equal(
  model.POLICY_STATE_FIELDS.hospital_room_expense.type,
  "non_negative_money",
);
assert.equal(
  model.POLICY_STATE_FIELDS.intensive_care_room_expense.type,
  "non_negative_money",
);
assert.equal(
  model.POLICY_STATE_FIELDS.inpatient_surgery_expense.type,
  "non_negative_money",
);

const revision5 = scheduleFor("217311R11A00105");
assert.equal(
  revision5.version_characteristics.therapy_benefit_term,
  "每日療養補助費用保險金",
);
const revision9 = scheduleFor("217311R11A00109");
assert.equal(
  revision9.version_characteristics
    .newborn_screening_waiting_exception,
  true,
);
const revision10 = scheduleFor("217311R11A00110");
assert.equal(
  revision10.version_characteristics
    .post_expiry_readmission_excluded,
  true,
);

console.log({
  status: "ok",
  batch_id: "tii-life-086",
  product_count: proposal.proposal_count,
  user_flow_cases: 24,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-062-mercantile-new-hospital-medical-rider-v248.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 16);

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

const revision0 = scheduleFor("211311R11A00600");
assert.equal(model.selectionRequirements(revision0).mode, "plan");
assert.equal(
  revision0.version_characteristics.social_insurance_wording,
  true,
);

const planB = selectedSchedule(revision0, "B", {
  hospitalization_days: 20,
  hospital_room_expense: 50_000,
  inpatient_medical_expense: 50_000,
  inpatient_surgery_expense: 100_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 200,
});
const planBEntries = entriesFor(planB);
assert.equal(Object.keys(planBEntries).length, 4);
assert.equal(
  model.coverageValue(
    planBEntries["daily-room-expense-reimbursement"],
    planB,
  ).value,
  20_000,
);
assert.equal(
  model.coverageValue(
    planBEntries["inpatient-medical-expense-reimbursement"],
    planB,
  ).value,
  30_000,
);
assert.equal(
  model.coverageValue(
    planBEntries["inpatient-surgery-expense-reimbursement"],
    planB,
  ).value,
  90_000,
);
assert.equal(
  model.coverageValue(
    planBEntries["hospital-daily-cash-alternative"],
    planB,
  ).value,
  20_000,
);

const overThirtyDays = selectedSchedule(revision0, "B", {
  hospitalization_days: 45,
  inpatient_medical_expense: 100_000,
  national_health_insurance_payment_status: "covered",
});
const overThirtyResult = model.coverageValue(
  entriesFor(overThirtyDays)[
    "inpatient-medical-expense-reimbursement"
  ],
  overThirtyDays,
);
assert.equal(overThirtyResult.value, 45_000);
assert.equal(overThirtyResult.eligible_quantity, 45);
assert.equal(overThirtyResult.limit_proration_threshold, 30);

const overOneHundredTwentyDays = selectedSchedule(revision0, "B", {
  hospitalization_days: 180,
  hospital_room_expense: 500_000,
  inpatient_medical_expense: 500_000,
  national_health_insurance_payment_status: "covered",
});
const cappedEntries = entriesFor(overOneHundredTwentyDays);
assert.equal(
  model.coverageValue(
    cappedEntries["daily-room-expense-reimbursement"],
    overOneHundredTwentyDays,
  ).value,
  120_000,
);
assert.equal(
  model.coverageValue(
    cappedEntries["inpatient-medical-expense-reimbursement"],
    overOneHundredTwentyDays,
  ).value,
  120_000,
);
assert.equal(
  model.coverageValue(
    cappedEntries["hospital-daily-cash-alternative"],
    overOneHundredTwentyDays,
  ).value,
  120_000,
);

const nonCovered = selectedSchedule(revision0, "B", {
  hospitalization_days: 120,
  inpatient_medical_expense: 100_000,
  national_health_insurance_payment_status: "not_covered",
});
assert.equal(
  model.coverageValue(
    entriesFor(nonCovered)[
      "inpatient-medical-expense-reimbursement"
    ],
    nonCovered,
  ).value,
  66_000,
);

const missingDays = selectedSchedule(revision0, "B", {
  inpatient_medical_expense: 50_000,
  national_health_insurance_payment_status: "covered",
});
const missingDaysResult = model.coverageValue(
  entriesFor(missingDays)[
    "inpatient-medical-expense-reimbursement"
  ],
  missingDays,
);
assert.equal(missingDaysResult.state, "needs_policy_state");
assert.deepEqual(missingDaysResult.required_fields, [
  "hospitalization_days",
]);

const missingSurgeryRate = selectedSchedule(revision0, "B", {
  inpatient_surgery_expense: 100_000,
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

const planF = selectedSchedule(revision0, "F", {
  hospitalization_days: 31,
  inpatient_medical_expense: 200_000,
  national_health_insurance_payment_status: "covered",
});
assert.equal(
  model.coverageValue(
    entriesFor(planF)[
      "inpatient-medical-expense-reimbursement"
    ],
    planF,
  ).value,
  124_000,
);

const revision9 = scheduleFor("211311R11A00609");
assert.equal(
  revision9.version_characteristics
    .designated_physician_expense_included,
  false,
);
const revision10 = scheduleFor("211311R11A00610");
assert.equal(
  revision10.version_characteristics
    .post_expiry_readmission_excluded,
  true,
);
const revision11 = scheduleFor("211311R11A00611");
assert.equal(
  revision11.version_characteristics.day_hospital_excluded,
  true,
);

console.log({
  status: "ok",
  batch_id: "tii-life-062",
  product_count: proposal.proposal_count,
  user_flow_cases: 23,
});

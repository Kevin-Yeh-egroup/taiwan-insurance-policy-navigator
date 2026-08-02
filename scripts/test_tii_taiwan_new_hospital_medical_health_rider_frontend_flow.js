const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-008-taiwan-new-hospital-medical-health-rider-v268.json",
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

const revision1 = scheduleFor("202311R11AG9A01");
assert.equal(model.selectionRequirements(revision1).mode, "plan");
assert.deepEqual(
  revision1.plan_options.map((option) => option.value),
  ["HS-5", "HS-7", "HS-10", "HS-15", "HS-20", "HS-25", "HS-30"],
);

const eligibleReimbursement = selectedSchedule(
  revision1,
  "HS-20",
  {
    taiwan_inpatient_daily_event_status:
      "eligible_disease_after_waiting_period",
    medical_claim_receipt_status: "original_receipt",
    hospitalization_days: 10,
    hospital_room_expense: 30_000,
    inpatient_medical_expense: 80_000,
    inpatient_surgery_expense: 120_000,
    national_health_insurance_payment_status: "covered",
    surgery_benefit_rate_percent: 200,
    specific_surgery_count: 1,
  },
);
const eligibleEntries = entriesFor(eligibleReimbursement);
assert.equal(
  model.coverageValue(
    eligibleEntries["daily-room-expense-reimbursement"],
    eligibleReimbursement,
  ).value,
  20_000,
);
assert.equal(
  model.coverageValue(
    eligibleEntries["inpatient-medical-expense-reimbursement"],
    eligibleReimbursement,
  ).value,
  60_000,
);
assert.equal(
  model.coverageValue(
    eligibleEntries["inpatient-surgery-expense-reimbursement"],
    eligibleReimbursement,
  ).value,
  100_000,
);
assert.equal(
  model.coverageValue(
    eligibleEntries[
      "specific-surgery-discharge-recuperation-benefit"
    ],
    eligibleReimbursement,
  ).value,
  40_000,
);
assert.equal(
  model.coverageValue(
    eligibleEntries["hospital-daily-cash-alternative"],
    eligibleReimbursement,
  ).state,
  "not_eligible",
);

const nonCovered = selectedSchedule(revision1, "HS-20", {
  taiwan_inpatient_daily_event_status: "eligible_accident",
  medical_claim_receipt_status: "original_receipt",
  hospitalization_days: 10,
  inpatient_medical_expense: 80_000,
  national_health_insurance_payment_status: "not_covered",
});
assert.equal(
  model.coverageValue(
    entriesFor(nonCovered)[
      "inpatient-medical-expense-reimbursement"
    ],
    nonCovered,
  ).value,
  52_000,
);

const noReceipt = selectedSchedule(revision1, "HS-20", {
  taiwan_inpatient_daily_event_status: "eligible_accident",
  medical_claim_receipt_status:
    "no_original_receipt_daily_cash",
  hospitalization_days: 10,
});
const noReceiptEntries = entriesFor(noReceipt);
assert.equal(
  model.coverageValue(
    noReceiptEntries["hospital-daily-cash-alternative"],
    noReceipt,
  ).value,
  20_000,
);
for (const entryId of [
  "daily-room-expense-reimbursement",
  "inpatient-medical-expense-reimbursement",
  "inpatient-surgery-expense-reimbursement",
  "specific-surgery-discharge-recuperation-benefit",
]) {
  const result = model.coverageValue(
    noReceiptEntries[entryId],
    noReceipt,
  );
  assert.equal(result.state, "not_eligible");
  assert.equal(result.value, 0);
}

const waitingPeriod = selectedSchedule(revision1, "HS-5", {
  taiwan_inpatient_daily_event_status:
    "disease_within_waiting_period",
  medical_claim_receipt_status: "original_receipt",
  hospitalization_days: 3,
  hospital_room_expense: 1_500,
  national_health_insurance_payment_status: "covered",
});
const waitingResult = model.coverageValue(
  entriesFor(waitingPeriod)["daily-room-expense-reimbursement"],
  waitingPeriod,
);
assert.equal(waitingResult.state, "not_eligible");
assert.equal(waitingResult.value, 0);

const earlyDayHospital = selectedSchedule(revision1, "HS-5", {
  taiwan_inpatient_daily_event_status: "day_hospital_or_day_care",
  medical_claim_receipt_status: "original_receipt",
  hospitalization_days: 1,
  hospital_room_expense: 500,
  national_health_insurance_payment_status: "covered",
});
assert.equal(
  model.coverageValue(
    entriesFor(earlyDayHospital)[
      "daily-room-expense-reimbursement"
    ],
    earlyDayHospital,
  ).state,
  "needs_insurer_confirmation",
);

const revision9 = scheduleFor("202311R11AG9A09");
const excludedDayHospital = selectedSchedule(
  revision9,
  "HS-5",
  {
    taiwan_inpatient_daily_event_status:
      "day_hospital_or_day_care",
    medical_claim_receipt_status: "original_receipt",
    hospitalization_days: 1,
    hospital_room_expense: 500,
    national_health_insurance_payment_status: "covered",
  },
);
assert.equal(
  model.coverageValue(
    entriesFor(excludedDayHospital)[
      "daily-room-expense-reimbursement"
    ],
    excludedDayHospital,
  ).state,
  "not_eligible",
);

const uncertain = selectedSchedule(revision9, "HS-5", {
  taiwan_inpatient_daily_event_status:
    "not_eligible_or_uncertain",
  medical_claim_receipt_status: "original_receipt",
  hospitalization_days: 1,
  hospital_room_expense: 500,
  national_health_insurance_payment_status: "covered",
});
const uncertainResult = model.coverageValue(
  entriesFor(uncertain)["daily-room-expense-reimbursement"],
  uncertain,
);
assert.equal(
  uncertainResult.state,
  "needs_insurer_confirmation",
);
assert.equal(
  uncertainResult.confirmation_reason,
  "claim_eligibility_uncertain",
);

const missingEligibility = selectedSchedule(revision9, "HS-5", {
  medical_claim_receipt_status: "original_receipt",
  hospitalization_days: 1,
  hospital_room_expense: 500,
  national_health_insurance_payment_status: "covered",
});
assert.deepEqual(
  model.coverageValue(
    entriesFor(missingEligibility)[
      "daily-room-expense-reimbursement"
    ],
    missingEligibility,
  ).required_fields,
  ["taiwan_inpatient_daily_event_status"],
);

const missingReceipt = selectedSchedule(revision9, "HS-5", {
  taiwan_inpatient_daily_event_status: "eligible_accident",
  hospitalization_days: 1,
  hospital_room_expense: 500,
  national_health_insurance_payment_status: "covered",
});
assert.deepEqual(
  model.coverageValue(
    entriesFor(missingReceipt)[
      "daily-room-expense-reimbursement"
    ],
    missingReceipt,
  ).required_fields,
  ["medical_claim_receipt_status"],
);

const surgeryRateBounds = selectedSchedule(revision9, "HS-5", {
  taiwan_inpatient_daily_event_status: "eligible_accident",
  medical_claim_receipt_status: "original_receipt",
  inpatient_surgery_expense: 200_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 500,
});
assert.equal(
  model.coverageValue(
    entriesFor(surgeryRateBounds)[
      "inpatient-surgery-expense-reimbursement"
    ],
    surgeryRateBounds,
  ).state,
  "needs_policy_state",
);

console.log({
  status: "ok",
  batch_id: "tii-life-008",
  product_count: proposal.proposal_count,
  plan_count: 7,
  user_flow_cases: 18,
});

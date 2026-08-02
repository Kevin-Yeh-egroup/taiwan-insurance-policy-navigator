const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-086-hongtai-group-hospital-medical-reimbursement-v265.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 15);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, policyState = {}) {
  return {
    ...schedule,
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

const revision0 = scheduleFor("217317M11A00200");
assert.equal(model.selectionRequirements(revision0).mode, "unit");
assert.equal(
  revision0.version_characteristics.non_nhi_payment_rate_percent,
  65,
);

const covered = selectedSchedule(revision0, {
  hospitalization_days: 5,
  hospital_room_expense: 8_000,
  inpatient_medical_expense: 40_000,
  inpatient_surgery_expense: 20_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 50,
});
const coveredEntries = entriesFor(covered);
assert.equal(
  model.coverageValue(
    coveredEntries["daily-room-expense-reimbursement"],
    covered,
  ).value,
  5_000,
);
assert.equal(
  model.coverageValue(
    coveredEntries["inpatient-medical-expense-reimbursement"],
    covered,
  ).value,
  30_000,
);
assert.equal(
  model.coverageValue(
    coveredEntries["inpatient-surgery-expense-reimbursement"],
    covered,
  ).value,
  15_000,
);

const nonCovered = selectedSchedule(revision0, {
  hospitalization_days: 5,
  hospital_room_expense: 8_000,
  inpatient_medical_expense: 40_000,
  inpatient_surgery_expense: 20_000,
  national_health_insurance_payment_status: "not_covered",
  surgery_benefit_rate_percent: 50,
});
const nonCoveredEntries = entriesFor(nonCovered);
assert.equal(
  model.coverageValue(
    nonCoveredEntries["inpatient-medical-expense-reimbursement"],
    nonCovered,
  ).value,
  26_000,
);
assert.equal(
  model.coverageValue(
    nonCoveredEntries["inpatient-surgery-expense-reimbursement"],
    nonCovered,
  ).value,
  13_000,
);

const revision9 = scheduleFor("217313M11A00209");
const notifiedDayHospital = selectedSchedule(revision9, {
  hospital_medical_claim_mode:
    "day_hospital_no_other_or_notified",
  hospitalization_days: 0,
  hospital_room_expense: 0,
  inpatient_medical_expense: 0,
  inpatient_surgery_expense: 0,
  day_hospital_medical_expense: 25_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 50,
});
const notifiedEntries = entriesFor(notifiedDayHospital);
assert.equal(
  model.coverageValue(
    notifiedEntries["daily-room-expense-reimbursement"],
    notifiedDayHospital,
  ).state,
  "not_eligible",
);
assert.equal(
  model.coverageValue(
    notifiedEntries["day-hospital-medical-expense-reimbursement"],
    notifiedDayHospital,
  ).value,
  25_000,
);
assert.equal(
  model.coverageValue(
    notifiedEntries["day-hospital-daily-cash-fallback"],
    notifiedDayHospital,
  ).state,
  "not_eligible",
);

const unnotifiedDayHospital = selectedSchedule(revision9, {
  hospital_medical_claim_mode:
    "day_hospital_unnotified_other_reimbursement",
  day_hospital_days: 3,
  day_hospital_daily_cash_amount: 800,
});
const unnotifiedEntries = entriesFor(unnotifiedDayHospital);
assert.equal(
  model.coverageValue(
    unnotifiedEntries[
      "day-hospital-medical-expense-reimbursement"
    ],
    unnotifiedDayHospital,
  ).state,
  "not_eligible",
);
assert.equal(
  model.coverageValue(
    unnotifiedEntries["day-hospital-daily-cash-fallback"],
    unnotifiedDayHospital,
  ).value,
  2_400,
);

const missingRecordedDailyAmount = selectedSchedule(revision9, {
  hospital_medical_claim_mode:
    "day_hospital_unnotified_other_reimbursement",
  day_hospital_days: 3,
});
assert.deepEqual(
  model.coverageValue(
    entriesFor(missingRecordedDailyAmount)[
      "day-hospital-daily-cash-fallback"
    ],
    missingRecordedDailyAmount,
  ).required_fields,
  ["day_hospital_daily_cash_amount"],
);

assert.equal(
  model.POLICY_STATE_FIELDS.day_hospital_medical_expense.type,
  "non_negative_money",
);
assert.equal(
  model.POLICY_STATE_FIELDS.day_hospital_days.type,
  "integer",
);
assert.equal(
  model.POLICY_STATE_FIELDS.day_hospital_daily_cash_amount.type,
  "non_negative_money",
);
assert.equal(
  model.POLICY_STATE_FIELDS.hospital_medical_claim_mode.type,
  "choice",
);

console.log({
  status: "ok",
  batch_id: "tii-life-086",
  product_count: proposal.proposal_count,
  user_flow_cases: 18,
});

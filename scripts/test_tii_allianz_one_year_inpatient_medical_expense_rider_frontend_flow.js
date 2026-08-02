const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-092-allianz-one-year-inpatient-medical-expense-rider-v266.json",
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

const revision3 = scheduleFor("218311R12D00203");
assert.equal(model.selectionRequirements(revision3).mode, "unit");
assert.equal(
  revision3.version_characteristics
    .non_health_insurance_payment_rate_percent,
  70,
);

const reimbursement = selectedSchedule(revision3, {
  reimbursement_or_daily_cash_choice: "reimbursement",
  hospitalization_days: 5,
  hospital_room_expense: 8_000,
  inpatient_medical_expense: 40_000,
  inpatient_surgery_expense: 30_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 50,
});
const reimbursementEntries = entriesFor(reimbursement);
assert.equal(
  model.coverageValue(
    reimbursementEntries["daily-room-expense-reimbursement"],
    reimbursement,
  ).value,
  5_000,
);
assert.equal(
  model.coverageValue(
    reimbursementEntries[
      "inpatient-medical-expense-reimbursement"
    ],
    reimbursement,
  ).value,
  30_000,
);
assert.equal(
  model.coverageValue(
    reimbursementEntries[
      "inpatient-surgery-expense-reimbursement"
    ],
    reimbursement,
  ).value,
  20_000,
);
assert.equal(
  model.coverageValue(
    reimbursementEntries["hospital-daily-cash-alternative"],
    reimbursement,
  ).state,
  "not_eligible",
);

const nonCovered = selectedSchedule(revision3, {
  reimbursement_or_daily_cash_choice: "reimbursement",
  hospitalization_days: 5,
  hospital_room_expense: 8_000,
  inpatient_medical_expense: 40_000,
  inpatient_surgery_expense: 12_000,
  national_health_insurance_payment_status: "not_covered",
  surgery_benefit_rate_percent: 50,
});
const nonCoveredEntries = entriesFor(nonCovered);
assert.equal(
  model.coverageValue(
    nonCoveredEntries[
      "inpatient-medical-expense-reimbursement"
    ],
    nonCovered,
  ).value,
  28_000,
);
assert.equal(
  model.coverageValue(
    nonCoveredEntries[
      "inpatient-surgery-expense-reimbursement"
    ],
    nonCovered,
  ).value,
  8_400,
);

const dailyCash = selectedSchedule(revision3, {
  reimbursement_or_daily_cash_choice: "daily_cash",
  hospitalization_days: 5,
});
const dailyCashEntries = entriesFor(dailyCash);
assert.equal(
  model.coverageValue(
    dailyCashEntries["daily-room-expense-reimbursement"],
    dailyCash,
  ).state,
  "not_eligible",
);
assert.equal(
  model.coverageValue(
    dailyCashEntries["hospital-daily-cash-alternative"],
    dailyCash,
  ).value,
  6_000,
);

const overThirtyDays = selectedSchedule(revision3, {
  reimbursement_or_daily_cash_choice: "reimbursement",
  hospitalization_days: 45,
  inpatient_medical_expense: 200_000,
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

const cappedDays = selectedSchedule(revision3, {
  reimbursement_or_daily_cash_choice: "daily_cash",
  hospitalization_days: 180,
});
assert.equal(
  model.coverageValue(
    entriesFor(cappedDays)["hospital-daily-cash-alternative"],
    cappedDays,
  ).value,
  144_000,
);

const missingChoice = selectedSchedule(revision3, {
  hospitalization_days: 5,
  hospital_room_expense: 8_000,
  national_health_insurance_payment_status: "covered",
});
assert.deepEqual(
  model.coverageValue(
    entriesFor(missingChoice)["daily-room-expense-reimbursement"],
    missingChoice,
  ).required_fields,
  ["reimbursement_or_daily_cash_choice"],
);

assert.equal(
  scheduleFor("218311R12D00205").version_characteristics
    .annual_same_hospitalization_day_limit,
  true,
);
assert.equal(
  scheduleFor("218311R12D00206").version_characteristics
    .annual_same_hospitalization_day_limit,
  false,
);
assert.equal(
  scheduleFor("218311R12D00211").version_characteristics
    .post_expiry_readmission_excluded,
  true,
);
assert.equal(
  scheduleFor("218311R12D00212").version_characteristics
    .day_hospital_excluded,
  true,
);
assert.equal(
  scheduleFor(
    "218311RZ1A00521A11Z10000013",
  ).version_characteristics.source_text_extractor,
  "pymupdf",
);
assert.equal(
  model.POLICY_STATE_FIELDS.reimbursement_or_daily_cash_choice.type,
  "choice",
);

console.log({
  status: "ok",
  batch_id: "tii-life-092",
  product_count: proposal.proposal_count,
  user_flow_cases: 25,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-002-bank-taiwan-group-one-year-hospital-medical-health-rider-v290.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);
assert.equal(proposal.proposed_count, 13);
assert.equal(proposal.manual_review_count, 0);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, planName, unitCount, policyState = {}) {
  return {
    ...schedule,
    plan_name: planName,
    unit_count: unitCount,
    policy_state: policyState,
  };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [entry.id, entry]),
  );
}

const revision2 = scheduleFor("201317R11A05A02");
assert.equal(model.selectionRequirements(revision2).mode, "plan_unit");
assert.deepEqual(model.selectionRequirements(revision2).fields, [
  "plan_name",
  "unit_count",
]);

const covered = selectedSchedule(revision2, "reimbursement", 2, {
  hospitalization_days: 3,
  hospital_room_expense: 5_000,
  inpatient_medical_expense: 30_000,
  inpatient_surgery_expense: 12_000,
  national_health_insurance_payment_status: "covered",
});
const coveredEntries = entriesFor(covered);
assert.equal(
  model.coverageValue(
    coveredEntries["daily-room-expense-reimbursement"],
    covered,
  ).value,
  3_000,
);
assert.equal(
  model.coverageValue(
    coveredEntries["inpatient-medical-expense-reimbursement"],
    covered,
  ).value,
  20_000,
);
assert.equal(
  model.coverageValue(
    coveredEntries["inpatient-surgery-expense-reimbursement"],
    covered,
  ).value,
  12_000,
);

const notCovered = selectedSchedule(revision2, "reimbursement", 2, {
  hospitalization_days: 3,
  hospital_room_expense: 5_000,
  inpatient_medical_expense: 30_000,
  inpatient_surgery_expense: 12_000,
  national_health_insurance_payment_status: "not_covered",
});
const notCoveredEntries = entriesFor(notCovered);
assert.equal(
  model.coverageValue(
    notCoveredEntries["daily-room-expense-reimbursement"],
    notCovered,
  ).value,
  3_000,
);
assert.equal(
  model.coverageValue(
    notCoveredEntries["inpatient-medical-expense-reimbursement"],
    notCovered,
  ).value,
  20_000,
);
assert.equal(
  model.coverageValue(
    notCoveredEntries["inpatient-surgery-expense-reimbursement"],
    notCovered,
  ).value,
  8_400,
);

const daily = selectedSchedule(revision2, "daily", 2, {
  hospitalization_days: 400,
});
assert.equal(
  model.coverageValue(
    entriesFor(daily)["hospital-daily-benefit"],
    daily,
  ).value,
  365_000,
);

const invalidFractionalUnits = selectedSchedule(revision2, "daily", 1.5, {
  hospitalization_days: 3,
});
assert.equal(
  model.coverageValue(
    entriesFor(invalidFractionalUnits)["hospital-daily-benefit"],
    invalidFractionalUnits,
  ).state,
  "needs_unit_count",
);

const aboveContractMaximum = selectedSchedule(revision2, "daily", 6, {
  hospitalization_days: 3,
});
assert.equal(
  model.coverageValue(
    entriesFor(aboveContractMaximum)["hospital-daily-benefit"],
    aboveContractMaximum,
  ).state,
  "needs_unit_count",
);

const revision1 = scheduleFor("201317R11A05A01");
const missingLegacyStatus = selectedSchedule(
  revision1,
  "reimbursement",
  2,
  {
    hospitalization_days: 3,
    hospital_room_expense: 5_000,
    inpatient_medical_expense: 30_000,
    inpatient_surgery_expense: 12_000,
  },
);
const legacyRoom = entriesFor(missingLegacyStatus)[
  "daily-room-expense-reimbursement"
];
assert.equal(
  model.coverageValue(legacyRoom, missingLegacyStatus).state,
  "needs_policy_state",
);
assert.deepEqual(
  model.coverageValue(legacyRoom, missingLegacyStatus).required_fields,
  ["bank_taiwan_legacy_reimbursement_eligibility_status"],
);

const ineligibleLegacy = selectedSchedule(
  revision1,
  "reimbursement",
  2,
  {
    hospitalization_days: 3,
    hospital_room_expense: 5_000,
    inpatient_medical_expense: 30_000,
    inpatient_surgery_expense: 12_000,
    bank_taiwan_legacy_reimbursement_eligibility_status:
      "missing_social_insurance_or_original_receipt",
  },
);
assert.equal(
  model.coverageValue(entriesFor(ineligibleLegacy)[
    "daily-room-expense-reimbursement"
  ], ineligibleLegacy).state,
  "not_eligible",
);

const uncertainLegacy = selectedSchedule(
  revision1,
  "reimbursement",
  2,
  {
    hospitalization_days: 3,
    hospital_room_expense: 5_000,
    inpatient_medical_expense: 30_000,
    inpatient_surgery_expense: 12_000,
    bank_taiwan_legacy_reimbursement_eligibility_status: "uncertain",
  },
);
assert.equal(
  model.coverageValue(entriesFor(uncertainLegacy)[
    "daily-room-expense-reimbursement"
  ], uncertainLegacy).state,
  "needs_insurer_confirmation",
);

const eligibleLegacy = selectedSchedule(
  revision1,
  "reimbursement",
  2,
  {
    hospitalization_days: 3,
    hospital_room_expense: 5_000,
    inpatient_medical_expense: 30_000,
    inpatient_surgery_expense: 12_000,
    bank_taiwan_legacy_reimbursement_eligibility_status:
      "social_insurance_and_original_receipt",
  },
);
assert.equal(
  model.coverageValue(entriesFor(eligibleLegacy)[
    "inpatient-surgery-expense-reimbursement"
  ], eligibleLegacy).value,
  12_000,
);

const legacyDaily = selectedSchedule(revision1, "daily", 2, {
  hospitalization_days: 3,
});
assert.equal(
  model.coverageValue(
    entriesFor(legacyDaily)["hospital-daily-benefit"],
    legacyDaily,
  ).value,
  3_000,
);

assert.equal(
  model.POLICY_STATE_FIELDS[
    "bank_taiwan_legacy_reimbursement_eligibility_status"
  ].type,
  "choice",
);

console.log({
  status: "ok",
  batch_id: "tii-life-002",
  product_count: proposal.proposal_count,
  user_flow_cases: 19,
});

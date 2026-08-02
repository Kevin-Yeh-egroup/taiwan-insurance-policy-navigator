const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-080-farglory-group-anjia-hospital-medical-rider-a-v280.json",
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

function itemFor(schedule, policyState) {
  return {
    ...schedule,
    policy_state: { ...policyState },
  };
}

function coverageResult(item, entryId) {
  const entry = model
    .effectiveCoverageEntries(item)
    .find((candidate) => candidate.id === entryId);
  return model.coverageValue(entry, item);
}

function scenario(item, eventKey) {
  return model
    .coverageEventScenarios(item)
    .find((candidate) => candidate.event_key === eventKey);
}

const revision7 = scheduleFor("216312R12B62507");
assert.equal(model.selectionRequirements(revision7).mode, "policy_state");

const commonState = {
  farglory_anjia_event_status: "eligible_accident",
  national_health_insurance_payment_status: "covered",
  farglory_anjia_daily_room_limit: 2000,
  farglory_anjia_daily_physician_limit: 500,
  farglory_anjia_inpatient_medical_limit: 50000,
  farglory_anjia_surgery_base_limit: 100000,
  farglory_anjia_hospital_day_limit: 30,
  hospitalization_days: 4,
  general_ward_days: 3,
  intensive_care_days: 1,
  hospital_room_expense: 7000,
  intensive_care_room_expense: 8000,
  physician_examination_expense: 2500,
  inpatient_medical_expense: 60000,
  surgery_medical_expense: 70000,
  surgery_benefit_rate_percent: 50,
};
const covered = itemFor(revision7, commonState);
assert.equal(
  coverageResult(covered, "hospital-room-expense-benefit").value,
  6000,
);
assert.equal(
  coverageResult(
    covered,
    "intensive-care-room-expense-benefit",
  ).value,
  6000,
);
assert.equal(
  coverageResult(
    covered,
    "physician-examination-expense-benefit",
  ).value,
  2000,
);
assert.equal(
  coverageResult(
    covered,
    "inpatient-medical-expense-benefit",
  ).value,
  50000,
);
assert.equal(
  coverageResult(covered, "surgery-expense-benefit").value,
  50000,
);
assert.equal(scenario(covered, "reimbursement").value, 114000);
assert.equal(scenario(covered, "daily_cash").value, 8000);

const nonNhi = itemFor(revision7, {
  ...commonState,
  national_health_insurance_payment_status: "not_covered",
});
assert.equal(scenario(nonNhi, "reimbursement").value, 97350);
assert.equal(scenario(nonNhi, "daily_cash").value, 8000);

const missingLimit = itemFor(revision7, { ...commonState });
delete missingLimit.policy_state.farglory_anjia_daily_physician_limit;
assert.equal(
  coverageResult(
    missingLimit,
    "physician-examination-expense-benefit",
  ).state,
  "needs_policy_state",
);

const waitingNotMet = itemFor(revision7, {
  ...commonState,
  farglory_anjia_event_status: "disease_waiting_not_met",
});
assert.equal(
  coverageResult(
    waitingNotMet,
    "hospital-room-expense-benefit",
  ).state,
  "not_eligible",
);

const revision6 = scheduleFor("216312R12B62506");
const oldDayHospital = itemFor(revision6, {
  ...commonState,
  farglory_anjia_event_status: "day_hospital_or_day_care",
});
assert.equal(
  coverageResult(
    oldDayHospital,
    "hospital-room-expense-benefit",
  ).state,
  "needs_insurer_confirmation",
);

const excludedDayHospital = itemFor(revision7, {
  ...commonState,
  farglory_anjia_event_status: "day_hospital_or_day_care",
});
assert.equal(
  coverageResult(
    excludedDayHospital,
    "hospital-room-expense-benefit",
  ).state,
  "not_eligible",
);

const revision5 = scheduleFor("216312R12B62505");
const newbornException = itemFor(revision5, {
  ...commonState,
  farglory_anjia_event_status:
    "eligible_newborn_screening_exception",
});
assert.equal(
  coverageResult(
    newbornException,
    "hospital-room-expense-benefit",
  ).value,
  6000,
);

const revision9 = scheduleFor(
  "216313RZ1A62521A11Z10000009",
);
const removedNewbornException = itemFor(revision9, {
  ...commonState,
  farglory_anjia_event_status:
    "eligible_newborn_screening_exception",
});
assert.equal(
  coverageResult(
    removedNewbornException,
    "hospital-room-expense-benefit",
  ).state,
  "needs_insurer_confirmation",
);

assert.deepEqual(
  model.POLICY_STATE_FIELDS
    .farglory_anjia_event_status.options.map(
      (option) => option.value,
    ),
  [
    "eligible_disease_waiting_met",
    "eligible_accident",
    "eligible_newborn_screening_exception",
    "day_hospital_or_day_care",
    "disease_waiting_not_met",
    "confirmed_not_eligible",
    "uncertain",
  ],
);

console.log({
  status: "ok",
  batch_id: "tii-life-080",
  product_count: proposal.proposal_count,
  choice_scenarios: 2,
  user_flow_cases: 15,
});

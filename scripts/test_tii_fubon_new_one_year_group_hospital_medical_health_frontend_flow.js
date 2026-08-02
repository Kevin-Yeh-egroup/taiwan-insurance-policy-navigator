const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-new-one-year-group-hospital-medical-health-v302.json",
    ),
    "utf8",
  ),
);

function scheduleFor(productId) {
  return proposal.proposals.find((item) => item.product_id === productId)
    .candidates[0].schedule;
}

function selectedSchedule(schedule, policyState) {
  return { ...schedule, policy_state: policyState };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [entry.id, entry]),
  );
}

function value(item, entryId) {
  return model.coverageValue(entriesFor(item)[entryId], item);
}

assert.equal(proposal.proposal_count, 13);
const revision0 = scheduleFor("209313M11A00206");
assert.equal(model.selectionRequirements(revision0).mode, "policy_state");

const state = {
  fubon_new_group_hospital_event_claim_status:
    "reimbursement_disease_after_waiting",
  fubon_new_group_hospital_room_daily_limit: 3_000,
  fubon_new_group_hospital_medical_limit: 100_000,
  fubon_new_group_hospital_surgery_limit: 50_000,
  fubon_new_group_hospital_max_days: 30,
  fubon_new_group_hospital_icu_daily_limit: 5_000,
  fubon_new_group_hospital_icu_max_days: 10,
  fubon_new_group_hospital_burn_daily_limit: 4_000,
  fubon_new_group_hospital_burn_max_days: 10,
  fubon_new_group_hospital_special_agreement_status: "both_included",
  hospitalization_days: 10,
  hospital_room_expense: 40_000,
  inpatient_medical_expense: 120_000,
  inpatient_surgery_expense: 40_000,
  intensive_care_days: 3,
  intensive_care_room_expense: 20_000,
  burn_unit_days: 2,
  burn_unit_room_expense: 9_000,
  surgery_benefit_rate_percent: 50,
  national_health_insurance_payment_status: "covered",
};
const selected = selectedSchedule(revision0, state);
assert.equal(value(selected, "room-and-board-reimbursement").value, 30_000);
assert.equal(value(selected, "hospital-medical-reimbursement").value, 100_000);
assert.equal(value(selected, "surgery-reimbursement").value, 25_000);
assert.equal(value(selected, "intensive-care-reimbursement").value, 15_000);
assert.equal(value(selected, "burn-center-reimbursement").value, 8_000);
assert.equal(value(selected, "hospital-daily-cash-alternative").state, "not_eligible");
assert.equal(value(selected, "accident-emergency-expense-sublimit").value, 5_000);
assert.equal(value(selected, "accident-emergency-expense-sublimit").result_kind, "reference");

const nonNhi = selectedSchedule(revision0, {
  ...state,
  national_health_insurance_payment_status: "not_covered",
});
assert.equal(value(nonNhi, "room-and-board-reimbursement").value, 26_000);
assert.equal(value(nonNhi, "hospital-medical-reimbursement").value, 78_000);
assert.equal(value(nonNhi, "surgery-reimbursement").value, 25_000);

const noIcuAgreement = selectedSchedule(revision0, {
  ...state,
  fubon_new_group_hospital_special_agreement_status: "burn_only",
});
assert.equal(value(noIcuAgreement, "intensive-care-reimbursement").state, "not_eligible");
assert.equal(value(noIcuAgreement, "burn-center-reimbursement").value, 8_000);

const dailyCash = selectedSchedule(revision0, {
  ...state,
  fubon_new_group_hospital_event_claim_status:
    "daily_cash_disease_after_waiting",
});
assert.equal(value(dailyCash, "room-and-board-reimbursement").state, "not_eligible");
assert.equal(value(dailyCash, "hospital-daily-cash-alternative").value, 30_000);

const excludedDayHospital = selectedSchedule(revision0, {
  ...state,
  fubon_new_group_hospital_event_claim_status: "day_hospital_or_day_care",
});
assert.equal(value(excludedDayHospital, "room-and-board-reimbursement").state, "not_eligible");

const revision8 = scheduleFor("209317M11A00701");
const unresolvedDayHospital = selectedSchedule(revision8, {
  ...state,
  fubon_new_group_hospital_event_claim_status: "day_hospital_or_day_care",
});
assert.equal(
  value(unresolvedDayHospital, "room-and-board-reimbursement").state,
  "needs_insurer_confirmation",
);
const unavailableNewborn = selectedSchedule(revision8, {
  ...state,
  fubon_new_group_hospital_event_claim_status:
    "reimbursement_newborn_screening_exception",
});
assert.equal(value(unavailableNewborn, "room-and-board-reimbursement").state, "not_eligible");

const revision11 = scheduleFor("209317M11A00704");
const eligibleNewborn = selectedSchedule(revision11, {
  ...state,
  fubon_new_group_hospital_event_claim_status:
    "reimbursement_newborn_screening_exception",
});
assert.equal(value(eligibleNewborn, "room-and-board-reimbursement").value, 30_000);

const unresolvedPostExpiry = selectedSchedule(revision8, {
  ...state,
  fubon_new_group_hospital_event_claim_status: "post_expiry_readmission",
});
assert.equal(
  value(unresolvedPostExpiry, "room-and-board-reimbursement").state,
  "needs_insurer_confirmation",
);
const revision12 = scheduleFor("209317M11A00705");
const excludedPostExpiry = selectedSchedule(revision12, {
  ...state,
  fubon_new_group_hospital_event_claim_status: "post_expiry_readmission",
});
assert.equal(value(excludedPostExpiry, "room-and-board-reimbursement").state, "not_eligible");

const missingRoomLimit = selectedSchedule(revision0, {
  ...state,
  fubon_new_group_hospital_room_daily_limit: undefined,
});
assert.deepEqual(value(missingRoomLimit, "room-and-board-reimbursement").required_fields, [
  "fubon_new_group_hospital_room_daily_limit",
]);

const requirementKeys = model
  .policyStateRequirements(selected)
  .fields.map((field) => field.key);
for (const key of Object.keys(state)) assert(requirementKeys.includes(key), key);
assert.equal(
  model.POLICY_STATE_FIELDS.fubon_new_group_hospital_event_claim_status.type,
  "choice",
);
assert.equal(
  model.POLICY_STATE_FIELDS.fubon_new_group_hospital_max_days.type,
  "integer",
);
assert.equal(model.POLICY_STATE_FIELDS.burn_unit_room_expense.type, "non_negative_money");

console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: 25,
});

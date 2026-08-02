const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-062-mercantile-group-new-hospital-medical-v305.json",
    ),
    "utf8",
  ),
);

function scheduleFor(productId) {
  return proposal.proposals.find((item) => item.product_id === productId)
    .candidates[0].schedule;
}

function selectedSchedule(schedule, selection = {}, policyState = {}) {
  return { ...schedule, ...selection, policy_state: policyState };
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

const legacy = scheduleFor("211317M11A00900");
assert.equal(model.selectionRequirements(legacy).mode, "policy_state");
const legacyState = {
  mercantile_group_new_hospital_event_claim_status: "reimbursement",
  mercantile_group_new_hospital_room_daily_limit: 1_500,
  mercantile_group_new_hospital_medical_limit: 30_000,
  mercantile_group_new_hospital_surgery_base_limit: 40_000,
  hospitalization_days: 45,
  hospital_room_expense: 50_000,
  inpatient_medical_expense: 50_000,
  inpatient_surgery_expense: 30_000,
  surgery_benefit_rate_percent: 50,
  national_health_insurance_payment_status: "covered",
};
const legacySelected = selectedSchedule(legacy, {}, legacyState);
assert.equal(value(legacySelected, "daily-room-expense-reimbursement").value, 50_000);
assert.equal(value(legacySelected, "inpatient-medical-expense-reimbursement").value, 45_000);
assert.equal(value(legacySelected, "inpatient-surgery-expense-reimbursement").value, 20_000);
assert.equal(value(legacySelected, "hospital-daily-cash-alternative").state, "not_eligible");

const nonNhi = selectedSchedule(legacy, {}, {
  ...legacyState,
  national_health_insurance_payment_status: "not_covered",
});
assert.equal(value(nonNhi, "daily-room-expense-reimbursement").value, 33_000);
assert.equal(value(nonNhi, "inpatient-medical-expense-reimbursement").value, 33_000);
assert.equal(value(nonNhi, "inpatient-surgery-expense-reimbursement").value, 19_800);

const legacyDaily = selectedSchedule(legacy, {}, {
  ...legacyState,
  mercantile_group_new_hospital_event_claim_status: "daily_cash",
});
assert.equal(value(legacyDaily, "daily-room-expense-reimbursement").state, "not_eligible");
assert.equal(value(legacyDaily, "hospital-daily-cash-alternative").value, 67_500);

const missingLegacyLimit = selectedSchedule(legacy, {}, {
  ...legacyState,
  mercantile_group_new_hospital_room_daily_limit: undefined,
});
assert.deepEqual(
  value(missingLegacyLimit, "daily-room-expense-reimbursement").required_fields,
  ["mercantile_group_new_hospital_room_daily_limit"],
);

const unitSchedule = scheduleFor("211317M11A00902");
assert.equal(model.selectionRequirements(unitSchedule).mode, "unit");
const unitState = {
  mercantile_group_new_hospital_event_claim_status: "reimbursement",
  hospitalization_days: 45,
  hospital_room_expense: 20_000,
  inpatient_medical_expense: 20_000,
  inpatient_surgery_expense: 20_000,
  surgery_benefit_rate_percent: 50,
  national_health_insurance_payment_status: "covered",
};
const unitSelected = selectedSchedule(unitSchedule, { unit_count: 2 }, unitState);
assert.equal(value(unitSelected, "daily-room-expense-reimbursement").value, 9_000);
assert.equal(value(unitSelected, "inpatient-medical-expense-reimbursement").value, 9_000);
assert.equal(value(unitSelected, "inpatient-surgery-expense-reimbursement").value, 4_000);

const unitDaily = selectedSchedule(unitSchedule, { unit_count: 2 }, {
  ...unitState,
  mercantile_group_new_hospital_event_claim_status: "daily_cash",
});
assert.equal(value(unitDaily, "hospital-daily-cash-alternative").value, 9_000);

const cappedAt120 = selectedSchedule(unitSchedule, { unit_count: 2 }, {
  ...unitState,
  hospitalization_days: 180,
  hospital_room_expense: 999_999,
  inpatient_medical_expense: 999_999,
});
assert.equal(value(cappedAt120, "daily-room-expense-reimbursement").value, 24_000);
assert.equal(value(cappedAt120, "inpatient-medical-expense-reimbursement").value, 24_000);

const revision5 = scheduleFor("211317M11A00905");
const unresolvedOldStatus = selectedSchedule(revision5, { unit_count: 1 }, {
  ...unitState,
  mercantile_group_new_hospital_event_claim_status: "post_expiry_readmission",
});
assert.equal(
  value(unresolvedOldStatus, "daily-room-expense-reimbursement").state,
  "needs_insurer_confirmation",
);

const revision8 = scheduleFor("211313M11A00908");
for (const status of ["day_hospital_or_day_care", "post_expiry_readmission"]) {
  const excluded = selectedSchedule(revision8, { unit_count: 1 }, {
    ...unitState,
    mercantile_group_new_hospital_event_claim_status: status,
  });
  assert.equal(value(excluded, "daily-room-expense-reimbursement").state, "not_eligible");
}

const legacyRequirementKeys = model
  .policyStateRequirements(legacySelected)
  .fields.map((field) => field.key);
for (const key of Object.keys(legacyState)) {
  assert(legacyRequirementKeys.includes(key), key);
}
assert.equal(
  model.POLICY_STATE_FIELDS.mercantile_group_new_hospital_event_claim_status.type,
  "choice",
);
assert.equal(
  model.POLICY_STATE_FIELDS.mercantile_group_new_hospital_room_daily_limit.type,
  "money",
);

console.log({
  status: "ok",
  batch_id: "tii-life-062",
  product_count: proposal.proposal_count,
  user_flow_cases: 20,
});

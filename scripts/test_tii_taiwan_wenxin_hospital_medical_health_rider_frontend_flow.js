const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-008-taiwan-wenxin-hospital-medical-health-rider-v270.json",
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

const revision0 = scheduleFor("202311R11ABB100");
assert.equal(model.selectionRequirements(revision0).mode, "plan");
assert.deepEqual(
  revision0.plan_options.map((option) => option.value),
  ["M6", "M12", "M18"],
);

const expectedFields = new Set([
  "taiwan_inpatient_daily_event_status",
  "taiwan_wenxin_no_claim_factor_percent",
  "hospitalization_days",
  "hospital_room_expense",
  "inpatient_medical_expense",
  "taiwan_wenxin_icu_status",
  "national_health_insurance_payment_status",
  "specific_surgery_count",
  "outpatient_surgery_count",
  "outpatient_surgery_expense",
]);
assert.deepEqual(
  new Set(
    revision0.version_characteristics.claim_event_inputs,
  ),
  expectedFields,
);
assert.deepEqual(
  model.policyStateRequirements({
    ...revision0,
    plan_name: "M12",
  }).fields.map((field) => field.key),
  ["taiwan_inpatient_daily_event_status"],
);
assert.ok(
  model
    .policyStateRequirements({
      ...revision0,
      plan_name: "M12",
      policy_state: {
        taiwan_inpatient_daily_event_status: "eligible_accident",
      },
    })
    .fields.some(
      (field) =>
        field.key === "taiwan_wenxin_no_claim_factor_percent",
    ),
);

const commonState = {
  taiwan_inpatient_daily_event_status:
    "eligible_disease_after_waiting_period",
  taiwan_wenxin_no_claim_factor_percent: "100",
  hospitalization_days: 40,
  hospital_room_expense: 100_000,
  inpatient_medical_expense: 120_000,
  taiwan_wenxin_icu_status: "not_admitted",
  national_health_insurance_payment_status: "covered",
  specific_surgery_count: 1,
  outpatient_surgery_count: 2,
  outpatient_surgery_expense: 30_000,
};
const standard = selectedSchedule(revision0, "M12", commonState);
assert.equal(
  coverageResult(
    standard,
    "daily-room-expense-reimbursement",
  ).value,
  48_000,
);
assert.equal(
  coverageResult(
    standard,
    "inpatient-medical-expense-reimbursement-standard",
  ).value,
  100_000,
);
assert.equal(
  coverageResult(
    standard,
    "inpatient-medical-expense-reimbursement-icu",
  ).value,
  0,
);
assert.equal(
  coverageResult(standard, "major-surgery-nursing-benefit").value,
  50_000,
);
assert.equal(
  coverageResult(
    standard,
    "outpatient-surgery-expense-reimbursement",
  ).value,
  20_000,
);
assert.equal(
  coverageResult(
    standard,
    "outpatient-surgery-fixed-benefit",
  ).value,
  2_000,
);
assert.equal(
  coverageResult(standard, "inpatient-daily-cash-benefit").value,
  65_000,
);

const inpatientScenarios = model.coverageEventScenarios(standard);
assert.deepEqual(
  inpatientScenarios
    .filter(
      (scenario) =>
        scenario.benefit_group_id ===
        "taiwan-wenxin-inpatient-reimbursement-or-daily-cash",
    )
    .map((scenario) => [scenario.event_key, scenario.value]),
  [
    ["reimbursement", 148_000],
    ["daily_cash", 65_000],
  ],
);
assert.deepEqual(
  inpatientScenarios
    .filter(
      (scenario) =>
        scenario.benefit_group_id ===
        "taiwan-wenxin-outpatient-surgery-choice",
    )
    .map((scenario) => [scenario.event_key, scenario.value]),
  [
    ["outpatient_reimbursement", 20_000],
    ["outpatient_fixed", 2_000],
  ],
);

const bonus = selectedSchedule(revision0, "M12", {
  ...commonState,
  taiwan_wenxin_no_claim_factor_percent: "130",
});
assert.equal(
  coverageResult(
    bonus,
    "daily-room-expense-reimbursement",
  ).value,
  62_400,
);
assert.equal(
  coverageResult(
    bonus,
    "inpatient-medical-expense-reimbursement-standard",
  ).value,
  120_000,
);
assert.equal(
  coverageResult(bonus, "major-surgery-nursing-benefit").value,
  65_000,
);
assert.equal(
  coverageResult(
    bonus,
    "outpatient-surgery-expense-reimbursement",
  ).value,
  26_000,
);
assert.equal(
  coverageResult(
    bonus,
    "outpatient-surgery-fixed-benefit",
  ).value,
  2_600,
);
assert.equal(
  coverageResult(bonus, "inpatient-daily-cash-benefit").value,
  84_500,
);

const icu = selectedSchedule(revision0, "M12", {
  ...commonState,
  taiwan_wenxin_no_claim_factor_percent: "130",
  inpatient_medical_expense: 250_000,
  taiwan_wenxin_icu_status: "admitted",
});
assert.equal(
  coverageResult(
    icu,
    "inpatient-medical-expense-reimbursement-standard",
  ).value,
  0,
);
assert.equal(
  coverageResult(
    icu,
    "inpatient-medical-expense-reimbursement-icu",
  ).value,
  250_000,
);

const nonCovered = selectedSchedule(revision0, "M18", {
  ...commonState,
  inpatient_medical_expense: 100_000,
  national_health_insurance_payment_status: "not_covered",
});
assert.equal(
  coverageResult(
    nonCovered,
    "inpatient-medical-expense-reimbursement-standard",
  ).value,
  65_000,
);

const waitingPeriod = selectedSchedule(revision0, "M6", {
  ...commonState,
  taiwan_inpatient_daily_event_status:
    "disease_within_waiting_period",
});
assert.equal(
  coverageResult(
    waitingPeriod,
    "daily-room-expense-reimbursement",
  ).state,
  "not_eligible",
);

const earlyDayHospital = selectedSchedule(revision0, "M6", {
  ...commonState,
  taiwan_inpatient_daily_event_status:
    "day_hospital_or_day_care",
});
assert.equal(
  coverageResult(
    earlyDayHospital,
    "daily-room-expense-reimbursement",
  ).state,
  "needs_insurer_confirmation",
);

const revision5 = scheduleFor("202311R11ABB105");
const excludedDayHospital = selectedSchedule(revision5, "M6", {
  ...commonState,
  taiwan_inpatient_daily_event_status:
    "day_hospital_or_day_care",
});
assert.equal(
  coverageResult(
    excludedDayHospital,
    "daily-room-expense-reimbursement",
  ).state,
  "not_eligible",
);

const missingBonusState = selectedSchedule(revision5, "M6", {
  ...commonState,
  taiwan_wenxin_no_claim_factor_percent: undefined,
});
assert.deepEqual(
  coverageResult(
    missingBonusState,
    "inpatient-daily-cash-benefit",
  ).required_fields,
  ["taiwan_wenxin_no_claim_factor_percent"],
);

assert.deepEqual(
  model.POLICY_STATE_FIELDS
    .taiwan_wenxin_no_claim_factor_percent.options.map(
      (option) => option.value,
    ),
  ["100", "130"],
);
assert.deepEqual(
  model.POLICY_STATE_FIELDS.taiwan_wenxin_icu_status.options.map(
    (option) => option.value,
  ),
  ["not_admitted", "admitted"],
);

console.log({
  status: "ok",
  batch_id: "tii-life-008",
  product_count: proposal.proposal_count,
  plan_count: 3,
  user_flow_cases: 21,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-one-year-group-hospital-medical-v299.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);
assert.equal(proposal.proposed_count, 13);
assert.equal(proposal.manual_review_count, 0);

function scheduleFor(productId) {
  return proposal.proposals.find((item) => item.product_id === productId)
    .candidates[0].schedule;
}

function selected(schedule, policyState) {
  return { ...schedule, policy_state: policyState };
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function value(schedule, entryId, policyState) {
  return model.coverageValue(
    entriesFor(schedule)[entryId],
    selected(schedule, policyState),
  );
}

const dailyChoiceSchedule = scheduleFor("209313MZ1A00221A11Z10000015");
const noDailyChoiceSchedule = scheduleFor("209313MZ1A00221A11Z10000016");
const claimModeKey = "fubon_group_hospital_claim_mode";

assert.equal(model.selectionRequirements(dailyChoiceSchedule).mode, "policy_state");
const requiredBeforeInput = new Set(
  model.policyStateRequirements(dailyChoiceSchedule).fields.map(
    (field) => field.key,
  ),
);
for (const key of [
  "fubon_group_hospital_daily_room_limit",
  "fubon_group_hospital_ordinary_surgery_limit",
  "fubon_group_hospital_major_surgery_limit",
  "fubon_group_hospital_misc_limit",
  "fubon_group_hospital_misc_daily_limit",
  "fubon_group_hospital_deductible",
  "fubon_group_hospital_max_days",
  claimModeKey,
]) {
  assert(requiredBeforeInput.has(key), key);
}
const reimbursementRequirements = new Set(
  model
    .policyStateRequirements(
      selected(dailyChoiceSchedule, { [claimModeKey]: "reimbursement" }),
    )
    .fields.map((field) => field.key),
);
for (const key of [
  "hospitalization_days",
  "hospital_room_expense",
  "inpatient_surgery_expense",
  "inpatient_medical_expense",
  "national_health_insurance_payment_status",
  "surgery_benefit_rate_percent",
]) {
  assert(reimbursementRequirements.has(key), key);
}

const baseState = {
  fubon_group_hospital_daily_room_limit: 3_000,
  fubon_group_hospital_ordinary_surgery_limit: 20_000,
  fubon_group_hospital_major_surgery_limit: 80_000,
  fubon_group_hospital_misc_limit: 50_000,
  fubon_group_hospital_misc_daily_limit: 2_000,
  fubon_group_hospital_deductible: 5_000,
  fubon_group_hospital_max_days: 60,
  hospitalization_days: 10,
  hospital_room_expense: 40_000,
  inpatient_surgery_expense: 100_000,
  inpatient_medical_expense: 80_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 150,
  [claimModeKey]: "reimbursement",
};

assert.equal(
  value(
    dailyChoiceSchedule,
    "daily-room-reimbursement-benefit",
    baseState,
  ).value,
  30_000,
);
const ordinarySurgery = value(
  dailyChoiceSchedule,
  "surgery-reimbursement-benefit",
  baseState,
);
assert.equal(ordinarySurgery.value, 30_000);
assert.equal(ordinarySurgery.schedule_rate, 1.5);
assert.equal(ordinarySurgery.schedule_limit, 30_000);

const majorSurgery = value(
  dailyChoiceSchedule,
  "surgery-reimbursement-benefit",
  { ...baseState, surgery_benefit_rate_percent: 400 },
);
assert.equal(majorSurgery.value, 80_000);
assert.equal(majorSurgery.schedule_limit, 80_000);

const fixedMiscCap = value(
  dailyChoiceSchedule,
  "hospital-misc-reimbursement-benefit",
  baseState,
);
assert.equal(fixedMiscCap.value, 50_000);
assert.equal(fixedMiscCap.reference_amount, 50_000);

const dailyMiscCap = value(
  dailyChoiceSchedule,
  "hospital-misc-reimbursement-benefit",
  {
    ...baseState,
    hospitalization_days: 40,
    inpatient_medical_expense: 100_000,
  },
);
assert.equal(dailyMiscCap.value, 80_000);
assert.equal(dailyMiscCap.daily_aggregate_limit, 80_000);

const reducedByNhi = value(
  dailyChoiceSchedule,
  "surgery-reimbursement-benefit",
  {
    ...baseState,
    surgery_benefit_rate_percent: 400,
    national_health_insurance_payment_status: "not_covered",
  },
);
assert.equal(reducedByNhi.eligible_expense, 65_000);
assert.equal(reducedByNhi.value, 65_000);

const dailyCashState = {
  ...baseState,
  [claimModeKey]: "daily_cash",
};
assert.equal(
  value(
    dailyChoiceSchedule,
    "hospital-medical-daily-cash-alternative",
    dailyCashState,
  ).value,
  20_000,
);
assert.equal(
  value(
    dailyChoiceSchedule,
    "daily-room-reimbursement-benefit",
    dailyCashState,
  ).state,
  "not_eligible",
);
assert.equal(
  value(
    dailyChoiceSchedule,
    "hospital-deductible-reference",
    baseState,
  ).value,
  5_000,
);

const uncertain = value(
  dailyChoiceSchedule,
  "surgery-reimbursement-benefit",
  { ...baseState, [claimModeKey]: "uncertain" },
);
assert.equal(uncertain.state, "needs_insurer_confirmation");

assert.equal(
  noDailyChoiceSchedule.coverage_entries.some(
    (entry) => entry.id === "hospital-medical-daily-cash-alternative",
  ),
  false,
);
assert.equal(
  model.policyStateRequirements(noDailyChoiceSchedule).fields.some(
    (field) => field.key === claimModeKey,
  ),
  false,
);

const missingSurgeryRate = value(
  noDailyChoiceSchedule,
  "surgery-reimbursement-benefit",
  {
    ...baseState,
    [claimModeKey]: undefined,
    surgery_benefit_rate_percent: undefined,
  },
);
assert.equal(missingSurgeryRate.state, "needs_policy_state");
assert(missingSurgeryRate.required_fields.includes("surgery_benefit_rate_percent"));

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 13,
});

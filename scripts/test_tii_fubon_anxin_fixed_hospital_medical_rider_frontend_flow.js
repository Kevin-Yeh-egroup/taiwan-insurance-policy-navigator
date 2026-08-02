const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-anxin-fixed-hospital-medical-rider-v301.json",
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
const revision0 = scheduleFor("209311R11A00200");
assert.equal(model.selectionRequirements(revision0).mode, "policy_state");

const state = {
  fubon_anxin_hospital_event_status: "eligible_accident",
  hospital_daily_amount: 1_000,
  hospitalization_days: 40,
  intensive_care_days: 2,
  burn_unit_days: 1,
  surgery_benefit_rate_percent: 50,
  fubon_anxin_highest_surgery_rate_percent: 80,
  current_eligible_hospital_benefit_total_amount: 102_000,
  fubon_anxin_health_increment_rate_percent: "20",
};
const selected = selectedSchedule(revision0, state);
assert.equal(value(selected, "hospital-daily-tiered-benefit").value, 50_000);
assert.equal(value(selected, "intensive-care-additional-benefit").value, 4_000);
assert.equal(value(selected, "burn-unit-additional-benefit").value, 3_000);
assert.equal(value(selected, "inpatient-nursing-benefit").value, 20_000);
assert.equal(value(selected, "post-discharge-recuperation-benefit").value, 20_000);
assert.equal(value(selected, "surgery-benefit").value, 15_000);
assert.equal(value(selected, "same-stay-surgery-aggregate-cap").value, 24_000);
assert.equal(value(selected, "surgery-nursing-benefit").value, 5_000);
assert.equal(value(selected, "health-increment-benefit").value, 20_400);

const capped = selectedSchedule(revision0, {
  ...state,
  hospitalization_days: 400,
  intensive_care_days: 100,
  burn_unit_days: 100,
});
assert.equal(value(capped, "hospital-daily-tiered-benefit").value, 700_000);
assert.equal(value(capped, "intensive-care-additional-benefit").value, 180_000);
assert.equal(value(capped, "burn-unit-additional-benefit").value, 270_000);
assert.equal(value(capped, "inpatient-nursing-benefit").value, 45_000);

const noIncrement = selectedSchedule(revision0, {
  ...state,
  fubon_anxin_health_increment_rate_percent: "0",
});
assert.equal(value(noIncrement, "health-increment-benefit").state, "not_eligible");
assert.equal(value(noIncrement, "health-increment-benefit").value, 0);

const waiting = selectedSchedule(revision0, {
  ...state,
  fubon_anxin_hospital_event_status: "disease_waiting_not_met",
});
assert.equal(value(waiting, "hospital-daily-tiered-benefit").state, "not_eligible");

const earlyDayHospital = selectedSchedule(revision0, {
  ...state,
  fubon_anxin_hospital_event_status: "day_hospital_or_day_stay",
});
assert.equal(
  value(earlyDayHospital, "hospital-daily-tiered-benefit").state,
  "needs_insurer_confirmation",
);

const revision8 = scheduleFor("209311R11A00208");
const excludedAfterExpiry = selectedSchedule(revision8, {
  ...state,
  fubon_anxin_hospital_event_status: "post_expiry_readmission",
});
assert.equal(
  value(excludedAfterExpiry, "hospital-daily-tiered-benefit").state,
  "not_eligible",
);

const revision9 = scheduleFor("209311R11A00209");
const excludedDayHospital = selectedSchedule(revision9, {
  ...state,
  fubon_anxin_hospital_event_status: "day_hospital_or_day_stay",
});
assert.equal(
  value(excludedDayHospital, "hospital-daily-tiered-benefit").state,
  "not_eligible",
);

const missingDaily = selectedSchedule(revision9, {
  ...state,
  hospital_daily_amount: undefined,
});
assert.deepEqual(value(missingDaily, "hospital-daily-tiered-benefit").required_fields, [
  "hospital_daily_amount",
]);

const requirementKeys = model
  .policyStateRequirements(selected)
  .fields.map((field) => field.key);
for (const key of Object.keys(state)) assert(requirementKeys.includes(key), key);
assert.equal(model.POLICY_STATE_FIELDS.fubon_anxin_hospital_event_status.type, "choice");
assert.equal(
  model.POLICY_STATE_FIELDS.fubon_anxin_highest_surgery_rate_percent.type,
  "rate",
);

console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: 22,
});

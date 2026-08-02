const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-164-global-inpatient-medical-fixed-rider-v287.json",
    ),
    "utf8",
  ),
);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, planName, policyState = {}) {
  return { ...schedule, plan_name: planName, policy_state: policyState };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [entry.id, entry]),
  );
}

assert.equal(proposal.proposal_count, 14);

const revision0 = scheduleFor("264311R11AMIR00");
assert.equal(model.selectionRequirements(revision0).mode, "policy_state");
const legacy = selectedSchedule(revision0, "", {
  global_fixed_hospital_event_status: "eligible_accident",
  hospital_daily_amount: 1_000,
  global_fixed_icu_daily_amount: 2_000,
  global_fixed_burn_daily_amount: 2_000,
  global_fixed_surgery_base_amount: 15_000,
  hospitalization_days: 5,
  intensive_care_days: 2,
  burn_unit_days: 1,
  surgery_benefit_rate_percent: 50,
});
const legacyEntries = entriesFor(legacy);
assert.equal(
  model.coverageValue(legacyEntries["hospital-daily-benefit"], legacy).value,
  5_000,
);
assert.equal(
  model.coverageValue(
    legacyEntries["intensive-care-daily-benefit"],
    legacy,
  ).value,
  4_000,
);
assert.equal(
  model.coverageValue(legacyEntries["burn-unit-daily-benefit"], legacy).value,
  2_000,
);
assert.equal(
  model.coverageValue(legacyEntries["surgery-fixed-benefit"], legacy).value,
  7_500,
);
assert.equal(
  model.coverageValue(legacyEntries["surgery-aggregate-cap"], legacy).value,
  45_000,
);
assert.equal(legacyEntries["unexpired-premium-refund"], undefined);

const revision2 = scheduleFor("264311R11AMIR02");
assert.equal(model.selectionRequirements(revision2).mode, "plan");
assert.equal(revision2.plan_options.length, 12);
const plan = selectedSchedule(revision2, "HI-10", {
  global_fixed_hospital_event_status: "eligible_accident",
  hospitalization_days: 5,
  intensive_care_days: 2,
  burn_unit_days: 1,
  surgery_benefit_rate_percent: 50,
  unexpired_premium_refund_amount: 1_234,
});
const planEntries = entriesFor(plan);
assert.equal(
  model.coverageValue(planEntries["hospital-daily-benefit"], plan).value,
  5_000,
);
assert.equal(
  model.coverageValue(planEntries["intensive-care-daily-benefit"], plan).value,
  4_000,
);
assert.equal(
  model.coverageValue(planEntries["burn-unit-daily-benefit"], plan).value,
  2_000,
);
assert.equal(
  model.coverageValue(planEntries["surgery-fixed-benefit"], plan).value,
  7_500,
);
assert.equal(
  model.coverageValue(planEntries["surgery-aggregate-cap"], plan).value,
  45_000,
);
assert.equal(
  model.coverageValue(planEntries["unexpired-premium-refund"], plan).value,
  1_234,
);

const cappedDays = selectedSchedule(revision2, "HI-05", {
  global_fixed_hospital_event_status: "eligible_accident",
  hospitalization_days: 400,
  intensive_care_days: 40,
  burn_unit_days: 70,
});
const cappedEntries = entriesFor(cappedDays);
assert.equal(
  model.coverageValue(cappedEntries["hospital-daily-benefit"], cappedDays).value,
  182_500,
);
assert.equal(
  model.coverageValue(
    cappedEntries["intensive-care-daily-benefit"],
    cappedDays,
  ).value,
  30_000,
);
assert.equal(
  model.coverageValue(cappedEntries["burn-unit-daily-benefit"], cappedDays)
    .value,
  60_000,
);

const preExclusion = selectedSchedule(revision2, "HI-05", {
  global_fixed_hospital_event_status: "day_hospital_or_day_stay",
  hospitalization_days: 1,
});
assert.equal(
  model.coverageValue(
    entriesFor(preExclusion)["hospital-daily-benefit"],
    preExclusion,
  ).state,
  "needs_insurer_confirmation",
);

const revision8 = scheduleFor("264311R11AMIR08");
const excluded = selectedSchedule(revision8, "HI-05", {
  global_fixed_hospital_event_status: "day_hospital_or_day_stay",
  hospitalization_days: 1,
});
assert.equal(
  model.coverageValue(entriesFor(excluded)["hospital-daily-benefit"], excluded)
    .state,
  "not_eligible",
);

const revision5 = scheduleFor("264311R11AMIR05");
const oldNewborn = selectedSchedule(revision5, "HI-05", {
  global_fixed_hospital_event_status: "eligible_newborn_screening_exception",
  hospitalization_days: 1,
});
assert.equal(
  model.coverageValue(entriesFor(oldNewborn)["hospital-daily-benefit"], oldNewborn)
    .state,
  "not_eligible",
);

const revision6 = scheduleFor("264311R11AMIR06");
const newNewborn = selectedSchedule(revision6, "HI-05", {
  global_fixed_hospital_event_status: "eligible_newborn_screening_exception",
  hospitalization_days: 1,
});
assert.equal(
  model.coverageValue(entriesFor(newNewborn)["hospital-daily-benefit"], newNewborn)
    .value,
  500,
);

const missingLegacyAmount = selectedSchedule(revision0, "", {
  global_fixed_hospital_event_status: "eligible_accident",
  intensive_care_days: 1,
});
assert.deepEqual(
  model.coverageValue(
    entriesFor(missingLegacyAmount)["intensive-care-daily-benefit"],
    missingLegacyAmount,
  ).required_fields,
  ["global_fixed_icu_daily_amount"],
);

assert.equal(
  model.POLICY_STATE_FIELDS.global_fixed_hospital_event_status.type,
  "choice",
);
assert.equal(
  model.POLICY_STATE_FIELDS.global_fixed_surgery_base_amount.type,
  "money",
);

console.log({
  status: "ok",
  batch_id: "tii-life-164",
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

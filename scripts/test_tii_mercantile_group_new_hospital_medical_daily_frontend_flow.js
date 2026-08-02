const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-062-mercantile-group-new-hospital-medical-daily-v306.json",
    ),
    "utf8",
  ),
);

function scheduleFor(productId) {
  return proposal.proposals.find((item) => item.product_id === productId)
    .candidates[0].schedule;
}

function selectedSchedule(schedule, policyState = {}) {
  return { ...schedule, face_amount: 1_000, policy_state: policyState };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [entry.id, entry]),
  );
}

function value(item, entryId) {
  return model.coverageValue(entriesFor(item)[entryId], item);
}

assert.equal(proposal.proposal_count, 12);
const revision8 = scheduleFor("211313M11A00808");
assert.equal(model.selectionRequirements(revision8).mode, "face_amount");

const eligible = selectedSchedule(revision8, {
  mercantile_group_daily_event_status: "eligible_inpatient",
  mercantile_group_daily_max_hospital_days: 60,
  mercantile_group_daily_surgery_option_status: "included",
  mercantile_group_daily_discharge_option_status: "included",
  hospitalization_days: 90,
  intensive_care_days: 40,
  surgery_benefit_multiplier_decimal: 20,
});
assert.equal(value(eligible, "hospital-daily-benefit").value, 60_000);
assert.equal(value(eligible, "intensive-care-additional-benefit").value, 25_000);
assert.equal(value(eligible, "surgery-benefit").value, 20_000);
assert.equal(value(eligible, "discharge-recuperation-benefit").value, 82_500);

const missingMaximum = selectedSchedule(revision8, {
  ...eligible.policy_state,
  mercantile_group_daily_max_hospital_days: undefined,
});
assert.deepEqual(value(missingMaximum, "hospital-daily-benefit").required_fields, [
  "mercantile_group_daily_max_hospital_days",
]);

const noOptionalBenefits = selectedSchedule(revision8, {
  mercantile_group_daily_event_status: "eligible_inpatient",
  mercantile_group_daily_max_hospital_days: 60,
  mercantile_group_daily_surgery_option_status: "not_included",
  mercantile_group_daily_discharge_option_status: "not_included",
  hospitalization_days: 10,
  intensive_care_days: 0,
});
assert.equal(value(noOptionalBenefits, "surgery-benefit").state, "not_eligible");
assert.equal(
  value(noOptionalBenefits, "discharge-recuperation-benefit").state,
  "not_eligible",
);

const dayHospital = selectedSchedule(revision8, {
  ...eligible.policy_state,
  mercantile_group_daily_event_status: "day_hospital_or_day_care",
});
assert.equal(value(dayHospital, "hospital-daily-benefit").state, "not_eligible");

const revision7 = scheduleFor("211313M11A00807");
const oldDayHospital = selectedSchedule(revision7, {
  ...eligible.policy_state,
  mercantile_group_daily_event_status: "day_hospital_or_day_care",
});
assert.equal(
  value(oldDayHospital, "hospital-daily-benefit").state,
  "needs_insurer_confirmation",
);

const requiredKeys = model
  .policyStateRequirements(eligible)
  .fields.map((field) => field.key);
for (const key of [
  "mercantile_group_daily_event_status",
  "mercantile_group_daily_max_hospital_days",
  "mercantile_group_daily_surgery_option_status",
  "mercantile_group_daily_discharge_option_status",
  "hospitalization_days",
  "intensive_care_days",
  "surgery_benefit_multiplier_decimal",
]) {
  assert(requiredKeys.includes(key), key);
}
assert.equal(model.POLICY_STATE_FIELDS.mercantile_group_daily_max_hospital_days.type, "integer");
assert.equal(model.POLICY_STATE_FIELDS.mercantile_group_daily_event_status.type, "choice");

console.log({
  status: "ok",
  batch_id: "tii-life-062",
  proposal_count: proposal.proposal_count,
  source_gap_count: 1,
  user_flow_cases: 14,
});

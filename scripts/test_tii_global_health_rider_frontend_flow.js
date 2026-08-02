const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(ROOT, "work/tii-benefit-proposals/tii-life-164-global-health-rider-v288.json"),
    "utf8",
  ),
);

function scheduleFor(productId) {
  return proposal.proposals.find((item) => item.product_id === productId).candidates[0].schedule;
}
function selected(schedule, planName, policyState) {
  return { ...schedule, plan_name: planName, policy_state: policyState };
}
function entries(item) {
  return Object.fromEntries(model.effectiveCoverageEntries(item).map((entry) => [entry.id, entry]));
}
function value(item, id) {
  return model.coverageValue(entries(item)[id], item);
}

assert.equal(proposal.proposal_count, 14);
const revision8 = scheduleFor("264311R11AHIR08");
assert.equal(model.selectionRequirements(revision8).mode, "plan");
const caseItem = selected(revision8, "HI-20", {
  global_health_event_status: "eligible_accident",
  hospitalization_days: 5,
  intensive_care_days: 2,
  global_health_surgery_schedule_multiplier: 250,
  global_health_same_stay_surgery_paid_amount: 0,
  global_health_bonus_factor_percent: "120",
  global_health_work_inability_status: "persisting_180_days",
  global_health_premiums_paid_within_180_days: 3000,
  remaining_premium_amount: 18000,
});
assert.equal(value(caseItem, "hospital-daily-benefit").value, 12000);
assert.equal(value(caseItem, "intensive-care-daily-benefit").value, 4800);
assert.equal(value(caseItem, "surgery-fixed-benefit").value, 60000);
assert.equal(value(caseItem, "major-surgery-additional-benefit").value, 20000);
assert.equal(value(caseItem, "misc-medical-daily-benefit").value, 5000);
assert.equal(value(caseItem, "first-180-day-premium-refund").value, 3000);
assert.equal(value(caseItem, "future-premium-waiver").value, 18000);

const threshold = selected(revision8, "HI-20", {
  ...caseItem.policy_state,
  global_health_surgery_schedule_multiplier: 200,
});
assert.equal(value(threshold, "major-surgery-additional-benefit").state, "not_eligible");
assert.equal(value(threshold, "major-surgery-additional-benefit").value, 0);

const capped = selected(revision8, "HI-05", {
  ...caseItem.policy_state,
  hospitalization_days: 400,
  intensive_care_days: 40,
  global_health_bonus_factor_percent: "100",
});
assert.equal(value(capped, "hospital-daily-benefit").value, 182500);
assert.equal(value(capped, "intensive-care-daily-benefit").value, 30000);
assert.equal(value(capped, "misc-medical-daily-benefit").value, 7500);

const oldNewborn = selected(scheduleFor("264391R11AHIR05"), "HI-05", {
  ...caseItem.policy_state,
  global_health_event_status: "eligible_newborn_screening_exception",
});
assert.equal(value(oldNewborn, "hospital-daily-benefit").state, "not_eligible");
const newNewborn = selected(scheduleFor("264391R11AHIR06"), "HI-05", {
  ...oldNewborn.policy_state,
});
assert.equal(value(newNewborn, "hospital-daily-benefit").value, 3000);

const preDayStay = selected(scheduleFor("264391R11AHIR07"), "HI-05", {
  ...caseItem.policy_state,
  global_health_event_status: "day_hospital_or_day_stay",
});
assert.equal(value(preDayStay, "hospital-daily-benefit").state, "needs_insurer_confirmation");
const postDayStay = selected(revision8, "HI-05", { ...preDayStay.policy_state });
assert.equal(value(postDayStay, "hospital-daily-benefit").state, "not_eligible");

const missingSurgeryRate = selected(revision8, "HI-20", {
  global_health_event_status: "eligible_accident",
  global_health_bonus_factor_percent: "100",
});
assert.deepEqual(value(missingSurgeryRate, "surgery-fixed-benefit").required_fields, ["global_health_surgery_schedule_multiplier"]);
assert.equal(model.POLICY_STATE_FIELDS.global_health_event_status.type, "choice");
assert.equal(model.POLICY_STATE_FIELDS.global_health_surgery_schedule_multiplier.type, "rate");

console.log({ status: "ok", batch_id: "tii-life-164", product_count: 14, user_flow_cases: 18 });

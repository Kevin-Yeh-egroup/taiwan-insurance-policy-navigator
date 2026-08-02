const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-new-inpatient-medical-daily-benefit-rider-v303.json",
    ),
    "utf8",
  ),
);

function scheduleFor(productId) {
  return proposal.proposals.find((item) => item.product_id === productId)
    .candidates[0].schedule;
}

function result(schedule, state) {
  return model.coverageValue(schedule.coverage_entries[0], {
    ...schedule,
    policy_state: state,
  });
}

assert.equal(proposal.proposal_count, 13);
for (const proposalItem of proposal.proposals) {
  const schedule = proposalItem.candidates[0].schedule;
  assert.equal(model.selectionRequirements(schedule).mode, "policy_state");
  assert.deepEqual(
    new Set(model.policyStateRequirements(schedule).fields.map((field) => field.key)),
    new Set([
      "fubon_new_inpatient_daily_event_status",
      "hospital_daily_amount",
    ]),
  );
  assert.deepEqual(
    new Set(
      model
        .policyStateRequirements({
          ...schedule,
          policy_state: {
            fubon_new_inpatient_daily_event_status: "eligible_accident",
          },
        })
        .fields.map((field) => field.key),
    ),
    new Set([
      "fubon_new_inpatient_daily_event_status",
      "hospital_daily_amount",
      "hospitalization_days",
    ]),
  );
  const eligible = {
    fubon_new_inpatient_daily_event_status: "eligible_accident",
    hospital_daily_amount: 1_000,
  };
  assert.equal(result(schedule, { ...eligible, hospitalization_days: 10 }).value, 10_000);
  assert.equal(result(schedule, { ...eligible, hospitalization_days: 45 }).value, 60_000);
  assert.equal(result(schedule, { ...eligible, hospitalization_days: 200 }).value, 390_000);
  assert.equal(result(schedule, { ...eligible, hospitalization_days: 400 }).value, 885_000);

  const waiting = result(schedule, {
    ...eligible,
    hospitalization_days: 10,
    fubon_new_inpatient_daily_event_status: "disease_waiting_not_met",
  });
  assert.equal(waiting.state, "not_eligible");
  assert.equal(waiting.value, 0);
}

const revision6 = scheduleFor("209311R11A00106");
assert.equal(
  result(revision6, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 1,
    fubon_new_inpatient_daily_event_status: "eligible_newborn_screening_exception",
  }).state,
  "not_eligible",
);
const revision7 = scheduleFor("209311R11A00107");
assert.equal(
  result(revision7, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 1,
    fubon_new_inpatient_daily_event_status: "eligible_newborn_screening_exception",
  }).value,
  1_000,
);
assert.equal(
  result(revision7, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 1,
    fubon_new_inpatient_daily_event_status: "post_expiry_readmission",
  }).state,
  "needs_insurer_confirmation",
);
const revision8 = scheduleFor("209311R11A00108");
assert.equal(
  result(revision8, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 1,
    fubon_new_inpatient_daily_event_status: "post_expiry_readmission",
  }).state,
  "not_eligible",
);
assert.equal(
  result(revision8, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 1,
    fubon_new_inpatient_daily_event_status: "day_hospital_or_day_stay",
  }).state,
  "needs_insurer_confirmation",
);
const revision9 = scheduleFor("209311R11A00109");
assert.equal(
  result(revision9, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 1,
    fubon_new_inpatient_daily_event_status: "day_hospital_or_day_stay",
  }).state,
  "not_eligible",
);

for (const [missingKey, policyState] of [
  ["hospital_daily_amount", { hospitalization_days: 10, fubon_new_inpatient_daily_event_status: "eligible_accident" }],
  ["hospitalization_days", { hospital_daily_amount: 1_000, fubon_new_inpatient_daily_event_status: "eligible_accident" }],
  ["fubon_new_inpatient_daily_event_status", { hospital_daily_amount: 1_000, hospitalization_days: 10 }],
]) {
  const missing = result(revision9, policyState);
  assert.equal(missing.state, "needs_policy_state");
  assert.deepEqual(missing.required_fields, [missingKey]);
}

assert.equal(model.POLICY_STATE_FIELDS.fubon_new_inpatient_daily_event_status.type, "choice");
console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 5 + 10,
});

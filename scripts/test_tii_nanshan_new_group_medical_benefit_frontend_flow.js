const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-032-nanshan-new-group-medical-benefit-v298.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);

const schedule = proposal.proposals.find(
  (item) => item.product_id === "206317M11A30200",
).candidates[0].schedule;
const entries = Object.fromEntries(
  schedule.coverage_entries.map((entry) => [entry.id, entry]),
);

assert.equal(model.selectionRequirements(schedule).mode, "policy_state");
assert.deepEqual(
  model.policyStateRequirements(schedule).fields.map((field) => field.key),
  [
    "nanshan_new_group_daily_room_limit",
    "nanshan_new_group_misc_limit",
    "nanshan_new_group_physician_daily_limit",
    "nanshan_new_group_surgery_base_limit",
    "nanshan_new_group_surgery_schedule_rate",
  ],
);

const policyState = {
  nanshan_new_group_daily_room_limit: 1_000,
  nanshan_new_group_misc_limit: 50_000,
  nanshan_new_group_physician_daily_limit: 500,
  nanshan_new_group_surgery_base_limit: 20_000,
  nanshan_new_group_surgery_schedule_rate: "50",
};

function valueFor(entryId, state = policyState) {
  return model.coverageValue(entries[entryId], {
    ...schedule,
    policy_state: state,
  });
}

assert.equal(valueFor("daily-room-reimbursement-limit").value, 1_000);
assert.equal(valueFor("icu-daily-room-reimbursement-limit").value, 2_000);
assert.equal(
  valueFor("surgery-stay-daily-room-reimbursement-limit").value,
  1_500,
);
assert.equal(
  valueFor("hospital-misc-shared-reimbursement-limit").value,
  50_000,
);
assert.equal(valueFor("accident-emergency-fixed-sublimit").value, 5_000);
assert.equal(
  valueFor("pre-post-hospital-outpatient-per-visit-limit").value,
  500,
);
assert.equal(
  valueFor("physician-consultation-daily-limit").value,
  500,
);
assert.equal(valueFor("surgery-schedule-limit").value, 10_000);
assert.equal(valueFor("hospital-cash-alternative-daily").value, 1_000);
assert.equal(valueFor("accident-accessory-per-item-limit").value, 2_000);
assert.equal(valueFor("accident-accessory-aggregate-limit").value, 10_000);

assert.equal(
  valueFor("surgery-schedule-limit", {
    ...policyState,
    nanshan_new_group_surgery_schedule_rate: "400",
  }).value,
  80_000,
);
assert.equal(
  valueFor("surgery-schedule-limit", {
    ...policyState,
    nanshan_new_group_surgery_schedule_rate: "100",
  }).state,
  "needs_policy_state",
);
assert.equal(
  valueFor("surgery-schedule-limit", {
    ...policyState,
    nanshan_new_group_surgery_base_limit: "",
  }).state,
  "needs_policy_state",
);

console.log({
  status: "ok",
  batch_id: "tii-life-032",
  product_count: proposal.proposal_count,
  user_flow_cases: 14,
});

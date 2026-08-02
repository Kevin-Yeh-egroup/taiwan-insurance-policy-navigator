const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-032-nanshan-group-hospital-daily-rider-v245.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 16);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function valueFor(schedule, dailyAmount, days) {
  return model.coverageValue(schedule.coverage_entries[0], {
    ...schedule,
    policy_state: {
      hospital_daily_amount: dailyAmount,
      hospitalization_days: days,
    },
  });
}

for (const proposalItem of proposal.proposals) {
  const schedule = proposalItem.candidates[0].schedule;
  assert.equal(
    model.selectionRequirements(schedule).mode,
    "policy_state",
  );
  assert.deepEqual(
    model.policyStateRequirements(schedule).fields.map(
      (field) => field.key,
    ),
    ["hospital_daily_amount", "hospitalization_days"],
  );
  assert.equal(valueFor(schedule, 1_000, 30).value, 30_000);
  assert.equal(valueFor(schedule, 1_000, 35).value, 36_250);
  assert.equal(valueFor(schedule, 1_000, 90).value, 105_000);
  assert.equal(valueFor(schedule, 1_000, 365).value, 517_500);
  assert.equal(valueFor(schedule, 1_000, 500).value, 517_500);
}

const revision15 = scheduleFor(
  "206313RZ1A30121A11Z10000015",
);
const missingDailyAmount = model.coverageValue(
  revision15.coverage_entries[0],
  {
    ...revision15,
    policy_state: { hospitalization_days: 35 },
  },
);
assert.equal(missingDailyAmount.state, "needs_policy_state");
assert.deepEqual(
  missingDailyAmount.required_fields,
  ["hospital_daily_amount"],
);

const missingDays = model.coverageValue(
  revision15.coverage_entries[0],
  {
    ...revision15,
    policy_state: { hospital_daily_amount: 1_000 },
  },
);
assert.equal(missingDays.state, "needs_policy_state");
assert.deepEqual(
  missingDays.required_fields,
  ["hospitalization_days"],
);

console.log({
  status: "ok",
  batch_id: "tii-life-032",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 6 + 2,
});

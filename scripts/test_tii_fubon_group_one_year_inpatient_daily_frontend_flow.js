const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-group-one-year-inpatient-daily-v247.json",
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

function valueFor(schedule, dailyAmount, days, dayLimit) {
  return model.coverageValue(schedule.coverage_entries[0], {
    ...schedule,
    policy_state: {
      hospital_daily_amount: dailyAmount,
      hospitalization_days: days,
      hospitalization_day_limit_per_stay: dayLimit,
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
    [
      "hospital_daily_amount",
      "hospitalization_days",
      "hospitalization_day_limit_per_stay",
    ],
  );
  const uncapped = valueFor(schedule, 1_500, 10, 21);
  assert.equal(uncapped.state, "policy_state_value");
  assert.equal(uncapped.value, 15_000);
  assert.equal(uncapped.eligible_quantity, 10);

  const capped = valueFor(schedule, 1_500, 30, 21);
  assert.equal(capped.state, "policy_state_value");
  assert.equal(capped.value, 31_500);
  assert.equal(capped.quantity, 30);
  assert.equal(capped.eligible_quantity, 21);
  assert.equal(capped.quantity_cap, 21);
  assert.equal(
    capped.quantity_cap_state_key,
    "hospitalization_day_limit_per_stay",
  );
}

const revision15 = scheduleFor(
  "209313RZ1A00121A11Z10000015",
);
for (const [missingKey, policyState] of [
  [
    "hospital_daily_amount",
    {
      hospitalization_days: 10,
      hospitalization_day_limit_per_stay: 21,
    },
  ],
  [
    "hospitalization_days",
    {
      hospital_daily_amount: 1_500,
      hospitalization_day_limit_per_stay: 21,
    },
  ],
  [
    "hospitalization_day_limit_per_stay",
    {
      hospital_daily_amount: 1_500,
      hospitalization_days: 10,
    },
  ],
]) {
  const result = model.coverageValue(
    revision15.coverage_entries[0],
    {
      ...revision15,
      policy_state: policyState,
    },
  );
  assert.equal(result.state, "needs_policy_state");
  assert.deepEqual(result.required_fields, [missingKey]);
}

console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 2 + 3,
});

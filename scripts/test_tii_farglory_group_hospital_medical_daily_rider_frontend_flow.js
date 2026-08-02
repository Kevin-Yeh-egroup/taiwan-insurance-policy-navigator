const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-080-farglory-group-hospital-medical-daily-rider-v279.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

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

  const uncapped = valueFor(schedule, 2_000, 5, 30);
  assert.equal(uncapped.state, "policy_state_value");
  assert.equal(uncapped.value, 10_000);
  assert.equal(uncapped.eligible_quantity, 5);

  const capped = valueFor(schedule, 2_000, 45, 30);
  assert.equal(capped.state, "policy_state_value");
  assert.equal(capped.value, 60_000);
  assert.equal(capped.quantity, 45);
  assert.equal(capped.eligible_quantity, 30);
  assert.equal(capped.quantity_cap, 30);
  assert.equal(
    capped.quantity_cap_state_key,
    "hospitalization_day_limit_per_stay",
  );
}

const latest = proposal.proposals.at(-1).candidates[0].schedule;
for (const [missingKey, policyState] of [
  [
    "hospital_daily_amount",
    {
      hospitalization_days: 5,
      hospitalization_day_limit_per_stay: 30,
    },
  ],
  [
    "hospitalization_days",
    {
      hospital_daily_amount: 2_000,
      hospitalization_day_limit_per_stay: 30,
    },
  ],
  [
    "hospitalization_day_limit_per_stay",
    {
      hospital_daily_amount: 2_000,
      hospitalization_days: 5,
    },
  ],
]) {
  const result = model.coverageValue(
    latest.coverage_entries[0],
    {
      ...latest,
      policy_state: policyState,
    },
  );
  assert.equal(result.state, "needs_policy_state");
  assert.deepEqual(result.required_fields, [missingKey]);
}

console.log({
  status: "ok",
  batch_id: "tii-life-080",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 2 + 3,
});

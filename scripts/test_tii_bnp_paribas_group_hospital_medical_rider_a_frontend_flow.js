const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-170-bnp-group-hospital-medical-rider-a-v255.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 16);

function valueFor(schedule, entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find((entry) => entry.id === entryId),
    { ...schedule, policy_state: policyState },
  );
}

const policyState = {
  hospital_daily_amount: 2_000,
  hospitalization_days: 12,
  cancer_hospitalization_days: 5,
};

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
      "cancer_hospitalization_days",
    ],
  );
  assert.deepEqual(
    schedule.coverage_entries.map((entry) => entry.id),
    [
      "general-hospital-daily-benefit",
      "cancer-hospital-daily-additional-benefit",
    ],
  );
  assert.equal(
    valueFor(
      schedule,
      "general-hospital-daily-benefit",
      policyState,
    ).value,
    24_000,
  );
  assert.equal(
    valueFor(
      schedule,
      "cancer-hospital-daily-additional-benefit",
      policyState,
    ).value,
    10_000,
  );

  const cappedHospital = valueFor(
    schedule,
    "general-hospital-daily-benefit",
    { ...policyState, hospitalization_days: 400 },
  );
  assert.equal(cappedHospital.value, 730_000);
  assert.equal(cappedHospital.eligible_quantity, 365);
  assert.equal(cappedHospital.quantity_cap, 365);

  const missingDailyAmount = valueFor(
    schedule,
    "general-hospital-daily-benefit",
    { ...policyState, hospital_daily_amount: undefined },
  );
  assert.equal(missingDailyAmount.state, "needs_policy_state");
  assert.deepEqual(missingDailyAmount.required_fields, [
    "hospital_daily_amount",
  ]);
}

console.log({
  status: "ok",
  batch_id: "tii-life-170",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 4,
});

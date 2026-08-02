const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-170-bnp-paribas-hospital-medical-abc-v289.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

const policyState = {
  hospital_daily_amount: 2_000,
  hospitalization_days: 12,
  cancer_hospitalization_days: 5,
  intensive_care_days: 3,
  burn_unit_days: 2,
  outpatient_visit_count: 4,
};

function selected(schedule, planName, state = policyState) {
  return { ...schedule, plan_name: planName, policy_state: state };
}

function valueFor(item, entryId) {
  const entry = model
    .effectiveCoverageEntries(item)
    .find((candidate) => candidate.id === entryId);
  assert.ok(entry, `${item.plan_name}/${entryId}`);
  return model.coverageValue(entry, item);
}

for (const proposalItem of proposal.proposals) {
  const schedule = proposalItem.candidates[0].schedule;
  const requirements = model.selectionRequirements(schedule);
  assert.equal(requirements.mode, "plan");
  assert.deepEqual(
    requirements.plan_options.map((option) => option.value),
    ["A", "B", "C"],
  );

  const typeA = selected(schedule, "A");
  assert.deepEqual(
    model.policyStateRequirements(typeA).fields.map((field) => field.key),
    [
      "hospital_daily_amount",
      "hospitalization_days",
      "cancer_hospitalization_days",
    ],
  );
  assert.equal(
    valueFor(typeA, "general-hospital-daily-benefit").value,
    24_000,
  );
  assert.equal(
    valueFor(typeA, "cancer-hospital-daily-additional-benefit").value,
    10_000,
  );

  const typeB = selected(schedule, "B");
  assert.equal(
    valueFor(typeB, "intensive-care-daily-additional-benefit").value,
    6_000,
  );
  assert.equal(
    valueFor(typeB, "burn-intensive-care-daily-additional-benefit").value,
    8_000,
  );

  const typeC = selected(schedule, "C");
  assert.equal(
    valueFor(typeC, "inpatient-surgery-medical-benefit").value,
    6_000,
  );
  assert.equal(
    valueFor(typeC, "inpatient-treatment-procedure-medical-benefit").value,
    6_000,
  );
  assert.equal(
    valueFor(typeC, "post-discharge-convalescence-benefit").value,
    12_000,
  );
  assert.equal(
    valueFor(typeC, "pre-post-hospital-outpatient-benefit").value,
    2_000,
  );

  const capped = selected(schedule, "A", {
    ...policyState,
    hospitalization_days: 400,
  });
  const cappedResult = valueFor(
    capped,
    "general-hospital-daily-benefit",
  );
  assert.equal(cappedResult.value, 730_000);
  assert.equal(cappedResult.eligible_quantity, 365);

  const missingAmount = selected(schedule, "A", {
    ...policyState,
    hospital_daily_amount: undefined,
  });
  assert.equal(
    valueFor(missingAmount, "general-hospital-daily-benefit").state,
    "needs_policy_state",
  );
}

console.log({
  status: "ok",
  batch_id: "tii-life-170",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 10,
});

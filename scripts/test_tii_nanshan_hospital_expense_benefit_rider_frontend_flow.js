const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-032-nanshan-hospital-expense-benefit-rider-v275.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

function coverageResult(schedule, policyState) {
  return model.coverageValue(schedule.coverage_entries[0], {
    ...schedule,
    policy_state: policyState,
  });
}

for (const proposalItem of proposal.proposals) {
  const schedule = proposalItem.candidates[0].schedule;
  assert.equal(
    model.selectionRequirements(schedule).mode,
    "policy_state",
  );
  assert.deepEqual(
    new Set(
      model.policyStateRequirements(schedule).fields.map(
        (field) => field.key,
      ),
    ),
    new Set([
      "hospital_daily_amount",
      "hospitalization_days",
      "taiwan_inpatient_daily_event_status",
    ]),
  );

  for (const [days, expectedValue] of [
    [20, 20_000],
    [60, 67_500],
    [120, 150_000],
  ]) {
    const result = coverageResult(schedule, {
      hospital_daily_amount: 1_000,
      hospitalization_days: days,
      taiwan_inpatient_daily_event_status:
        "eligible_disease_after_waiting_period",
    });
    assert.equal(result.state, "calculated");
    assert.equal(result.value, expectedValue);
    assert.equal(
      result.tier_values.reduce(
        (total, tier) => total + tier.quantity,
        0,
      ),
      days,
    );
  }

  const capped = coverageResult(schedule, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 400,
    taiwan_inpatient_daily_event_status: "eligible_accident",
  });
  assert.equal(capped.state, "calculated");
  assert.equal(capped.value, 517_500);
  assert.equal(capped.quantity, 400);
  assert.equal(
    capped.tier_values.reduce(
      (total, tier) => total + tier.quantity,
      0,
    ),
    365,
  );

  for (const eventStatus of [
    "disease_within_waiting_period",
    "day_hospital_or_day_care",
  ]) {
    const result = coverageResult(schedule, {
      hospital_daily_amount: 1_000,
      hospitalization_days: 10,
      taiwan_inpatient_daily_event_status: eventStatus,
    });
    assert.equal(result.state, "not_eligible");
    assert.equal(result.value, 0);
  }

  const uncertain = coverageResult(schedule, {
    hospital_daily_amount: 1_000,
    hospitalization_days: 10,
    taiwan_inpatient_daily_event_status:
      "not_eligible_or_uncertain",
  });
  assert.equal(
    uncertain.state,
    "needs_insurer_confirmation",
  );
  assert.equal(
    uncertain.confirmation_reason,
    "claim_eligibility_uncertain",
  );
}

const schedule =
  proposal.proposals[proposal.proposals.length - 1].candidates[0]
    .schedule;
for (const [missingKey, policyState] of [
  [
    "hospital_daily_amount",
    {
      hospitalization_days: 10,
      taiwan_inpatient_daily_event_status:
        "eligible_disease_after_waiting_period",
    },
  ],
  [
    "hospitalization_days",
    {
      hospital_daily_amount: 1_000,
      taiwan_inpatient_daily_event_status:
        "eligible_disease_after_waiting_period",
    },
  ],
  [
    "taiwan_inpatient_daily_event_status",
    {
      hospital_daily_amount: 1_000,
      hospitalization_days: 10,
    },
  ],
]) {
  const result = coverageResult(schedule, policyState);
  assert.equal(result.state, "needs_policy_state");
  assert.deepEqual(result.required_fields, [missingKey]);
}

console.log({
  status: "ok",
  batch_id: "tii-life-032",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 7 + 3,
});

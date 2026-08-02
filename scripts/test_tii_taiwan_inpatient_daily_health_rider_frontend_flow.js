const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-008-taiwan-inpatient-daily-health-rider-v267.json",
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
  const revision = Number(
    schedule.version_characteristics.terms_revision.replace(
      "partial_change_",
      "",
    ),
  );
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

  const eligibleDisease = coverageResult(schedule, {
    hospital_daily_amount: 1_500,
    hospitalization_days: 20,
    taiwan_inpatient_daily_event_status:
      "eligible_disease_after_waiting_period",
  });
  assert.equal(eligibleDisease.state, "policy_state_value");
  assert.equal(eligibleDisease.value, 30_000);
  assert.equal(eligibleDisease.eligible_quantity, 20);

  const cappedAccident = coverageResult(schedule, {
    hospital_daily_amount: 1_500,
    hospitalization_days: 120,
    taiwan_inpatient_daily_event_status: "eligible_accident",
  });
  assert.equal(cappedAccident.state, "policy_state_value");
  assert.equal(cappedAccident.value, 135_000);
  assert.equal(cappedAccident.quantity, 120);
  assert.equal(cappedAccident.eligible_quantity, 90);
  assert.equal(cappedAccident.quantity_cap, 90);

  const waitingPeriod = coverageResult(schedule, {
    hospital_daily_amount: 1_500,
    hospitalization_days: 10,
    taiwan_inpatient_daily_event_status:
      "disease_within_waiting_period",
  });
  assert.equal(waitingPeriod.state, "not_eligible");
  assert.equal(waitingPeriod.value, 0);

  const dayHospital = coverageResult(schedule, {
    hospital_daily_amount: 1_500,
    hospitalization_days: 1,
    taiwan_inpatient_daily_event_status:
      "day_hospital_or_day_care",
  });
  if (revision >= 7) {
    assert.equal(dayHospital.state, "not_eligible");
    assert.equal(dayHospital.value, 0);
  } else {
    assert.equal(
      dayHospital.state,
      "needs_insurer_confirmation",
    );
    assert.equal(
      dayHospital.confirmation_reason,
      "day_hospital_not_explicitly_resolved",
    );
  }

  const uncertain = coverageResult(schedule, {
    hospital_daily_amount: 1_500,
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
    "inpatient_event_eligibility_uncertain",
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
      hospital_daily_amount: 1_500,
      taiwan_inpatient_daily_event_status:
        "eligible_disease_after_waiting_period",
    },
  ],
  [
    "taiwan_inpatient_daily_event_status",
    {
      hospital_daily_amount: 1_500,
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
  batch_id: "tii-life-008",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 5 + 3,
});

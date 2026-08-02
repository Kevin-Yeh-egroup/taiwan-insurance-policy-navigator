const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-008-taiwan-yongjian-hospital-medical-health-rider-v269.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

function coverageResult(schedule, entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find(
      (entry) => entry.id === entryId,
    ),
    {
      ...schedule,
      policy_state: policyState,
    },
  );
}

const expectedFields = new Set([
  "hospital_daily_amount",
  "hospitalization_days",
  "intensive_care_days",
  "burn_unit_days",
  "hospital_transfer_count",
  "taiwan_yongjian_surgery_multiplier",
  "taiwan_inpatient_daily_event_status",
]);

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
    expectedFields,
  );

  const commonState = {
    hospital_daily_amount: 1_000,
    hospitalization_days: 40,
    intensive_care_days: 2,
    burn_unit_days: 1,
    hospital_transfer_count: 1,
    taiwan_yongjian_surgery_multiplier: 12,
    taiwan_inpatient_daily_event_status: "eligible_accident",
  };
  const expectedValues = {
    "hospital-daily-medical-benefit": ["calculated", 45_000],
    "discharge-recuperation-benefit": [
      "policy_state_percentage",
      20_000,
    ],
    "surgery-benefit": ["policy_state_multiplier", 12_000],
    "surgery-recuperation-benefit": [
      "policy_state_multiplier",
      6_000,
    ],
    "intensive-care-benefit": [
      "policy_state_percentage",
      4_000,
    ],
    "burn-unit-benefit": ["policy_state_percentage", 2_000],
    "hospital-transfer-benefit": [
      "policy_state_percentage",
      1_000,
    ],
  };
  for (const [entryId, [expectedState, expectedValue]] of Object.entries(
    expectedValues,
  )) {
    const result = coverageResult(
      schedule,
      entryId,
      commonState,
    );
    assert.equal(result.state, expectedState, entryId);
    assert.equal(result.value, expectedValue, entryId);
  }

  const waitingPeriod = coverageResult(
    schedule,
    "hospital-daily-medical-benefit",
    {
      ...commonState,
      taiwan_inpatient_daily_event_status:
        "disease_within_waiting_period",
    },
  );
  assert.equal(waitingPeriod.state, "not_eligible");
  assert.equal(waitingPeriod.value, 0);

  const dayHospital = coverageResult(
    schedule,
    "hospital-daily-medical-benefit",
    {
      ...commonState,
      taiwan_inpatient_daily_event_status:
        "day_hospital_or_day_care",
    },
  );
  if (revision >= 7) {
    assert.equal(dayHospital.state, "not_eligible");
    assert.equal(dayHospital.value, 0);
  } else {
    assert.equal(
      dayHospital.state,
      "needs_insurer_confirmation",
    );
  }
}

const schedule =
  proposal.proposals[proposal.proposals.length - 1].candidates[0]
    .schedule;
const missingTransfer = coverageResult(
  schedule,
  "hospital-transfer-benefit",
  {
    hospital_daily_amount: 1_000,
    taiwan_inpatient_daily_event_status: "eligible_accident",
  },
);
assert.equal(missingTransfer.state, "needs_policy_state");
assert.deepEqual(missingTransfer.required_fields, [
  "hospital_transfer_count",
]);

const zeroTransfer = coverageResult(
  schedule,
  "hospital-transfer-benefit",
  {
    hospital_daily_amount: 1_000,
    hospital_transfer_count: 0,
    taiwan_inpatient_daily_event_status: "eligible_accident",
  },
);
assert.equal(zeroTransfer.state, "policy_state_percentage");
assert.equal(zeroTransfer.value, 0);

assert.equal(
  model.POLICY_STATE_FIELDS.hospital_transfer_count.max,
  1,
);
assert.equal(
  model.POLICY_STATE_FIELDS
    .taiwan_yongjian_surgery_multiplier.max,
  50,
);

console.log({
  status: "ok",
  batch_id: "tii-life-008",
  product_count: proposal.proposal_count,
  calculated_entry_cases: proposal.proposal_count * 7,
});

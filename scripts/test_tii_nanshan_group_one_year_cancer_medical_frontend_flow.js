const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-032-nanshan-group-one-year-cancer-medical-v246.json",
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

function resultFor(schedule, entryId, policyState) {
  const entry = schedule.coverage_entries.find(
    (item) => item.id === entryId,
  );
  return model.coverageValue(entry, {
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
    model.policyStateRequirements(schedule).fields.map(
      (field) => field.key,
    ),
    [
      "cancer_hospital_daily_amount",
      "cancer_hospitalization_days",
      "cancer_surgery_benefit_amount",
      "cancer_surgery_count",
      "cancer_death_benefit_amount",
      "cancer_recovery_daily_amount",
    ],
  );
  const state = {
    cancer_hospital_daily_amount: 1_500,
    cancer_hospitalization_days: 30,
    cancer_surgery_benefit_amount: 30_000,
    cancer_surgery_count: 2,
    cancer_death_benefit_amount: 250_000,
    cancer_recovery_daily_amount: 500,
  };
  assert.equal(
    resultFor(
      schedule,
      "cancer-inpatient-daily-benefit",
      state,
    ).value,
    45_000,
  );
  assert.equal(
    resultFor(
      schedule,
      "cancer-surgery-treatment-benefit",
      state,
    ).value,
    60_000,
  );
  assert.equal(
    resultFor(schedule, "cancer-death-benefit", state).value,
    250_000,
  );
}

const earlySchedule = scheduleFor("206327M11A30100");
const laterSchedule = scheduleFor(
  "206323MZ1A30121A11Z10000015",
);
const sharedState = {
  cancer_hospital_daily_amount: 1_500,
  cancer_hospitalization_days: 30,
  cancer_surgery_benefit_amount: 30_000,
  cancer_surgery_count: 2,
  cancer_death_benefit_amount: 250_000,
  cancer_recovery_daily_amount: 500,
};
const earlyRecovery = resultFor(
  earlySchedule,
  "cancer-post-discharge-recovery-benefit",
  sharedState,
);
assert.equal(earlyRecovery.value, 10_500);
assert.equal(earlyRecovery.quantity, 30);
assert.equal(earlyRecovery.eligible_quantity, 21);
assert.equal(earlyRecovery.quantity_cap, 21);
assert.equal(
  resultFor(
    laterSchedule,
    "cancer-post-discharge-recovery-benefit",
    sharedState,
  ).value,
  15_000,
);

const missingHospitalDays = resultFor(
  laterSchedule,
  "cancer-inpatient-daily-benefit",
  { cancer_hospital_daily_amount: 1_500 },
);
assert.equal(missingHospitalDays.state, "needs_policy_state");
assert.deepEqual(
  missingHospitalDays.required_fields,
  ["cancer_hospitalization_days"],
);

const missingSurgeryAmount = resultFor(
  laterSchedule,
  "cancer-surgery-treatment-benefit",
  { cancer_surgery_count: 2 },
);
assert.equal(missingSurgeryAmount.state, "needs_policy_state");
assert.deepEqual(
  missingSurgeryAmount.required_fields,
  ["cancer_surgery_benefit_amount"],
);

console.log({
  status: "ok",
  batch_id: "tii-life-032",
  product_count: proposal.proposal_count,
  user_flow_cases: proposal.proposal_count * 4 + 4,
});

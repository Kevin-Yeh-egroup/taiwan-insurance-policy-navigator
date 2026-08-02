const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-014-prudential-group-cancer-hospital-daily-v257.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 15);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function valueFor(schedule, entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find((entry) => entry.id === entryId),
    { ...schedule, policy_state: policyState },
  );
}

function requiredFieldKeys(schedule) {
  return model
    .policyStateRequirements(schedule)
    .fields.map((field) => field.key);
}

const legacySchedule = scheduleFor("203327M11A00100");
const severeSchedule = scheduleFor(
  "203323MZ1A00121A11Z10000012",
);
const policyState = {
  cancer_hospital_daily_amount: 3_000,
  cancer_hospitalization_days: 20,
};

for (const schedule of [legacySchedule, severeSchedule]) {
  assert.equal(model.selectionRequirements(schedule).mode, "policy_state");
  assert.deepEqual(
    new Set(requiredFieldKeys(schedule)),
    new Set([
      "cancer_hospital_daily_amount",
      "cancer_hospitalization_days",
    ]),
  );
  assert.equal(
    valueFor(
      schedule,
      "cancer-hospital-daily-benefit",
      policyState,
    ).value,
    60_000,
  );
  assert.equal(
    valueFor(
      schedule,
      "post-discharge-home-recovery-benefit",
      policyState,
    ).value,
    36_000,
  );
}

const cappedState = {
  cancer_hospital_daily_amount: 3_000,
  cancer_hospitalization_days: 400,
};
const cappedHospital = valueFor(
  severeSchedule,
  "cancer-hospital-daily-benefit",
  cappedState,
);
assert.equal(cappedHospital.value, 1_095_000);
assert.equal(cappedHospital.eligible_quantity, 365);
assert.equal(cappedHospital.quantity_cap, 365);

const cappedRecovery = valueFor(
  severeSchedule,
  "post-discharge-home-recovery-benefit",
  cappedState,
);
assert.equal(cappedRecovery.value, 657_000);
assert.equal(cappedRecovery.eligible_quantity, 365);

const missingDailyAmount = valueFor(
  severeSchedule,
  "cancer-hospital-daily-benefit",
  { cancer_hospitalization_days: 20 },
);
assert.equal(missingDailyAmount.state, "needs_policy_state");
assert.ok(
  missingDailyAmount.required_fields.includes(
    "cancer_hospital_daily_amount",
  ),
);

const missingDays = valueFor(
  severeSchedule,
  "post-discharge-home-recovery-benefit",
  { cancer_hospital_daily_amount: 3_000 },
);
assert.equal(missingDays.state, "needs_policy_state");
assert.ok(
  missingDays.required_fields.includes(
    "cancer_hospitalization_days",
  ),
);

assert.equal(
  model.POLICY_STATE_FIELDS.cancer_hospitalization_days.type,
  "integer",
);
assert.equal(
  model.POLICY_STATE_FIELDS.cancer_hospital_daily_amount.type,
  "money",
);

console.log({
  status: "ok",
  batch_id: "tii-life-014",
  product_count: proposal.proposal_count,
  input_flow: "daily-amount-and-eligible-hospital-days",
  hospital_value: 60_000,
  recovery_value: 36_000,
});

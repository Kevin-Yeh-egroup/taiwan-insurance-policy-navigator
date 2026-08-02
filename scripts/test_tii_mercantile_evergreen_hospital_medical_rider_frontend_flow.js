const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-062-mercantile-evergreen-hospital-medical-rider-v278.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, policyState = {}) {
  return {
    ...schedule,
    face_amount: 1_000,
    policy_state: policyState,
  };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [
      entry.id,
      entry,
    ]),
  );
}

const revision0 = scheduleFor("211311R11A00700");
assert.equal(
  model.selectionRequirements(revision0).mode,
  "face_amount",
);
assert.equal(
  revision0.version_characteristics.same_hospital_readmission_days,
  90,
);

const fortyFiveDays = selectedSchedule(revision0, {
  hospitalization_days: 45,
  intensive_care_days: 40,
  surgery_benefit_multiplier_decimal: 20,
});
const entries = entriesFor(fortyFiveDays);
assert.equal(
  model.coverageValue(
    entries["hospital-daily-benefit"],
    fortyFiveDays,
  ).value,
  45_000,
);
assert.equal(
  model.coverageValue(
    entries["intensive-care-additional-benefit"],
    fortyFiveDays,
  ).value,
  25_000,
);
assert.equal(
  model.coverageValue(
    entries["surgery-benefit"],
    fortyFiveDays,
  ).value,
  20_000,
);
assert.equal(
  model.coverageValue(
    entries["discharge-recuperation-benefit"],
    fortyFiveDays,
  ).value,
  37_500,
);

const capped = selectedSchedule(revision0, {
  hospitalization_days: 500,
  intensive_care_days: 100,
});
const cappedEntries = entriesFor(capped);
assert.equal(
  model.coverageValue(
    cappedEntries["hospital-daily-benefit"],
    capped,
  ).value,
  365_000,
);
assert.equal(
  model.coverageValue(
    cappedEntries["intensive-care-additional-benefit"],
    capped,
  ).value,
  45_000,
);
assert.equal(
  model.coverageValue(
    cappedEntries["discharge-recuperation-benefit"],
    capped,
  ).value,
  112_500,
);

const missingSurgeryMultiplier = selectedSchedule(revision0, {});
const missingSurgeryResult = model.coverageValue(
  entriesFor(missingSurgeryMultiplier)["surgery-benefit"],
  missingSurgeryMultiplier,
);
assert.equal(missingSurgeryResult.state, "needs_policy_state");
assert.deepEqual(missingSurgeryResult.required_fields, [
  "surgery_benefit_multiplier_decimal",
]);

const requiredKeys = model
  .policyStateRequirements({
    ...revision0,
    face_amount: 1_000,
    policy_state: {},
  })
  .fields.map((field) => field.key);
for (const key of [
  "hospitalization_days",
  "intensive_care_days",
  "surgery_benefit_multiplier_decimal",
]) {
  assert(requiredKeys.includes(key), key);
}

const revision8 = scheduleFor("211311R11A00708");
assert.equal(
  revision8.version_characteristics
    .post_expiry_readmission_excluded,
  true,
);
assert.equal(
  revision8.version_characteristics.day_hospital_excluded,
  false,
);
const revision9 = scheduleFor("211311R11A00709");
assert.equal(
  revision9.version_characteristics.day_hospital_excluded,
  true,
);

console.log({
  status: "ok",
  batch_id: "tii-life-062",
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

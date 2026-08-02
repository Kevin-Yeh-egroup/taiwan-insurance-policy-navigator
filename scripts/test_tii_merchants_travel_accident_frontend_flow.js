const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-061-merchants-travel-accident-v221.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 25);
assert.equal(proposal.proposed_count, 25);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectionFor(schedule, faceAmount, policyState = {}) {
  return {
    ...schedule,
    face_amount: faceAmount,
    policy_state: policyState,
  };
}

function entriesFor(selection) {
  return Object.fromEntries(
    selection.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(selection, entryId) {
  return model.coverageValue(
    entriesFor(selection)[entryId],
    selection,
  );
}

function policyFields(selection) {
  return model.policyStateRequirements(selection).fields;
}

const original = scheduleFor("211221M11A00100");
const latest = scheduleFor("211221MZ1A00121A11Z10000024");

assert.equal(model.selectionRequirements(original).mode, "face_amount");
assert.deepEqual(
  model.selectionRequirements(original).fields,
  ["face_amount"],
);

const originalMissingMedicalDecision = selectionFor(
  original,
  2_000_000,
  {
    same_accident_prior_disability_benefit_paid_amount: 0,
    disability_benefit_rate_percent: "35",
    prior_disability_benefit_paid_amount: 0,
  },
);
assert.deepEqual(
  policyFields(originalMissingMedicalDecision).map((field) => field.key),
  [
    "same_accident_prior_disability_benefit_paid_amount",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "injury_medical_rider_status",
  ],
);
assert.deepEqual(
  policyFields(originalMissingMedicalDecision)[1].options.map(
    (option) => option.value,
  ),
  ["100", "75", "50", "35", "15", "5"],
);

const originalNoMedical = selectionFor(original, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  disability_benefit_rate_percent: "35",
  prior_disability_benefit_paid_amount: 100_000,
  injury_medical_rider_status: "not_included",
});
assert.deepEqual(
  policyFields(originalNoMedical).map((field) => field.key),
  [
    "same_accident_prior_disability_benefit_paid_amount",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "injury_medical_rider_status",
  ],
);
assert.equal(
  valueFor(originalNoMedical, "accidental-death").value,
  2_000_000,
);
assert.equal(
  valueFor(originalNoMedical, "accidental-disability").value,
  600_000,
);
const noMedicalResult = valueFor(
  originalNoMedical,
  "injury-medical-reimbursement",
);
assert.equal(noMedicalResult.value, 0);
assert.equal(noMedicalResult.state, "not_eligible");

const originalWithMedical = selectionFor(original, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  disability_benefit_rate_percent: "35",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "included",
  injury_medical_expense: 120_000,
  reimbursement_limit: 100_000,
  prior_same_injury_medical_benefit_paid_amount: 20_000,
});
assert.equal(
  valueFor(originalWithMedical, "accidental-death").value,
  2_000_000,
);
assert.equal(
  valueFor(originalWithMedical, "accidental-disability").value,
  700_000,
);
const medicalResult = valueFor(
  originalWithMedical,
  "injury-medical-reimbursement",
);
assert.equal(medicalResult.value, 80_000);
assert.equal(medicalResult.state, "calculated");
assert.equal(medicalResult.eligible_expense, 120_000);
assert.equal(medicalResult.reference_amount, 100_000);
assert.equal(medicalResult.remaining_aggregate_limit, 80_000);

const originalMissingMedicalLimit = selectionFor(original, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  disability_benefit_rate_percent: "35",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "included",
  injury_medical_expense: 120_000,
  prior_same_injury_medical_benefit_paid_amount: 0,
});
const missingMedicalLimit = valueFor(
  originalMissingMedicalLimit,
  "injury-medical-reimbursement",
);
assert.equal(missingMedicalLimit.state, "needs_policy_state");
assert.deepEqual(missingMedicalLimit.required_fields, [
  "reimbursement_limit",
]);

const latestMissingStatus = selectionFor(latest, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "not_included",
});
assert.deepEqual(
  policyFields(latestMissingStatus).map((field) => field.key),
  [
    "same_accident_prior_disability_benefit_paid_amount",
    "death_benefit_status",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "injury_medical_rider_status",
  ],
);
assert.deepEqual(
  policyFields(latestMissingStatus)[2].options.map(
    (option) => option.value,
  ),
  ["100", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5"],
);

const latestStandard = selectionFor(latest, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 200_000,
  death_benefit_status: "standard_death",
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "not_included",
});
assert.equal(
  valueFor(
    latestStandard,
    "accidental-death-or-funeral",
  ).value,
  1_800_000,
);
assert.deepEqual(
  policyFields(latestStandard).map((field) => field.key),
  [
    "same_accident_prior_disability_benefit_paid_amount",
    "death_benefit_status",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "injury_medical_rider_status",
  ],
);

const latestFuneralMissingLimit = selectionFor(latest, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 200_000,
  death_benefit_status: "funeral_limited",
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "not_included",
});
assert.deepEqual(
  policyFields(latestFuneralMissingLimit).map((field) => field.key),
  [
    "same_accident_prior_disability_benefit_paid_amount",
    "death_benefit_status",
    "remaining_funeral_benefit_limit",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "injury_medical_rider_status",
  ],
);
assert.equal(
  valueFor(
    latestFuneralMissingLimit,
    "accidental-death-or-funeral",
  ).state,
  "needs_policy_state",
);

const latestFuneral = selectionFor(latest, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 200_000,
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 500_000,
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "not_included",
});
const funeralResult = valueFor(
  latestFuneral,
  "accidental-death-or-funeral",
);
assert.equal(funeralResult.value, 500_000);
assert.equal(funeralResult.gross_value_before_funeral_cap, 2_000_000);
assert.equal(funeralResult.funeral_benefit_limit, 500_000);
assert.equal(funeralResult.remaining_same_accident_amount, 1_800_000);

const latestInvalidRate = selectionFor(latest, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  death_benefit_status: "standard_death",
  disability_benefit_rate_percent: "35",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_rider_status: "not_included",
});
const invalidRateResult = valueFor(
  latestInvalidRate,
  "accidental-disability",
);
assert.equal(invalidRateResult.state, "needs_policy_state");
assert.deepEqual(invalidRateResult.required_fields, [
  "disability_benefit_rate_percent",
]);

assert.equal(
  original.version_characteristics.disability_term,
  "殘廢",
);
assert.equal(
  latest.version_characteristics.disability_term,
  "失能",
);
assert.equal(
  original.version_characteristics.after_180_causal_exception,
  false,
);
assert.equal(
  latest.version_characteristics.after_180_causal_exception,
  true,
);

console.log({
  status: "ok",
  batch_id: "tii-life-061",
  product_count: proposal.proposal_count,
  user_flow_cases: 29,
});

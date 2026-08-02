const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-007-taiwan-travel-accident-v221.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 22);
assert.equal(proposal.proposed_count, 22);

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

const original = scheduleFor("202221M11A58000");
const age15Transition = scheduleFor("202221M11A58008");
const latest = scheduleFor("202221MZ1A58021A11Z10000021");

assert.equal(model.selectionRequirements(original).mode, "face_amount");
assert.deepEqual(
  model.selectionRequirements(original).fields,
  ["face_amount"],
);

const originalMissingState = selectionFor(original, 2_000_000);
assert.deepEqual(
  policyFields(originalMissingState).map((field) => field.key),
  [
    "same_accident_prior_disability_benefit_paid_amount",
    "death_benefit_status",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "injury_medical_expense",
    "prior_same_injury_medical_benefit_paid_amount",
    "reimbursement_limit",
  ],
);
assert.ok(
  !policyFields(originalMissingState)
    .map((field) => field.key)
    .includes("minor_death_benefit_status"),
);

const originalCalculated = selectionFor(original, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 200_000,
  death_benefit_status: "standard_death",
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 100_000,
  injury_medical_expense: 120_000,
  reimbursement_limit: 100_000,
  prior_same_injury_medical_benefit_paid_amount: 20_000,
});
assert.equal(
  valueFor(
    originalCalculated,
    "accidental-death-or-funeral",
  ).value,
  1_800_000,
);
assert.equal(
  valueFor(originalCalculated, "accidental-disability").value,
  700_000,
);
const originalMedical = valueFor(
  originalCalculated,
  "injury-medical-reimbursement",
);
assert.equal(originalMedical.value, 80_000);
assert.equal(originalMedical.state, "calculated");
assert.equal(originalMedical.eligible_expense, 120_000);
assert.equal(originalMedical.reference_amount, 100_000);
assert.equal(originalMedical.remaining_aggregate_limit, 80_000);

const age15MissingDecision = selectionFor(
  age15Transition,
  2_000_000,
);
assert.equal(
  policyFields(age15MissingDecision)[0].key,
  "minor_death_benefit_status",
);
assert.deepEqual(
  policyFields(age15MissingDecision)[0].options.map(
    (option) => option.value,
  ),
  ["effective", "not_effective"],
);
assert.equal(
  valueFor(
    age15MissingDecision,
    "accidental-death-or-funeral",
  ).state,
  "needs_policy_state",
);

const age15NotEffective = selectionFor(age15Transition, 2_000_000, {
  minor_death_benefit_status: "not_effective",
});
const notEffectiveResult = valueFor(
  age15NotEffective,
  "accidental-death-or-funeral",
);
assert.equal(notEffectiveResult.value, 0);
assert.equal(notEffectiveResult.state, "not_eligible");
assert.equal(
  notEffectiveResult.exclusion_state_key,
  "minor_death_benefit_status",
);
assert.ok(
  !policyFields(age15NotEffective)
    .map((field) => field.key)
    .includes("death_benefit_status"),
);

const latestStandard = selectionFor(latest, 2_000_000, {
  minor_death_benefit_status: "effective",
  same_accident_prior_disability_benefit_paid_amount: 200_000,
  death_benefit_status: "standard_death",
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_expense: 0,
  reimbursement_limit: 100_000,
  prior_same_injury_medical_benefit_paid_amount: 0,
});
assert.equal(
  valueFor(
    latestStandard,
    "accidental-death-or-funeral",
  ).value,
  1_800_000,
);
const rateField = policyFields(latestStandard).find(
  (field) => field.key === "disability_benefit_rate_percent",
);
assert.deepEqual(
  rateField.options.map((option) => option.value),
  ["100", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5"],
);
assert.ok(
  !policyFields(latestStandard)
    .map((field) => field.key)
    .includes("injury_medical_rider_status"),
);

const latestFuneralMissingLimit = selectionFor(latest, 2_000_000, {
  minor_death_benefit_status: "effective",
  same_accident_prior_disability_benefit_paid_amount: 200_000,
  death_benefit_status: "funeral_limited",
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  injury_medical_expense: 0,
  reimbursement_limit: 100_000,
  prior_same_injury_medical_benefit_paid_amount: 0,
});
assert.ok(
  policyFields(latestFuneralMissingLimit)
    .map((field) => field.key)
    .includes("remaining_funeral_benefit_limit"),
);
assert.equal(
  valueFor(
    latestFuneralMissingLimit,
    "accidental-death-or-funeral",
  ).state,
  "needs_policy_state",
);

const latestFuneral = selectionFor(latest, 2_000_000, {
  ...latestFuneralMissingLimit.policy_state,
  remaining_funeral_benefit_limit: 500_000,
});
const funeralResult = valueFor(
  latestFuneral,
  "accidental-death-or-funeral",
);
assert.equal(funeralResult.value, 500_000);
assert.equal(funeralResult.gross_value_before_funeral_cap, 2_000_000);
assert.equal(funeralResult.funeral_benefit_limit, 500_000);
assert.equal(funeralResult.remaining_same_accident_amount, 1_800_000);

const invalidRate = selectionFor(latest, 2_000_000, {
  ...latestStandard.policy_state,
  disability_benefit_rate_percent: "35",
});
const invalidRateResult = valueFor(
  invalidRate,
  "accidental-disability",
);
assert.equal(invalidRateResult.state, "needs_policy_state");
assert.deepEqual(invalidRateResult.required_fields, [
  "disability_benefit_rate_percent",
]);

assert.equal(original.version_characteristics.disability_term, "殘廢");
assert.equal(latest.version_characteristics.disability_term, "失能");
assert.equal(
  original.version_characteristics.minor_death_benefit_rule,
  "under_14_converts_to_funeral",
);
assert.equal(
  latest.version_characteristics.minor_death_benefit_rule,
  "under_15_benefit_not_effective",
);
assert.equal(
  original.version_characteristics.injury_medical_in_main_terms,
  true,
);
assert.equal(
  latest.version_characteristics.source_text_extractor,
  "pypdf",
);

console.log({
  status: "ok",
  batch_id: "tii-life-007",
  product_count: proposal.proposal_count,
  user_flow_cases: 36,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-031-nanshan-travel-accident-v226.json",
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

const original = scheduleFor("206221M11A30100");
const under15Version = scheduleFor("206221M11A30110");
const deathCareVersion = scheduleFor("206221M11A30115");
const latest = scheduleFor("206221MZ1A30221A11Z10000021");

assert.equal(model.selectionRequirements(original).mode, "face_amount");
assert.deepEqual(
  model.selectionRequirements(original).fields,
  ["face_amount"],
);

const originalSelection = selectionFor(original, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  death_benefit_status: "standard_death",
  disability_benefit_rate_percent: "35",
  prior_disability_benefit_paid_amount: 100_000,
  prior_same_insurer_major_burn_claim_status: "not_paid",
  same_insurer_other_major_burn_benefit_amount: 0,
  injury_medical_rider_status: "not_included",
});
assert.equal(
  valueFor(
    originalSelection,
    "accidental-death-or-funeral",
  ).value,
  2_000_000,
);
assert.equal(
  valueFor(
    originalSelection,
    "accidental-disability",
  ).value,
  600_000,
);
assert.equal(
  valueFor(originalSelection, "major-burn-benefit").value,
  500_000,
);
assert.equal(
  valueFor(
    originalSelection,
    "injury-medical-reimbursement",
  ).state,
  "not_eligible",
);
assert.deepEqual(
  policyFields(originalSelection)
    .find(
      (field) =>
        field.key === "disability_benefit_rate_percent",
    )
    .options.map((option) => option.value),
  ["100", "75", "50", "35", "15", "5"],
);

const under15Selection = selectionFor(under15Version, 2_000_000, {
  same_accident_prior_disability_benefit_paid_amount: 0,
  minor_death_benefit_status: "not_effective",
  death_benefit_status: "standard_death",
  disability_benefit_rate_percent: "40",
  prior_disability_benefit_paid_amount: 0,
  prior_same_insurer_major_burn_claim_status: "not_paid",
  same_insurer_other_major_burn_benefit_amount: 0,
  injury_medical_rider_status: "not_included",
});
const under15Death = valueFor(
  under15Selection,
  "accidental-death-or-funeral",
);
assert.equal(under15Death.value, 0);
assert.equal(under15Death.state, "not_eligible");
assert.equal(
  under15Death.exclusion_state_key,
  "minor_death_benefit_status",
);

const deathCareStandard = selectionFor(
  deathCareVersion,
  2_000_000,
  {
    same_accident_prior_disability_benefit_paid_amount: 200_000,
    minor_death_benefit_status: "effective",
    death_benefit_status: "standard_death",
    disability_benefit_rate_percent: "40",
    prior_disability_benefit_paid_amount: 0,
    prior_same_insurer_major_burn_claim_status: "not_paid",
    same_insurer_other_major_burn_benefit_amount: 0,
    injury_medical_rider_status: "not_included",
  },
);
const deathCareStandardResult = valueFor(
  deathCareStandard,
  "accidental-death-and-care-or-funeral",
);
assert.equal(deathCareStandardResult.value, 1_900_000);
assert.equal(deathCareStandardResult.face_amount, 2_000_000);
assert.equal(deathCareStandardResult.applied_rate, 1.05);
assert.equal(
  deathCareStandardResult.gross_value_before_funeral_cap,
  2_100_000,
);

const deathCareFuneral = selectionFor(
  deathCareVersion,
  2_000_000,
  {
    ...deathCareStandard.policy_state,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 500_000,
  },
);
const deathCareFuneralResult = valueFor(
  deathCareFuneral,
  "accidental-death-and-care-or-funeral",
);
assert.equal(deathCareFuneralResult.value, 500_000);
assert.equal(
  deathCareFuneralResult.formula_type,
  "face_amount_percentage_funeral_cap",
);
assert.equal(
  deathCareFuneralResult.gross_value_before_funeral_cap,
  2_100_000,
);

const singlePolicyAboveBurnCap = selectionFor(
  latest,
  12_000_000,
  {
    same_accident_prior_disability_benefit_paid_amount: 0,
    minor_death_benefit_status: "effective",
    death_benefit_status: "standard_death",
    disability_benefit_rate_percent: "40",
    prior_disability_benefit_paid_amount: 0,
    prior_same_insurer_major_burn_claim_status: "not_paid",
    same_insurer_other_major_burn_benefit_amount: 0,
    injury_medical_rider_status: "not_included",
  },
);
const singlePolicyBurnResult = valueFor(
  singlePolicyAboveBurnCap,
  "major-burn-benefit",
);
assert.equal(singlePolicyBurnResult.gross_value, 3_000_000);
assert.equal(singlePolicyBurnResult.value, 2_500_000);
assert.equal(singlePolicyBurnResult.aggregate_limit, 2_500_000);

const crossPolicyBurnAllocation = selectionFor(
  latest,
  2_000_000,
  {
    ...singlePolicyAboveBurnCap.policy_state,
    same_insurer_other_major_burn_benefit_amount: 2_200_000,
  },
);
const crossPolicyBurnResult = valueFor(
  crossPolicyBurnAllocation,
  "major-burn-benefit",
);
assert.equal(
  crossPolicyBurnResult.state,
  "needs_insurer_confirmation",
);
assert.equal(
  crossPolicyBurnResult.confirmation_reason,
  "aggregate_cap_allocation_required",
);
assert.equal(crossPolicyBurnResult.gross_value, 500_000);
assert.equal(
  crossPolicyBurnResult.combined_benefit_amount,
  2_700_000,
);
assert.equal(crossPolicyBurnResult.marginal_capacity, 300_000);

const priorBurnPaid = selectionFor(latest, 2_000_000, {
  ...singlePolicyAboveBurnCap.policy_state,
  prior_same_insurer_major_burn_claim_status: "paid",
});
const priorBurnPaidResult = valueFor(
  priorBurnPaid,
  "major-burn-benefit",
);
assert.equal(priorBurnPaidResult.value, 0);
assert.equal(priorBurnPaidResult.state, "not_eligible");
assert.equal(
  priorBurnPaidResult.exclusion_state_key,
  "prior_same_insurer_major_burn_claim_status",
);
assert.equal(
  policyFields(priorBurnPaid).some(
    (field) =>
      field.key ===
      "same_insurer_other_major_burn_benefit_amount",
  ),
  false,
);

const medicalIncluded = selectionFor(latest, 2_000_000, {
  ...singlePolicyAboveBurnCap.policy_state,
  injury_medical_rider_status: "included",
  injury_medical_expense: 120_000,
  reimbursement_limit: 100_000,
  prior_same_injury_medical_benefit_paid_amount: 20_000,
});
const medicalResult = valueFor(
  medicalIncluded,
  "injury-medical-reimbursement",
);
assert.equal(medicalResult.value, 80_000);
assert.equal(medicalResult.state, "calculated");
assert.equal(medicalResult.remaining_aggregate_limit, 80_000);

assert.deepEqual(
  policyFields(latest)
    .find(
      (field) =>
        field.key === "disability_benefit_rate_percent",
    )
    .options.map((option) => option.value),
  ["100", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5"],
);
assert.deepEqual(
  policyFields(latest).map((field) => field.key),
  [
    "minor_death_benefit_status",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "prior_same_insurer_major_burn_claim_status",
    "injury_medical_rider_status",
  ],
);
assert.deepEqual(
  policyFields(
    selectionFor(latest, 2_000_000, {
      minor_death_benefit_status: "effective",
    }),
  ).map((field) => field.key),
  [
    "minor_death_benefit_status",
    "same_accident_prior_disability_benefit_paid_amount",
    "death_benefit_status",
    "disability_benefit_rate_percent",
    "prior_disability_benefit_paid_amount",
    "prior_same_insurer_major_burn_claim_status",
    "injury_medical_rider_status",
  ],
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
  batch_id: "tii-life-031",
  product_count: proposal.proposal_count,
  user_flow_cases: 31,
});

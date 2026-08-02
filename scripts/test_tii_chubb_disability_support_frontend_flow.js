const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-182-chubb-disability-support-addendum-v225.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 38);
assert.equal(proposal.proposed_count, 38);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function entryFor(schedule, entryId) {
  return schedule.coverage_entries.find(
    (entry) => entry.id === entryId,
  );
}

function selectionFor(
  schedule,
  policyState = {},
  faceAmount = 5_000_000,
  planName = "",
) {
  return {
    ...schedule,
    face_amount: faceAmount,
    plan_name: planName,
    policy_state: policyState,
  };
}

function monthlyValue(selection) {
  return model.coverageValue(
    entryFor(
      selection,
      "chubb-disability-support-monthly",
    ),
    selection,
  );
}

function deathBalanceValue(selection) {
  return model.coverageValue(
    entryFor(
      selection,
      "chubb-disability-support-death-balance",
    ),
    selection,
  );
}

const baseState = {
  disability_support_claim_status: "monthly_entitlement",
  policy_effect_status_at_event: "active",
  insured_age_at_event: 60,
  disability_grade: "1",
  disability_status_after_180_days: "persisting",
  other_disability_support_monthly_amount: 0,
  prior_disability_status: "none",
};

const legacy = scheduleFor("270391A11A00118");
const legacyGradeOne = monthlyValue(
  selectionFor(legacy, baseState),
);
assert.equal(legacyGradeOne.state, "calculated");
assert.equal(legacyGradeOne.value, 50_000);
assert.equal(legacyGradeOne.raw_monthly_amount, 50_000);
assert.equal(legacyGradeOne.payment_months, 100);
assert.equal(legacyGradeOne.payable_nominal_total, 5_000_000);
assert.equal(
  legacyGradeOne.allocation_state,
  "within_combined_cap",
);

const capped = monthlyValue(
  selectionFor(legacy, baseState, 20_000_000),
);
assert.equal(capped.value, 100_000);
assert.equal(capped.raw_monthly_amount, 200_000);
assert.equal(capped.payable_nominal_total, 10_000_000);

const combinedCapNeedsConfirmation = monthlyValue(
  selectionFor(legacy, {
    ...baseState,
    other_disability_support_monthly_amount: 70_000,
  }),
);
assert.equal(combinedCapNeedsConfirmation.value, 50_000);
assert.equal(
  combinedCapNeedsConfirmation.combined_monthly_total,
  120_000,
);
assert.equal(
  combinedCapNeedsConfirmation.marginal_monthly_capacity,
  30_000,
);
assert.equal(
  combinedCapNeedsConfirmation.allocation_state,
  "needs_insurer_confirmation",
);

const typed = scheduleFor("270391A11A00119");
const missingPlan = monthlyValue(
  selectionFor(typed, baseState),
);
assert.equal(missingPlan.state, "needs_plan");

const typedGradeThree = monthlyValue(
  selectionFor(
    typed,
    {...baseState, disability_grade: "3"},
    3_000_000,
    "investment",
  ),
);
assert.equal(typedGradeThree.value, 30_000);
assert.equal(typedGradeThree.payment_months, 75);
assert.equal(
  typedGradeThree.payable_nominal_total,
  2_250_000,
);
assert.equal(typedGradeThree.policy_type, "investment");

const priorNeedsApprovedMonths = monthlyValue(
  selectionFor(typed, {
    ...baseState,
    disability_grade: "3",
    prior_disability_status: "exists",
  }, 3_000_000, "non_investment"),
);
assert.equal(
  priorNeedsApprovedMonths.state,
  "needs_policy_state",
);
assert(
  priorNeedsApprovedMonths.required_fields.includes(
    "insurer_approved_remaining_disability_support_months",
  ),
);

const priorApproved = monthlyValue(
  selectionFor(typed, {
    ...baseState,
    disability_grade: "3",
    prior_disability_status: "exists",
    insurer_approved_remaining_disability_support_months: 20,
  }, 3_000_000, "non_investment"),
);
assert.equal(priorApproved.value, 30_000);
assert.equal(priorApproved.payable_payment_months, 20);
assert.equal(priorApproved.payable_nominal_total, 600_000);

const notPersisting = monthlyValue(
  selectionFor(legacy, {
    ...baseState,
    disability_status_after_180_days: "not_persisting",
  }),
);
assert.equal(notPersisting.state, "not_eligible");
assert.equal(notPersisting.value, 0);

const uncertainPersistence = monthlyValue(
  selectionFor(legacy, {
    ...baseState,
    disability_status_after_180_days: "uncertain",
  }),
);
assert.equal(
  uncertainPersistence.state,
  "needs_insurer_confirmation",
);

const age76 = monthlyValue(
  selectionFor(legacy, {
    ...baseState,
    insured_age_at_event: 76,
  }),
);
assert.equal(age76.state, "not_eligible");
assert.equal(age76.value, 0);

const fractionalMonthly = monthlyValue(
  selectionFor(legacy, baseState, 12_345),
);
assert.equal(
  fractionalMonthly.state,
  "needs_insurer_confirmation",
);
assert.equal(
  fractionalMonthly.confirmation_reason,
  "fractional_monthly_amount_rounding_undefined",
);

const deathSelection = selectionFor(legacy, {
  disability_support_claim_status: "death_during_payment",
  discounted_unpaid_disability_support_amount: 760_000,
});
const monthlyExcluded = monthlyValue(deathSelection);
assert.equal(monthlyExcluded.state, "not_eligible");
const deathBalance = deathBalanceValue(deathSelection);
assert.equal(deathBalance.state, "policy_state_value");
assert.equal(deathBalance.value, 760_000);

const initialRequirements = model.policyStateRequirements(
  selectionFor(legacy),
).fields;
assert.deepEqual(
  initialRequirements.map((field) => field.key),
  ["disability_support_claim_status"],
);
const monthlyRequirements = model.policyStateRequirements(
  selectionFor(legacy, {
    disability_support_claim_status: "monthly_entitlement",
  }),
).fields;
assert(
  monthlyRequirements.some(
    (field) => field.key === "disability_grade",
  ),
);
assert(
  monthlyRequirements.some(
    (field) => field.key === "prior_disability_status",
  ),
);

console.log({
  status: "ok",
  products: proposal.proposal_count,
  calculation_cases: 11,
  conditional_input_cases: 2,
});

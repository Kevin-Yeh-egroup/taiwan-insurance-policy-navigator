const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-group-one-year-cancer-health-rider-v276.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);
assert.equal(proposal.proposed_count, 14);
assert.equal(proposal.manual_review_count, 0);

const schedule = proposal.proposals[0].candidates[0].schedule;
const entries = Object.fromEntries(
  schedule.coverage_entries.map((entry) => [entry.id, entry]),
);
const eventKey = "fubon_group_one_year_cancer_event_status";

function selected(policyState) {
  return {
    ...schedule,
    policy_state: policyState,
  };
}

function value(entryId, policyState) {
  return model.coverageValue(
    entries[entryId],
    selected(policyState),
  );
}

assert.equal(model.selectionRequirements(schedule).mode, "policy_state");
assert.deepEqual(
  model.policyStateRequirements(schedule).fields.map(
    (field) => field.key,
  ),
  [eventKey],
);

const deathState = {
  [eventKey]: "eligible_cancer_death",
  cancer_death_benefit_amount: 800_000,
};
assert.equal(
  value("cancer-death-benefit", deathState).value,
  800_000,
);
assert.equal(
  value("cancer-inpatient-daily-benefit", deathState).state,
  "not_eligible",
);

const treatmentState = {
  [eventKey]: "eligible_cancer_treatment",
  cancer_hospital_daily_amount: 1_500,
  cancer_hospitalization_days: 6,
  cancer_recovery_daily_amount: 700,
  home_care_eligible_days: 8,
  cancer_radiation_daily_amount: 1_200,
  cancer_radiation_treatment_days: 4,
  cancer_surgery_benefit_amount: 25_000,
  cancer_surgery_count: 2,
};
assert.equal(
  value("cancer-inpatient-daily-benefit", treatmentState).value,
  9_000,
);
const homeCare = value(
  "cancer-post-discharge-home-care-benefit",
  treatmentState,
);
assert.equal(homeCare.value, 4_200);
assert.equal(homeCare.quantity, 8);
assert.equal(homeCare.eligible_quantity, 6);
assert.equal(homeCare.quantity_cap, 6);
assert.equal(
  value("cancer-radiation-daily-benefit", treatmentState).value,
  4_800,
);
assert.equal(
  value("cancer-surgery-treatment-benefit", treatmentState).value,
  50_000,
);
assert.equal(
  value("cancer-death-benefit", treatmentState).state,
  "not_eligible",
);

const treatmentRequirements = new Set(
  model.policyStateRequirements(selected(treatmentState)).fields.map(
    (field) => field.key,
  ),
);
for (const requiredKey of [
  eventKey,
  "cancer_hospital_daily_amount",
  "cancer_hospitalization_days",
  "cancer_recovery_daily_amount",
  "home_care_eligible_days",
  "cancer_radiation_daily_amount",
  "cancer_radiation_treatment_days",
  "cancer_surgery_benefit_amount",
  "cancer_surgery_count",
]) {
  assert(treatmentRequirements.has(requiredKey), requiredKey);
}
assert(!treatmentRequirements.has("cancer_death_benefit_amount"));
assert(
  !treatmentRequirements.has(
    "fubon_group_one_year_cancer_waiting_refund_amount",
  ),
);

const waitingState = {
  [eventKey]: "diagnosed_within_applicable_waiting_period",
  fubon_group_one_year_cancer_waiting_refund_amount: 3_200,
};
assert.equal(
  value("waiting-period-premium-refund", waitingState).value,
  3_200,
);
assert.equal(
  value("cancer-death-benefit", waitingState).state,
  "not_eligible",
);

const missingAmount = value("cancer-radiation-daily-benefit", {
  [eventKey]: "eligible_cancer_treatment",
  cancer_radiation_treatment_days: 4,
});
assert.equal(missingAmount.state, "needs_policy_state");
assert.deepEqual(missingAmount.required_fields, [
  "cancer_radiation_daily_amount",
]);

for (const entry of schedule.coverage_entries) {
  const uncertain = model.coverageValue(
    entry,
    selected({
      [eventKey]: "not_eligible_or_uncertain",
    }),
  );
  assert.equal(uncertain.state, "needs_insurer_confirmation");
  assert.equal(
    uncertain.confirmation_reason,
    "fubon_group_cancer_event_eligibility_uncertain",
  );
}

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 18,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-008-taiwan-new-cancer-health-v291.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);
assert.equal(proposal.proposed_count, 13);
assert.equal(proposal.manual_review_count, 0);

const schedule = proposal.proposals[0].candidates[0].schedule;
const entries = Object.fromEntries(
  schedule.coverage_entries.map((entry) => [entry.id, entry]),
);
const eventKey = "taiwan_new_cancer_health_event_status";

function selected(unitCount, policyState) {
  return {
    ...schedule,
    unit_count: unitCount,
    policy_state: policyState,
  };
}

function value(entryId, unitCount, policyState) {
  return model.coverageValue(
    entries[entryId],
    selected(unitCount, policyState),
  );
}

assert.equal(model.selectionRequirements(schedule).mode, "unit");
assert.deepEqual(
  model.policyStateRequirements(schedule).fields.map(
    (field) => field.key,
  ),
  [eventKey],
);

const hospitalState = {
  [eventKey]: "eligible_cancer_hospitalization",
  cancer_hospitalization_days: 4,
};
assert.equal(
  value("cancer-hospital-daily", 2, hospitalState).value,
  20_000,
);
assert.equal(
  value("cancer-death", 2, hospitalState).state,
  "not_eligible",
);
assert.equal(
  value("cancer-hospital-daily", 2, {
    [eventKey]: "eligible_cancer_hospitalization",
    cancer_hospitalization_days: 3650,
  }).value,
  18_250_000,
);

const homeState = {
  [eventKey]: "eligible_home_recovery",
  cancer_hospitalization_days: 6,
  taiwan_new_cancer_home_recovery_claim_count: 2,
};
assert.equal(
  value("cancer-home-recovery", 2, homeState).value,
  60_000,
);
assert.equal(
  value("cancer-home-recovery", 2, {
    ...homeState,
    cancer_hospitalization_days: 5,
  }).state,
  "not_eligible",
);
assert.equal(
  value("cancer-home-recovery", 2, {
    [eventKey]: "eligible_home_recovery",
  }).state,
  "needs_policy_state",
);

assert.equal(
  value("cancer-death", 2, {
    [eventKey]: "eligible_cancer_death",
  }).value,
  360_000,
);
assert.equal(
  value("waiting-period-premium-refund", 1, {
    [eventKey]: "diagnosed_within_initial_waiting_period",
    taiwan_new_cancer_waiting_refund_amount: 18_000,
  }).value,
  18_000,
);
assert.equal(
  value("non-cancer-death-current-year-premium-refund", 1, {
    [eventKey]: "eligible_non_cancer_death_refund",
    taiwan_new_cancer_policy_form: "individual",
    current_policy_year_paid_premium_amount: 24_000,
  }).value,
  24_000,
);
assert.equal(
  value("non-cancer-death-current-year-premium-refund", 1, {
    [eventKey]: "eligible_non_cancer_death_refund",
    taiwan_new_cancer_policy_form: "family",
    current_policy_year_paid_premium_amount: 24_000,
  }).value,
  12_000,
);

assert.equal(
  value("cancer-death", 3, {
    [eventKey]: "eligible_cancer_death",
  }).state,
  "needs_unit_count",
);
assert.equal(
  value("cancer-death", 1.5, {
    [eventKey]: "eligible_cancer_death",
  }).state,
  "needs_unit_count",
);
assert.equal(
  value("waiting-period-premium-refund", 1, {
    [eventKey]: "diagnosed_within_initial_waiting_period",
  }).state,
  "needs_policy_state",
);

for (const entry of schedule.coverage_entries) {
  const uncertain = model.coverageValue(
    entry,
    selected(1, {
      [eventKey]: "not_eligible_or_uncertain",
    }),
  );
  assert.equal(uncertain.state, "needs_insurer_confirmation");
  assert.equal(
    uncertain.confirmation_reason,
    "taiwan_new_cancer_event_eligibility_uncertain",
  );
}

const homeRequirements = new Set(
  model.policyStateRequirements(selected(2, homeState)).fields.map(
    (field) => field.key,
  ),
);
for (const requiredKey of [
  eventKey,
  "cancer_hospitalization_days",
  "taiwan_new_cancer_home_recovery_claim_count",
]) {
  assert(homeRequirements.has(requiredKey), requiredKey);
}
assert(!homeRequirements.has("current_policy_year_paid_premium_amount"));

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

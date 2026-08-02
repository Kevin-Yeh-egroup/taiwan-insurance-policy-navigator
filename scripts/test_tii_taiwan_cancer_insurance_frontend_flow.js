const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-008-taiwan-cancer-insurance-v292.json",
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
const eventKey = "taiwan_cancer_insurance_event_status";

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
  12_800,
);
assert.equal(
  value("posthumous-cancer-diagnosis-daily", 2, hospitalState).state,
  "not_eligible",
);
assert.equal(
  value("cancer-hospital-daily", 2, {
    [eventKey]: "eligible_cancer_hospitalization",
    cancer_hospitalization_days: 3650,
  }).value,
  11_680_000,
);

assert.equal(
  value("posthumous-cancer-diagnosis-daily", 2, {
    [eventKey]: "eligible_posthumous_cancer_diagnosis",
    cancer_hospitalization_days: 60,
  }).value,
  144_000,
);
assert.equal(
  value("waiting-period-premium-refund", 1, {
    [eventKey]: "diagnosed_within_initial_waiting_period",
    taiwan_cancer_waiting_refund_amount: 18_000,
  }).value,
  18_000,
);
assert.equal(
  value("precontract-unaware-cancer-premium-refund", 1, {
    [eventKey]: "precontract_unaware_cancer_premium_refund",
    taiwan_cancer_precontract_refund_amount: 24_000,
  }).value,
  24_000,
);

assert.equal(
  value("cancer-hospital-daily", 1.5, hospitalState).state,
  "needs_unit_count",
);
assert.equal(
  value("cancer-hospital-daily", 0, hospitalState).state,
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
    "taiwan_cancer_insurance_event_eligibility_uncertain",
  );
}

const posthumousRequirements = new Set(
  model.policyStateRequirements(
    selected(2, {
      [eventKey]: "eligible_posthumous_cancer_diagnosis",
    }),
  ).fields.map((field) => field.key),
);
assert(posthumousRequirements.has(eventKey));
assert(posthumousRequirements.has("cancer_hospitalization_days"));
assert(!posthumousRequirements.has("taiwan_cancer_waiting_refund_amount"));

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 14,
});

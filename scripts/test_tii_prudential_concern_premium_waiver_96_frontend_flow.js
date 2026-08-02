const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-014-prudential-concern-premium-waiver-96-v244.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 16);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (proposalItem) => proposalItem.product_id === productId,
  ).candidates[0].schedule;
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(schedule, entryId, policyState = {}) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    policy_state: policyState,
  });
}

const early = scheduleFor("203341R11A00301");
const requirementKeys = new Set(
  model
    .policyStateRequirements(early)
    .fields.map((field) => field.key),
);
assert.deepEqual(
  requirementKeys,
  new Set([
    "remaining_premium_amount",
    "unexpired_premium_refund_amount",
  ]),
);

const policyState = {
  remaining_premium_amount: 240_000,
  unexpired_premium_refund_amount: 12_000,
};
const waiver = valueFor(
  early,
  "specified-disease-future-premium-waiver",
  policyState,
);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 240_000);
assert.equal(waiver.result_kind, "non_cash_effect");

const refund = valueFor(
  early,
  "current-unexpired-premium-refund",
  policyState,
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 12_000);

const missingRemainingPremium = valueFor(
  early,
  "specified-disease-future-premium-waiver",
  {
    unexpired_premium_refund_amount: 12_000,
  },
);
assert.equal(
  missingRemainingPremium.state,
  "needs_policy_state",
);
assert(
  missingRemainingPremium.required_fields.includes(
    "remaining_premium_amount",
  ),
);

const scenarios = model.coverageEventScenarios({
  ...early,
  policy_state: policyState,
});
assert.equal(scenarios.length, 1);
assert.equal(scenarios[0].event_key, "specified_disease");
assert.equal(scenarios[0].value, 252_000);
assert.deepEqual(
  scenarios[0].additive_entry_ids,
  ["current-unexpired-premium-refund"],
);

for (const productItem of proposal.proposals) {
  const schedule = productItem.candidates[0].schedule;
  const characteristics = schedule.version_characteristics;
  assert.equal(
    characteristics.source_product_id,
    productItem.product_id,
  );
  assert.equal(
    characteristics.death_is_waiver_trigger,
    false,
  );
  assert.equal(
    characteristics.disability_or_impairment_is_waiver_trigger,
    false,
  );
  assert.equal(
    characteristics.first_policy_year_cash_benefit_available,
    false,
  );
  assert.deepEqual(
    Object.keys(entriesFor(schedule)).sort(),
    [
      "current-unexpired-premium-refund",
      "specified-disease-future-premium-waiver",
    ],
  );
}

const revision9 = scheduleFor(
  "203341RZ1A00322A11Z10000009",
).version_characteristics;
assert.equal(
  revision9.specific_disease_waiting_start_first_7,
  "effective_or_reinstatement_date",
);

const revision10 = scheduleFor(
  "203341RZ1A00322A11Z10000010",
).version_characteristics;
assert.equal(
  revision10.specific_disease_waiting_start_first_7,
  "effective_date",
);

const revision11 = scheduleFor(
  "203341RZ1A00322A11Z10000011",
).version_characteristics;
assert.equal(
  revision11.termination_definition_term,
  "失能",
);

console.log({
  status: "ok",
  batch_id: "tii-life-014",
  product_count: proposal.proposal_count,
  user_flow_cases: 18,
});

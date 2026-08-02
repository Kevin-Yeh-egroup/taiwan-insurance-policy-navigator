const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-014-prudential-anjia-premium-waiver-96-v243.json",
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

const early = scheduleFor("203341R11A00202");
const requirementKeys = new Set(
  model
    .policyStateRequirements(early)
    .fields.map((field) => field.key),
);
assert.deepEqual(
  requirementKeys,
  new Set([
    "remaining_premium_amount",
    "premium_total_amount",
    "policy_year",
    "unexpired_premium_refund_amount",
  ]),
);

const policyState = {
  remaining_premium_amount: 240_000,
  premium_total_amount: 100_000,
  policy_year: 1,
  unexpired_premium_refund_amount: 12_000,
};
const waiver = valueFor(
  early,
  "death-future-premium-waiver",
  policyState,
);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 240_000);
assert.equal(waiver.result_kind, "non_cash_effect");

const cancer = valueFor(
  early,
  "first-policy-year-cancer-triple-premium-benefit",
  policyState,
);
assert.equal(cancer.state, "policy_state_percentage");
assert.equal(cancer.value, 300_000);
assert.equal(cancer.reference_amount, 100_000);

const refund = valueFor(
  early,
  "current-unexpired-premium-refund",
  policyState,
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 12_000);

const missingPremiumTotal = valueFor(
  early,
  "first-policy-year-cancer-triple-premium-benefit",
  {
    ...policyState,
    premium_total_amount: undefined,
  },
);
assert.equal(missingPremiumTotal.state, "needs_policy_state");
assert(
  missingPremiumTotal.required_fields.includes(
    "premium_total_amount",
  ),
);

const scenarios = model.coverageEventScenarios({
  ...early,
  policy_state: policyState,
});
assert.equal(scenarios.length, 4);
assert.deepEqual(
  scenarios.map((scenario) => scenario.event_key),
  [
    "death",
    "disability_or_impairment",
    "specified_disease",
    "first_policy_year_cancer",
  ],
);
assert.deepEqual(
  scenarios.map((scenario) => scenario.value),
  [252_000, 252_000, 252_000, 312_000],
);
assert(
  scenarios.every(
    (scenario) =>
      scenario.additive_entry_ids.join(",") ===
      "current-unexpired-premium-refund",
  ),
);

const revised = scheduleFor(
  "203341RZ1A00222A11Z10000013",
);
assert.equal(
  entriesFor(revised)["disability-future-premium-waiver"].name,
  "第一至第六級失能後未來保險費豁免",
);
assert.equal(
  entriesFor(revised)[
    "first-policy-year-cancer-triple-premium-benefit"
  ].name,
  "第一保單年度癌症(重度)三倍年繳保費給付",
);

console.log({
  status: "ok",
  batch_id: "tii-life-014",
  product_count: proposal.proposal_count,
  user_flow_cases: 22,
});

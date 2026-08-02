const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-028-legacy-declared-rate-annuity-v217.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 12);
assert.equal(proposal.proposed_count, 12);

const schedules = Object.fromEntries(
  proposal.proposals.map((item) => [
    item.product_id,
    item.candidates[0].schedule,
  ]),
);
assert.ok(!schedules["205491M21A02701"]);

const selection = {
  ...schedules["205491M21A02806"],
  plan_name: "guarantee-15",
  policy_state: {
    policy_reserve_value: 1_000_000,
    policy_loan_and_interest_amount: 125_000,
    annuity_payment_amount: 60_000,
    unpaid_annuity_balance: 500_000,
    excess_annuity_reserve_return_amount: 0,
  },
};

assert.equal(model.selectionRequirements(selection).mode, "plan");
assert.deepEqual(
  model.policyStateRequirements(selection).fields.map(
    (field) => field.key,
  ),
  [
    "policy_reserve_value",
    "policy_loan_and_interest_amount",
    "annuity_payment_amount",
    "unpaid_annuity_balance",
    "excess_annuity_reserve_return_amount",
  ],
);

const entries = Object.fromEntries(
  model.effectiveCoverageEntries(selection).map((entry) => [
    entry.id,
    entry,
  ]),
);
for (const entryId of [
  "pre-annuity-death-reserve-return",
  "low-annuity-lump-sum-reserve-payment",
]) {
  const result = model.coverageValue(entries[entryId], selection);
  assert.equal(result.state, "calculated");
  assert.equal(result.value, 875_000);
}
assert.equal(
  model.coverageValue(
    entries["annual-annuity-payment"],
    selection,
  ).value,
  60_000,
);
assert.equal(
  model.coverageValue(
    entries["unpaid-guaranteed-annuity-balance"],
    selection,
  ).value,
  500_000,
);
assert.equal(
  model.coverageValue(
    entries["excess-annuity-reserve-return"],
    selection,
  ).value,
  0,
);

const appSource = fs.readFileSync(
  path.join(ROOT, "app.js"),
  "utf8",
);
const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__legacyDeclaredRateTestHooks = {
  coverageEntryText,
};
`,
);
const context = {
  console,
  Intl,
  window: { PolicyCoverageModel: model },
  CSS: { escape: (value) => String(value) },
};
vm.createContext(context);
vm.runInContext(testableAppSource, context, {
  filename: "app.js",
});

const formulaText =
  context.__legacyDeclaredRateTestHooks.coverageEntryText(
    entries["pre-annuity-death-reserve-return"],
    selection,
  );
assert.match(formulaText, /保單價值準備金 1,000,000 元/);
assert.match(formulaText, /保單借款及應付利息 125,000 元/);
assert.match(formulaText, /= 875,000 元/);

const scenarios = model.coverageEventScenarios(selection);
assert.ok(
  scenarios.some(
    (scenario) =>
      scenario.event_key === "annual-annuity" &&
      scenario.value === 60_000,
  ),
);
assert.ok(
  scenarios.some(
    (scenario) =>
      scenario.event_key === "pre-annuity-death" &&
      scenario.value === 875_000,
  ),
);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 15,
});

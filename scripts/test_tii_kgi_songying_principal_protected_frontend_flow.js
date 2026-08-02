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
      "work/tii-benefit-proposals/tii-life-028-songying-principal-protected-annuity-v216.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 7);
assert.equal(proposal.proposed_count, 7);

const schedules = Object.fromEntries(
  proposal.proposals.map((item) => [
    item.product_id,
    item.candidates[0].schedule,
  ]),
);
const firstVersion = {
  ...schedules["205411M11A02600"],
  face_amount: 100_000,
  plan_name: "monthly",
  policy_state: {
    single_premium_amount: 1_000_000,
    annuity_paid_total_amount: 24_594,
    policy_dividend_amount: 12_000,
  },
};
assert.equal(
  model.selectionRequirements(firstVersion).mode,
  "face_amount_plan",
);
assert.deepEqual(
  model.policyStateRequirements(firstVersion).fields.map(
    (field) => field.key,
  ),
  [
    "single_premium_amount",
    "annuity_paid_total_amount",
    "policy_dividend_amount",
  ],
);
assert.ok(
  !model
    .policyStateRequirements(firstVersion)
    .fields.some((field) => field.key === "unpaid_annuity_balance"),
  "the derived balance must not request a duplicate manual amount",
);

const firstEntries = Object.fromEntries(
  model.effectiveCoverageEntries(firstVersion).map((entry) => [
    entry.id,
    entry,
  ]),
);
assert.equal(
  model.coverageValue(
    firstEntries["annuity-payment"],
    firstVersion,
  ).value,
  8_198,
);
const firstBalance = model.coverageValue(
  firstEntries["unpaid-annuity-balance"],
  firstVersion,
);
assert.equal(firstBalance.state, "calculated_annuity_balance");
assert.equal(firstBalance.paid_annuity_total, 24_594);
assert.equal(firstBalance.value, 975_406);
assert.equal(
  model.coverageValue(
    firstEntries["policy-dividend"],
    firstVersion,
  ).value,
  12_000,
);

const laterVersion = {
  ...schedules["205411M11A02602"],
  face_amount: 100_000,
  plan_name: "semiannual",
  policy_state: {
    single_premium_amount: 1_000_000,
    annuity_paid_total_amount: 197_932,
    policy_dividend_amount: 0,
    successor_discounted_annuity_amount: 0,
  },
};
const laterEntries = Object.fromEntries(
  model.effectiveCoverageEntries(laterVersion).map((entry) => [
    entry.id,
    entry,
  ]),
);
assert.equal(
  model.coverageValue(
    laterEntries["annuity-payment"],
    laterVersion,
  ).value,
  49_483,
);
assert.equal(
  model.coverageValue(
    laterEntries["continuing-annuity-balance"],
    laterVersion,
  ).value,
  802_068,
);

const zeroReceived = {
  ...laterVersion,
  policy_state: {
    ...laterVersion.policy_state,
    annuity_paid_total_amount: 0,
  },
};
assert.equal(
  model.coverageValue(
    laterEntries["continuing-annuity-balance"],
    zeroReceived,
  ).value,
  1_000_000,
  "zero received payments should preserve the full guaranteed amount",
);

const appSource = fs.readFileSync(
  path.join(ROOT, "app.js"),
  "utf8",
);
const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__principalProtectedTestHooks = {
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
  context.__principalProtectedTestHooks.coverageEntryText(
    firstEntries["unpaid-annuity-balance"],
    firstVersion,
  );
assert.match(formulaText, /躉繳保險費 1,000,000 元/);
assert.match(formulaText, /累計實際已領年金 24,594 元/);
assert.match(formulaText, /= 975,406 元/);
assert.match(formulaText, /一次給付餘額/);

const continuingFormulaText =
  context.__principalProtectedTestHooks.coverageEntryText(
    laterEntries["continuing-annuity-balance"],
    laterVersion,
  );
assert.match(continuingFormulaText, /按原頻率續領的剩餘總額/);
assert.match(continuingFormulaText, /不是身故當下一次給付/);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

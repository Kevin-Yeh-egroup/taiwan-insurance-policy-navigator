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
      "work/tii-benefit-proposals/tii-life-028-songying-immediate-annuity-v208.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 7);

const schedule = proposal.proposals[0].candidates[0].schedule;
const level = {
  ...schedule,
  face_amount: 100_000,
  plan_name: "level-monthly-guarantee-10",
};
assert.equal(model.selectionRequirements(level).mode, "face_amount_plan");
assert.deepEqual(
  model.policyStateRequirements(level).fields.map((field) => field.key),
  ["unpaid_annuity_balance"],
);
const levelEntries = Object.fromEntries(
  model.effectiveCoverageEntries(level).map((entry) => [entry.id, entry]),
);
assert.equal(
  model.coverageValue(levelEntries["annuity-payment"], level).value,
  8_198,
);

const increasing = {
  ...schedule,
  face_amount: 100_000,
  plan_name: "increasing-annual-guarantee-10",
  policy_state: {
    annuity_payment_year: 12,
    unpaid_annuity_balance: 450_000,
  },
};
assert.deepEqual(
  model.policyStateRequirements(increasing).fields.map((field) => field.key),
  ["annuity_payment_year", "unpaid_annuity_balance"],
);
const increasingEntries = Object.fromEntries(
  model.effectiveCoverageEntries(increasing).map((entry) => [entry.id, entry]),
);
assert.equal(
  model.coverageValue(increasingEntries["annuity-payment"], increasing).value,
  130_000,
);
assert.equal(
  model.coverageValue(
    increasingEntries["unpaid-annuity-balance"],
    increasing,
  ).value,
  450_000,
);

const appSource = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");
const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__songyingTestHooks = {
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
vm.runInContext(testableAppSource, context, { filename: "app.js" });

const formulaText = context.__songyingTestHooks.coverageEntryText(
  increasingEntries["annuity-payment"],
  increasing,
);
assert.match(formulaText, /年金投保金額 100,000 元/);
assert.match(formulaText, /第 12 年/);
assert.match(formulaText, /3% 單利增額係數 1.3/);
assert.match(formulaText, /每期 130,000 元/);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 8,
});

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
      "work/tii-benefit-proposals/tii-life-050-fubon-nhsd-fixed-inpatient-v209.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 10);
assert.equal(proposal.proposed_count, 10);

const schedule = proposal.proposals[0].candidates[0].schedule;
const selected = {
  ...schedule,
  unit_count: 2,
  policy_state: {
    hospital_daily_amount: 1_200,
  },
};
assert.equal(model.selectionRequirements(selected).mode, "unit");
assert.deepEqual(
  model.policyStateRequirements(selected).fields.map((field) => field.key),
  ["hospital_daily_amount"],
);

const entries = Object.fromEntries(
  model.effectiveCoverageEntries(selected).map((entry) => [entry.id, entry]),
);
assert.equal(
  model.coverageValue(entries["hospital-daily-benefit"], selected).value,
  1_200,
);
assert.equal(
  model.coverageValue(
    entries["icu-or-burn-center-daily-benefit"],
    selected,
  ).value,
  1_500,
);
assert.equal(
  model.coverageValue(entries["inpatient-surgery-grade-1"], selected).value,
  700,
);
assert.equal(
  model.coverageValue(entries["inpatient-surgery-grade-8"], selected).value,
  15_000,
);
assert.equal(
  model.coverageValue(
    entries["inpatient-surgery-aggregate-cap"],
    selected,
  ).value,
  90_000,
);
assert.equal(
  model.coverageValue(
    entries["home-recovery-daily-benefit"],
    selected,
  ).value,
  300,
);
assert.equal(
  model.coverageValue(
    entries["long-hospital-daily-subsidy"],
    selected,
  ).value,
  300,
);
assert.equal(
  model.coverageValue(entries["hospital-daily-benefit"], {
    ...schedule,
    unit_count: 2,
  }).state,
  "needs_policy_state",
);

const appSource = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");
const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__fubonNhsdTestHooks = {
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

const dailyText = context.__fubonNhsdTestHooks.coverageEntryText(
  entries["hospital-daily-benefit"],
  selected,
);
assert.match(dailyText, /每日 1,200 元/);
const icuText = context.__fubonNhsdTestHooks.coverageEntryText(
  entries["icu-or-burn-center-daily-benefit"],
  selected,
);
assert.match(icuText, /1,200 元 × 1.25 = 1,500 元/);
const surgeryText = context.__fubonNhsdTestHooks.coverageEntryText(
  entries["inpatient-surgery-grade-8"],
  selected,
);
assert.match(surgeryText, /每單位 7,500 元 × 2 單位 = 15,000 元/);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 11,
});

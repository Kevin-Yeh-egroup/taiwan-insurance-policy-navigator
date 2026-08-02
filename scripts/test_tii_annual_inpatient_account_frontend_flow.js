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
      "work/tii-benefit-proposals/tii-life-013-annual-inpatient-claim-inputs-v219.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 4);
assert.equal(proposal.proposed_count, 4);

const schedule = proposal.proposals[0].candidates[0].schedule;
const selected = {
  ...schedule,
  unit_count: 2,
  policy_state: {
    hospitalization_days: 35,
    intensive_care_days: 3,
    cancer_hospitalization_days: 4,
    home_care_eligible_days: 5,
    surgery_benefit_rate_percent: 17.5,
    outpatient_visit_count: 4,
    inpatient_medical_expense_days: 10,
  },
};
assert.equal(model.selectionRequirements(selected).mode, "unit");
assert.deepEqual(
  new Set(
    model.policyStateRequirements(selected).fields.map((field) => field.key),
  ),
  new Set([
    "hospitalization_days",
    "intensive_care_days",
    "cancer_hospitalization_days",
    "home_care_eligible_days",
    "surgery_benefit_rate_percent",
    "outpatient_visit_count",
    "inpatient_medical_expense_days",
  ]),
);

const entries = Object.fromEntries(
  model.effectiveCoverageEntries(selected).map((entry) => [entry.id, entry]),
);
assert.equal(
  model.coverageValue(entries["hospital-daily-tiered"], selected).value,
  75_000,
);
assert.equal(
  model.coverageValue(entries["intensive-care-daily"], selected).value,
  6_000,
);
assert.equal(
  model.coverageValue(entries["cancer-hospital-daily"], selected).value,
  8_000,
);
assert.equal(
  model.coverageValue(entries["home-care-daily"], selected).value,
  5_000,
);
assert.equal(
  model.coverageValue(entries["inpatient-surgery-base"], selected).value,
  3_500,
);
assert.equal(
  model.coverageValue(entries["pre-post-outpatient-daily"], selected).value,
  2_000,
);
assert.equal(
  model.coverageValue(
    entries["inpatient-medical-expense-daily"],
    selected,
  ).value,
  4_000,
);

const appSource = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");
const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__annualInpatientTestHooks = {
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

assert.match(
  context.__annualInpatientTestHooks.coverageEntryText(
    entries["hospital-daily-tiered"],
    selected,
  ),
  /合計 75,000 元/,
);
assert.match(
  context.__annualInpatientTestHooks.coverageEntryText(
    entries["inpatient-surgery-base"],
    selected,
  ),
  /基準額 20,000 元 × 17.5% = 3,500 元/,
);
assert.match(
  context.__annualInpatientTestHooks.coverageEntryText(
    entries["intensive-care-daily"],
    selected,
  ),
  /2 單位 × 3 本次加護病房日數 = 6,000 元/,
);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 12,
});

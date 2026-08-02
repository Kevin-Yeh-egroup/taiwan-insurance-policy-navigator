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
      "work/tii-benefit-proposals/tii-life-050-fubon-cancer-claim-inputs-v220.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 17);
assert.equal(proposal.proposed_count, 17);

const schedule = proposal.proposals[0].candidates[0].schedule;
const selected = {
  ...schedule,
  unit_count: 2,
  policy_state: {
    policy_year: 21,
    cancer_benefit_category: "reduced_benefit_cancer",
    prior_cancer_diagnosis_benefit_paid_amount: 10_000,
    cancer_hospitalization_days: 95,
    cancer_surgery_count: 2,
    cancer_outpatient_treatment_days: 3,
    cancer_radiation_treatment_days: 4,
    cancer_chemotherapy_treatment_days: 5,
    cancer_hospice_anniversary_count: 3,
  },
};
assert.equal(model.selectionRequirements(selected).mode, "unit");
assert.deepEqual(
  new Set(
    model.policyStateRequirements(selected).fields.map((field) => field.key),
  ),
  new Set([
    "policy_year",
    "cancer_benefit_category",
    "prior_cancer_diagnosis_benefit_paid_amount",
    "cancer_hospitalization_days",
    "cancer_surgery_count",
    "cancer_outpatient_treatment_days",
    "cancer_radiation_treatment_days",
    "cancer_chemotherapy_treatment_days",
    "cancer_hospice_anniversary_count",
  ]),
);

const entries = Object.fromEntries(
  model.effectiveCoverageEntries(selected).map((entry) => [entry.id, entry]),
);
assert.equal(
  model.coverageValue(entries["cancer-diagnosis"], selected).value,
  12_500,
);
assert.equal(
  model.coverageValue(
    entries["cancer-hospital-daily-tiered"],
    selected,
  ).value,
  234_000,
);
assert.equal(
  model.coverageValue(entries["cancer-discharge-recovery"], selected).value,
  114_000,
);
assert.equal(
  model.coverageValue(entries["cancer-surgery"], selected).value,
  9_000,
);
assert.equal(
  model.coverageValue(entries["cancer-outpatient"], selected).value,
  3_000,
);
assert.equal(
  model.coverageValue(entries["cancer-radiation"], selected).value,
  4_000,
);
assert.equal(
  model.coverageValue(entries["cancer-chemotherapy"], selected).value,
  8_000,
);
assert.equal(
  model.coverageValue(
    entries["cancer-hospice-anniversary"],
    selected,
  ).state,
  "not_eligible",
);
assert.equal(
  model.coverageValue(entries["cancer-hospice-anniversary"], {
    ...selected,
    policy_state: {
      ...selected.policy_state,
      cancer_benefit_category: "full_benefit_cancer",
    },
  }).value,
  120_000,
);

const appSource = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");
const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__fubonCancerClaimTestHooks = {
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
  context.__fubonCancerClaimTestHooks.coverageEntryText(
    entries["cancer-diagnosis"],
    selected,
  ),
  /保單年度 21.*75,000 元 × 2 單位 × 15% - 本次事故前已領 10,000 元 = 12,500 元/,
);
assert.match(
  context.__fubonCancerClaimTestHooks.coverageEntryText(
    entries["cancer-hospital-daily-tiered"],
    selected,
  ),
  /合計 234,000 元/,
);
assert.match(
  context.__fubonCancerClaimTestHooks.coverageEntryText(
    entries["cancer-surgery"],
    selected,
  ),
  /2 單位 × 2 本次可計入癌症手術次數 × 15% = 9,000 元/,
);
assert.match(
  context.__fubonCancerClaimTestHooks.coverageEntryText(
    entries["cancer-hospice-anniversary"],
    selected,
  ),
  /不符合條款給付條件，保障試算為 0 元/,
);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 17,
});

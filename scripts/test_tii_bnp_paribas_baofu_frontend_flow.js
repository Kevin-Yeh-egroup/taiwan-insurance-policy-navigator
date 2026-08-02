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
      "work/tii-benefit-proposals/tii-life-173-bnp-baofu-variable-life-v207.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 12);

const candidate = proposal.proposals.find(
  (item) => item.product_id === "267191M32A00100",
).candidates[0];
const schedule = candidate.schedule;
const requirements = model.policyStateRequirements(schedule);
assert.deepEqual(
  requirements.fields.map((field) => field.key),
  [
    "maturity_policy_account_value",
    "policy_value_component",
    "general_death_disability_insurance_amount",
    "accidental_death_disability_insurance_amount",
    "policy_values_converted_to_twd",
  ],
);
assert.equal(model.selectionRequirements(schedule).mode, "policy_state");

const policyState = {
  maturity_policy_account_value: 600_000,
  policy_values_converted_to_twd: true,
  policy_value_component: 400_000,
  general_death_disability_insurance_amount: 1_000_000,
  accidental_death_disability_insurance_amount: 500_000,
};
const entries = Object.fromEntries(
  schedule.coverage_entries.map((entry) => [entry.id, entry]),
);
function value(entryId, state = policyState) {
  return model.coverageValue(entries[entryId], {
    ...schedule,
    policy_state: state,
  });
}

assert.equal(value("maturity-benefit").value, 600_000);
assert.equal(value("maturity-benefit").state, "conditional_amount");
assert.equal(value("general-death-benefit").value, 1_400_000);
assert.equal(value("general-death-benefit").state, "conditional_amount");
assert.equal(value("accidental-death-benefit").value, 1_900_000);
assert.equal(value("general-total-disability-benefit").value, 1_400_000);
assert.equal(value("accidental-total-disability-benefit").value, 1_900_000);

const missingAccidentAmount = value("accidental-death-benefit", {
  policy_value_component: 400_000,
  general_death_disability_insurance_amount: 1_000_000,
  policy_values_converted_to_twd: true,
});
assert.equal(missingAccidentAmount.value, null);
assert.equal(missingAccidentAmount.state, "needs_policy_state");
assert.deepEqual(missingAccidentAmount.required_fields, [
  "accidental_death_disability_insurance_amount",
]);
assert.equal(
  value("general-death-benefit", {
    policy_value_component: 400_000,
    general_death_disability_insurance_amount: 1_000_000,
    policy_values_converted_to_twd: true,
  }).value,
  1_400_000,
);

const unconfirmedCurrency = value("general-death-benefit", {
  policy_value_component: 400_000,
  general_death_disability_insurance_amount: 1_000_000,
});
assert.equal(unconfirmedCurrency.value, null);
assert.equal(unconfirmedCurrency.state, "needs_policy_state");
assert.deepEqual(unconfirmedCurrency.required_fields, [
  "policy_values_converted_to_twd",
]);

const appSource = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");
assert.match(
  appSource,
  /不可用目前帳戶價值推定/,
);
assert.match(
  appSource,
  /這是保障試算，不代表個案一定理賠/,
);
assert.match(
  appSource,
  /這是保障試算，不代表滿期時一定給付此金額/,
);

const testableAppSource = appSource.replace(
  /\nmain\(\);\s*$/,
  `
globalThis.__baofuTestHooks = {
  normalizePolicyStateForItem,
  policyStateWithFieldUpdate,
  syncPolicyStateConfirmationControl,
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

const controls = Object.fromEntries(
  requirements.fields.map((field) => [
    field.key,
    {
      checked: field.key === "policy_values_converted_to_twd",
      reportValidity() {},
      setCustomValidity() {},
      type: field.type === "boolean" ? "checkbox" : "number",
      value: String(policyState[field.key] ?? ""),
    },
  ]),
);
const detailContainer = {
  querySelector(selector) {
    const key = selector.match(/data-policy-state-key="([^"]+)"/)?.[1];
    return key ? controls[key] || null : null;
  },
};
const hooks = context.__baofuTestHooks;
const editedSchedule = {
  ...schedule,
  policy_state: hooks.policyStateWithFieldUpdate(
    { ...schedule, policy_state: policyState },
    "policy_value_component",
    "450000",
  ),
};
hooks.syncPolicyStateConfirmationControl(
  detailContainer,
  editedSchedule,
  "policy_value_component",
);
assert.equal(
  controls.policy_values_converted_to_twd.checked,
  false,
  "changing a dependent amount must visibly clear the TWD confirmation",
);
controls.policy_value_component.value = "450000";
const submittedState = hooks.normalizePolicyStateForItem(
  detailContainer,
  editedSchedule,
);
assert.equal(
  submittedState.policy_values_converted_to_twd,
  undefined,
  "submitting after an amount edit must omit the stale TWD confirmation",
);
assert.equal(submittedState.policy_value_component, 450_000);
const submittedCalculation = model.coverageValue(
  entries["general-death-benefit"],
  { ...schedule, policy_state: submittedState },
);
assert.equal(submittedCalculation.value, null);
assert.deepEqual(submittedCalculation.required_fields, [
  "policy_values_converted_to_twd",
]);

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  product_count: proposal.proposal_count,
  user_flow_cases: 19,
});

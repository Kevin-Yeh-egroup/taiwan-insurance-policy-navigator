const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

const commonDeathEntry = {
  id: "account-value-return-before-annuity-start-death",
  name: "年金開始前身故返還保單帳戶價值",
  basis: "policy_recorded_limit",
  calculation_basis: "policy_state_amount",
  amount_role: "payout",
  limit_scope: "per_policy",
  aggregation_rule: "choose_one",
  event_key: "death_before_annuity_start",
  unit_key: "benefit_valuation_policy_account_value",
  policy_state_keys: ["benefit_valuation_policy_account_value"],
  source: "terms",
};

const schedule = {
  selection_type: "plan",
  input_mode: "plan",
  selection_source: "terms",
  selection_label: "年金給付方式",
  plan_options: [
    {
      value: "一次給付",
      label: "一次給付",
      coverage_entries: [
        {
          id: "annuity-start-lump-sum",
          name: "年金開始日一次給付",
          basis: "policy_recorded_limit",
          calculation_basis: "policy_state_amount",
          amount_role: "payout",
          limit_scope: "per_policy",
          aggregation_rule: "choose_one",
          event_key: "annuity_start",
          unit_key: "annuity_start_policy_account_value",
          policy_state_keys: ["annuity_start_policy_account_value"],
          source: "terms",
        },
        commonDeathEntry,
      ],
    },
    {
      value: "分期給付",
      label: "分期給付",
      coverage_entries: [
        {
          id: "annual-annuity-or-low-amount-lump-sum",
          name: "分期年金給付（低額時改一次給付）",
          basis: "policy_recorded_limit",
          calculation_basis: "annuity_amount_or_lump_sum",
          amount_role: "payout",
          limit_scope: "per_policy",
          aggregation_rule: "choose_one",
          event_key: "annuity_start_or_annual_payment",
          unit_key: "annual_annuity_or_lump_sum",
          policy_state_keys: [
            "annuity_payment_amount",
            "annuity_start_policy_account_value",
          ],
          minimum_annual_annuity_amount: 10_000,
          maximum_annual_annuity_amount: 1_200_000,
          source: "terms",
        },
        {
          id: "excess-account-value-return-at-annuity-start",
          name: "年金開始時超額保單帳戶價值返還",
          basis: "policy_recorded_limit",
          calculation_basis: "policy_state_amount",
          amount_role: "payout",
          limit_scope: "per_policy",
          aggregation_rule: "conditional_additive",
          conditional_event_key:
            "annuity_start_excess_return",
          conditional_event_label: "年金開始時超額返還",
          applies_to_entry_ids: [
            "annual-annuity-or-low-amount-lump-sum",
          ],
          unit_key: "excess_annuity_reserve_return_amount",
          policy_state_keys: [
            "excess_annuity_reserve_return_amount",
          ],
          source: "terms",
        },
        commonDeathEntry,
        {
          id: "unpaid-annuity-balance-after-death",
          name: "年金開始後身故之未支領年金餘額",
          basis: "policy_recorded_limit",
          calculation_basis: "policy_state_amount",
          amount_role: "payout",
          limit_scope: "per_policy",
          aggregation_rule: "choose_one",
          event_key: "death_after_annuity_start",
          unit_key: "unpaid_annuity_balance",
          policy_state_keys: ["unpaid_annuity_balance"],
          source: "terms",
        },
      ],
    },
  ],
};

assert.deepEqual(
  model.selectionRequirements(schedule).fields,
  ["plan_name"],
);

const once = {
  ...schedule,
  plan_name: "一次給付",
  policy_state: {
    annuity_start_policy_account_value: 500_000,
    benefit_valuation_policy_account_value: 480_000,
  },
};
assert.deepEqual(
  model.effectiveCoverageEntries(once).map((entry) => entry.id),
  [
    "annuity-start-lump-sum",
    "account-value-return-before-annuity-start-death",
  ],
);
assert.equal(
  model.coverageValue(
    model.effectiveCoverageEntries(once)[0],
    once,
  ).value,
  500_000,
);

function installment(policyState) {
  return {
    ...schedule,
    plan_name: "分期給付",
    policy_state: policyState,
  };
}

const lowAmount = installment({
  annuity_payment_amount: 9_999,
  annuity_start_policy_account_value: 500_000,
});
const installmentEntry =
  model.effectiveCoverageEntries(lowAmount)[0];
const lowAmountResult = model.coverageValue(
  installmentEntry,
  lowAmount,
);
assert.equal(lowAmountResult.value, 500_000);
assert.equal(lowAmountResult.state, "account_value_return");
assert.equal(
  lowAmountResult.formula_type,
  "low_annual_annuity_lump_sum",
);

const thresholdAmount = installment({
  annuity_payment_amount: 10_000,
  annuity_start_policy_account_value: 500_000,
});
const thresholdResult = model.coverageValue(
  installmentEntry,
  thresholdAmount,
);
assert.equal(thresholdResult.value, 10_000);
assert.equal(thresholdResult.state, "policy_state_value");
assert.equal(
  thresholdResult.formula_type,
  "insurer_quoted_annual_annuity",
);

for (const policyState of [
  { annuity_payment_amount: 10_000 },
  { annuity_start_policy_account_value: 500_000 },
]) {
  const missingResult = model.coverageValue(
    installmentEntry,
    installment(policyState),
  );
  assert.equal(missingResult.state, "needs_policy_state");
}

const installmentEntries =
  model.effectiveCoverageEntries(thresholdAmount);
assert.equal(installmentEntries.length, 4);
const requiredFieldKeys = model
  .policyStateRequirements(thresholdAmount)
  .fields.map((field) => field.key);
assert(requiredFieldKeys.includes("annuity_payment_amount"));
assert(
  requiredFieldKeys.includes(
    "annuity_start_policy_account_value",
  ),
);
assert(
  requiredFieldKeys.includes(
    "excess_annuity_reserve_return_amount",
  ),
);
assert(requiredFieldKeys.includes("unpaid_annuity_balance"));

const excessEntry = installmentEntries.find(
  (entry) =>
    entry.id ===
    "excess-account-value-return-at-annuity-start",
);
const zeroExcessResult = model.coverageValue(
  excessEntry,
  installment({
    excess_annuity_reserve_return_amount: 0,
  }),
);
assert.equal(zeroExcessResult.value, 0);
assert.equal(zeroExcessResult.state, "policy_state_value");

const unpaidEntry = installmentEntries.find(
  (entry) => entry.id === "unpaid-annuity-balance-after-death",
);
const unpaidResult = model.coverageValue(
  unpaidEntry,
  installment({ unpaid_annuity_balance: 320_000 }),
);
assert.equal(unpaidResult.value, 320_000);

console.log({
  status: "ok",
  product_family: "hongtai-lehuo-variable-annuity",
  plan_count: 2,
  exact_threshold_tested: 10_000,
});

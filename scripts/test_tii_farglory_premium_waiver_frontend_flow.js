const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entry(id, overrides) {
  return {
    id,
    name: id,
    basis: "policy_recorded_limit",
    calculation_basis: "policy_state_amount",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    source: "terms",
    note: id,
    source_ref: "條款",
    ...overrides,
  };
}

const schedule = {
  selection_type: "policy_state",
  input_mode: "policy_state",
  selection_source: "terms",
  selection_label: "剩餘應繳保費與豁免狀態",
  version_characteristics: {
    product_family: "farglory-premium-waiver-rider",
  },
  coverage_entries: [
    entry("future-premium-waiver", {
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      unit_key: "remaining_premium_amount",
      policy_state_keys: ["remaining_premium_amount"],
      result_kind: "non_cash_effect",
      amount_stage: "non_cash_estimate",
    }),
    entry("current-unexpired-premium-refund", {
      unit_key: "unexpired_premium_refund_amount",
      policy_state_keys: ["unexpired_premium_refund_amount"],
    }),
    entry("overlapping-waiver-cash-settlement", {
      unit_key: "overlapping_waiver_settlement_amount",
      policy_state_keys: ["overlapping_waiver_settlement_amount"],
    }),
  ],
};

function value(entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find(
      (candidate) => candidate.id === entryId,
    ),
    {
      ...schedule,
      policy_state: policyState,
    },
  );
}

const policyState = {
  remaining_premium_amount: 240_000,
  unexpired_premium_refund_amount: 12_000,
  overlapping_waiver_settlement_amount: 180_000,
};

const waiver = value("future-premium-waiver", policyState);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 240_000);
assert.equal(waiver.reference_amount, 240_000);
assert.equal(waiver.policy_state_key, "remaining_premium_amount");

const refund = value(
  "current-unexpired-premium-refund",
  policyState,
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 12_000);

const settlement = value(
  "overlapping-waiver-cash-settlement",
  policyState,
);
assert.equal(settlement.state, "policy_state_value");
assert.equal(settlement.value, 180_000);

const missingWaiver = value("future-premium-waiver", {
  ...policyState,
  remaining_premium_amount: undefined,
});
assert.equal(missingWaiver.state, "needs_policy_state");
assert.deepEqual(missingWaiver.required_fields, [
  "remaining_premium_amount",
]);

const missingSettlement = value(
  "overlapping-waiver-cash-settlement",
  {
    ...policyState,
    overlapping_waiver_settlement_amount: undefined,
  },
);
assert.equal(missingSettlement.state, "needs_policy_state");
assert.deepEqual(missingSettlement.required_fields, [
  "overlapping_waiver_settlement_amount",
]);

const requirementKeys = model
  .policyStateRequirements(schedule)
  .fields.map((field) => field.key);
assert(requirementKeys.includes("remaining_premium_amount"));
assert(requirementKeys.includes("unexpired_premium_refund_amount"));
assert(
  requirementKeys.includes(
    "overlapping_waiver_settlement_amount",
  ),
);
assert.equal(
  model.POLICY_STATE_FIELDS
    .overlapping_waiver_settlement_amount.type,
  "non_negative_money",
);

console.log(
  "TII Farglory premium waiver frontend flow tests passed.",
);

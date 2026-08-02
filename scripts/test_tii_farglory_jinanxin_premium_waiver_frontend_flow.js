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
    source_ref: "條款第九條",
    ...overrides,
  };
}

const latestSchedule = {
  selection_type: "policy_state",
  input_mode: "policy_state",
  selection_source: "terms",
  selection_label: "剩餘應繳保費與豁免狀態",
  version_characteristics: {
    product_family: "farglory-jinanxin-premium-waiver-rider",
    terms_revision: "partial_change_15",
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
      limit_scope: "per_event",
      unit_key: "unexpired_premium_refund_amount",
      policy_state_keys: ["unexpired_premium_refund_amount"],
      result_kind: "cash_payout",
      amount_stage: "gross_contract_benefit",
    }),
    entry("overlapping-waiver-cash-settlement", {
      unit_key: "overlapping_waiver_settlement_amount",
      policy_state_keys: ["overlapping_waiver_settlement_amount"],
      result_kind: "cash_payout",
      amount_stage: "gross_contract_benefit",
    }),
  ],
};

function value(schedule, entryId, policyState) {
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
  remaining_premium_amount: 360_000,
  unexpired_premium_refund_amount: 15_000,
  overlapping_waiver_settlement_amount: 210_000,
};

const waiver = value(
  latestSchedule,
  "future-premium-waiver",
  policyState,
);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 360_000);
assert.equal(waiver.policy_state_key, "remaining_premium_amount");

const refund = value(
  latestSchedule,
  "current-unexpired-premium-refund",
  policyState,
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 15_000);

const settlement = value(
  latestSchedule,
  "overlapping-waiver-cash-settlement",
  policyState,
);
assert.equal(settlement.state, "policy_state_value");
assert.equal(settlement.value, 210_000);

const missingWaiver = value(
  latestSchedule,
  "future-premium-waiver",
  {
    ...policyState,
    remaining_premium_amount: undefined,
  },
);
assert.equal(missingWaiver.state, "needs_policy_state");
assert.deepEqual(missingWaiver.required_fields, [
  "remaining_premium_amount",
]);

const latestRequirementKeys = model
  .policyStateRequirements(latestSchedule)
  .fields.map((field) => field.key);
assert(latestRequirementKeys.includes("remaining_premium_amount"));
assert(
  latestRequirementKeys.includes(
    "unexpired_premium_refund_amount",
  ),
);
assert(
  latestRequirementKeys.includes(
    "overlapping_waiver_settlement_amount",
  ),
);

const legacySchedule = {
  ...latestSchedule,
  version_characteristics: {
    product_family: "farglory-jinanxin-premium-waiver-rider",
    terms_revision: "partial_change_14",
  },
  coverage_entries: [
    latestSchedule.coverage_entries[0],
  ],
};
assert.deepEqual(
  model
    .policyStateRequirements(legacySchedule)
    .fields.map((field) => field.key),
  ["remaining_premium_amount"],
);

console.log(
  "TII Farglory Jinanxin premium waiver frontend flow tests passed.",
);

const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entry(id, overrides) {
  return {
    id,
    name: id,
    basis: "face_amount",
    calculation_basis: "percentage_of_base",
    amount_role: "payout",
    limit_scope: "lifetime",
    aggregation_rule: "separate",
    source: "terms",
    note: id,
    source_ref: "條款",
    unit_key: "face_amount",
    ...overrides,
  };
}

const schedule = {
  selection_type: "face_amount",
  input_mode: "face_amount",
  selection_source: "terms",
  selection_label: "保險金額",
  face_amount: 1_000_000,
  version_characteristics: {
    product_family:
      "hongtai-wholeheart-cancer-whole-life-rider",
  },
  coverage_entries: [
    entry("initial-early-cancer-benefit", {
      rate_percent: 5,
    }),
    entry("initial-severe-cancer-benefit", {
      calculation_basis: "tiered_or_stepped",
      tier_selection_state_key: "policy_year",
      policy_state_keys: ["policy_year"],
      amount_tiers: [
        {
          label: "第 1 保單年度",
          multiplier: 0.10,
          min_quantity: 1,
          max_quantity: 1,
        },
        {
          label: "第 2 保單年度",
          multiplier: 0.20,
          min_quantity: 2,
          max_quantity: 2,
        },
        {
          label: "第 3 保單年度起",
          multiplier: 0.40,
          min_quantity: 3,
          max_quantity: null,
        },
      ],
    }),
    entry("cancer-living-support-anniversary-benefit", {
      calculation_basis: "table_multiplier",
      rate_percent: 12,
      multiplier: 1,
      quantity_state_key:
        "cancer_living_support_anniversary_count",
      quantity_cap: 5,
    }),
    entry("discounted-cancer-living-support-balance", {
      basis: "policy_recorded_limit",
      calculation_basis: "policy_state_amount",
      unit_key:
        "discounted_cancer_living_support_balance_amount",
      policy_state_keys: [
        "discounted_cancer_living_support_balance_amount",
      ],
    }),
    entry("future-premium-waiver", {
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      limit_scope: "per_policy",
      unit_key: "remaining_premium_amount",
      policy_state_keys: ["remaining_premium_amount"],
      result_kind: "non_cash_effect",
      amount_stage: "non_cash_estimate",
    }),
    entry("current-unexpired-premium-refund", {
      basis: "policy_recorded_limit",
      calculation_basis: "policy_state_amount",
      limit_scope: "per_event",
      unit_key: "unexpired_premium_refund_amount",
      policy_state_keys: ["unexpired_premium_refund_amount"],
    }),
  ],
};

function value(entryId, policyState = {}) {
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

assert.equal(value("initial-early-cancer-benefit").value, 50_000);

for (const [policyYear, expected] of [
  [1, 100_000],
  [2, 200_000],
  [3, 400_000],
  [20, 400_000],
]) {
  const severe = value("initial-severe-cancer-benefit", {
    policy_year: policyYear,
  });
  assert.equal(severe.value, expected);
  assert.equal(severe.reference_amount, 1_000_000);
  assert.equal(
    severe.multiplier,
    policyYear === 1 ? 0.10 : policyYear === 2 ? 0.20 : 0.40,
  );
}

const missingPolicyYear = value(
  "initial-severe-cancer-benefit",
);
assert.equal(missingPolicyYear.state, "needs_policy_state");
assert.deepEqual(missingPolicyYear.required_fields, [
  "policy_year",
]);

assert.equal(
  value("cancer-living-support-anniversary-benefit", {
    cancer_living_support_anniversary_count: 3,
  }).value,
  360_000,
);
assert.equal(
  value("cancer-living-support-anniversary-benefit", {
    cancer_living_support_anniversary_count: 5,
  }).value,
  600_000,
);
assert.equal(
  value("discounted-cancer-living-support-balance", {
    discounted_cancer_living_support_balance_amount: 420_000,
  }).value,
  420_000,
);

const waiver = value("future-premium-waiver", {
  remaining_premium_amount: 240_000,
});
assert.equal(waiver.value, 240_000);
assert.equal(waiver.result_kind, "non_cash_effect");
assert.equal(
  value("current-unexpired-premium-refund", {
    unexpired_premium_refund_amount: 12_000,
  }).value,
  12_000,
);

const requirementKeys = model
  .policyStateRequirements(schedule)
  .fields.map((field) => field.key);
for (const key of [
  "policy_year",
  "cancer_living_support_anniversary_count",
  "discounted_cancer_living_support_balance_amount",
  "remaining_premium_amount",
  "unexpired_premium_refund_amount",
]) {
  assert.equal(requirementKeys.includes(key), true, key);
}
assert.equal(
  model.POLICY_STATE_FIELDS.cancer_living_support_anniversary_count
    .max,
  5,
);
assert.equal(
  model.POLICY_STATE_FIELDS
    .discounted_cancer_living_support_balance_amount.type,
  "non_negative_money",
);

console.log(
  "TII Hongtai Wholeheart cancer whole-life rider frontend flow tests passed.",
);

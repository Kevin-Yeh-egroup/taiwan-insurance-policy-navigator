const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entry(id, overrides) {
  return {
    id,
    name: id,
    basis: "face_amount",
    calculation_basis: "table_multiplier",
    amount_role: "payout",
    limit_scope: "per_event",
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
  selection_label: "住院醫療保險金日額",
  version_characteristics: {
    source_product_id: "209311R12B00113",
    product_family: "fubon-whole-life-medical-health-rider",
    family_fingerprint: "e8f04c6086eb051a16ce4cf5",
  },
  coverage_entries: [
    entry("remaining-lifetime-benefit-cap", {
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      multiplier: 1000,
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
    }),
    entry("hospital-daily-tiered-benefit", {
      calculation_basis: "tiered_or_stepped",
      limit_scope: "per_hospitalization",
      quantity_state_key: "hospitalization_days",
      quantity_cap: 365,
      amount_tiers: [
        {
          label: "第 1 至 30 日",
          multiplier: 1,
          min_quantity: 1,
          max_quantity: 30,
        },
        {
          label: "第 31 至 365 日",
          multiplier: 2,
          min_quantity: 31,
          max_quantity: 365,
        },
      ],
    }),
    entry("inpatient-surgery-benefit", {
      multiplier: 30,
      rate_state_key: "surgery_total_benefit_rate_percent",
      rate_min_percent: 10,
      rate_max_percent: 500,
    }),
    entry("death-or-funeral-benefit", {
      calculation_basis:
        "death_or_funeral_multiplier_of_face_amount",
      multiplier: 1000,
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
      policy_state_keys: [
        "cumulative_medical_benefit_paid_amount",
        "death_benefit_status",
        "remaining_funeral_benefit_limit",
      ],
    }),
  ],
};

function value(entryId, policyState, faceAmount = 1_000) {
  return model.coverageValue(
    schedule.coverage_entries.find(
      (candidate) => candidate.id === entryId,
    ),
    {
      ...schedule,
      face_amount: faceAmount,
      policy_state: policyState,
    },
  );
}

const state = {
  hospitalization_days: 45,
  surgery_total_benefit_rate_percent: 165,
  cumulative_medical_benefit_paid_amount: 250_000,
  death_benefit_status: "standard_death",
};

assert.equal(
  value("hospital-daily-tiered-benefit", state).value,
  60_000,
);

const surgery = value("inpatient-surgery-benefit", state);
assert.equal(surgery.value, 49_500);
assert.equal(surgery.applied_multiplier, 30);
assert.equal(surgery.applied_rate, 1.65);

const missingRate = value("inpatient-surgery-benefit", {
  ...state,
  surgery_total_benefit_rate_percent: undefined,
});
assert.equal(missingRate.state, "needs_policy_state");
assert.deepEqual(missingRate.required_fields, [
  "surgery_total_benefit_rate_percent",
]);

assert.equal(
  value("remaining-lifetime-benefit-cap", state).value,
  750_000,
);
assert.equal(
  value("death-or-funeral-benefit", state).value,
  750_000,
);
assert.equal(
  value("death-or-funeral-benefit", {
    ...state,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 300_000,
  }).value,
  300_000,
);

const requiredKeys = model
  .policyStateRequirements({
    ...schedule,
    face_amount: 1_000,
    policy_state: {},
  })
  .fields.map((field) => field.key);
for (const key of [
  "hospitalization_days",
  "surgery_total_benefit_rate_percent",
  "cumulative_medical_benefit_paid_amount",
  "death_benefit_status",
]) {
  assert(requiredKeys.includes(key), key);
}

console.log(
  "TII Fubon whole-life medical health rider frontend flow tests passed.",
);

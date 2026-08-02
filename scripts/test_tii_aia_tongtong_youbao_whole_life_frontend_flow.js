const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entry(id, overrides) {
  return {
    id,
    name: id,
    basis: "per_unit",
    calculation_basis: "per_unit",
    amount_role: "payout",
    limit_scope: "per_event",
    aggregation_rule: "separate",
    source: "terms",
    note: id,
    source_ref: "條款",
    result_kind: "cash_payout",
    amount_stage: "gross_contract_benefit",
    ...overrides,
  };
}

const capState = "aia_tongtong_prior_cap_benefit_paid_amount";
const schedule = {
  selection_type: "unit",
  input_mode: "unit",
  selection_source: "terms",
  selection_label: "投保單位數",
  unit_count: 3,
  version_characteristics: {
    product_family: "aia-tongtong-youbao-whole-life",
  },
  coverage_entries: [
    entry("hospital-medical-benefit", {
      amount: 1_000,
      quantity_state_key: "hospitalization_days",
      quantity_cap: 90,
      cumulative_paid_state_key: capState,
      aggregate_limit_entry_id: "remaining-total-benefit-cap",
    }),
    entry("surgery-medical-benefit", {
      amount: 1_000,
      calculation_basis: "table_multiplier",
      multiplier_state_key: "surgery_benefit_multiplier_decimal",
      cumulative_paid_state_key: capState,
      aggregate_limit_entry_id: "remaining-total-benefit-cap",
    }),
    entry("disease-death-benefit", {
      amount: 10_000,
      calculation_basis:
        "death_or_funeral_greater_of_per_unit_floor_and_paid_premium_net",
      policy_state_keys: ["paid_premium_total", capState],
    }),
    entry("accident-disability-benefit", {
      amount: 1_000_000,
      calculation_basis: "percentage_of_base",
      rate_state_key: "disability_benefit_rate_percent",
    }),
    entry("remaining-total-benefit-cap", {
      amount: 1_000_000,
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      cumulative_paid_state_key: capState,
    }),
  ],
};

function value(entryId, policyState = {}) {
  return model.coverageValue(
    schedule.coverage_entries.find((item) => item.id === entryId),
    { ...schedule, policy_state: policyState },
  );
}

assert.equal(
  value("hospital-medical-benefit", {
    hospitalization_days: 12,
    [capState]: 0,
  }).value,
  36_000,
);
assert.equal(
  value("hospital-medical-benefit", {
    hospitalization_days: 120,
    [capState]: 0,
  }).value,
  270_000,
);
assert.equal(
  value("surgery-medical-benefit", {
    surgery_benefit_multiplier_decimal: 0.25,
    [capState]: 0,
  }).value,
  750,
);
assert.equal(
  value("accident-disability-benefit", {
    disability_benefit_rate_percent: 35,
  }).value,
  1_050_000,
);

const death = value("disease-death-benefit", {
  paid_premium_total: 620_000,
  [capState]: 120_000,
  death_benefit_status: "standard_death",
});
assert.equal(death.value, 500_000);
assert.equal(death.unit_floor_amount, 30_000);
assert.equal(death.paid_premium_net_amount, 500_000);

const funeral = value("disease-death-benefit", {
  paid_premium_total: 620_000,
  [capState]: 120_000,
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 180_000,
});
assert.equal(funeral.value, 180_000);

const requirements = model
  .policyStateRequirements(schedule)
  .fields.map((field) => field.key);
for (const key of [
  "hospitalization_days",
  "surgery_benefit_multiplier_decimal",
  capState,
  "paid_premium_total",
  "death_benefit_status",
  "disability_benefit_rate_percent",
]) {
  assert.equal(requirements.includes(key), true, key);
}
assert.equal(
  model
    .policyStateRequirements({
      ...schedule,
      policy_state: {
        death_benefit_status: "funeral_limited",
      },
    })
    .fields.some(
      (field) => field.key === "remaining_funeral_benefit_limit",
    ),
  true,
);
assert.equal(
  model.POLICY_STATE_FIELDS.surgery_benefit_multiplier_decimal.type,
  "number",
);

console.log("TII AIA Tongtong Youbao frontend flow tests passed.");

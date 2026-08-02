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
  selection_label: "單位日額",
  face_amount_label: "單位日額",
  version_characteristics: {
    product_family: "nanshan-new-whole-life-medical",
  },
  coverage_entries: [
    entry("remaining-lifetime-benefit-cap", {
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      multiplier: 3000,
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
          label: "第 31 至 90 日",
          multiplier: 2,
          min_quantity: 31,
          max_quantity: 90,
        },
        {
          label: "第 91 至 365 日",
          multiplier: 3,
          min_quantity: 91,
          max_quantity: 365,
        },
      ],
    }),
    entry("icu-burn-center-daily-benefit", {
      multiplier: 2,
      quantity_state_key: "intensive_care_or_burn_unit_days",
      quantity_cap: 365,
    }),
    entry("pre-post-hospital-outpatient-benefit", {
      multiplier: 0.25,
      quantity_state_key: "outpatient_visit_count",
    }),
    entry("discharge-recuperation-benefit", {
      multiplier: 0.5,
      quantity_state_key: "hospitalization_days",
      quantity_cap: 365,
    }),
    entry("inpatient-surgery-benefit", {
      multiplier: 3,
      quantity_state_key: "inpatient_surgery_count",
    }),
    entry("health-increment-benefit", {
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_base",
      unit_key: "current_eligible_hospital_benefit_total_amount",
      rate_state_key: "health_increment_rate_percent",
      policy_state_keys: [
        "current_eligible_hospital_benefit_total_amount",
        "health_increment_rate_percent",
      ],
    }),
    entry("future-premium-waiver", {
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      unit_key: "remaining_premium_amount",
      policy_state_keys: [
        "remaining_premium_amount",
        "premium_payment_period_status",
      ],
      exclusion_state_key: "premium_payment_period_status",
      exclusion_values: ["payment_period_ended", "reduced_paid_up"],
    }),
    entry("maturity-benefit", {
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_base",
      rate_percent: 105,
      unit_key: "paid_premium_total",
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
      policy_state_keys: [
        "paid_premium_total",
        "cumulative_medical_benefit_paid_amount",
      ],
    }),
    entry("death-or-funeral-benefit", {
      basis: "policy_recorded_limit",
      calculation_basis:
        "death_or_funeral_percentage_of_policy_state_amount",
      rate_percent: 105,
      unit_key: "paid_premium_total",
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
      policy_state_keys: [
        "paid_premium_total",
        "cumulative_medical_benefit_paid_amount",
        "death_benefit_status",
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
  hospitalization_days: 100,
  intensive_care_or_burn_unit_days: 5,
  outpatient_visit_count: 8,
  inpatient_surgery_count: 2,
  current_eligible_hospital_benefit_total_amount: 50_000,
  health_increment_rate_percent: "40",
  cumulative_medical_benefit_paid_amount: 250_000,
  remaining_premium_amount: 360_000,
  premium_payment_period_status: "within_payment_period",
  paid_premium_total: 400_000,
  death_benefit_status: "standard_death",
};

assert.equal(
  value("hospital-daily-tiered-benefit", state).value,
  180_000,
);
assert.equal(
  value("icu-burn-center-daily-benefit", state).value,
  10_000,
);
assert.equal(
  value("pre-post-hospital-outpatient-benefit", state).value,
  2_000,
);
assert.equal(
  value("discharge-recuperation-benefit", state).value,
  50_000,
);
assert.equal(
  value("inpatient-surgery-benefit", state).value,
  6_000,
);

const increment = value("health-increment-benefit", state);
assert.equal(increment.value, 20_000);
assert.equal(increment.applied_rate, 0.4);

const noIncrement = value("health-increment-benefit", {
  ...state,
  health_increment_rate_percent: "0",
});
assert.equal(noIncrement.value, 0);
assert.equal(noIncrement.state, "not_eligible");

const remainingCap = value(
  "remaining-lifetime-benefit-cap",
  state,
);
assert.equal(remainingCap.value, 2_750_000);
assert.equal(remainingCap.multiplier, 3000);
assert.equal(
  remainingCap.cumulative_paid_amount,
  250_000,
);

const waiver = value("future-premium-waiver", state);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 360_000);
assert.equal(waiver.result_kind, "non_cash_effect");

const maturity = value("maturity-benefit", state);
assert.equal(maturity.value, 170_000);
assert.equal(maturity.gross_value, 420_000);

const death = value("death-or-funeral-benefit", state);
assert.equal(death.value, 170_000);
assert.equal(death.state, "death_or_funeral_amount");

const missingIncrementRate = value("health-increment-benefit", {
  ...state,
  health_increment_rate_percent: undefined,
});
assert.equal(missingIncrementRate.state, "needs_policy_state");
assert.deepEqual(missingIncrementRate.required_fields, [
  "health_increment_rate_percent",
]);

const requirementKeys = model
  .policyStateRequirements({
    ...schedule,
    face_amount: 1_000,
    policy_state: state,
  })
  .fields.map((field) => field.key);
for (const key of [
  "hospitalization_days",
  "intensive_care_or_burn_unit_days",
  "outpatient_visit_count",
  "inpatient_surgery_count",
  "current_eligible_hospital_benefit_total_amount",
  "health_increment_rate_percent",
  "cumulative_medical_benefit_paid_amount",
]) {
  assert(requirementKeys.includes(key), key);
}

console.log(
  "TII Nanshan new whole-life medical frontend flow tests passed.",
);

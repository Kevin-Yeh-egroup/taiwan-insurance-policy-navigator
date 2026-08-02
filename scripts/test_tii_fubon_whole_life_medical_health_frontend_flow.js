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
    product_family: "fubon-whole-life-medical-health",
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
    entry("intensive-care-additional-benefit", {
      multiplier: 2,
      quantity_state_key: "intensive_care_days",
      quantity_cap: 365,
    }),
    entry("burn-center-additional-benefit", {
      multiplier: 3,
      quantity_state_key: "burn_unit_days",
      quantity_cap: 365,
    }),
    entry("discharge-recuperation-benefit", {
      multiplier: 0.5,
      quantity_state_key: "hospitalization_days",
      quantity_cap: 365,
    }),
    entry("pre-post-hospital-outpatient-benefit", {
      multiplier: 0.25,
      quantity_state_key: "outpatient_visit_count",
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
  intensive_care_days: 5,
  burn_unit_days: 3,
  outpatient_visit_count: 8,
  surgery_total_benefit_rate_percent: 165,
  cumulative_medical_benefit_paid_amount: 250_000,
  death_benefit_status: "standard_death",
};

assert.equal(
  value("hospital-daily-tiered-benefit", state).value,
  60_000,
);
assert.equal(
  value("intensive-care-additional-benefit", state).value,
  10_000,
);
assert.equal(
  value("burn-center-additional-benefit", state).value,
  9_000,
);
assert.equal(
  value("discharge-recuperation-benefit", state).value,
  22_500,
);
assert.equal(
  value("pre-post-hospital-outpatient-benefit", state).value,
  2_000,
);

const surgery = value("inpatient-surgery-benefit", state);
assert.equal(surgery.value, 49_500);
assert.equal(surgery.applied_multiplier, 30);
assert.equal(surgery.applied_rate, 1.65);

const missingSurgeryRate = value(
  "inpatient-surgery-benefit",
  {
    ...state,
    surgery_total_benefit_rate_percent: undefined,
  },
);
assert.equal(missingSurgeryRate.state, "needs_policy_state");
assert.deepEqual(missingSurgeryRate.required_fields, [
  "surgery_total_benefit_rate_percent",
]);

const excessiveSurgeryRate = value(
  "inpatient-surgery-benefit",
  {
    ...state,
    surgery_total_benefit_rate_percent: 550,
  },
);
assert.equal(excessiveSurgeryRate.state, "needs_policy_state");
assert.deepEqual(excessiveSurgeryRate.required_fields, [
  "surgery_total_benefit_rate_percent",
]);

const remainingCap = value(
  "remaining-lifetime-benefit-cap",
  state,
);
assert.equal(remainingCap.value, 750_000);

const death = value("death-or-funeral-benefit", state);
assert.equal(death.value, 750_000);
assert.equal(death.state, "death_or_funeral_amount");
assert.equal(death.applied_multiplier, 1000);

const funeral = value("death-or-funeral-benefit", {
  ...state,
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 300_000,
});
assert.equal(funeral.value, 300_000);
assert.equal(
  funeral.formula_type,
  "face_amount_multiplier_funeral_cap",
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
  "intensive_care_days",
  "burn_unit_days",
  "outpatient_visit_count",
  "surgery_total_benefit_rate_percent",
  "cumulative_medical_benefit_paid_amount",
  "death_benefit_status",
]) {
  assert(requiredKeys.includes(key), key);
}

const funeralRequiredKeys = model
  .policyStateRequirements({
    ...schedule,
    face_amount: 1_000,
    policy_state: {
      death_benefit_status: "funeral_limited",
    },
  })
  .fields.map((field) => field.key);
assert(
  funeralRequiredKeys.includes(
    "remaining_funeral_benefit_limit",
  ),
);

console.log(
  "TII Fubon whole-life medical health frontend flow tests passed.",
);

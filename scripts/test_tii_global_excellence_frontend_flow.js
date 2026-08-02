const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor({
  formulaVariant,
  minimumFormulaAge,
  thresholdSchedule,
}) {
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: "基本保額",
    plan_options: [
      { value: "A型", label: "A型" },
      { value: "B型", label: "B型" },
    ],
    version_characteristics: {
      product_family:
        "global-excellence-variable-universal-life",
      minimum_rate_formula_variant: formulaVariant,
      minimum_benefit_formula_age: minimumFormulaAge,
      threshold_factor_schedule: thresholdSchedule,
    },
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: "九五祝壽金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
      },
      {
        id: "death-benefit",
        name: "身故保險金",
        basis: "policy_recorded_limit",
        calculation_basis:
          "net_amount_at_risk_plus_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key:
          "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
        policy_state_keys: [
          "benefit_valuation_policy_account_value",
        ],
      },
      {
        id: "total-disability-benefit",
        name: "全殘廢保險金",
        basis: "policy_recorded_limit",
        calculation_basis:
          "net_amount_at_risk_plus_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key:
          "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
        policy_state_keys: [
          "benefit_valuation_policy_account_value",
        ],
      },
    ],
  };
}

function valueFor(schedule, entryId, selection) {
  const entry = schedule.coverage_entries.find(
    (candidate) => candidate.id === entryId,
  );
  return model.coverageValue(entry, {
    ...schedule,
    ...selection,
  });
}

const fixedSchedule = scheduleFor({
  formulaVariant: "fixed_110_percent",
  minimumFormulaAge: 0,
  thresholdSchedule: [],
});
const fixedA = valueFor(fixedSchedule, "death-benefit", {
  face_amount: 1_000_000,
  plan_name: "A型",
  policy_state: {
    benefit_valuation_policy_account_value: 1_200_000,
  },
});
assert.equal(fixedA.state, "calculated");
assert.equal(fixedA.value, 1_320_000);
assert.equal(fixedA.net_amount_at_risk, 120_000);
assert.equal(fixedA.threshold_factor, 1.1);

const fixedB = valueFor(
  fixedSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: {
      benefit_valuation_policy_account_value: 800_000,
    },
  },
);
assert.equal(fixedB.state, "calculated");
assert.equal(fixedB.value, 1_800_000);
assert.equal(fixedB.net_amount_at_risk, 1_000_000);
assert.equal(
  model
    .policyStateRequirements({
      ...fixedSchedule,
      face_amount: 1_000_000,
      plan_name: "A型",
    })
    .fields.some((field) => field.key === "insured_age_at_event"),
  false,
);

const ageSchedule = scheduleFor({
  formulaVariant: "age_bands_130_115_101",
  minimumFormulaAge: 0,
  thresholdSchedule: [
    { min_age: 0, max_age: 40, factor: 1.3 },
    { min_age: 41, max_age: 70, factor: 1.15 },
    { min_age: 71, max_age: 130, factor: 1.01 },
  ],
});
for (const [age, planName, faceAmount, expected] of [
  [40, "A型", 1_000_000, 1_300_000],
  [41, "A型", 1_000_000, 1_150_000],
  [70, "B型", 100_000, 1_150_000],
  [71, "B型", 100_000, 1_100_000],
]) {
  const result = valueFor(ageSchedule, "death-benefit", {
    face_amount: faceAmount,
    plan_name: planName,
    policy_state: {
      insured_age_at_event: age,
      benefit_valuation_policy_account_value: 1_000_000,
    },
  });
  assert.equal(result.state, "calculated");
  assert.equal(result.value, expected);
}
assert.equal(
  model
    .policyStateRequirements({
      ...ageSchedule,
      face_amount: 1_000_000,
      plan_name: "A型",
    })
    .fields.some((field) => field.key === "insured_age_at_event"),
  true,
);

const ageFloorSchedule = scheduleFor({
  formulaVariant: "age_bands_15_floor_130_115_101",
  minimumFormulaAge: 15,
  thresholdSchedule: [
    { min_age: 15, max_age: 40, factor: 1.3 },
    { min_age: 41, max_age: 70, factor: 1.15 },
    { min_age: 71, max_age: 130, factor: 1.01 },
  ],
});
const under15 = valueFor(ageFloorSchedule, "death-benefit", {
  face_amount: 1_000_000,
  plan_name: "A型",
  policy_state: {
    insured_age_at_event: 14,
    benefit_valuation_policy_account_value: 600_000,
  },
});
assert.equal(under15.state, "outside_terms_formula_age_range");
assert.equal(under15.minimum_formula_age, 15);
assert.equal(under15.insured_age_at_event, 14);
assert.equal(under15.value, null);

const missingAge = valueFor(ageFloorSchedule, "death-benefit", {
  face_amount: 1_000_000,
  plan_name: "A型",
  policy_state: {
    benefit_valuation_policy_account_value: 600_000,
  },
});
assert.equal(missingAge.state, "needs_policy_state");
assert.deepEqual(missingAge.required_fields, [
  "insured_age_at_event",
]);

const missingAccount = valueFor(
  ageFloorSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: { insured_age_at_event: 35 },
  },
);
assert.equal(missingAccount.state, "needs_account_value");
assert.deepEqual(missingAccount.required_fields, [
  "benefit_valuation_policy_account_value",
]);

const maturity = valueFor(ageFloorSchedule, "maturity-benefit", {
  policy_state: {
    maturity_policy_account_value: 925_000,
    policy_values_converted_to_twd: true,
  },
});
assert.equal(maturity.value, 925_000);
assert.equal(maturity.state, "conditional_amount");

console.log({
  status: "ok",
  batch_id: "tii-life-167",
  user_flow_cases: 13,
  exact_formula_groups: 3,
});

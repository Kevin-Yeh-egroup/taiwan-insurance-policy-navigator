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
    product_family:
      "hongtai-xianghaokang-whole-life-medical",
  },
  coverage_entries: [
    entry("hospital-daily-benefit", {
      limit_scope: "per_hospitalization",
      multiplier: 1,
      quantity_state_key: "hospitalization_days",
    }),
    entry("outpatient-surgery-benefit", {
      limit_scope: "per_surgery",
      multiplier: 3,
    }),
    entry("inpatient-surgery-benefit", {
      limit_scope: "per_surgery",
      multiplier: 10,
    }),
    entry("major-surgery-benefit", {
      limit_scope: "per_surgery",
      aggregation_rule: "conditional_additive",
      applies_to_entry_ids: ["inpatient-surgery-benefit"],
      multiplier: 40,
    }),
    entry("trauma-treatment-benefit", {
      calculation_basis: "percentage_of_base",
      limit_scope: "per_day",
      aggregation_rule: "highest",
      rate_percent: 50,
    }),
    entry("remaining-lifetime-medical-benefit-cap", {
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      multiplier: 1500,
      cumulative_paid_multiplier_state_key:
        "cumulative_medical_benefit_paid_multiplier",
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
  hospitalization_days: 12,
  cumulative_medical_benefit_paid_multiplier: 200.5,
};

const hospitalization = value("hospital-daily-benefit", state);
assert.equal(hospitalization.value, 12_000);
assert.equal(hospitalization.quantity, 12);
assert.equal(hospitalization.applied_multiplier, 1);
assert.equal(
  value("outpatient-surgery-benefit", state).value,
  3_000,
);
assert.equal(
  value("inpatient-surgery-benefit", state).value,
  10_000,
);
assert.equal(
  value("major-surgery-benefit", state).value,
  40_000,
);
assert.equal(
  value("trauma-treatment-benefit", state).value,
  500,
);

const remainingCap = value(
  "remaining-lifetime-medical-benefit-cap",
  state,
);
assert.equal(remainingCap.value, 1_299_500);
assert.equal(remainingCap.multiplier, 1500);
assert.equal(remainingCap.applied_multiplier, 1299.5);
assert.equal(remainingCap.cumulative_paid_multiplier, 200.5);

const fullCap = value(
  "remaining-lifetime-medical-benefit-cap",
  {
    ...state,
    cumulative_medical_benefit_paid_multiplier: 0,
  },
);
assert.equal(fullCap.value, 1_500_000);

const exhaustedCap = value(
  "remaining-lifetime-medical-benefit-cap",
  {
    ...state,
    cumulative_medical_benefit_paid_multiplier: 1500,
  },
);
assert.equal(exhaustedCap.value, 0);

const missingDays = value("hospital-daily-benefit", {
  cumulative_medical_benefit_paid_multiplier: 0,
});
assert.equal(missingDays.state, "needs_policy_state");
assert.deepEqual(missingDays.required_fields, [
  "hospitalization_days",
]);

const missingPaidMultiplier = value(
  "remaining-lifetime-medical-benefit-cap",
  { hospitalization_days: 12 },
);
assert.equal(missingPaidMultiplier.state, "needs_policy_state");
assert.deepEqual(missingPaidMultiplier.required_fields, [
  "cumulative_medical_benefit_paid_multiplier",
]);

console.log(
  "TII Hongtai Xianghaokang whole-life medical frontend flow tests passed.",
);

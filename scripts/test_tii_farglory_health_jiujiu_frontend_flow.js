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
  selection_type: "face_amount",
  input_mode: "face_amount",
  selection_source: "terms",
  selection_label: "手術醫療保險金額",
  version_characteristics: {
    product_family:
      "farglory-health-jiujiu-surgical-medical",
  },
  coverage_entries: [
    entry("inpatient-surgery-benefit", {
      basis: "face_amount",
      calculation_basis: "table_multiplier",
      amount_role: "payout",
      limit_scope: "per_surgery",
      aggregation_rule: "highest",
      multiplier_state_key: "surgery_benefit_multiplier",
      unit_key: "face_amount",
    }),
    entry("surgery-benefit-lifetime-cap", {
      basis: "face_amount",
      calculation_basis: "table_multiplier",
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      multiplier: 1200,
      unit_key: "face_amount",
    }),
    entry("maturity-benefit", {
      calculation_basis: "percentage_of_base",
      rate_percent: 110,
      unit_key: "premium_total_amount",
      cumulative_paid_state_key:
        "cumulative_surgery_benefit_paid_amount",
      policy_state_keys: ["premium_total_amount"],
    }),
    entry("death-or-funeral-benefit", {
      calculation_basis:
        "death_or_funeral_percentage_of_policy_state_amount",
      rate_percent: 110,
      unit_key: "premium_total_amount",
      cumulative_paid_state_key:
        "cumulative_surgery_benefit_paid_amount",
      policy_state_keys: [
        "premium_total_amount",
        "death_benefit_status",
      ],
      exclusion_state_key: "death_age_band_status",
      exclusion_values: [
        "under_15_refund",
        "age_15_before_age_16_anniversary",
      ],
    }),
    entry("minor-paid-premium-refund-or-death-benefit", {
      calculation_basis: "policy_state_amount",
      unit_key: "premium_total_amount",
      policy_state_keys: ["premium_total_amount"],
      exclusion_state_key: "death_age_band_status",
      exclusion_values: ["standard"],
    }),
  ],
};

function value(entryId, policyState, faceAmount = 10_000) {
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

const commonState = {
  surgery_benefit_multiplier: 8,
  premium_total_amount: 500_000,
  cumulative_surgery_benefit_paid_amount: 50_000,
  death_benefit_status: "standard_death",
  death_age_band_status: "standard",
};

const surgery = value(
  "inpatient-surgery-benefit",
  commonState,
);
assert.equal(surgery.state, "policy_state_multiplier");
assert.equal(surgery.value, 80_000);
assert.equal(surgery.multiplier, 8);
assert.equal(
  surgery.multiplier_state_key,
  "surgery_benefit_multiplier",
);

const lifetimeCap = value(
  "surgery-benefit-lifetime-cap",
  commonState,
);
assert.equal(lifetimeCap.value, 12_000_000);
assert.equal(lifetimeCap.multiplier, 1200);

const maturity = value("maturity-benefit", commonState);
assert.equal(maturity.state, "policy_state_percentage");
assert.equal(maturity.reference_amount, 500_000);
assert.equal(maturity.gross_value, 550_000);
assert.equal(maturity.cumulative_paid_amount, 50_000);
assert.equal(maturity.value, 500_000);

const death = value("death-or-funeral-benefit", commonState);
assert.equal(death.state, "death_or_funeral_amount");
assert.equal(
  death.formula_type,
  "policy_state_percentage_standard_death",
);
assert.equal(death.value, 500_000);

const funeral = value("death-or-funeral-benefit", {
  ...commonState,
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 120_000,
});
assert.equal(
  funeral.formula_type,
  "policy_state_percentage_funeral_cap",
);
assert.equal(funeral.protected_amount, 500_000);
assert.equal(funeral.value, 120_000);

const minorStandard = value(
  "minor-paid-premium-refund-or-death-benefit",
  commonState,
);
assert.equal(minorStandard.state, "not_eligible");
assert.equal(minorStandard.value, 0);

const minorRefund = value(
  "minor-paid-premium-refund-or-death-benefit",
  {
    ...commonState,
    death_age_band_status: "under_15_refund",
  },
);
assert.equal(minorRefund.state, "policy_state_value");
assert.equal(minorRefund.value, 500_000);

const excludedStandardDeath = value(
  "death-or-funeral-benefit",
  {
    ...commonState,
    death_age_band_status:
      "age_15_before_age_16_anniversary",
  },
);
assert.equal(excludedStandardDeath.state, "not_eligible");
assert.equal(excludedStandardDeath.value, 0);

const missingMultiplier = value(
  "inpatient-surgery-benefit",
  {
    ...commonState,
    surgery_benefit_multiplier: undefined,
  },
);
assert.equal(missingMultiplier.state, "needs_policy_state");
assert.deepEqual(missingMultiplier.required_fields, [
  "surgery_benefit_multiplier",
]);

console.log(
  "TII Farglory Health Jiujiu frontend flow tests passed.",
);

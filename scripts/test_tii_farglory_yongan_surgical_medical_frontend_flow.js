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
    product_family: "farglory-yongan-surgical-medical-whole-life",
  },
  coverage_entries: [
    entry("surgery-medical-benefit", {
      basis: "face_amount",
      calculation_basis: "table_multiplier",
      limit_scope: "per_surgery",
      aggregation_rule: "highest",
      multiplier_state_key: "surgery_benefit_multiplier",
      unit_key: "face_amount",
    }),
    entry("inpatient-surgery-recuperation-benefit", {
      basis: "face_amount",
      calculation_basis: "table_multiplier",
      limit_scope: "per_surgery",
      multiplier: 3,
      unit_key: "face_amount",
      exclusion_state_key: "surgery_care_setting",
      exclusion_values: ["outpatient"],
    }),
    entry("major-surgery-consolation-benefit", {
      basis: "face_amount",
      calculation_basis: "table_multiplier",
      limit_scope: "per_surgery",
      aggregation_rule: "highest",
      rate_percent: 50,
      minimum_multiplier: 60,
      multiplier_state_key: "surgery_benefit_multiplier",
      unit_key: "face_amount",
    }),
    entry("accidental-wound-suture-benefit", {
      basis: "face_amount",
      calculation_basis: "percentage_of_base",
      limit_scope: "per_accident",
      aggregation_rule: "highest",
      rate_state_key: "wound_suture_benefit_rate_percent",
      unit_key: "face_amount",
    }),
    entry("no-claim-record-bonus-benefit", {
      calculation_basis: "percentage_of_base",
      limit_scope: "per_claim",
      rate_state_key: "no_claim_bonus_rate_percent",
      unit_key: "current_articles_11_to_14_benefit_total_amount",
      policy_state_keys: [
        "current_articles_11_to_14_benefit_total_amount",
      ],
    }),
    entry("remaining-lifetime-medical-benefit-cap", {
      basis: "face_amount",
      calculation_basis: "table_multiplier",
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      multiplier: 1200,
      unit_key: "face_amount",
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
    }),
    entry("maturity-benefit", {
      calculation_basis: "percentage_of_base",
      rate_percent: 110,
      unit_key: "premium_total_amount",
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
      policy_state_keys: ["premium_total_amount"],
    }),
    entry("death-or-funeral-benefit", {
      calculation_basis:
        "death_or_funeral_percentage_of_policy_state_amount",
      rate_percent: 110,
      unit_key: "premium_total_amount",
      cumulative_paid_state_key:
        "cumulative_medical_benefit_paid_amount",
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
  surgery_benefit_multiplier: 60,
  surgery_care_setting: "inpatient",
  wound_suture_benefit_rate_percent: "50",
  current_articles_11_to_14_benefit_total_amount: 100_000,
  no_claim_bonus_rate_percent: "30",
  cumulative_medical_benefit_paid_amount: 2_000_000,
  premium_total_amount: 500_000,
  death_benefit_status: "standard_death",
  death_age_band_status: "standard",
};

const surgery = value("surgery-medical-benefit", commonState);
assert.equal(surgery.state, "policy_state_multiplier");
assert.equal(surgery.value, 600_000);

const inpatient = value(
  "inpatient-surgery-recuperation-benefit",
  commonState,
);
assert.equal(inpatient.value, 30_000);
const outpatient = value(
  "inpatient-surgery-recuperation-benefit",
  { ...commonState, surgery_care_setting: "outpatient" },
);
assert.equal(outpatient.state, "not_eligible");
assert.equal(outpatient.value, 0);

const major = value("major-surgery-consolation-benefit", commonState);
assert.equal(major.value, 300_000);
assert.equal(major.applied_rate, 0.5);
const nonMajor = value(
  "major-surgery-consolation-benefit",
  { ...commonState, surgery_benefit_multiplier: 59 },
);
assert.equal(nonMajor.state, "not_eligible");
assert.equal(nonMajor.value, 0);

assert.equal(
  value("accidental-wound-suture-benefit", commonState).value,
  5_000,
);
assert.equal(
  value(
    "accidental-wound-suture-benefit",
    { ...commonState, wound_suture_benefit_rate_percent: "100" },
  ).value,
  10_000,
);

const bonus = value("no-claim-record-bonus-benefit", commonState);
assert.equal(bonus.value, 30_000);
const noBonus = value(
  "no-claim-record-bonus-benefit",
  { ...commonState, no_claim_bonus_rate_percent: "0" },
);
assert.equal(noBonus.state, "not_eligible");
assert.equal(noBonus.value, 0);

const remainingCap = value(
  "remaining-lifetime-medical-benefit-cap",
  commonState,
);
assert.equal(remainingCap.gross_value, 12_000_000);
assert.equal(remainingCap.value, 10_000_000);

const maturity = value("maturity-benefit", commonState);
assert.equal(maturity.gross_value, 550_000);
assert.equal(maturity.value, 0);

const death = value("death-or-funeral-benefit", {
  ...commonState,
  cumulative_medical_benefit_paid_amount: 50_000,
});
assert.equal(death.value, 500_000);

const missingMultiplier = value(
  "surgery-medical-benefit",
  { ...commonState, surgery_benefit_multiplier: undefined },
);
assert.equal(missingMultiplier.state, "needs_policy_state");
assert.deepEqual(missingMultiplier.required_fields, [
  "surgery_benefit_multiplier",
]);

console.log(
  "TII Farglory Yongan surgical medical frontend flow tests passed.",
);

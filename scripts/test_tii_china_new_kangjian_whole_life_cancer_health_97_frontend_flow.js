const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

const eventKey = "china_new_kangjian_97_event_status";
const cumulativeKey =
  "china_new_kangjian_97_cumulative_paid_amount";
const eventValues = [
  "eligible_in_situ_diagnosis",
  "eligible_full_diagnosis",
  "eligible_specified_cancer_diagnosis",
  "eligible_cancer_treatment",
  "eligible_cancer_death",
  "eligible_terminal_death_advance",
  "diagnosed_within_applicable_waiting_period",
  "eligible_non_cancer_death_refund",
  "not_eligible_or_uncertain",
];

function exclusions(...eligibleValues) {
  return eventValues.filter(
    (value) => !eligibleValues.includes(value),
  );
}

function cappedEntry(id, amount, eligibleValue, overrides = {}) {
  return {
    id,
    name: id,
    amount,
    basis: "per_unit",
    calculation_basis: "per_unit",
    amount_role: "payout",
    limit_scope: "per_event",
    aggregation_rule: "separate",
    source: "terms",
    note: id,
    source_ref: "條款",
    result_kind: "cash_payout",
    cumulative_paid_state_key: cumulativeKey,
    aggregate_limit_entry_id: "cancer-lifetime-benefit-cap",
    exclusion_state_key: eventKey,
    exclusion_values: exclusions(eligibleValue),
    ...overrides,
  };
}

const schedule = {
  selection_type: "unit",
  input_mode: "unit",
  selection_source: "terms",
  selection_label: "投保單位數",
  version_characteristics: {
    product_family:
      "china-new-kangjian-whole-life-cancer-health-97",
  },
  coverage_entries: [
    cappedEntry(
      "cancer-death",
      300_000,
      "eligible_cancer_death",
    ),
    cappedEntry(
      "cancer-terminal-death-advance",
      300_000,
      "eligible_terminal_death_advance",
    ),
    cappedEntry(
      "cancer-diagnosis-in-situ",
      5_000,
      "eligible_in_situ_diagnosis",
    ),
    {
      ...cappedEntry(
        "cancer-diagnosis-full",
        100_000,
        "eligible_full_diagnosis",
      ),
      cumulative_paid_state_key:
        "prior_cancer_diagnosis_benefit_paid_amount",
      aggregate_limit_entry_id: "",
    },
    {
      ...cappedEntry(
        "cancer-diagnosis-specified-combined",
        130_000,
        "eligible_specified_cancer_diagnosis",
      ),
      cumulative_paid_state_key:
        "prior_cancer_diagnosis_benefit_paid_amount",
      aggregate_limit_entry_id: "",
    },
    cappedEntry(
      "cancer-hospital-daily",
      2_000,
      "eligible_cancer_treatment",
      { quantity_state_key: "cancer_hospitalization_days" },
    ),
    cappedEntry(
      "cancer-inpatient-surgery",
      30_000,
      "eligible_cancer_treatment",
      { quantity_state_key: "inpatient_surgery_count" },
    ),
    cappedEntry(
      "cancer-outpatient-surgery",
      5_000,
      "eligible_cancer_treatment",
      { quantity_state_key: "outpatient_surgery_count" },
    ),
    cappedEntry(
      "cancer-discharge-recovery",
      1_500,
      "eligible_cancer_treatment",
      { quantity_state_key: "cancer_hospitalization_days" },
    ),
    cappedEntry(
      "cancer-outpatient-medical",
      1_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "cancer_outpatient_treatment_days",
      },
    ),
    cappedEntry(
      "cancer-radiation",
      1_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "cancer_radiation_treatment_days",
      },
    ),
    cappedEntry(
      "cancer-chemotherapy",
      1_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "cancer_chemotherapy_treatment_days",
      },
    ),
    cappedEntry(
      "cancer-bone-marrow-transplant",
      100_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "china_new_kangjian_97_bone_marrow_transplant_count",
      },
    ),
    cappedEntry(
      "cancer-prosthetic-limb",
      20_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "china_new_kangjian_97_prosthetic_limb_count",
        quantity_cap: 4,
      },
    ),
    cappedEntry(
      "cancer-denture",
      20_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "china_new_kangjian_97_denture_count",
        quantity_cap: 1,
      },
    ),
    cappedEntry(
      "cancer-breast-reconstruction",
      20_000,
      "eligible_cancer_treatment",
      {
        quantity_state_key:
          "cancer_breast_reconstruction_side_count",
        quantity_cap: 2,
      },
    ),
    {
      id: "cancer-lifetime-benefit-cap",
      name: "cancer-lifetime-benefit-cap",
      amount: 2_500_000,
      basis: "per_unit",
      calculation_basis: "per_unit",
      amount_role: "limit",
      limit_scope: "lifetime",
      aggregation_rule: "cumulative_cap",
      source: "terms",
      note: "cap",
      source_ref: "條款",
      result_kind: "reference",
      cumulative_paid_state_key: cumulativeKey,
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_in_situ_diagnosis",
        "eligible_full_diagnosis",
        "eligible_specified_cancer_diagnosis",
        "eligible_cancer_treatment",
        "eligible_cancer_death",
        "eligible_terminal_death_advance",
      ),
    },
    {
      id: "waiting-period-premium-refund",
      name: "waiting-period-premium-refund",
      calculation_basis: "policy_state_amount",
      amount_role: "payout",
      limit_scope: "per_policy",
      aggregation_rule: "separate",
      source: "terms",
      note: "refund",
      source_ref: "條款",
      unit_key:
        "china_new_kangjian_97_waiting_refund_amount",
      policy_state_keys: [
        "china_new_kangjian_97_waiting_refund_amount",
      ],
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "diagnosed_within_applicable_waiting_period",
      ),
    },
    {
      id: "non-cancer-death-unexpired-premium-refund",
      name: "non-cancer-death-unexpired-premium-refund",
      calculation_basis: "policy_state_amount",
      amount_role: "payout",
      limit_scope: "per_policy",
      aggregation_rule: "separate",
      source: "terms",
      note: "refund",
      source_ref: "條款",
      unit_key:
        "china_new_kangjian_97_unexpired_premium_refund_amount",
      policy_state_keys: [
        "china_new_kangjian_97_unexpired_premium_refund_amount",
      ],
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_non_cancer_death_refund",
      ),
    },
    {
      id: "future-premium-waiver",
      name: "future-premium-waiver",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      limit_scope: "per_policy",
      aggregation_rule: "separate",
      source: "terms",
      note: "waiver",
      source_ref: "條款",
      unit_key: "remaining_premium_amount",
      policy_state_keys: ["remaining_premium_amount"],
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_full_diagnosis",
        "eligible_specified_cancer_diagnosis",
      ),
      result_kind: "non_cash_effect",
    },
  ],
};

function value(entryId, policyState, unitCount = 2) {
  return model.coverageValue(
    schedule.coverage_entries.find(
      (candidate) => candidate.id === entryId,
    ),
    {
      ...schedule,
      unit_count: unitCount,
      policy_state: policyState,
    },
  );
}

assert.equal(
  value(
    "cancer-diagnosis-in-situ",
    {
      [eventKey]: "eligible_in_situ_diagnosis",
      [cumulativeKey]: 0,
    },
    2,
  ).value,
  10_000,
);
assert.equal(
  value(
    "cancer-diagnosis-full",
    {
      [eventKey]: "eligible_full_diagnosis",
      prior_cancer_diagnosis_benefit_paid_amount: 10_000,
    },
    2,
  ).value,
  190_000,
);
assert.equal(
  value(
    "cancer-diagnosis-specified-combined",
    {
      [eventKey]: "eligible_specified_cancer_diagnosis",
      prior_cancer_diagnosis_benefit_paid_amount: 10_000,
    },
    2,
  ).value,
  250_000,
);

const treatmentState = {
  [eventKey]: "eligible_cancer_treatment",
  [cumulativeKey]: 0,
  cancer_hospitalization_days: 5,
  inpatient_surgery_count: 1,
  outpatient_surgery_count: 2,
  cancer_outpatient_treatment_days: 3,
  cancer_radiation_treatment_days: 4,
  cancer_chemotherapy_treatment_days: 2,
  china_new_kangjian_97_bone_marrow_transplant_count: 2,
  china_new_kangjian_97_prosthetic_limb_count: 4,
  china_new_kangjian_97_denture_count: 1,
  cancer_breast_reconstruction_side_count: 2,
};
assert.equal(
  value("cancer-hospital-daily", treatmentState).value,
  20_000,
);
assert.equal(
  value("cancer-inpatient-surgery", treatmentState).value,
  60_000,
);
assert.equal(
  value("cancer-outpatient-surgery", treatmentState).value,
  20_000,
);
assert.equal(
  value("cancer-discharge-recovery", treatmentState).value,
  15_000,
);
assert.equal(
  value("cancer-outpatient-medical", treatmentState).value,
  6_000,
);
assert.equal(
  value("cancer-radiation", treatmentState).value,
  8_000,
);
assert.equal(
  value("cancer-chemotherapy", treatmentState).value,
  4_000,
);
assert.equal(
  value("cancer-bone-marrow-transplant", treatmentState)
    .value,
  400_000,
);
assert.equal(
  value("cancer-prosthetic-limb", treatmentState).value,
  160_000,
);
assert.equal(
  value("cancer-denture", treatmentState).value,
  40_000,
);
assert.equal(
  value("cancer-breast-reconstruction", treatmentState)
    .value,
  80_000,
);

assert.equal(
  value(
    "cancer-death",
    {
      [eventKey]: "eligible_cancer_death",
      [cumulativeKey]: 4_900_000,
    },
    2,
  ).value,
  100_000,
);
assert.equal(
  value(
    "waiting-period-premium-refund",
    {
      [eventKey]:
        "diagnosed_within_applicable_waiting_period",
      china_new_kangjian_97_waiting_refund_amount: 75_000,
    },
  ).value,
  75_000,
);
assert.equal(
  value(
    "non-cancer-death-unexpired-premium-refund",
    {
      [eventKey]: "eligible_non_cancer_death_refund",
      china_new_kangjian_97_unexpired_premium_refund_amount:
        18_000,
    },
  ).value,
  18_000,
);
assert.equal(
  value(
    "future-premium-waiver",
    {
      [eventKey]: "eligible_full_diagnosis",
      remaining_premium_amount: 420_000,
    },
  ).value,
  420_000,
);

const treatmentRequired = model
  .policyStateRequirements({
    ...schedule,
    unit_count: 2,
    policy_state: {
      [eventKey]: "eligible_cancer_treatment",
    },
  })
  .fields.map((field) => field.key);
for (const key of [
  eventKey,
  cumulativeKey,
  "cancer_hospitalization_days",
  "inpatient_surgery_count",
  "outpatient_surgery_count",
  "cancer_outpatient_treatment_days",
  "cancer_radiation_treatment_days",
  "cancer_chemotherapy_treatment_days",
  "china_new_kangjian_97_bone_marrow_transplant_count",
  "china_new_kangjian_97_prosthetic_limb_count",
  "china_new_kangjian_97_denture_count",
  "cancer_breast_reconstruction_side_count",
]) {
  assert(treatmentRequired.includes(key), key);
}
assert(
  !treatmentRequired.includes(
    "china_new_kangjian_97_waiting_refund_amount",
  ),
);
assert(!treatmentRequired.includes("remaining_premium_amount"));

const waitingRequired = model
  .policyStateRequirements({
    ...schedule,
    unit_count: 2,
    policy_state: {
      [eventKey]:
        "diagnosed_within_applicable_waiting_period",
    },
  })
  .fields.map((field) => field.key);
assert.deepEqual(waitingRequired, [
  eventKey,
  "china_new_kangjian_97_waiting_refund_amount",
]);

console.log(
  "TII China new Kangjian whole-life cancer health 97 "
    + "frontend flow tests passed.",
);

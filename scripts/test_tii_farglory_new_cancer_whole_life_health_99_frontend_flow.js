const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

const eventKey = "farglory_new_cancer_99_event_status";
const cumulativeKey =
  "farglory_new_cancer_99_cumulative_paid_amount";
const eventValues = [
  "eligible_reduced_diagnosis",
  "eligible_full_diagnosis",
  "eligible_cancer_treatment",
  "diagnosed_within_applicable_waiting_period",
  "not_eligible_or_uncertain",
];

function entry(id, amount, overrides = {}) {
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
    ...overrides,
  };
}

function exclusions(eligibleValue) {
  return eventValues.filter((value) => value !== eligibleValue);
}

const schedule = {
  selection_type: "unit",
  input_mode: "unit",
  selection_source: "terms",
  selection_label: "投保單位數",
  version_characteristics: {
    product_family:
      "farglory-new-cancer-whole-life-health-99",
  },
  coverage_entries: [
    entry("cancer-diagnosis-reduced", 15_000, {
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_reduced_diagnosis",
      ),
    }),
    entry("cancer-diagnosis-full", 100_000, {
      exclusion_state_key: eventKey,
      exclusion_values: exclusions("eligible_full_diagnosis"),
    }),
    entry("cancer-hospital-daily", 1_200, {
      quantity_state_key: "cancer_hospitalization_days",
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-hospital-auxiliary", 600, {
      quantity_state_key: "cancer_hospitalization_days",
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-inpatient-surgery", 30_000, {
      quantity_state_key: "inpatient_surgery_count",
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-outpatient-surgery", 4_500, {
      quantity_state_key: "outpatient_surgery_count",
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-bone-marrow-transplant", 60_000, {
      quantity_state_key: "cancer_bone_marrow_transplant_count",
      quantity_cap: 1,
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-outpatient-medical", 600, {
      quantity_state_key: "cancer_outpatient_treatment_days",
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-radiochemotherapy", 1_000, {
      quantity_state_key:
        "cancer_radiochemotherapy_treatment_count",
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-breast-reconstruction", 60_000, {
      quantity_state_key:
        "cancer_breast_reconstruction_side_count",
      quantity_cap: 2,
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    entry("cancer-prosthetic-limb", 100_000, {
      quantity_state_key: "cancer_prosthetic_limb_count",
      quantity_cap: 1,
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "eligible_cancer_treatment",
      ),
    }),
    {
      id: "cancer-lifetime-benefit-cap",
      name: "cancer-lifetime-benefit-cap",
      amount: 1_800_000,
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
      exclusion_values: [
        "diagnosed_within_applicable_waiting_period",
        "not_eligible_or_uncertain",
      ],
    },
    {
      id: "waiting-period-premium-refund",
      name: "waiting-period-premium-refund",
      amount: null,
      basis: "policy_recorded_limit",
      calculation_basis: "policy_state_amount",
      amount_role: "payout",
      limit_scope: "per_policy",
      aggregation_rule: "separate",
      source: "terms",
      note: "refund",
      source_ref: "條款",
      unit_key:
        "farglory_new_cancer_99_waiting_refund_amount",
      policy_state_keys: [
        "farglory_new_cancer_99_waiting_refund_amount",
      ],
      exclusion_state_key: eventKey,
      exclusion_values: exclusions(
        "diagnosed_within_applicable_waiting_period",
      ),
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

const baseState = {
  [cumulativeKey]: 0,
};
assert.equal(
  value("cancer-diagnosis-reduced", {
    ...baseState,
    [eventKey]: "eligible_reduced_diagnosis",
  }, 3).value,
  45_000,
);
assert.equal(
  value("cancer-diagnosis-full", {
    ...baseState,
    [eventKey]: "eligible_full_diagnosis",
  }, 3).value,
  300_000,
);
assert.equal(
  value("cancer-diagnosis-reduced", {
    ...baseState,
    [eventKey]: "eligible_full_diagnosis",
  }).state,
  "not_eligible",
);

const treatmentState = {
  ...baseState,
  [eventKey]: "eligible_cancer_treatment",
  cancer_hospitalization_days: 5,
  inpatient_surgery_count: 2,
  outpatient_surgery_count: 3,
  cancer_bone_marrow_transplant_count: 1,
  cancer_outpatient_treatment_days: 4,
  cancer_radiochemotherapy_treatment_count: 3,
  cancer_breast_reconstruction_side_count: 2,
  cancer_prosthetic_limb_count: 1,
};
assert.equal(
  value("cancer-hospital-daily", treatmentState).value,
  12_000,
);
assert.equal(
  value("cancer-hospital-auxiliary", treatmentState).value,
  6_000,
);
assert.equal(
  value("cancer-inpatient-surgery", treatmentState).value,
  120_000,
);
assert.equal(
  value("cancer-outpatient-surgery", treatmentState).value,
  27_000,
);
assert.equal(
  value("cancer-bone-marrow-transplant", treatmentState).value,
  120_000,
);
assert.equal(
  value("cancer-outpatient-medical", treatmentState).value,
  4_800,
);
assert.equal(
  value("cancer-radiochemotherapy", treatmentState).value,
  6_000,
);
assert.equal(
  value("cancer-breast-reconstruction", treatmentState).value,
  240_000,
);
assert.equal(
  value("cancer-prosthetic-limb", treatmentState).value,
  200_000,
);

const remainingCap = value(
  "cancer-lifetime-benefit-cap",
  {
    ...treatmentState,
    [cumulativeKey]: 3_500_000,
  },
);
assert.equal(remainingCap.value, 100_000);

const refund = value(
  "waiting-period-premium-refund",
  {
    [eventKey]:
      "diagnosed_within_applicable_waiting_period",
    farglory_new_cancer_99_waiting_refund_amount: 75_000,
  },
);
assert.equal(refund.value, 75_000);

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
  cumulativeKey,
  "cancer_hospitalization_days",
  "inpatient_surgery_count",
  "outpatient_surgery_count",
  "cancer_bone_marrow_transplant_count",
  "cancer_outpatient_treatment_days",
  "cancer_radiochemotherapy_treatment_count",
  "cancer_breast_reconstruction_side_count",
  "cancer_prosthetic_limb_count",
]) {
  assert(treatmentRequired.includes(key), key);
}
assert(
  !treatmentRequired.includes(
    "farglory_new_cancer_99_waiting_refund_amount",
  ),
);

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
  "farglory_new_cancer_99_waiting_refund_amount",
]);

console.log(
  "TII Farglory new cancer whole-life health 99 "
    + "frontend flow tests passed.",
);

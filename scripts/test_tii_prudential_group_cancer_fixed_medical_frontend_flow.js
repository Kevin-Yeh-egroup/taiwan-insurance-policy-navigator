const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

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
    amount_stage: "gross_contract_benefit",
    ...overrides,
  };
}

function schedule(earlySchedule) {
  const outpatientAmount = earlySchedule ? 1_000 : 500;
  return {
    selection_type: "unit",
    input_mode: "unit",
    selection_source: "terms",
    version_characteristics: {
      product_family: "prudential-group-cancer-fixed-medical",
      maximum_unit_count: earlySchedule ? 10 : 20,
    },
    coverage_entries: [
      entry(
        "cancer-death-benefit",
        earlySchedule ? 500_000 : 250_000,
        earlySchedule
          ? {
              exclusion_state_key: "minor_death_benefit_status",
              exclusion_values: ["not_effective"],
            }
          : {},
      ),
      entry(
        "cancer-inpatient-daily-benefit",
        earlySchedule ? 2_000 : 1_000,
        {
          basis: "daily_per_unit",
          calculation_basis: "per_unit_per_day",
          limit_scope: "per_day",
          quantity_state_key: "cancer_hospitalization_days",
        },
      ),
      entry(
        "cancer-post-discharge-outpatient-benefit",
        outpatientAmount,
        {
          calculation_basis: "tiered_or_stepped",
          limit_scope: "annual",
          aggregation_rule: "cumulative_cap",
          quantity_state_key:
            "cancer_post_discharge_outpatient_visit_count",
          amount_tiers: [
            {
              label: "同一保單年度第 1 至 70 次",
              amount: outpatientAmount,
              min_quantity: 1,
              max_quantity: 70,
            },
          ],
        },
      ),
      entry(
        "cancer-inpatient-surgery-benefit",
        earlySchedule ? 30_000 : 15_000,
        {
          limit_scope: "per_hospitalization",
          quantity_state_key:
            "cancer_inpatient_surgery_hospitalization_count",
        },
      ),
    ],
  };
}

function value(sourceSchedule, entryId, policyState, unitCount = 2) {
  return model.coverageValue(
    sourceSchedule.coverage_entries.find(
      (candidate) => candidate.id === entryId,
    ),
    {
      ...sourceSchedule,
      unit_count: unitCount,
      policy_state: policyState,
    },
  );
}

const early = schedule(true);
const earlyState = {
  minor_death_benefit_status: "effective",
  cancer_hospitalization_days: 3,
  cancer_post_discharge_outpatient_visit_count: 80,
  cancer_inpatient_surgery_hospitalization_count: 2,
};
assert.equal(
  value(early, "cancer-death-benefit", earlyState).value,
  1_000_000,
);
assert.equal(
  value(early, "cancer-inpatient-daily-benefit", earlyState).value,
  12_000,
);
assert.equal(
  value(
    early,
    "cancer-post-discharge-outpatient-benefit",
    earlyState,
  ).value,
  140_000,
);
assert.equal(
  value(early, "cancer-inpatient-surgery-benefit", earlyState).value,
  120_000,
);

const minorDeath = value(
  early,
  "cancer-death-benefit",
  {
    ...earlyState,
    minor_death_benefit_status: "not_effective",
  },
);
assert.equal(minorDeath.state, "not_eligible");
assert.equal(minorDeath.value, 0);
assert.equal(minorDeath.exclusion_state_key, "minor_death_benefit_status");
assert.equal(minorDeath.exclusion_value, "not_effective");

const later = schedule(false);
const laterState = {
  cancer_hospitalization_days: 3,
  cancer_post_discharge_outpatient_visit_count: 80,
  cancer_inpatient_surgery_hospitalization_count: 2,
};
assert.equal(
  value(later, "cancer-death-benefit", laterState).value,
  500_000,
);
assert.equal(
  value(later, "cancer-inpatient-daily-benefit", laterState).value,
  6_000,
);
assert.equal(
  value(
    later,
    "cancer-post-discharge-outpatient-benefit",
    laterState,
  ).value,
  70_000,
);
assert.equal(
  value(later, "cancer-inpatient-surgery-benefit", laterState).value,
  60_000,
);

const missingOutpatientCount = value(
  later,
  "cancer-post-discharge-outpatient-benefit",
  {
    cancer_hospitalization_days: 3,
    cancer_inpatient_surgery_hospitalization_count: 2,
  },
);
assert.equal(missingOutpatientCount.state, "needs_policy_state");
assert.deepEqual(missingOutpatientCount.required_fields, [
  "cancer_post_discharge_outpatient_visit_count",
]);

console.log(
  "TII Prudential group cancer fixed medical frontend flow tests passed.",
);

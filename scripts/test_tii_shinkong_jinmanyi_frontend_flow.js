const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const age15Rule = revision >= 13;
  const disabilityBoundary = revision >= 18;
  const sharedOffsets = [
    "policy_effect_status_at_event",
    "policy_loan_and_interest_amount",
    "unpaid_policy_charge_amount",
  ];
  const riskKeys = [
    "risk_amount_source",
    "risk_calculation_actual_age",
    "risk_calculation_insurance_age",
    "insured_age_accuracy_status",
    "risk_calculation_stage",
    "risk_calculation_policy_account_value",
    "risk_calculation_net_premium_amount",
    "risk_amount_effective_status",
    "insurer_confirmed_current_risk_amount",
  ];
  const claimKeys = [
    "benefit_valuation_policy_account_value",
    ...sharedOffsets,
    ...(age15Rule ? ["insured_age_at_event"] : []),
    ...riskKeys,
    "claim_time_status",
    "benefit_exclusion_status",
    "post_event_insurance_cost_refund_status",
    "post_event_insurance_cost_refund_amount",
  ];
  const commonEntry = {
    basis: "policy_recorded_limit",
    calculation_basis:
      "net_amount_at_risk_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
  };
  return {
    selection_type: "face_amount",
    input_mode: "face_amount",
    face_amount_label: "保險金額",
    version_characteristics: {
      product_family:
        "shinkong-jinmanyi-variable-universal-life",
      terms_revision: `partial-change-${revision}`,
      risk_amount_actual_age_threshold: age15Rule ? 15 : 14,
      age15_recalculation_applies: age15Rule,
      risk_coefficient_schedule: [
        {
          min_insurance_age: 14,
          max_insurance_age: 40,
          factor: 0.3,
        },
        {
          min_insurance_age: 41,
          max_insurance_age: 70,
          factor: 0.15,
        },
        {
          min_insurance_age: 71,
          max_insurance_age: 130,
          factor: 0.01,
        },
      ],
    },
    coverage_entries: [
      {
        ...commonEntry,
        id: "death-benefit",
        name: "身故保險金或喪葬費用保險金",
        policy_state_keys: [
          ...claimKeys,
          ...(age15Rule
            ? ["event_before_policy_maturity_status"]
            : []),
          "death_benefit_status",
          "remaining_funeral_benefit_limit",
          "funeral_excess_insurance_cost_refund_status",
          "funeral_excess_insurance_cost_refund_amount",
        ],
        ...(age15Rule
          ? { minor_account_value_return_age: 15 }
          : {}),
      },
      {
        ...commonEntry,
        id: "total-disability-benefit",
        name: "全殘廢保險金",
        policy_state_keys: [
          ...claimKeys,
          ...(disabilityBoundary
            ? ["event_before_policy_maturity_status"]
            : []),
          "total_disability_qualification_status",
        ],
      },
    ],
  };
}

function entryFor(schedule, entryId) {
  return schedule.coverage_entries.find(
    (entry) => entry.id === entryId,
  );
}

function valueFor(schedule, entryId, selection) {
  return model.coverageValue(entryFor(schedule, entryId), {
    ...schedule,
    ...selection,
  });
}

function commonState(revision, overrides = {}) {
  return {
    benefit_valuation_policy_account_value: 200_000,
    policy_effect_status_at_event: "active",
    policy_loan_and_interest_amount: 0,
    unpaid_policy_charge_amount: 0,
    ...(revision >= 13 ? { insured_age_at_event: 35 } : {}),
    claim_time_status: "within_claim_period",
    benefit_exclusion_status: "none_confirmed",
    post_event_insurance_cost_refund_status: "none",
    post_event_insurance_cost_refund_amount: 0,
    ...(revision >= 13
      ? { event_before_policy_maturity_status: "before_maturity" }
      : {}),
    death_benefit_status: "standard_death",
    total_disability_qualification_status:
      "confirmed_first_level_item",
    ...overrides,
  };
}

const latest = scheduleFor(23);
const insurerAmount = valueFor(latest, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(23, {
    risk_amount_source: "insurer_statement",
    insurer_confirmed_current_risk_amount: 180_000,
  }),
});
assert.equal(insurerAmount.state, "death_or_funeral_amount");
assert.equal(insurerAmount.value, 380_000);
assert.equal(insurerAmount.risk_amount, 180_000);

const recalculated = valueFor(
  latest,
  "total-disability-benefit",
  {
    face_amount: 100_000,
    policy_state: commonState(23, {
      risk_amount_source: "recalculate_from_history",
      insured_age_accuracy_status: "confirmed_accurate",
      risk_calculation_actual_age: 40,
      risk_calculation_insurance_age: 40,
      risk_calculation_stage: "subsequent_regular_premium",
      risk_calculation_policy_account_value: 300_000,
      risk_calculation_net_premium_amount: 100_000,
      risk_amount_effective_status: "current_formula_effective",
    }),
  },
);
assert.equal(recalculated.value, 320_000);
assert.equal(recalculated.risk_amount, 120_000);
assert.equal(recalculated.risk_coefficient, 0.3);

const minorDeath = valueFor(latest, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(23, {
    insured_age_at_event: 14,
    benefit_valuation_policy_account_value: 100_000,
  }),
});
assert.equal(minorDeath.state, "account_value_return");
assert.equal(minorDeath.value, 100_000);

const early = scheduleFor(12);
const earlyMinorRisk = valueFor(
  early,
  "total-disability-benefit",
  {
    face_amount: 100_000,
    policy_state: commonState(12, {
      risk_amount_source: "recalculate_from_history",
      insured_age_accuracy_status: "confirmed_accurate",
      risk_calculation_actual_age: 13,
      risk_calculation_insurance_age: 14,
      risk_calculation_stage: "before_second_premium",
      risk_amount_effective_status: "current_formula_effective",
    }),
  },
);
assert.equal(earlyMinorRisk.risk_amount, 100_000);
assert.equal(earlyMinorRisk.value, 300_000);

assert.equal(
  entryFor(
    scheduleFor(17),
    "total-disability-benefit",
  ).policy_state_keys.includes(
    "event_before_policy_maturity_status",
  ),
  false,
);
assert.equal(
  entryFor(
    scheduleFor(18),
    "total-disability-benefit",
  ).policy_state_keys.includes(
    "event_before_policy_maturity_status",
  ),
  true,
);

const insurerFields = model.policyStateRequirements({
  ...latest,
  face_amount: 100_000,
  policy_state: commonState(23, {
    risk_amount_source: "insurer_statement",
  }),
}).fields.map((field) => field.key);
assert.equal(
  insurerFields.includes("insurer_confirmed_current_risk_amount"),
  true,
);
assert.equal(insurerFields.includes("risk_calculation_stage"), false);

const historyFields = model.policyStateRequirements({
  ...latest,
  face_amount: 100_000,
  policy_state: commonState(23, {
    risk_amount_source: "recalculate_from_history",
  }),
}).fields.map((field) => field.key);
assert.equal(
  historyFields.includes("risk_calculation_actual_age"),
  true,
);
assert.equal(historyFields.includes("risk_calculation_stage"), true);

console.log({
  status: "ok",
  batch_id: "tii-life-047",
  exact_versions: 24,
  user_flow_cases: 7,
});

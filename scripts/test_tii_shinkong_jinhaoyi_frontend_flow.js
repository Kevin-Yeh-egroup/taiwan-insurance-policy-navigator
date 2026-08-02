const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const late = revision >= 14;
  const disabilityBoundary = revision >= 19;
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
    ...(late ? ["insured_age_at_event"] : []),
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
        "shinkong-jinhaoyi-variable-universal-life",
      terms_revision: `partial-change-${revision}`,
      semantic_phase:
        revision <= 13
          ? "age14-risk-threshold-appendix5"
          : revision <= 18
            ? "age15-minor-return-death-before-maturity-appendix5"
            : revision <= 22
              ? "age15-minor-return-all-events-before-maturity-appendix5"
              : "age15-minor-return-all-events-before-maturity-appendix4",
      risk_amount_actual_age_threshold: late ? 15 : 14,
      age15_recalculation_applies: late,
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
          ...(late ? ["event_before_policy_maturity_status"] : []),
          "death_benefit_status",
          "remaining_funeral_benefit_limit",
          "funeral_excess_insurance_cost_refund_status",
          "funeral_excess_insurance_cost_refund_amount",
        ],
        ...(late ? { minor_account_value_return_age: 15 } : {}),
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
    ...(revision >= 14 ? { insured_age_at_event: 35 } : {}),
    claim_time_status: "within_claim_period",
    benefit_exclusion_status: "none_confirmed",
    post_event_insurance_cost_refund_status: "none",
    post_event_insurance_cost_refund_amount: 0,
    ...(revision >= 14
      ? { event_before_policy_maturity_status: "before_maturity" }
      : {}),
    death_benefit_status: "standard_death",
    total_disability_qualification_status:
      "confirmed_first_level_item",
    ...overrides,
  };
}

const late = scheduleFor(24);
const insurerAmount = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "insurer_statement",
    insurer_confirmed_current_risk_amount: 180_000,
  }),
});
assert.equal(insurerAmount.state, "death_or_funeral_amount");
assert.equal(insurerAmount.value, 380_000);
assert.equal(insurerAmount.risk_amount, 180_000);

const recalcAgeNotEventAge = valueFor(
  late,
  "total-disability-benefit",
  {
    face_amount: 100_000,
    policy_state: commonState(24, {
      insured_age_at_event: 41,
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
assert.equal(recalcAgeNotEventAge.value, 320_000);
assert.equal(recalcAgeNotEventAge.risk_amount, 120_000);
assert.equal(recalcAgeNotEventAge.risk_coefficient, 0.3);

for (const [insuranceAge, expectedCoefficient, expectedRisk] of [
  [41, 0.15, 100_000],
  [71, 0.01, 100_000],
]) {
  const result = valueFor(late, "total-disability-benefit", {
    face_amount: 100_000,
    policy_state: commonState(24, {
      risk_amount_source: "recalculate_from_history",
      insured_age_accuracy_status: "confirmed_accurate",
      risk_calculation_actual_age: insuranceAge,
      risk_calculation_insurance_age: insuranceAge,
      risk_calculation_stage: "subsequent_nonregular_premium",
      risk_calculation_policy_account_value: 300_000,
      risk_calculation_net_premium_amount: 100_000,
      risk_amount_effective_status: "current_formula_effective",
    }),
  });
  assert.equal(result.risk_coefficient, expectedCoefficient);
  assert.equal(result.risk_amount, expectedRisk);
}

const early = scheduleFor(0);
const earlyMinorRecalculation = valueFor(
  early,
  "total-disability-benefit",
  {
    face_amount: 100_000,
    policy_state: commonState(0, {
      risk_amount_source: "recalculate_from_history",
      insured_age_accuracy_status: "confirmed_accurate",
      risk_calculation_actual_age: 13,
      risk_calculation_insurance_age: 14,
      risk_calculation_stage: "before_second_premium",
      risk_amount_effective_status: "current_formula_effective",
    }),
  },
);
assert.equal(earlyMinorRecalculation.risk_amount, 100_000);
assert.equal(earlyMinorRecalculation.value, 300_000);

const minorDeath = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    insured_age_at_event: 14,
    benefit_valuation_policy_account_value: 100_000,
    post_event_insurance_cost_refund_status:
      "charged_after_event",
    post_event_insurance_cost_refund_amount: 1_000,
  }),
});
assert.equal(minorDeath.state, "account_value_return");
assert.equal(minorDeath.value, 100_000);
assert.equal(minorDeath.post_event_insurance_cost_refund_amount, 0);

const timeBarred = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    claim_time_status: "time_barred",
    benefit_valuation_policy_account_value: 100_000,
    post_event_insurance_cost_refund_status:
      "charged_after_event",
    post_event_insurance_cost_refund_amount: 1_000,
  }),
});
assert.equal(timeBarred.state, "account_value_return");
assert.equal(timeBarred.value, 100_000);
assert.equal(timeBarred.post_event_insurance_cost_refund_amount, 0);

const funeral = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "insurer_statement",
    insurer_confirmed_current_risk_amount: 300_000,
    benefit_valuation_policy_account_value: 200_000,
    post_event_insurance_cost_refund_status:
      "charged_after_event",
    post_event_insurance_cost_refund_amount: 1_000,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 100_000,
    funeral_excess_insurance_cost_refund_status:
      "confirmed_amount",
    funeral_excess_insurance_cost_refund_amount: 5_000,
  }),
});
assert.equal(funeral.value, 306_000);
assert.equal(funeral.payable_risk_amount, 100_000);
assert.equal(
  funeral.funeral_excess_insurance_cost_refund_amount,
  5_000,
);

const unknownFuneralRefund = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "insurer_statement",
    insurer_confirmed_current_risk_amount: 300_000,
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 100_000,
    funeral_excess_insurance_cost_refund_status: "unknown",
  }),
});
assert.equal(
  unknownFuneralRefund.confirmation_reason,
  "funeral_excess_insurance_cost_refund_unknown",
);

const ageError = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "recalculate_from_history",
    insured_age_accuracy_status: "error_or_uncertain",
  }),
});
assert.equal(
  ageError.confirmation_reason,
  "insured_age_error_requires_adjusted_risk_amount",
);

const pendingDecrease = valueFor(late, "death-benefit", {
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "recalculate_from_history",
    insured_age_accuracy_status: "confirmed_accurate",
    risk_calculation_actual_age: 40,
    risk_calculation_insurance_age: 40,
    risk_calculation_stage: "subsequent_regular_premium",
    risk_amount_effective_status:
      "decrease_pending_next_monthiversary",
    insurer_confirmed_current_risk_amount: 190_000,
  }),
});
assert.equal(pendingDecrease.risk_amount, 190_000);

const fractionalNeedsConfirmation = valueFor(
  late,
  "death-benefit",
  {
    face_amount: 1,
    policy_state: commonState(24, {
      risk_amount_source: "recalculate_from_history",
      insured_age_accuracy_status: "confirmed_accurate",
      risk_calculation_actual_age: 40,
      risk_calculation_insurance_age: 40,
      risk_calculation_stage: "subsequent_regular_premium",
      risk_calculation_policy_account_value: 100_000,
      risk_calculation_net_premium_amount: 1,
      risk_amount_effective_status: "current_formula_effective",
    }),
  },
);
assert.equal(
  fractionalNeedsConfirmation.confirmation_reason,
  "fractional_policy_amount_rounding_undefined",
);

const revision18 = scheduleFor(18);
const revision19 = scheduleFor(19);
assert.equal(
  entryFor(
    revision18,
    "total-disability-benefit",
  ).policy_state_keys.includes(
    "event_before_policy_maturity_status",
  ),
  false,
);
assert.equal(
  entryFor(
    revision19,
    "total-disability-benefit",
  ).policy_state_keys.includes(
    "event_before_policy_maturity_status",
  ),
  true,
);
const boundaryUncertain = valueFor(
  revision19,
  "total-disability-benefit",
  {
    face_amount: 100_000,
    policy_state: commonState(19, {
      event_before_policy_maturity_status: "uncertain",
    }),
  },
);
assert.equal(
  boundaryUncertain.confirmation_reason,
  "event_not_confirmed_before_policy_maturity",
);

const insurerFields = model.policyStateRequirements({
  ...late,
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "insurer_statement",
  }),
}).fields.map((field) => field.key);
assert.equal(
  insurerFields.includes("insurer_confirmed_current_risk_amount"),
  true,
);
assert.equal(insurerFields.includes("risk_calculation_stage"), false);

const historyFields = model.policyStateRequirements({
  ...late,
  face_amount: 100_000,
  policy_state: commonState(24, {
    risk_amount_source: "recalculate_from_history",
  }),
}).fields.map((field) => field.key);
assert.equal(historyFields.includes("risk_calculation_actual_age"), true);
assert.equal(
  historyFields.includes("risk_calculation_insurance_age"),
  true,
);

const minorFields = model.policyStateRequirements({
  ...late,
  face_amount: 100_000,
  policy_state: commonState(24, {
    insured_age_at_event: 14,
  }),
}).fields.map((field) => field.key);
assert.equal(minorFields.includes("risk_amount_source"), false);
assert.equal(minorFields.includes("risk_calculation_stage"), false);
assert.equal(minorFields.includes("death_benefit_status"), false);

console.log({
  status: "ok",
  batch_id: "tii-life-047",
  exact_versions: 25,
  user_flow_cases: 18,
});

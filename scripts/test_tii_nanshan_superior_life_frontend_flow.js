const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const disabilityName =
    revision <= 11
      ? "殘廢保險金"
      : revision <= 18
        ? "完全殘廢保險金"
        : "完全失能保險金";
  const legacy = revision <= 11;
  const commonKeys = [
    "policy_effect_status_at_event",
    "benefit_valuation_policy_account_value",
    "claim_time_status",
    "benefit_exclusion_status",
    "insured_age_accuracy_status",
    ...(legacy ? ["investment_allocation_status"] : []),
    "policy_loan_and_interest_amount",
    "unpaid_policy_charge_amount",
    ...(revision === 0 ? [] : ["insured_age_at_event"]),
  ];
  const benefitEntry = {
    basis: "policy_recorded_limit",
    calculation_basis: "protected_amount_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_event",
    aggregation_rule: "separate",
    unit_key:
      "protected_amount_plus_benefit_valuation_policy_account_value",
    ...(revision === 0
      ? {}
      : { minor_account_value_return_age: 15 }),
  };
  return {
    selection_type: "face_amount",
    input_mode: "face_amount",
    face_amount_label: "基本保額",
    version_characteristics: {
      product_family: "nanshan-superior-life-variable-life",
      semantic_phase:
        revision === 0
          ? "legacy_no_minor_age_rule"
          : revision === 1
            ? "legacy_actual_age_minor15"
            : revision <= 11
              ? "legacy_issue_age_minor15"
              : revision <= 18
          ? "minor15_mental_incapacity_complete_disability"
          : "minor15_guardianship_complete_impairment",
      claim_time_bar_account_value_return: !legacy,
      unallocated_net_premium_return_on_exclusion: legacy,
    },
    coverage_entries: [
      {
        id: "nanshan-superior-life-maturity",
        name: legacy ? "滿期保險金" : "祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_event",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
        policy_state_keys: [
          "policy_effect_status_at_event",
          "policy_loan_and_interest_amount",
          "unpaid_policy_charge_amount",
        ],
      },
      {
        ...benefitEntry,
        id: "nanshan-superior-life-death",
        name: "身故保險金或喪葬費用保險金",
        ...(legacy && revision !== 0
          ? { minor_unallocated_net_premium_return: false }
          : {}),
        policy_state_keys: [
          ...commonKeys,
          "death_benefit_status",
          "funeral_excess_insurance_cost_refund_status",
          "funeral_excess_insurance_cost_refund_amount",
        ],
      },
      {
        ...benefitEntry,
        id: "nanshan-superior-life-disability",
        name: disabilityName,
        ...(legacy && revision !== 0
          ? { minor_unallocated_net_premium_return: true }
          : {}),
        policy_state_keys: [
          ...commonKeys,
          "total_disability_qualification_status",
        ],
      },
      {
        id: "nanshan-superior-life-value-addition",
        name: "加值給付",
        basis: "policy_recorded_limit",
        calculation_basis:
          legacy
            ? "policy_year_average_basic_premium_account_value_addition"
            : "policy_year_average_target_premium_account_value_addition",
        amount_role: "reference",
        limit_scope: "per_event",
        aggregation_rule: "separate",
        unit_key: legacy
          ? "average_basic_premium_account_value"
          : "average_target_premium_account_value",
        policy_state_keys: [
          "policy_effect_status_at_event",
          "policy_year",
          legacy
            ? "average_basic_premium_account_value"
            : "average_target_premium_account_value",
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

function benefitState(overrides = {}) {
  return {
    policy_effect_status_at_event: "active",
    benefit_valuation_policy_account_value: 300_000,
    claim_time_status: "within_claim_period",
    benefit_exclusion_status: "none_confirmed",
    insured_age_accuracy_status: "confirmed_accurate",
    policy_loan_and_interest_amount: 100_000,
    unpaid_policy_charge_amount: 20_000,
    insured_age_at_event: 40,
    ...overrides,
  };
}

function legacyBenefitState(overrides = {}) {
  return benefitState({
    investment_allocation_status: "allocated",
    ...overrides,
  });
}

const legacyRevision0 = scheduleFor(0);
const legacyAllocated = valueFor(
  legacyRevision0,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      death_benefit_status: "standard_death",
    }),
  },
);
assert.equal(legacyAllocated.state, "death_or_funeral_amount");
assert.equal(legacyAllocated.value, 1_180_000);

const legacyPendingAllocation = valueFor(
  legacyRevision0,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      death_benefit_status: "standard_death",
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
    }),
  },
);
assert.equal(legacyPendingAllocation.value, 1_230_000);
assert.equal(
  legacyPendingAllocation.unallocated_net_premium_amount,
  50_000,
);

const legacyExclusion = valueFor(
  legacyRevision0,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      claim_time_status: "within_claim_period",
      benefit_exclusion_status: "confirmed_applies",
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
    }),
  },
);
assert.equal(legacyExclusion.state, "account_value_return");
assert.equal(legacyExclusion.value, 230_000);

const legacyTimeBarred = valueFor(
  legacyRevision0,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      claim_time_status: "time_barred",
    }),
  },
);
assert.equal(legacyTimeBarred.state, "needs_insurer_confirmation");
assert.equal(
  legacyTimeBarred.confirmation_reason,
  "claim_time_bar_return_not_stated",
);

const legacyRevision1 = scheduleFor(1);
const legacyMinorDeath = valueFor(
  legacyRevision1,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      insured_age_at_event: 14,
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
    }),
  },
);
assert.equal(legacyMinorDeath.state, "account_value_return");
assert.equal(legacyMinorDeath.value, 180_000);
assert.equal(legacyMinorDeath.unallocated_net_premium_amount, 0);

const legacyMinorDisability = valueFor(
  legacyRevision1,
  "nanshan-superior-life-disability",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      insured_age_at_event: 14,
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
      total_disability_qualification_status:
        "confirmed_first_level_item",
    }),
  },
);
assert.equal(legacyMinorDisability.state, "account_value_return");
assert.equal(legacyMinorDisability.value, 230_000);

const legacyAge15Death = valueFor(
  legacyRevision1,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: legacyBenefitState({
      insured_age_at_event: 15,
      death_benefit_status: "standard_death",
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
    }),
  },
);
assert.equal(legacyAge15Death.state, "death_or_funeral_amount");
assert.equal(legacyAge15Death.value, 1_230_000);

const legacyValueAddition = valueFor(
  legacyRevision1,
  "nanshan-superior-life-value-addition",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      policy_year: 6,
      average_basic_premium_account_value: 1_000_000,
    },
  },
);
assert.equal(legacyValueAddition.state, "value_added_account_credit");
assert.equal(legacyValueAddition.value, 2_000);
assert.equal(
  legacyValueAddition.average_basic_premium_account_value,
  1_000_000,
);

const legacyBeforeValueAddition = valueFor(
  legacyRevision1,
  "nanshan-superior-life-value-addition",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      policy_year: 5,
    },
  },
);
assert.equal(
  legacyBeforeValueAddition.state,
  "value_added_account_credit",
);
assert.equal(legacyBeforeValueAddition.value, 0);

const schedule = scheduleFor(12);
const standardDeath = valueFor(
  schedule,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      death_benefit_status: "standard_death",
    }),
  },
);
assert.equal(standardDeath.state, "death_or_funeral_amount");
assert.equal(standardDeath.value, 1_180_000);

const funeralLimited = valueFor(
  schedule,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 200_000,
      funeral_excess_insurance_cost_refund_status: "confirmed_amount",
      funeral_excess_insurance_cost_refund_amount: 10_000,
    }),
  },
);
assert.equal(funeralLimited.state, "death_or_funeral_amount");
assert.equal(funeralLimited.protected_amount, 200_000);
assert.equal(funeralLimited.value, 390_000);
assert.equal(
  funeralLimited.funeral_excess_insurance_cost_refund_amount,
  10_000,
);

const unknownFuneralRefund = valueFor(
  schedule,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 200_000,
      funeral_excess_insurance_cost_refund_status: "unknown",
    }),
  },
);
assert.equal(unknownFuneralRefund.state, "needs_insurer_confirmation");
assert.equal(
  unknownFuneralRefund.confirmation_reason,
  "funeral_excess_insurance_cost_refund_unknown",
);

const minorDeath = valueFor(
  schedule,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      insured_age_at_event: 14,
    }),
  },
);
assert.equal(minorDeath.state, "account_value_return");
assert.equal(minorDeath.value, 180_000);

const minorDisability = valueFor(
  schedule,
  "nanshan-superior-life-disability",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      insured_age_at_event: 14,
      total_disability_qualification_status:
        "confirmed_first_level_item",
    }),
  },
);
assert.equal(minorDisability.state, "account_value_return");
assert.equal(minorDisability.value, 180_000);

const timeBarred = valueFor(
  schedule,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 300_000,
      claim_time_status: "time_barred",
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
    },
  },
);
assert.equal(timeBarred.state, "account_value_return");
assert.equal(timeBarred.value, 180_000);
assert.equal(
  timeBarred.formula_type,
  "claim_time_barred_account_value_return",
);

const exclusionReturn = valueFor(
  schedule,
  "nanshan-superior-life-disability",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 300_000,
      benefit_exclusion_status: "confirmed_applies",
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
    },
  },
);
assert.equal(exclusionReturn.state, "account_value_return");
assert.equal(exclusionReturn.value, 180_000);
assert.equal(exclusionReturn.formula_type, "exclusion_account_value_return");

const ageUncertain = valueFor(
  schedule,
  "nanshan-superior-life-death",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      insured_age_accuracy_status: "error_or_uncertain",
      death_benefit_status: "standard_death",
    }),
  },
);
assert.equal(ageUncertain.state, "needs_insurer_confirmation");
assert.equal(
  ageUncertain.confirmation_reason,
  "insured_age_not_confirmed_accurate",
);

const disabilityUnconfirmed = valueFor(
  schedule,
  "nanshan-superior-life-disability",
  {
    face_amount: 1_000_000,
    policy_state: benefitState({
      total_disability_qualification_status: "not_confirmed",
    }),
  },
);
assert.equal(disabilityUnconfirmed.state, "needs_insurer_confirmation");
assert.equal(
  disabilityUnconfirmed.confirmation_reason,
  "total_disability_not_confirmed",
);

const maturity = valueFor(
  schedule,
  "nanshan-superior-life-maturity",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      maturity_policy_account_value: 800_000,
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
    },
  },
);
assert.equal(maturity.state, "conditional_amount");
assert.equal(maturity.value, 680_000);

const valueAdditionCases = [
  [5, 0, 0],
  [6, 1_000_000, 2_000],
  [11, 1_000_000, 3_000],
  [16, 1_000_000, 4_000],
];
for (const [policyYear, averageValue, expected] of valueAdditionCases) {
  const valueAddition = valueFor(
    schedule,
    "nanshan-superior-life-value-addition",
    {
      face_amount: 1_000_000,
      policy_state: {
        policy_effect_status_at_event: "active",
        policy_year: policyYear,
        ...(policyYear >= 6
          ? { average_target_premium_account_value: averageValue }
          : {}),
      },
    },
  );
  assert.equal(valueAddition.state, "value_added_account_credit");
  assert.equal(valueAddition.value, expected);
}

const earlyRequirements = model.policyStateRequirements({
  ...schedule,
  face_amount: 1_000_000,
  policy_state: {
    policy_effect_status_at_event: "active",
    policy_year: 5,
  },
});
assert.equal(
  earlyRequirements.fields.some(
    (field) => field.key === "average_target_premium_account_value",
  ),
  false,
);

const laterRequirements = model.policyStateRequirements({
  ...schedule,
  face_amount: 1_000_000,
  policy_state: {
    policy_effect_status_at_event: "active",
    policy_year: 6,
  },
});
assert.equal(
  laterRequirements.fields.some(
    (field) => field.key === "average_target_premium_account_value",
  ),
  true,
);

const timeBarredRequirements = model.policyStateRequirements({
  ...schedule,
  face_amount: 1_000_000,
  policy_state: {
    policy_effect_status_at_event: "active",
    claim_time_status: "time_barred",
  },
});
for (const omittedKey of [
  "benefit_exclusion_status",
  "insured_age_accuracy_status",
  "total_disability_qualification_status",
  "death_benefit_status",
  "remaining_funeral_benefit_limit",
]) {
  assert.equal(
    timeBarredRequirements.fields.some(
      (field) => field.key === omittedKey,
    ),
    false,
    omittedKey,
  );
}

console.log({
  status: "ok",
  batch_id: "tii-life-035",
  user_flow_cases: 25,
});

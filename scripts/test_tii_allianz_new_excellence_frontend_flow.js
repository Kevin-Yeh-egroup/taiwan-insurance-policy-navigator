const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const legacy = revision <= 6;
  const minorRule = revision >= 20;
  const policyTypes = legacy
    ? ["甲型", "乙型", "丙型"]
    : ["A型", "B型", "C型", ...(revision >= 8 ? ["D型"] : [])];
  const sharedOffsetStateKeys = [
    "policy_effect_status_at_event",
    "policy_loan_and_interest_amount",
    "unpaid_monthly_deduction_amount",
  ];
  const claimEntry = {
    basis: "policy_recorded_limit",
    calculation_basis: "net_amount_at_risk_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    policy_state_keys: [
      "benefit_valuation_policy_account_value",
      ...sharedOffsetStateKeys,
      "claim_time_status",
      "benefit_exclusion_status",
      "post_event_insurance_cost_refund_status",
      "post_event_insurance_cost_refund_amount",
    ],
    ...(minorRule ? { minor_account_value_return_age: 15 } : {}),
  };
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: legacy ? "基本保險金額" : "保險金額",
    plan_options: policyTypes.map((value) => ({ value, label: value })),
    version_characteristics: {
      product_family:
        "allianz-new-excellence-variable-universal-life",
      currency_basis: "twd",
      money_decimal_places: 0,
      money_rounding_rule_available: false,
      fractional_formula_requires_insurer_confirmation: true,
      semantic_phase: legacy
        ? "legacy-annual-insurance-amount-abc"
        : revision === 7
          ? "preservation-multiplier-abc"
          : minorRule
            ? "preservation-multiplier-abcd-minor-account-value-return"
            : "preservation-multiplier-abcd",
      policy_type_options: policyTypes,
      insurance_deduction_amount_policy_type_options: legacy
        ? ["甲型", "丙型"]
        : ["A型", ...(revision >= 8 ? ["D型"] : [])],
      threshold_factor_schedule: legacy
        ? []
        : [
            {
              min_age: minorRule ? 15 : 0,
              max_age: 40,
              factor: 1.3,
            },
            { min_age: 41, max_age: 70, factor: 1.15 },
            { min_age: 71, max_age: 130, factor: 1.01 },
          ],
    },
    coverage_entries: [
      {
        ...claimEntry,
        id: "maturity-benefit",
        name: "祝壽保險金",
        policy_state_keys: [
          "maturity_policy_account_value",
          ...sharedOffsetStateKeys,
        ],
        minor_account_value_return_age: undefined,
      },
      {
        ...claimEntry,
        id: "death-benefit",
        name: "身故保險金",
      },
      {
        ...claimEntry,
        id: "total-disability-benefit",
        name: "全殘廢保險金",
        policy_state_keys: [
          ...claimEntry.policy_state_keys,
          "total_disability_qualification_status",
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

function commonState(overrides = {}) {
  return {
    benefit_valuation_policy_account_value: 120_000,
    maturity_policy_account_value: 120_000,
    policy_effect_status_at_event: "active",
    policy_loan_and_interest_amount: 0,
    unpaid_monthly_deduction_amount: 0,
    post_event_insurance_cost_refund_status: "none",
    post_event_insurance_cost_refund_amount: 0,
    claim_time_status: "within_claim_period",
    benefit_exclusion_status: "none_confirmed",
    total_disability_qualification_status:
      "confirmed_first_level_item",
    ...overrides,
  };
}

const legacy = scheduleFor(5);
for (const [planName, state, expected] of [
  [
    "甲型",
    {
      insurance_deduction_amount: 10_000,
      insured_age_at_issue: 30,
      policy_year: 5,
    },
    120_000,
  ],
  ["乙型", {}, 220_000],
  ["丙型", { insurance_deduction_amount: 10_000 }, 120_000],
]) {
  const result = valueFor(legacy, "death-benefit", {
    face_amount: 100_000,
    plan_name: planName,
    policy_state: commonState(state),
  });
  assert.equal(result.state, "calculated", planName);
  assert.equal(result.value, expected, planName);
  assert.equal(result.currency_label, "元", planName);
  assert.equal(result.product_family,
    "allianz-new-excellence-variable-universal-life");
}

const legacyTableCap = valueFor(legacy, "maturity-benefit", {
  face_amount: 100_000,
  plan_name: "甲型",
  policy_state: commonState({
    maturity_policy_account_value: 0,
    insurance_deduction_amount: 0,
    insured_age_at_issue: 59,
    policy_year: 10,
  }),
});
assert.equal(legacyTableCap.value, 105_000);

const modern = scheduleFor(8);
for (const [planName, state, expected] of [
  [
    "A型",
    { insured_age_at_event: 40, insurance_deduction_amount: 10_000 },
    156_000,
  ],
  ["B型", { insured_age_at_event: 50 }, 220_000],
  ["C型", {}, 220_000],
  ["D型", { insurance_deduction_amount: 10_000 }, 120_000],
]) {
  const result = valueFor(modern, "total-disability-benefit", {
    face_amount: 100_000,
    plan_name: planName,
    policy_state: commonState(state),
  });
  assert.equal(result.state, "calculated", planName);
  assert.equal(result.value, expected, planName);
}

const adjustedForNoticeAndOffsets = valueFor(
  modern,
  "death-benefit",
  {
    face_amount: 100_000,
    plan_name: "A型",
    policy_state: commonState({
      insured_age_at_event: 40,
      insurance_deduction_amount: 0,
      post_event_insurance_cost_refund_status: "charged_after_event",
      post_event_insurance_cost_refund_amount: 10_000,
      policy_loan_and_interest_amount: 5_000,
      unpaid_monthly_deduction_amount: 2_000,
    }),
  },
);
assert.equal(adjustedForNoticeAndOffsets.adjusted_account_value, 130_000);
assert.equal(adjustedForNoticeAndOffsets.gross_insurance_amount, 169_000);
assert.equal(adjustedForNoticeAndOffsets.value, 162_000);

const fractionalMultiplierNeedsConfirmation = valueFor(
  modern,
  "death-benefit",
  {
    face_amount: 100_000,
    plan_name: "A型",
    policy_state: commonState({
      benefit_valuation_policy_account_value: 120_001,
      insured_age_at_event: 40,
      insurance_deduction_amount: 0,
    }),
  },
);
assert.equal(
  fractionalMultiplierNeedsConfirmation.state,
  "needs_insurer_confirmation",
);
assert.equal(
  fractionalMultiplierNeedsConfirmation.confirmation_reason,
  "fractional_policy_amount_rounding_undefined",
);

const fractionalMultiplierLosesToExactBranch = valueFor(
  modern,
  "death-benefit",
  {
    face_amount: 200_000,
    plan_name: "A型",
    policy_state: commonState({
      benefit_valuation_policy_account_value: 120_001,
      insured_age_at_event: 40,
      insurance_deduction_amount: 0,
    }),
  },
);
assert.equal(fractionalMultiplierLosesToExactBranch.state, "calculated");
assert.equal(fractionalMultiplierLosesToExactBranch.value, 200_000);

const timeBarredAccountValueReturn = valueFor(
  modern,
  "death-benefit",
  {
    face_amount: 500_000,
    plan_name: "C型",
    policy_state: commonState({
      benefit_valuation_policy_account_value: 120_000,
      claim_time_status: "time_barred",
      policy_loan_and_interest_amount: 5_000,
      unpaid_monthly_deduction_amount: 2_000,
    }),
  },
);
assert.equal(timeBarredAccountValueReturn.state, "account_value_return");
assert.equal(
  timeBarredAccountValueReturn.formula_type,
  "time_barred_account_value_return",
);
assert.equal(timeBarredAccountValueReturn.value, 113_000);

const exclusionRequiresReview = valueFor(
  modern,
  "death-benefit",
  {
    face_amount: 100_000,
    plan_name: "C型",
    policy_state: commonState({
      benefit_exclusion_status: "may_apply",
    }),
  },
);
assert.equal(exclusionRequiresReview.state, "needs_insurer_confirmation");
assert.equal(
  exclusionRequiresReview.confirmation_reason,
  "benefit_exclusion_requires_review",
);

const disabilityNotConfirmed = valueFor(
  modern,
  "total-disability-benefit",
  {
    face_amount: 100_000,
    plan_name: "C型",
    policy_state: commonState({
      total_disability_qualification_status: "not_confirmed",
    }),
  },
);
assert.equal(disabilityNotConfirmed.state, "needs_insurer_confirmation");
assert.equal(
  disabilityNotConfirmed.confirmation_reason,
  "total_disability_not_confirmed",
);

const fractionalAnnualAmountNeedsConfirmation = valueFor(
  legacy,
  "death-benefit",
  {
    face_amount: 100_001,
    plan_name: "甲型",
    policy_state: commonState({
      benefit_valuation_policy_account_value: 0,
      insurance_deduction_amount: 0,
      insured_age_at_issue: 30,
      policy_year: 2,
    }),
  },
);
assert.equal(
  fractionalAnnualAmountNeedsConfirmation.state,
  "needs_insurer_confirmation",
);
assert.equal(
  fractionalAnnualAmountNeedsConfirmation.confirmation_reason,
  "fractional_policy_amount_rounding_undefined",
);

const minor = valueFor(scheduleFor(20), "death-benefit", {
  face_amount: 1_000_000,
  plan_name: "D型",
  policy_state: commonState({
    insured_age_at_event: 14,
    benefit_valuation_policy_account_value: 200_000,
    post_event_insurance_cost_refund_status: "charged_after_event",
    post_event_insurance_cost_refund_amount: 10_000,
    policy_loan_and_interest_amount: 5_000,
    unpaid_monthly_deduction_amount: 2_000,
  }),
});
assert.equal(minor.state, "account_value_return");
assert.equal(minor.adjusted_account_value, 210_000);
assert.equal(minor.value, 203_000);
assert.equal(
  minor.product_family,
  "allianz-new-excellence-variable-universal-life",
);

const missingLegacyInputs = valueFor(legacy, "death-benefit", {
  face_amount: 100_000,
  plan_name: "甲型",
  policy_state: commonState({
    insurance_deduction_amount: 10_000,
  }),
});
assert.equal(missingLegacyInputs.state, "needs_policy_state");
assert.deepEqual(missingLegacyInputs.required_fields, [
  "insured_age_at_issue",
  "policy_year",
]);

const outsideTableAge = valueFor(legacy, "death-benefit", {
  face_amount: 100_000,
  plan_name: "甲型",
  policy_state: commonState({
    insurance_deduction_amount: 10_000,
    insured_age_at_issue: 13,
    policy_year: 1,
  }),
});
assert.equal(outsideTableAge.state, "outside_terms_formula_age_range");

const decimalAccountValue = valueFor(modern, "death-benefit", {
  face_amount: 100_000,
  plan_name: "C型",
  policy_state: commonState({
    benefit_valuation_policy_account_value: 120_000.5,
  }),
});
assert.equal(decimalAccountValue.state, "needs_account_value");

const decimalFaceAmount = valueFor(modern, "death-benefit", {
  face_amount: 100_000.5,
  plan_name: "C型",
  policy_state: commonState(),
});
assert.equal(decimalFaceAmount.state, "needs_face_amount");

const inactive = valueFor(modern, "death-benefit", {
  face_amount: 100_000,
  plan_name: "C型",
  policy_state: commonState({
    policy_effect_status_at_event: "suspended_or_lapsed",
  }),
});
assert.equal(inactive.state, "needs_insurer_confirmation");
assert.equal(inactive.confirmation_reason, "contract_not_confirmed_active");

const legacyRequirements = model.policyStateRequirements({
  ...legacy,
  face_amount: 100_000,
  plan_name: "甲型",
  policy_state: commonState(),
});
for (const key of [
  "insured_age_at_issue",
  "policy_year",
  "insurance_deduction_amount",
]) {
  assert.equal(
    legacyRequirements.fields.some((field) => field.key === key),
    true,
    key,
  );
}
assert.equal(
  legacyRequirements.fields.some(
    (field) => field.key === "contract_currency",
  ),
  false,
);

const refundStatusOnly = model.policyStateRequirements({
  ...modern,
  face_amount: 100_000,
  plan_name: "C型",
  policy_state: commonState({
    post_event_insurance_cost_refund_status: "",
  }),
});
assert.equal(
  refundStatusOnly.fields.some(
    (field) => field.key === "post_event_insurance_cost_refund_status",
  ),
  true,
);
assert.equal(
  refundStatusOnly.fields.some(
    (field) => field.key === "post_event_insurance_cost_refund_amount",
  ),
  false,
);

console.log({
  status: "ok",
  batch_id: "tii-life-095",
  exact_versions: 26,
  formula_cases: 20,
});

const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const legacy = revision <= 4;
  const minorRule = revision >= 20;
  const policyTypes = legacy
    ? ["A型", "B型"]
    : ["A型", "B型", "C型", "D型"];
  const semanticPhase = legacy
    ? "premium_three_way_ab"
    : minorRule
      ? "four_type_age_bands_minor15_130_115_101"
      : "four_type_age_bands_130_115_101";
  const policyStateKeys = [
    "benefit_valuation_policy_account_value",
    "delayed_notice_policy_fee_refund_amount",
    "policy_loan_and_interest_amount",
    ...(legacy
      ? [
          "paid_premium_total",
          "partial_termination_amount_total",
        ]
      : []),
  ];
  const funeralOptions = legacy
    ? ["B型"]
    : revision <= 19
      ? ["D型"]
      : policyTypes;
  const deathEntry = {
    id: "death-or-funeral-benefit",
    name: "身故保險金或喪葬費用保險金",
    basis: "policy_recorded_limit",
    calculation_basis:
      "net_amount_at_risk_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    unit_key:
      "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
    policy_state_keys: policyStateKeys,
    funeral_limit_plan_options: funeralOptions,
    ...(minorRule
      ? { minor_account_value_return_age: 15 }
      : {}),
  };
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: "基本保額",
    plan_options: policyTypes.map((value) => ({
      value,
      label: value,
    })),
    version_characteristics: {
      product_family:
        "global-new-excellence-variable-universal-life",
      semantic_phase: semanticPhase,
      minimum_rate_formula_variant: legacy
        ? "legacy_110_112_with_withdrawal"
        : semanticPhase,
      minimum_benefit_formula_age: minorRule ? 15 : 0,
      threshold_factor_schedule: legacy
        ? []
        : [
            { min_age: minorRule ? 15 : 0, max_age: 40, factor: 1.3 },
            { min_age: 41, max_age: 70, factor: 1.15 },
            { min_age: 71, max_age: 130, factor: 1.01 },
          ],
      delayed_notice_policy_fee_refund_rule:
        revision <= 16
          ? "add_to_calculated_benefit"
          : "restore_account_value_then_recalculate",
      minor_funeral_precedence_rule: minorRule
        ? "insurer_confirmation_required_when_both_apply"
        : "not_applicable",
    },
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: "一百祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
        policy_state_keys: [
          "policy_loan_and_interest_amount",
        ],
      },
      deathEntry,
      {
        ...deathEntry,
        id: "total-disability-benefit",
        name: "完全殘廢保險金",
        funeral_limit_plan_options: undefined,
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
    benefit_valuation_policy_account_value: 100,
    delayed_notice_policy_fee_refund_amount: 0,
    policy_loan_and_interest_amount: 0,
    ...overrides,
  };
}

const legacySchedule = scheduleFor(4);
const legacyA = valueFor(
  legacySchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 100,
    plan_name: "A型",
    policy_state: commonState({
      paid_premium_total: 1_000,
      partial_termination_amount_total: 100,
    }),
  },
);
assert.equal(legacyA.state, "calculated");
assert.equal(legacyA.value, 1_020);
assert.equal(legacyA.net_amount_at_risk, 920);

const legacyB = valueFor(
  legacySchedule,
  "total-disability-benefit",
  {
    face_amount: 100,
    plan_name: "B型",
    policy_state: commonState({
      paid_premium_total: 101,
      partial_termination_amount_total: 0,
    }),
  },
);
assert.equal(legacyB.value, 200);
assert.equal(legacyB.paid_premium_total, 101);

const modernSchedule = scheduleFor(5);
const exact115 = valueFor(
  modernSchedule,
  "total-disability-benefit",
  {
    face_amount: 1,
    plan_name: "A型",
    policy_state: commonState({
      insured_age_at_event: 41,
    }),
  },
);
assert.equal(exact115.value, 115);
assert.equal(exact115.net_amount_at_risk, 15);

for (const [planName, faceAmount, accountValue, expected] of [
  ["A型", 200, 100, 200],
  ["B型", 20, 100, 130],
  ["C型", 200, 100, 200],
  ["D型", 20, 100, 120],
]) {
  const result = valueFor(
    modernSchedule,
    "total-disability-benefit",
    {
      face_amount: faceAmount,
      plan_name: planName,
      policy_state: commonState({
        benefit_valuation_policy_account_value: accountValue,
        insured_age_at_event: 40,
      }),
    },
  );
  assert.equal(result.value, expected, planName);
}

const directRefund = valueFor(
  scheduleFor(16),
  "total-disability-benefit",
  {
    face_amount: 1,
    plan_name: "A型",
    policy_state: commonState({
      insured_age_at_event: 40,
      delayed_notice_policy_fee_refund_amount: 10,
      policy_loan_and_interest_amount: 3,
    }),
  },
);
assert.equal(directRefund.value, 137);
assert.equal(directRefund.adjusted_account_value, 100);
assert.equal(
  directRefund.delayed_notice_policy_fee_refund_rule,
  "add_to_calculated_benefit",
);

const recalculatedRefund = valueFor(
  scheduleFor(17),
  "total-disability-benefit",
  {
    face_amount: 1,
    plan_name: "A型",
    policy_state: commonState({
      insured_age_at_event: 40,
      delayed_notice_policy_fee_refund_amount: 10,
      policy_loan_and_interest_amount: 3,
    }),
  },
);
assert.equal(recalculatedRefund.value, 140);
assert.equal(recalculatedRefund.adjusted_account_value, 110);
assert.equal(
  recalculatedRefund.delayed_notice_policy_fee_refund_rule,
  "restore_account_value_then_recalculate",
);

const minorSchedule = scheduleFor(20);
const minorReturn = valueFor(
  minorSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000,
    plan_name: "D型",
    policy_state: commonState({
      insured_age_at_event: 14,
      delayed_notice_policy_fee_refund_amount: 10,
      policy_loan_and_interest_amount: 5,
    }),
  },
);
assert.equal(minorReturn.state, "account_value_return");
assert.equal(minorReturn.gross_value_before_loan_offset, 110);
assert.equal(minorReturn.value, 105);
assert.equal(
  minorReturn.minor_funeral_precedence_requires_insurer_confirmation,
  true,
);

const funeralLimited = valueFor(
  minorSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 100,
    plan_name: "D型",
    policy_state: commonState({
      insured_age_at_event: 40,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 20,
      policy_loan_and_interest_amount: 10,
    }),
  },
);
assert.equal(funeralLimited.state, "death_or_funeral_amount");
assert.equal(funeralLimited.gross_value_before_funeral_cap, 200);
assert.equal(funeralLimited.gross_value_before_loan_offset, 120);
assert.equal(funeralLimited.value, 110);

const zeroAfterLoan = valueFor(
  modernSchedule,
  "total-disability-benefit",
  {
    face_amount: 100,
    plan_name: "C型",
    policy_state: commonState({
      policy_loan_and_interest_amount: 500,
    }),
  },
);
assert.equal(zeroAfterLoan.state, "calculated");
assert.equal(zeroAfterLoan.value, 0);

const legacyRequirements = model.policyStateRequirements({
  ...legacySchedule,
  face_amount: 100,
  plan_name: "A型",
});
assert.equal(
  legacyRequirements.fields.some(
    (field) => field.key === "paid_premium_total",
  ),
  true,
);
assert.equal(
  legacyRequirements.fields.some(
    (field) => field.key === "insured_age_at_event",
  ),
  false,
);

for (const [revision, planName, expectedAgeField] of [
  [5, "A型", true],
  [5, "C型", false],
  [20, "D型", true],
]) {
  const schedule = scheduleFor(revision);
  const requirements = model.policyStateRequirements({
    ...schedule,
    face_amount: 100,
    plan_name: planName,
  });
  assert.equal(
    requirements.fields.some(
      (field) => field.key === "insured_age_at_event",
    ),
    expectedAgeField,
    `${revision}/${planName}`,
  );
}

const maturity = valueFor(
  minorSchedule,
  "maturity-benefit",
  {
    policy_state: {
      maturity_policy_account_value: 100,
      policy_loan_and_interest_amount: 20,
      policy_values_converted_to_twd: true,
    },
  },
);
assert.equal(maturity.state, "conditional_amount");
assert.equal(maturity.gross_value_before_loan_offset, 100);
assert.equal(maturity.value, 80);

console.log({
  status: "ok",
  batch_id: "tii-life-167",
  user_flow_cases: 18,
  exact_formula_groups: 3,
});

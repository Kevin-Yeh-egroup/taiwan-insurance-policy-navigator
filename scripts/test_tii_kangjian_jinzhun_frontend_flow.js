const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor({
  semanticPhase,
  funeralLimit = false,
  minorReturn = false,
  insuranceCostRefund = false,
  policyLoanOffset = false,
}) {
  const offsetKeys = [
    "policy_effect_status_at_event",
    "unpaid_policy_charge_amount",
    ...(policyLoanOffset
      ? ["policy_loan_and_interest_amount"]
      : []),
  ];
  const formulaKeys = [
    "benefit_valuation_policy_account_value",
    ...offsetKeys,
    ...(semanticPhase === "legacy_greater_of_basic_or_account"
      ? []
      : ["insured_age_at_event"]),
  ];
  const versionCharacteristics = {
    product_family:
      "kangjian-jinzhun-variable-universal-life",
    semantic_phase: semanticPhase,
    policy_type_options: ["甲型"],
    threshold_factor_schedule:
      semanticPhase === "legacy_greater_of_basic_or_account"
        ? []
        : [
            { min_age: 0, max_age: 40, factor: 1.3 },
            { min_age: 41, max_age: 70, factor: 1.15 },
            { min_age: 71, max_age: 130, factor: 1.01 },
          ],
    unexpired_insurance_cost_refund_rule:
      insuranceCostRefund ? "minor_death_only" : "",
  };
  const commonEntry = {
    basis: "policy_recorded_limit",
    calculation_basis:
      "net_amount_at_risk_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    unit_key:
      "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
    minor_account_value_return_age: minorReturn ? 15 : undefined,
  };
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: "基本保額",
    plan_options: [{ value: "甲型", label: "甲型" }],
    version_characteristics: versionCharacteristics,
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: "滿期保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
        policy_state_keys: [
          "maturity_policy_account_value",
          ...offsetKeys,
        ],
      },
      {
        ...commonEntry,
        id: "death-or-funeral-benefit",
        name: funeralLimit
          ? "身故保險金或喪葬費用保險金"
          : "身故保險金",
        policy_state_keys: [
          ...formulaKeys,
          ...(insuranceCostRefund
            ? ["unexpired_premium_refund_amount"]
            : []),
        ],
        funeral_limit_plan_options: funeralLimit
          ? ["甲型"]
          : [],
      },
      {
        ...commonEntry,
        id: "total-disability-benefit",
        name: "全殘廢保險金",
        policy_state_keys: formulaKeys,
      },
    ],
  };
}

function valueFor(schedule, entryId, selection) {
  const entry = schedule.coverage_entries.find(
    (item) => item.id === entryId,
  );
  return model.coverageValue(entry, {
    ...schedule,
    ...selection,
  });
}

const legacy = scheduleFor({
  semanticPhase: "legacy_greater_of_basic_or_account",
});
const legacyDeath = valueFor(
  legacy,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 1_200_000,
      unpaid_policy_charge_amount: 50_000,
    },
  },
);
assert.equal(legacyDeath.value, 1_150_000);
assert.equal(legacyDeath.state, "calculated");

const ratioWithLoan = scheduleFor({
  semanticPhase: "age_ratio_with_policy_loan",
  policyLoanOffset: true,
});
const age35 = valueFor(
  ratioWithLoan,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 800_000,
      policy_loan_and_interest_amount: 20_000,
      unpaid_policy_charge_amount: 10_000,
    },
  },
);
assert.equal(age35.value, 1_010_000);
assert.equal(age35.threshold_factor, 1.3);
assert.equal(age35.net_amount_at_risk, 240_000);

const age50 = valueFor(
  ratioWithLoan,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      insured_age_at_event: 50,
      benefit_valuation_policy_account_value: 800_000,
      policy_loan_and_interest_amount: 20_000,
      unpaid_policy_charge_amount: 10_000,
    },
  },
);
assert.equal(age50.value, 970_000);
assert.equal(age50.threshold_factor, 1.15);

const funeral = scheduleFor({
  semanticPhase: "age_ratio_funeral_limit",
  funeralLimit: true,
  policyLoanOffset: true,
});
const funeralLimited = valueFor(
  funeral,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 800_000,
      policy_loan_and_interest_amount: 20_000,
      unpaid_policy_charge_amount: 10_000,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 100_000,
    },
  },
);
assert.equal(funeralLimited.value, 870_000);
assert.equal(funeralLimited.gross_value_before_funeral_cap, 1_040_000);
assert.equal(funeralLimited.capped_protected_amount, 100_000);

const minor = scheduleFor({
  semanticPhase: "minor_return_death_to_next_policy_month",
  funeralLimit: true,
  minorReturn: true,
  insuranceCostRefund: true,
  policyLoanOffset: true,
});
const minorDeath = valueFor(
  minor,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      insured_age_at_event: 14,
      benefit_valuation_policy_account_value: 600_000,
      unexpired_premium_refund_amount: 50_000,
      policy_loan_and_interest_amount: 20_000,
      unpaid_policy_charge_amount: 10_000,
    },
  },
);
assert.equal(minorDeath.value, 620_000);
assert.equal(minorDeath.state, "account_value_return");
assert.equal(
  minorDeath.unexpired_insurance_cost_refund_amount,
  50_000,
);

const minorDisability = valueFor(
  minor,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      insured_age_at_event: 14,
      benefit_valuation_policy_account_value: 600_000,
      policy_loan_and_interest_amount: 20_000,
      unpaid_policy_charge_amount: 10_000,
    },
  },
);
assert.equal(minorDisability.value, 570_000);
assert.equal(minorDisability.state, "account_value_return");

const maturity = valueFor(minor, "maturity-benefit", {
  plan_name: "甲型",
  policy_state: {
    policy_effect_status_at_event: "active",
    maturity_policy_account_value: 900_000,
    policy_loan_and_interest_amount: 20_000,
    unpaid_policy_charge_amount: 10_000,
  },
});
assert.equal(maturity.value, 870_000);
assert.equal(maturity.state, "conditional_amount");

const inactive = valueFor(
  minor,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "suspended_or_lapsed",
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 600_000,
      policy_loan_and_interest_amount: 0,
      unpaid_policy_charge_amount: 0,
    },
  },
);
assert.equal(inactive.state, "needs_insurer_confirmation");
assert.equal(
  inactive.confirmation_reason,
  "contract_not_confirmed_active",
);

const missing = valueFor(
  ratioWithLoan,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_effect_status_at_event: "active",
      insured_age_at_event: 35,
    },
  },
);
assert.equal(missing.state, "needs_policy_state");
assert(missing.required_fields.includes(
  "benefit_valuation_policy_account_value",
));

const visibleMinorFields =
  model.policyStateFieldsForEntry(
    minor.coverage_entries[1],
    {
      ...minor,
      face_amount: 1_000_000,
      plan_name: "甲型",
      policy_state: { insured_age_at_event: 14 },
    },
  );
assert(visibleMinorFields.some(
  (field) => field.key === "unexpired_premium_refund_amount",
));
assert(!visibleMinorFields.some(
  (field) => field.key === "death_benefit_status",
));

console.log({
  status: "ok",
  batch_id: "tii-life-137",
  user_flow_cases: 10,
  exact_formula_groups: 6,
});

const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(schedule, entryId, selection) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    ...selection,
  });
}

function scheduleFor({ minorRule = false, maturityInterest = false } = {}) {
  const accountEntry = {
    basis: "policy_recorded_limit",
    calculation_basis:
      "net_amount_at_risk_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    policy_state_keys: [
      "benefit_valuation_policy_account_value",
    ],
  };
  if (minorRule) accountEntry.minor_account_value_return_age = 15;
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: "當年度保險金額",
    plan_options: [
      { value: "甲型", label: "甲型" },
      { value: "乙型", label: "乙型" },
      { value: "丙型", label: "丙型" },
    ],
    version_characteristics: {
      product_family:
        "farglory-ginjili-variable-universal-life",
      insurance_deduction_amount_policy_type_options: [
        "甲型",
        "丙型",
      ],
      maturity_interest_applies: maturityInterest,
    },
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: "祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis:
          "net_amount_at_risk_plus_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key:
          "net_amount_at_risk_plus_maturity_policy_account_value",
        policy_state_keys: ["maturity_policy_account_value"],
      },
      {
        ...accountEntry,
        id: "death-or-funeral-benefit",
        name: "身故保險金或喪葬費用保險金",
        unit_key:
          "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
        funeral_limit_plan_options: ["乙型"],
      },
      {
        ...accountEntry,
        id: "total-disability-benefit",
        name: "完全失能保險金",
        unit_key:
          "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
      },
    ],
  };
}

const adultSchedule = scheduleFor();
const basePolicyState = {
  insured_age_at_event: 35,
  benefit_valuation_policy_account_value: 600_000,
};

for (const [planName, expectedValue, expectedNetRisk] of [
  ["甲型", 900_000, 300_000],
  ["乙型", 1_600_000, 1_000_000],
  ["丙型", 900_000, 300_000],
]) {
  const result = valueFor(
    adultSchedule,
    "total-disability-benefit",
    {
      face_amount: 1_000_000,
      plan_name: planName,
      policy_state: {
        ...basePolicyState,
        ...(["甲型", "丙型"].includes(planName)
          ? { insurance_deduction_amount: 100_000 }
          : {}),
      },
    },
  );
  assert.equal(result.value, expectedValue);
  assert.equal(result.net_amount_at_risk, expectedNetRisk);
  assert.equal(result.state, "calculated");
}

const typeBFuneral = valueFor(
  adultSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      ...basePolicyState,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 400_000,
    },
  },
);
assert.equal(typeBFuneral.value, 1_000_000);
assert.equal(typeBFuneral.gross_value_before_funeral_cap, 1_600_000);
assert.equal(typeBFuneral.protected_amount, 1_000_000);
assert.equal(typeBFuneral.capped_protected_amount, 400_000);
assert.equal(typeBFuneral.account_value, 600_000);

const typeADeath = valueFor(
  adultSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      ...basePolicyState,
      insurance_deduction_amount: 100_000,
    },
  },
);
assert.equal(typeADeath.value, 900_000);
assert.equal(typeADeath.state, "calculated");
assert.equal(
  model
    .policyStateFieldsForEntry(
      entriesFor(adultSchedule)["death-or-funeral-benefit"],
      {
        ...adultSchedule,
        face_amount: 1_000_000,
        plan_name: "甲型",
        policy_state: {
          ...basePolicyState,
          insurance_deduction_amount: 100_000,
        },
      },
    )
    .some((field) => field.key === "death_benefit_status"),
  false,
);

const minorSchedule = scheduleFor({ minorRule: true });
for (const entryId of [
  "death-or-funeral-benefit",
  "total-disability-benefit",
]) {
  const minor = valueFor(minorSchedule, entryId, {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      insured_age_at_event: 14,
      benefit_valuation_policy_account_value: 600_000,
    },
  });
  assert.equal(minor.value, 600_000);
  assert.equal(minor.state, "account_value_return");
}

const postMinorRule = valueFor(
  adultSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      benefit_valuation_policy_account_value: 600_000,
    },
  },
);
assert.equal(postMinorRule.value, 1_600_000);
assert.equal(postMinorRule.state, "calculated");

const maturity = valueFor(adultSchedule, "maturity-benefit", {
  face_amount: 1_000_000,
  plan_name: "甲型",
  policy_state: {
    maturity_policy_account_value: 600_000,
    insurance_deduction_amount: 100_000,
  },
});
assert.equal(maturity.value, 900_000);
assert.equal(maturity.net_amount_at_risk, 300_000);

const zeroAccount = valueFor(
  adultSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 0,
      insurance_deduction_amount: 100_000,
    },
  },
);
assert.equal(zeroAccount.value, 900_000);
assert.equal(zeroAccount.account_value, 0);

const missingDeduction = valueFor(
  adultSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "丙型",
    policy_state: basePolicyState,
  },
);
assert.equal(missingDeduction.state, "needs_policy_state");
assert.deepEqual(missingDeduction.required_fields, [
  "insurance_deduction_amount",
]);

for (const [planName, deductionExpected] of [
  ["甲型", true],
  ["乙型", false],
  ["丙型", true],
]) {
  const { fields } = model.policyStateRequirements({
    ...adultSchedule,
    face_amount: 1_000_000,
    plan_name: planName,
    policy_state: basePolicyState,
  });
  assert.equal(
    fields.some((field) => field.key === "insurance_deduction_amount"),
    deductionExpected,
  );
}

console.log({
  status: "ok",
  batch_id: "tii-life-083",
  user_flow_cases: 15,
  exact_formula_groups: 5,
});

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

function scheduleFor({
  oldDirectFormula,
  disabilityTerm,
  funeralLimitPlanOptions,
}) {
  const accountValueEntry = {
    basis: "policy_recorded_limit",
    calculation_basis:
      "net_amount_at_risk_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    unit_key:
      "net_amount_at_risk_plus_benefit_valuation_policy_account_value",
    policy_state_keys: [
      "benefit_valuation_policy_account_value",
    ],
    minor_account_value_return_age: 15,
  };
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: oldDirectFormula
      ? "保單所載保險金額"
      : "基本保額",
    plan_options: [
      { value: "A型", label: "A型" },
      { value: "B型", label: "B型" },
    ],
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: "祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
      },
      {
        ...accountValueEntry,
        id: "death-or-funeral-benefit",
        name: "身故保險金或喪葬費用保險金",
        funeral_limit_plan_options: funeralLimitPlanOptions,
      },
      {
        ...accountValueEntry,
        id: "total-disability-benefit",
        name: `${disabilityTerm}保險金`,
      },
    ],
  };
}

const oldSchedule = scheduleFor({
  oldDirectFormula: true,
  disabilityTerm: "全殘廢",
  funeralLimitPlanOptions: ["B型"],
});
const oldAState = {
  face_amount: 1_000_000,
  plan_name: "A型",
  policy_state: {
    insured_age_at_event: 35,
    benefit_valuation_policy_account_value: 1_200_000,
  },
};
const oldADeath = valueFor(
  oldSchedule,
  "death-or-funeral-benefit",
  oldAState,
);
assert.equal(oldADeath.value, 1_200_000);
assert.equal(oldADeath.state, "calculated");
assert.equal(oldADeath.net_amount_at_risk, 0);
assert.equal(
  model
    .policyStateFieldsForEntry(
      entriesFor(oldSchedule)["death-or-funeral-benefit"],
      oldAState,
    )
    .some((field) => field.key === "death_benefit_status"),
  false,
);

const oldBStandardState = {
  face_amount: 1_000_000,
  plan_name: "B型",
  policy_state: {
    insured_age_at_event: 35,
    benefit_valuation_policy_account_value: 800_000,
    death_benefit_status: "standard_death",
  },
};
const oldBDeath = valueFor(
  oldSchedule,
  "death-or-funeral-benefit",
  oldBStandardState,
);
assert.equal(oldBDeath.value, 1_800_000);
assert.equal(oldBDeath.state, "death_or_funeral_amount");

const oldBFuneral = valueFor(
  oldSchedule,
  "death-or-funeral-benefit",
  {
    ...oldBStandardState,
    policy_state: {
      ...oldBStandardState.policy_state,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 300_000,
    },
  },
);
assert.equal(oldBFuneral.value, 1_100_000);
assert.equal(oldBFuneral.gross_value_before_funeral_cap, 1_800_000);
assert.equal(oldBFuneral.protected_amount, 1_000_000);
assert.equal(oldBFuneral.capped_protected_amount, 300_000);
assert.equal(oldBFuneral.account_value, 800_000);

const newSchedule = scheduleFor({
  oldDirectFormula: false,
  disabilityTerm: "完全失能",
  funeralLimitPlanOptions: ["A型", "B型"],
});
const newAFuneral = valueFor(
  newSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "A型",
    policy_state: {
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 600_000,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 250_000,
    },
  },
);
assert.equal(newAFuneral.value, 850_000);
assert.equal(newAFuneral.net_amount_at_risk, 400_000);
assert.equal(newAFuneral.capped_protected_amount, 250_000);

const newBDisability = valueFor(
  newSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: {
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 600_000,
    },
  },
);
assert.equal(newBDisability.value, 1_600_000);
assert.equal(newBDisability.state, "calculated");

for (const entryId of [
  "death-or-funeral-benefit",
  "total-disability-benefit",
]) {
  const minor = valueFor(newSchedule, entryId, {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: {
      insured_age_at_event: 14,
      benefit_valuation_policy_account_value: 600_000,
    },
  });
  assert.equal(minor.value, 600_000);
  assert.equal(minor.state, "account_value_return");
  assert.equal(
    minor.policy_state_key,
    "benefit_valuation_policy_account_value",
  );
}

const missingAccount = valueFor(
  newSchedule,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "A型",
    policy_state: { insured_age_at_event: 35 },
  },
);
assert.equal(missingAccount.state, "needs_policy_state");
assert.deepEqual(missingAccount.required_fields, [
  "benefit_valuation_policy_account_value",
]);

const maturity = valueFor(newSchedule, "maturity-benefit", {
  policy_state: {
    maturity_policy_account_value: 925_000,
    policy_values_converted_to_twd: true,
  },
});
assert.equal(maturity.value, 925_000);
assert.equal(maturity.state, "conditional_amount");

console.log({
  status: "ok",
  batch_id: "tii-life-053",
  user_flow_cases: 16,
  exact_formula_groups: 3,
});

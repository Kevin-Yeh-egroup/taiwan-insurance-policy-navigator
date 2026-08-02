const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor({
  refundRule,
  maturityInterest = false,
} = {}) {
  const payoutEntry = {
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
      "unexpired_premium_refund_amount",
    ],
  };
  return {
    selection_type: "face_amount_plan",
    input_mode: "face_amount_plan",
    face_amount_label: "基本保額",
    plan_options: [
      { value: "甲型", label: "甲型" },
      { value: "乙型", label: "乙型" },
    ],
    version_characteristics: {
      product_family:
        "hongtai-hongyuan-variable-universal-life",
      unexpired_insurance_cost_refund_rule: refundRule,
      maturity_interest_applies: maturityInterest,
    },
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: "滿期保險金",
        basis: "policy_recorded_limit",
        calculation_basis: maturityInterest
          ? "sum_policy_state_amounts"
          : "policy_state_amount",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
        policy_state_keys: maturityInterest
          ? [
              "maturity_policy_account_value",
              "maturity_interest_amount",
            ]
          : ["maturity_policy_account_value"],
      },
      {
        ...payoutEntry,
        id: "death-or-funeral-benefit",
        name: "身故保險金或喪葬費用保險金",
        funeral_limit_plan_options: ["乙型"],
      },
      {
        ...payoutEntry,
        id: "disability-benefit",
        name: "完全失能保險金",
      },
    ],
  };
}

function entryFor(schedule, entryId) {
  return schedule.coverage_entries.find((entry) => entry.id === entryId);
}

function valueFor(schedule, entryId, selection) {
  return model.coverageValue(entryFor(schedule, entryId), {
    ...schedule,
    ...selection,
  });
}

const legacySchedule = scheduleFor({
  refundRule:
    "type_a_when_account_value_exceeds_face_amount_type_b_always",
});
const legacyTypeABelowFace = valueFor(
  legacySchedule,
  "disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 600_000,
    },
  },
);
assert.equal(legacyTypeABelowFace.value, 1_000_000);
assert.equal(legacyTypeABelowFace.net_amount_at_risk, 400_000);
assert.equal(
  legacyTypeABelowFace.unexpired_insurance_cost_refund_applies,
  false,
);

const legacyTypeAAboveFaceMissingRefund = valueFor(
  legacySchedule,
  "disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 1_200_000,
    },
  },
);
assert.equal(
  legacyTypeAAboveFaceMissingRefund.state,
  "needs_policy_state",
);
assert.deepEqual(
  legacyTypeAAboveFaceMissingRefund.required_fields,
  ["unexpired_premium_refund_amount"],
);

const legacyTypeAAboveFace = valueFor(
  legacySchedule,
  "disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 1_200_000,
      unexpired_premium_refund_amount: 20_000,
    },
  },
);
assert.equal(legacyTypeAAboveFace.value, 1_220_000);
assert.equal(legacyTypeAAboveFace.net_amount_at_risk, 0);

const legacyTypeB = valueFor(
  legacySchedule,
  "disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      benefit_valuation_policy_account_value: 600_000,
      unexpired_premium_refund_amount: 20_000,
    },
  },
);
assert.equal(legacyTypeB.value, 1_620_000);
assert.equal(legacyTypeB.net_amount_at_risk, 1_000_000);

const modernSchedule = scheduleFor({ refundRule: "always" });
const modernTypeA = valueFor(
  modernSchedule,
  "disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 600_000,
      unexpired_premium_refund_amount: 20_000,
    },
  },
);
assert.equal(modernTypeA.value, 1_020_000);
assert.equal(modernTypeA.net_amount_at_risk, 400_000);

const modernTypeB = valueFor(
  modernSchedule,
  "disability-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      benefit_valuation_policy_account_value: 600_000,
      unexpired_premium_refund_amount: 20_000,
    },
  },
);
assert.equal(modernTypeB.value, 1_620_000);

const funeralLimited = valueFor(
  modernSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      benefit_valuation_policy_account_value: 600_000,
      unexpired_premium_refund_amount: 20_000,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 400_000,
    },
  },
);
assert.equal(funeralLimited.gross_value_before_funeral_cap, 1_620_000);
assert.equal(funeralLimited.protected_amount, 1_020_000);
assert.equal(funeralLimited.capped_protected_amount, 400_000);
assert.equal(funeralLimited.account_value, 600_000);
assert.equal(funeralLimited.value, 1_000_000);

const maturity = valueFor(
  legacySchedule,
  "maturity-benefit",
  {
    policy_state: {
      maturity_policy_account_value: 700_000,
    },
  },
);
assert.equal(maturity.value, 700_000);

const maturityInterestSchedule = scheduleFor({
  refundRule: "always",
  maturityInterest: true,
});
const maturityWithInterest = valueFor(
  maturityInterestSchedule,
  "maturity-benefit",
  {
    policy_state: {
      maturity_policy_account_value: 700_000,
      maturity_interest_amount: 5_000,
    },
  },
);
assert.equal(maturityWithInterest.value, 705_000);

for (const [schedule, planName, accountValue, refundExpected] of [
  [legacySchedule, "甲型", 600_000, false],
  [legacySchedule, "甲型", 1_200_000, true],
  [legacySchedule, "乙型", 600_000, true],
  [modernSchedule, "甲型", 600_000, true],
]) {
  const { fields } = model.policyStateRequirements({
    ...schedule,
    face_amount: 1_000_000,
    plan_name: planName,
    policy_state: {
      benefit_valuation_policy_account_value: accountValue,
    },
  });
  assert.equal(
    fields.some(
      (field) =>
        field.key === "unexpired_premium_refund_amount",
    ),
    refundExpected,
  );
}

console.log({
  status: "ok",
  batch_id: "tii-life-089",
  user_flow_cases: 12,
  exact_formula_groups: 7,
});

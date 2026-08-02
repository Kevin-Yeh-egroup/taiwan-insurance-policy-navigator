const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const includesPendingPremium = revision <= 17;
  const includesCharges = revision >= 18;
  const includesMinor = revision >= 9 && revision <= 24;
  const includesMaturityInterest = revision === 26;
  const commonKeys = [
    "policy_effect_status_at_event",
    "benefit_valuation_policy_account_value",
    "policy_values_converted_to_twd",
    ...(includesPendingPremium ? ["investment_allocation_status"] : []),
    "policy_loan_and_interest_amount",
    ...(includesCharges ? ["unpaid_policy_charge_amount"] : []),
    ...(includesMinor ? ["insured_age_at_event"] : []),
  ];
  const benefitEntry = {
    basis: "policy_recorded_limit",
    calculation_basis: "protected_amount_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_event",
    aggregation_rule: "separate",
    unit_key:
      "protected_amount_plus_benefit_valuation_policy_account_value",
    policy_state_keys: commonKeys,
    ...(includesMinor ? { minor_account_value_return_age: 15 } : {}),
  };
  return {
    selection_type: "face_amount",
    input_mode: "face_amount",
    face_amount_label: revision <= 17 ? "基本保險金額" : "基本保額",
    version_characteristics: {
      product_family: "nanshan-zhifu-yisheng-variable-life",
      semantic_phase: `revision-${revision}`,
    },
    coverage_entries: [
      {
        id: "nanshan-zhifu-yisheng-maturity",
        name: revision <= 17 ? "滿期保險金" : "祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_event",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
        policy_state_keys: [
          "policy_effect_status_at_event",
          "policy_loan_and_interest_amount",
          ...(includesCharges ? ["unpaid_policy_charge_amount"] : []),
          ...(includesMaturityInterest ? ["maturity_interest_amount"] : []),
        ],
      },
      {
        ...benefitEntry,
        id: "nanshan-zhifu-yisheng-death",
        name: "身故保險金或喪葬費用保險金",
        policy_state_keys: [...commonKeys, "death_benefit_status"],
      },
      {
        ...benefitEntry,
        id: "nanshan-zhifu-yisheng-disability",
        name:
          revision <= 17
            ? "殘廢保險金"
            : revision <= 20
              ? "完全殘廢保險金"
              : "完全失能保險金",
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

function policyState(overrides = {}) {
  return {
    policy_effect_status_at_event: "active",
    benefit_valuation_policy_account_value: 300_000,
    policy_values_converted_to_twd: true,
    investment_allocation_status: "allocated",
    policy_loan_and_interest_amount: 0,
    ...overrides,
  };
}

const revision0 = scheduleFor(0);
const standard = valueFor(
  revision0,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState(),
  },
);
assert.equal(standard.state, "calculated");
assert.equal(standard.value, 1_300_000);

const pendingPremium = valueFor(
  revision0,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
    }),
  },
);
assert.equal(pendingPremium.value, 1_350_000);
assert.equal(pendingPremium.unallocated_net_premium_amount, 50_000);

const oldFuneralLimited = valueFor(
  revision0,
  "nanshan-zhifu-yisheng-death",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 200_000,
    }),
  },
);
assert.equal(oldFuneralLimited.state, "death_or_funeral_amount");
assert.equal(oldFuneralLimited.protected_amount, 200_000);
assert.equal(oldFuneralLimited.value, 500_000);

const revision9 = scheduleFor(9);
const minorDeath = valueFor(
  revision9,
  "nanshan-zhifu-yisheng-death",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
      policy_loan_and_interest_amount: 10_000,
      insured_age_at_event: 14,
    }),
  },
);
assert.equal(minorDeath.state, "account_value_return");
assert.equal(minorDeath.protected_amount, 0);
assert.equal(minorDeath.value, 340_000);

const minorDisability = valueFor(
  revision9,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      insured_age_at_event: 14,
    }),
  },
);
assert.equal(minorDisability.state, "account_value_return");
assert.equal(minorDisability.value, 300_000);

const revision18 = scheduleFor(18);
const modernOffsets = valueFor(
  revision18,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      insured_age_at_event: 40,
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
    }),
  },
);
assert.equal(modernOffsets.state, "calculated");
assert.equal(modernOffsets.value, 1_180_000);

const revision25 = scheduleFor(25);
const revision25Requirements = model.policyStateRequirements({
  ...revision25,
  face_amount: 1_000_000,
  policy_state: policyState({
    unpaid_policy_charge_amount: 0,
    death_benefit_status: "standard_death",
  }),
});
assert.equal(
  revision25Requirements.fields.some(
    (field) => field.key === "insured_age_at_event",
  ),
  false,
);

const revision26 = scheduleFor(26);
const maturity = valueFor(
  revision26,
  "nanshan-zhifu-yisheng-maturity",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      policy_values_converted_to_twd: true,
      maturity_policy_account_value: 800_000,
      maturity_interest_amount: 10_000,
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
    },
  },
);
assert.equal(maturity.state, "conditional_amount");
assert.equal(maturity.gross_value_before_offsets, 810_000);
assert.equal(maturity.value, 690_000);

const missingPendingPremium = valueFor(
  revision0,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      investment_allocation_status: "awaiting_allocation",
    }),
  },
);
assert.equal(missingPendingPremium.state, "needs_policy_state");
assert.deepEqual(missingPendingPremium.required_fields, [
  "unallocated_net_premium_amount",
]);

const missingTwdConfirmation = valueFor(
  revision18,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      policy_values_converted_to_twd: false,
      insured_age_at_event: 40,
      unpaid_policy_charge_amount: 0,
    }),
  },
);
assert.equal(missingTwdConfirmation.state, "needs_policy_state");
assert.deepEqual(missingTwdConfirmation.required_fields, [
  "policy_values_converted_to_twd",
]);

const inactiveContract = valueFor(
  revision26,
  "nanshan-zhifu-yisheng-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      policy_effect_status_at_event: "suspended_or_lapsed",
      unpaid_policy_charge_amount: 0,
    }),
  },
);
assert.equal(inactiveContract.state, "needs_insurer_confirmation");
assert.equal(
  inactiveContract.confirmation_reason,
  "contract_not_confirmed_active",
);

console.log({
  status: "ok",
  batch_id: "tii-life-035",
  user_flow_cases: 11,
});

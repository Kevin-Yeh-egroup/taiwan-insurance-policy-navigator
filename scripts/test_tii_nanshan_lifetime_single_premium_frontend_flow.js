const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const includesPendingPremium = revision <= 26;
  const includesLoan = revision >= 10;
  const includesCharges = revision >= 27;
  const includesFuneral = (revision >= 2 && revision <= 13) || revision >= 19;
  const includesMinor = revision >= 19 && revision <= 32;
  const includesMaturityInterest = revision === 34;
  const commonKeys = [
    "policy_effect_status_at_event",
    "benefit_valuation_policy_account_value",
    "policy_values_converted_to_twd",
    ...(includesPendingPremium ? ["investment_allocation_status"] : []),
    ...(includesLoan ? ["policy_loan_and_interest_amount"] : []),
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
    face_amount_label: revision <= 26 ? "基本保險金額" : "基本保額",
    version_characteristics: {
      product_family:
        "nanshan-lifetime-single-premium-variable-life",
      semantic_phase: `revision-${revision}`,
    },
    coverage_entries: [
      {
        id: "nanshan-lifetime-maturity",
        name: revision <= 26 ? "滿期保險金" : "祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_event",
        aggregation_rule: "separate",
        unit_key: "maturity_policy_account_value",
        policy_state_keys: [
          "policy_effect_status_at_event",
          ...(includesLoan ? ["policy_loan_and_interest_amount"] : []),
          ...(includesCharges ? ["unpaid_policy_charge_amount"] : []),
          ...(includesMaturityInterest ? ["maturity_interest_amount"] : []),
        ],
      },
      {
        ...benefitEntry,
        id: "nanshan-lifetime-death",
        name: includesFuneral
          ? "身故保險金或喪葬費用保險金"
          : "身故保險金",
        policy_state_keys: [
          ...commonKeys,
          ...(includesFuneral ? ["death_benefit_status"] : []),
        ],
      },
      {
        ...benefitEntry,
        id: "nanshan-lifetime-disability",
        name: revision >= 30 ? "完全失能保險金" : "殘廢保險金",
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
    ...overrides,
  };
}

const revision0 = scheduleFor(0);
const standard = valueFor(
  revision0,
  "nanshan-lifetime-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState(),
  },
);
assert.equal(standard.state, "calculated");
assert.equal(standard.value, 1_300_000);
assert.equal(standard.protected_amount, 1_000_000);

const pendingPremium = valueFor(
  revision0,
  "nanshan-lifetime-disability",
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

const missingPendingPremium = valueFor(
  revision0,
  "nanshan-lifetime-disability",
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

const revision2 = scheduleFor(2);
const funeralLimited = valueFor(
  revision2,
  "nanshan-lifetime-death",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 200_000,
    }),
  },
);
assert.equal(funeralLimited.state, "death_or_funeral_amount");
assert.equal(funeralLimited.protected_amount, 200_000);
assert.equal(funeralLimited.value, 550_000);
assert.equal(
  funeralLimited.gross_value_before_funeral_cap,
  1_350_000,
);

const revision19 = scheduleFor(19);
const minorReturn = valueFor(
  revision19,
  "nanshan-lifetime-death",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      investment_allocation_status: "awaiting_allocation",
      unallocated_net_premium_amount: 50_000,
      policy_loan_and_interest_amount: 10_000,
      insured_age_at_event: 14,
      death_benefit_status: "funeral_limited",
    }),
  },
);
assert.equal(minorReturn.state, "account_value_return");
assert.equal(minorReturn.protected_amount, 0);
assert.equal(minorReturn.value, 340_000);

const revision14 = scheduleFor(14);
const revision14Requirements = model.policyStateRequirements({
  ...revision14,
  face_amount: 1_000_000,
  policy_state: policyState({
    policy_loan_and_interest_amount: 0,
  }),
});
assert.equal(
  revision14Requirements.fields.some(
    (field) => field.key === "death_benefit_status",
  ),
  false,
);

const revision27 = scheduleFor(27);
const modernOffsets = valueFor(
  revision27,
  "nanshan-lifetime-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
      insured_age_at_event: 40,
    }),
  },
);
assert.equal(modernOffsets.state, "calculated");
assert.equal(modernOffsets.value, 1_180_000);

const revision33 = scheduleFor(33);
const revision33Requirements = model.policyStateRequirements({
  ...revision33,
  face_amount: 1_000_000,
  policy_state: policyState({
    policy_loan_and_interest_amount: 0,
    unpaid_policy_charge_amount: 0,
    death_benefit_status: "standard_death",
  }),
});
assert.equal(
  revision33Requirements.fields.some(
    (field) => field.key === "insured_age_at_event",
  ),
  false,
);

const revision34 = scheduleFor(34);
const maturity = valueFor(
  revision34,
  "nanshan-lifetime-maturity",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      maturity_policy_account_value: 800_000,
      maturity_interest_amount: 10_000,
      policy_loan_and_interest_amount: 100_000,
      unpaid_policy_charge_amount: 20_000,
      policy_values_converted_to_twd: true,
    },
  },
);
assert.equal(maturity.state, "conditional_amount");
assert.equal(maturity.gross_value_before_offsets, 810_000);
assert.equal(maturity.value, 690_000);

const inactiveContract = valueFor(
  revision34,
  "nanshan-lifetime-disability",
  {
    face_amount: 1_000_000,
    policy_state: policyState({
      policy_effect_status_at_event: "suspended_or_lapsed",
      policy_loan_and_interest_amount: 0,
      unpaid_policy_charge_amount: 0,
    }),
  },
);
assert.equal(inactiveContract.state, "needs_insurer_confirmation");
assert.equal(
  inactiveContract.confirmation_reason,
  "contract_not_confirmed_active",
);

const excessiveOffsets = valueFor(
  revision34,
  "nanshan-lifetime-disability",
  {
    face_amount: 100_000,
    policy_state: policyState({
      benefit_valuation_policy_account_value: 0,
      policy_loan_and_interest_amount: 90_000,
      unpaid_policy_charge_amount: 20_000,
    }),
  },
);
assert.equal(excessiveOffsets.state, "needs_insurer_confirmation");
assert.equal(
  excessiveOffsets.confirmation_reason,
  "offsets_exceed_gross_benefit",
);

const allocatedRequirements = model.policyStateRequirements({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: policyState(),
});
assert.equal(
  allocatedRequirements.fields.some(
    (field) => field.key === "unallocated_net_premium_amount",
  ),
  false,
);
const awaitingRequirements = model.policyStateRequirements({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: policyState({
    investment_allocation_status: "awaiting_allocation",
  }),
});
assert.equal(
  awaitingRequirements.fields.some(
    (field) => field.key === "unallocated_net_premium_amount",
  ),
  true,
);

console.log({
  status: "ok",
  batch_id: "tii-life-035",
  user_flow_cases: 11,
  conditional_field_cases: 2,
});

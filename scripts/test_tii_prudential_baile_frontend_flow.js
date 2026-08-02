const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function scheduleFor(revision) {
  const basicAccountOnly = revision <= 4;
  const includesLoan = revision >= 8;
  const includesMinor = revision >= 10;
  const accountKey = basicAccountOnly
    ? "benefit_valuation_basic_premium_policy_account_value"
    : "benefit_valuation_policy_account_value";
  const maturityAccountKey = basicAccountOnly
    ? "maturity_basic_premium_policy_account_value"
    : "maturity_policy_account_value";
  const offsetKeys = [
    "policy_effect_status_at_event",
    ...(includesLoan ? ["policy_loan_and_interest_amount"] : []),
    "unpaid_policy_charge_amount",
  ];
  const commonKeys = [
    "policy_effect_status_at_event",
    accountKey,
    "post_event_insurance_cost_refund_amount",
    ...(includesLoan ? ["policy_loan_and_interest_amount"] : []),
    "unpaid_policy_charge_amount",
  ];
  const benefitEntry = {
    basis: "policy_recorded_limit",
    calculation_basis: "protected_amount_plus_policy_account_value",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    unit_key: `face_amount_plus_${accountKey}`,
    policy_state_keys: commonKeys,
    ...(includesMinor ? { minor_account_value_return_age: 15 } : {}),
  };
  return {
    selection_type: "face_amount",
    input_mode: "face_amount",
    face_amount_label: revision <= 25 ? "保險金額" : "基本保額",
    version_characteristics: {
      product_family: "prudential-baile-variable-life",
      terms_revision_number: revision,
    },
    coverage_entries: [
      {
        id: "maturity-benefit",
        name: revision <= 25 ? "滿期保險金" : "祝壽保險金",
        basis: "policy_recorded_limit",
        calculation_basis: "maturity_policy_account_value",
        amount_role: "payout",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: maturityAccountKey,
        policy_state_keys: [maturityAccountKey, ...offsetKeys],
      },
      {
        ...benefitEntry,
        id: "death-or-funeral-benefit",
        name: "身故保險金／喪葬費用保險金",
        policy_state_keys: [
          ...commonKeys,
          "death_benefit_status",
        ],
      },
      {
        ...benefitEntry,
        id: "total-disability-benefit",
        name: "完全殘廢保險金",
      },
      {
        id: "disability-premium-waiver",
        name: "二至六級殘廢豁免保險費",
        basis: "policy_premium",
        calculation_basis: "waiver",
        amount_role: "premium_waiver",
        limit_scope: "per_policy",
        aggregation_rule: "separate",
        unit_key: "remaining_premium_amount",
        policy_state_keys: ["remaining_premium_amount"],
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

const revision0 = scheduleFor(0);
const earlyDisability = valueFor(
  revision0,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_basic_premium_policy_account_value: 200_000,
      post_event_insurance_cost_refund_amount: 5_000,
      unpaid_policy_charge_amount: 10_000,
    },
  },
);
assert.equal(earlyDisability.state, "calculated");
assert.equal(earlyDisability.value, 1_195_000);
assert.equal(
  earlyDisability.policy_state_key,
  "benefit_valuation_basic_premium_policy_account_value",
);

const earlyRequirements = model.policyStateRequirements({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: {},
});
assert.equal(
  earlyRequirements.fields.some(
    (field) =>
      field.key ===
      "benefit_valuation_basic_premium_policy_account_value",
  ),
  true,
);
assert.equal(
  earlyRequirements.fields.some(
    (field) => field.key === "benefit_valuation_policy_account_value",
  ),
  false,
);
assert.equal(
  earlyRequirements.fields.some(
    (field) => field.key === "policy_values_converted_to_twd",
  ),
  false,
);
assert.equal(
  earlyRequirements.fields.some(
    (field) =>
      field.key === "post_event_insurance_cost_refund_amount",
  ),
  true,
);

const revision8 = scheduleFor(8);
const withLoan = valueFor(
  revision8,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 300_000,
      post_event_insurance_cost_refund_amount: 30_000,
      unpaid_policy_charge_amount: 20_000,
      policy_loan_and_interest_amount: 100_000,
    },
  },
);
assert.equal(withLoan.value, 1_210_000);

const revision10 = scheduleFor(10);
const minorReturn = valueFor(
  revision10,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 300_000,
      post_event_insurance_cost_refund_amount: 5_000,
      unpaid_policy_charge_amount: 20_000,
      policy_loan_and_interest_amount: 100_000,
      insured_age_at_event: 14,
    },
  },
);
assert.equal(minorReturn.state, "account_value_return");
assert.equal(minorReturn.protected_amount, 0);
assert.equal(minorReturn.value, 185_000);
const minorRequirements = model.policyStateRequirements({
  ...revision10,
  face_amount: 1_000_000,
  policy_state: {
    policy_effect_status_at_event: "active",
    benefit_valuation_policy_account_value: 300_000,
    post_event_insurance_cost_refund_amount: 5_000,
    unpaid_policy_charge_amount: 20_000,
    policy_loan_and_interest_amount: 100_000,
    insured_age_at_event: 14,
  },
});
assert.equal(
  minorRequirements.fields.some(
    (field) => field.key === "death_benefit_status",
  ),
  false,
);

const funeralLimited = valueFor(
  revision10,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 300_000,
      post_event_insurance_cost_refund_amount: 10_000,
      unpaid_policy_charge_amount: 20_000,
      policy_loan_and_interest_amount: 100_000,
      insured_age_at_event: 40,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 200_000,
    },
  },
);
assert.equal(funeralLimited.state, "death_or_funeral_amount");
assert.equal(funeralLimited.protected_amount, 200_000);
assert.equal(funeralLimited.value, 390_000);

const revision26 = scheduleFor(26);
const lateDisability = valueFor(
  revision26,
  "total-disability-benefit",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      benefit_valuation_policy_account_value: 400_000,
      post_event_insurance_cost_refund_amount: 50_000,
      unpaid_policy_charge_amount: 20_000,
      policy_loan_and_interest_amount: 100_000,
      insured_age_at_event: 40,
    },
  },
);
assert.equal(lateDisability.value, 1_330_000);

const maturity = valueFor(
  revision0,
  "maturity-benefit",
  {
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      maturity_basic_premium_policy_account_value: 800_000,
      unpaid_policy_charge_amount: 20_000,
    },
  },
);
assert.equal(maturity.state, "conditional_amount");
assert.equal(maturity.value, 780_000);
assert.equal(
  maturity.policy_state_key,
  "maturity_basic_premium_policy_account_value",
);

const waiver = valueFor(
  revision26,
  "disability-premium-waiver",
  {
    face_amount: 1_000_000,
    policy_state: {
      remaining_premium_amount: 360_000,
    },
  },
);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 360_000);

console.log({
  status: "ok",
  batch_id: "tii-life-017",
  user_flow_cases: 7,
  exact_account_scope_cases: 2,
});

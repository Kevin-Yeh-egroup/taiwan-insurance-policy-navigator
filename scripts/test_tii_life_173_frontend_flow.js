const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");

function loadProposal(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), "utf8"));
}

function scheduleFor(payload, productId) {
  const proposal = payload.proposals.find((item) => item.product_id === productId);
  assert.ok(proposal, productId);
  assert.equal(proposal.candidate_count, 1);
  return proposal.candidates[0].schedule;
}

function entry(schedule, entryId) {
  const result = schedule.coverage_entries.find((item) => item.id === entryId);
  assert.ok(result, entryId);
  return result;
}

function calculatedValue(schedule, entryId, selection) {
  return model.coverageValue(entry(schedule, entryId), {
    ...schedule,
    ...selection,
  });
}

const early = loadProposal(
  "work/tii-benefit-proposals/tii-life-173-bnp-early-variable-life-paid-premium-v204-combined.json",
);
const variableLife = loadProposal(
  "work/tii-benefit-proposals/tii-life-173-bnp-variable-life-net-risk-v205.json",
);
const variableUniversal = loadProposal(
  "work/tii-benefit-proposals/tii-life-173-bnp-variable-universal-life-net-risk-v205.json",
);
const hengfu = loadProposal(
  "work/tii-benefit-proposals/tii-life-173-bnp-hengfu-variable-life-v206.json",
);

const earlySchedule = scheduleFor(early, "267191M31A00200");
function requirementKeys(schedule, policyState = {}) {
  return model
    .policyStateRequirements({
      ...schedule,
      plan_name: "甲型",
      policy_state: policyState,
    })
    .fields.map((field) => field.key);
}

const initialEarlyRequirementKeys = requirementKeys(earlySchedule);
assert.ok(
  initialEarlyRequirementKeys.includes(
    "current_benefit_amount_status",
  ),
);
assert.ok(
  !initialEarlyRequirementKeys.includes(
    "current_death_disability_benefit_amount",
  ),
);
assert.ok(!initialEarlyRequirementKeys.includes("paid_premium_total"));
const formulaEarlyRequirementKeys = requirementKeys(earlySchedule, {
  current_benefit_amount_status: "formula_confirmed_current",
});
assert.ok(formulaEarlyRequirementKeys.includes("paid_premium_total"));
assert.ok(
  formulaEarlyRequirementKeys.includes("specified_factor_unit"),
);
assert.ok(
  !formulaEarlyRequirementKeys.includes(
    "current_death_disability_benefit_amount",
  ),
);
const currentAmountEarlyRequirementKeys = requirementKeys(
  earlySchedule,
  {
    current_benefit_amount_status: "current_amount_provided",
  },
);
assert.ok(
  currentAmountEarlyRequirementKeys.includes(
    "current_death_disability_benefit_amount",
  ),
);
assert.ok(
  !currentAmountEarlyRequirementKeys.includes("paid_premium_total"),
);
const timeBarredEarlyRequirementKeys = requirementKeys(
  earlySchedule,
  {
    claim_time_status: "time_barred",
  },
);
assert.ok(
  !timeBarredEarlyRequirementKeys.includes(
    "current_benefit_amount_status",
  ),
);
assert.ok(
  !timeBarredEarlyRequirementKeys.includes(
    "benefit_exclusion_status",
  ),
);
assert.ok(
  !timeBarredEarlyRequirementKeys.includes(
    "total_disability_qualification_status",
  ),
);
assert.ok(
  !timeBarredEarlyRequirementKeys.includes("paid_premium_total"),
);
const earlyState = {
  paid_premium_total: 1_000_000,
  partial_termination_amount_total: 100_000,
  specified_percent_or_multiplier: 1.3,
  specified_factor_unit: "multiplier",
  benefit_valuation_policy_account_value: 400_000,
  current_benefit_amount_status: "formula_confirmed_current",
  policy_effect_status_at_event: "active",
  claim_time_status: "within_claim_period",
  benefit_exclusion_status: "none_confirmed",
};
assert.equal(
  calculatedValue(earlySchedule, "death-or-funeral-benefit", {
    plan_name: "甲型",
    policy_state: earlyState,
  }).value,
  1_170_000,
);
assert.equal(
  calculatedValue(earlySchedule, "death-or-funeral-benefit", {
    plan_name: "乙型",
    policy_state: earlyState,
  }).value,
  1_570_000,
);
const earlyUnknown = calculatedValue(
  earlySchedule,
  "death-or-funeral-benefit",
  {
    plan_name: "甲型",
    policy_state: {
      ...earlyState,
      current_benefit_amount_status: "unknown",
    },
  },
);
assert.equal(earlyUnknown.value, null);
assert.equal(earlyUnknown.state, "needs_insurer_confirmation");
assert.equal(
  earlyUnknown.confirmation_reason,
  "current_benefit_amount_basis_unknown",
);
const earlyCurrentAmount = calculatedValue(
  earlySchedule,
  "death-or-funeral-benefit",
  {
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 400_000,
      current_benefit_amount_status: "current_amount_provided",
      current_death_disability_benefit_amount: 1_250_000,
      policy_effect_status_at_event: "active",
      claim_time_status: "within_claim_period",
      benefit_exclusion_status: "none_confirmed",
    },
  },
);
assert.equal(earlyCurrentAmount.value, 1_250_000);
assert.equal(
  earlyCurrentAmount.formula_type,
  "current_recorded_benefit_amount",
);
const earlyTimeBarred = calculatedValue(
  earlySchedule,
  "death-or-funeral-benefit",
  {
    plan_name: "甲型",
    policy_state: {
      ...earlyState,
      claim_time_status: "time_barred",
    },
  },
);
assert.equal(earlyTimeBarred.value, 400_000);
assert.equal(earlyTimeBarred.state, "account_value_return");
assert.equal(
  earlyTimeBarred.formula_type,
  "time_barred_account_value_return",
);
assert.equal(
  calculatedValue(earlySchedule, "total-disability-benefit", {
    plan_name: "乙型",
    policy_state: {
      ...earlyState,
      total_disability_qualification_status:
        "confirmed_first_level_item",
    },
  }).value,
  1_570_000,
);

const earlyForeignMinorSchedule = scheduleFor(
  early,
  "267191M31A00611",
);
const foreignMinorReturn = calculatedValue(
  earlyForeignMinorSchedule,
  "death-or-funeral-benefit",
  {
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 500_000,
      policy_effect_status_at_event: "active",
      claim_time_status: "within_claim_period",
      benefit_exclusion_status: "none_confirmed",
      current_benefit_amount_status: "unknown",
      policy_loan_and_interest_amount: 10_000,
      unpaid_policy_charge_amount: 5_000,
      remittance_fee_amount: 1_000,
      contract_currency: "USD",
      insured_age_at_event: 14,
    },
  },
);
assert.equal(foreignMinorReturn.value, 484_000);
assert.equal(foreignMinorReturn.state, "account_value_return");
assert.equal(
  foreignMinorReturn.formula_type,
  "minor_account_value_return",
);

const variableLifeSchedule = scheduleFor(
  variableLife,
  "267131MV1A00423A11C90000019",
);
const variableLifeSelection = {
  face_amount: 1_000_000,
  plan_name: "甲型",
  policy_state: {
    policy_account_value: 400_000,
    insured_age_at_event: 40,
  },
};
assert.equal(
  calculatedValue(
    variableLifeSchedule,
    "death-or-funeral-benefit",
    variableLifeSelection,
  ).value,
  1_000_000,
);
assert.equal(
  calculatedValue(variableLifeSchedule, "death-or-funeral-benefit", {
    ...variableLifeSelection,
    plan_name: "乙型",
  }).value,
  1_400_000,
);
const minorResult = calculatedValue(
  variableLifeSchedule,
  "death-or-funeral-benefit",
  {
    ...variableLifeSelection,
    policy_state: {
      policy_account_value: 400_000,
      insured_age_at_event: 14,
    },
  },
);
assert.equal(minorResult.value, 400_000);
assert.equal(minorResult.formula_type, "minor_account_value_return");

const foreignUniversalSchedule = scheduleFor(
  variableUniversal,
  "267131MV1A02723Z11C90000005",
);
const foreignRequirements = model.policyStateRequirements(
  foreignUniversalSchedule,
);
assert.ok(
  foreignRequirements.fields.some((field) => field.key === "contract_currency"),
);
const foreignMissingCurrency = calculatedValue(
  foreignUniversalSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "甲型",
    policy_state: {
      policy_account_value: 400_000,
      insured_age_at_event: 40,
    },
  },
);
assert.equal(foreignMissingCurrency.value, null);
assert.equal(foreignMissingCurrency.state, "needs_policy_state");
assert.ok(foreignMissingCurrency.required_fields.includes("contract_currency"));
assert.equal(
  calculatedValue(
    foreignUniversalSchedule,
    "death-or-funeral-benefit",
    {
      face_amount: 1_000_000,
      plan_name: "甲型",
      policy_state: {
        policy_account_value: 400_000,
        insured_age_at_event: 40,
        contract_currency: "USD",
      },
    },
  ).value,
  1_000_000,
);

const hengfuPaidSchedule = scheduleFor(hengfu, "267191M31A00300");
const hengfuPaidRequirementKeys = requirementKeys(hengfuPaidSchedule);
assert.ok(hengfuPaidRequirementKeys.includes("paid_premium_total"));
assert.ok(
  hengfuPaidRequirementKeys.includes(
    "benefit_valuation_policy_account_value",
  ),
);
assert.ok(
  hengfuPaidRequirementKeys.includes(
    "insured_age_accuracy_status",
  ),
);
assert.ok(!hengfuPaidRequirementKeys.includes("specified_factor_unit"));
const hengfuPaidState = {
  paid_premium_total: 1_000_000,
  partial_termination_amount_total: 100_000,
  specified_percent_or_multiplier: 130,
  benefit_valuation_policy_account_value: 400_000,
  policy_effect_status_at_event: "active",
  claim_time_status: "within_claim_period",
  benefit_exclusion_status: "none_confirmed",
  insured_age_accuracy_status: "confirmed_accurate",
  death_benefit_status: "standard_death",
};
assert.equal(
  calculatedValue(hengfuPaidSchedule, "death-or-funeral-benefit", {
    plan_name: "乙型",
    policy_state: hengfuPaidState,
  }).value,
  1_570_000,
);
const hengfuPaidExclusion = calculatedValue(
  hengfuPaidSchedule,
  "death-or-funeral-benefit",
  {
    plan_name: "乙型",
    policy_state: {
      ...hengfuPaidState,
      benefit_exclusion_status: "confirmed_applies",
    },
  },
);
assert.equal(hengfuPaidExclusion.value, 400_000);
assert.equal(hengfuPaidExclusion.state, "account_value_return");
assert.equal(
  hengfuPaidExclusion.formula_type,
  "exclusion_account_value_return",
);

const hengfuCurrentSchedule = scheduleFor(hengfu, "267191M31A00304");
const currentSelection = {
  face_amount: 900_000,
  plan_name: "甲型",
  policy_state: {
    benefit_valuation_policy_account_value: 400_000,
    policy_effect_status_at_event: "active",
    claim_time_status: "within_claim_period",
    benefit_exclusion_status: "none_confirmed",
    insured_age_accuracy_status: "confirmed_accurate",
  },
};
const currentResult = calculatedValue(
  hengfuCurrentSchedule,
  "death-or-funeral-benefit",
  currentSelection,
);
assert.equal(currentResult.value, 900_000);
assert.equal(currentResult.face_amount_label, "事故時有效保險金額");
assert.equal(
  calculatedValue(hengfuCurrentSchedule, "death-or-funeral-benefit", {
    ...currentSelection,
    plan_name: "乙型",
    policy_state: {
      ...currentSelection.policy_state,
      death_benefit_status: "standard_death",
    },
  }).value,
  1_300_000,
);

const hengfuCurrentTimeBarred = calculatedValue(
  hengfuCurrentSchedule,
  "death-or-funeral-benefit",
  {
    ...currentSelection,
    policy_state: {
      ...currentSelection.policy_state,
      claim_time_status: "time_barred",
    },
  },
);
assert.equal(hengfuCurrentTimeBarred.value, 400_000);
assert.equal(hengfuCurrentTimeBarred.state, "account_value_return");
const hengfuAgeUncertain = calculatedValue(
  hengfuCurrentSchedule,
  "death-or-funeral-benefit",
  {
    ...currentSelection,
    policy_state: {
      ...currentSelection.policy_state,
      insured_age_accuracy_status: "error_or_uncertain",
    },
  },
);
assert.equal(hengfuAgeUncertain.value, null);
assert.equal(
  hengfuAgeUncertain.confirmation_reason,
  "insured_age_not_confirmed_accurate",
);

const hengfuCurrentFuneral = calculatedValue(
  hengfuCurrentSchedule,
  "death-or-funeral-benefit",
  {
    ...currentSelection,
    plan_name: "乙型",
    policy_state: {
      ...currentSelection.policy_state,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 500_000,
      funeral_excess_insurance_cost_refund_status:
        "confirmed_amount",
      funeral_excess_insurance_cost_refund_amount: 25_000,
    },
  },
);
assert.equal(hengfuCurrentFuneral.value, 925_000);
assert.equal(hengfuCurrentFuneral.state, "death_or_funeral_amount");

const hengfuModernSchedule = scheduleFor(hengfu, "267191M31A00308");
const hengfuModernFuneral = calculatedValue(
  hengfuModernSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 900_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 400_000,
      policy_effect_status_at_event: "active",
      claim_time_status: "within_claim_period",
      benefit_exclusion_status: "none_confirmed",
      insured_age_accuracy_status: "confirmed_accurate",
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 300_000,
      funeral_excess_insurance_cost_refund_status:
        "confirmed_none",
    },
  },
);
assert.equal(hengfuModernFuneral.value, 700_000);
assert.equal(hengfuModernFuneral.state, "death_or_funeral_amount");

const hengfuDisability = calculatedValue(
  hengfuModernSchedule,
  "total-disability-benefit",
  {
    face_amount: 900_000,
    plan_name: "甲型",
    policy_state: {
      benefit_valuation_policy_account_value: 400_000,
      policy_effect_status_at_event: "active",
      claim_time_status: "within_claim_period",
      benefit_exclusion_status: "none_confirmed",
      insured_age_accuracy_status: "confirmed_accurate",
      total_disability_qualification_status:
        "confirmed_first_level_item",
    },
  },
);
assert.equal(hengfuDisability.value, 900_000);

console.log({
  status: "ok",
  batch_id: "tii-life-173",
  user_flow_cases: 29,
});

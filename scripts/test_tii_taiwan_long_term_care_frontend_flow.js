const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-009-taiwan-long-term-care-whole-life-v215.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 2);
assert.equal(proposal.proposed_count, 2);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectionFor(schedule, policyState = {}, faceAmount = 1_000_000) {
  return {
    ...schedule,
    face_amount: faceAmount,
    policy_state: policyState,
  };
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(selection, entryId) {
  return model.coverageValue(
    entriesFor(selection)[entryId],
    selection,
  );
}

const schedule = scheduleFor("202191MZ6G84423A11Z10000000");
const baseLongTermCareState = {
  policy_year: 2,
  standard_annual_premium_amount: 60_000,
  premium_payment_period_years: 20,
  long_term_care_qualification_type: "adl",
  adl_impairment_count: 3,
  impairment_duration_months: 3,
  long_term_care_permanence_status: "not_permanent",
  long_term_care_medical_confirmation_status: "confirmed",
  long_term_care_previous_claim_status: "not_claimed",
};

const yearTwo = selectionFor(schedule, baseLongTermCareState);
const yearTwoLongTermCare = valueFor(
  yearTwo,
  "long-term-care-benefit",
);
assert.equal(yearTwoLongTermCare.value, 120_000);
assert.equal(yearTwoLongTermCare.state, "calculated");
assert.equal(
  yearTwoLongTermCare.formula_type,
  "early_policy_year_annual_premium_total",
);
assert.equal(yearTwoLongTermCare.result_kind, "cash_payout");
assert.equal(
  yearTwoLongTermCare.amount_stage,
  "gross_contract_benefit",
);

const yearFour = selectionFor(schedule, {
  ...baseLongTermCareState,
  policy_year: 4,
});
const yearFourLongTermCare = valueFor(
  yearFour,
  "long-term-care-benefit",
);
assert.equal(yearFourLongTermCare.value, 500_000);
assert.equal(
  yearFourLongTermCare.formula_type,
  "later_policy_year_face_amount_rate",
);

const yearFourWithoutPremiumInputs = valueFor(
  selectionFor(schedule, {
    policy_year: 4,
    long_term_care_qualification_type: "adl",
    adl_impairment_count: 3,
    impairment_duration_months: 3,
    long_term_care_permanence_status: "not_permanent",
    long_term_care_medical_confirmation_status: "confirmed",
    long_term_care_previous_claim_status: "not_claimed",
  }),
  "long-term-care-benefit",
);
assert.equal(yearFourWithoutPremiumInputs.value, 500_000);
assert.deepEqual(yearFourWithoutPremiumInputs.required_fields, [
  "policy_year",
  "long_term_care_qualification_type",
  "impairment_duration_months",
  "long_term_care_permanence_status",
  "long_term_care_medical_confirmation_status",
  "long_term_care_previous_claim_status",
  "adl_impairment_count",
]);

const adlNotQualified = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    adl_impairment_count: 2,
  }),
  "long-term-care-benefit",
);
assert.equal(adlNotQualified.state, "not_eligible");
assert.equal(adlNotQualified.value, null);
assert.equal(
  adlNotQualified.eligibility.qualification_met,
  false,
);

const durationNotQualified = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    impairment_duration_months: 2,
  }),
  "long-term-care-benefit",
);
assert.equal(durationNotQualified.state, "not_eligible");
assert.equal(durationNotQualified.eligibility.duration_met, false);

const notMedicallyConfirmed = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    long_term_care_medical_confirmation_status: "not_confirmed",
  }),
  "long-term-care-benefit",
);
assert.equal(notMedicallyConfirmed.state, "not_eligible");
assert.equal(
  notMedicallyConfirmed.eligibility.medical_confirmation_met,
  false,
);

const alreadyClaimed = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    long_term_care_previous_claim_status: "already_claimed",
  }),
  "long-term-care-benefit",
);
assert.equal(alreadyClaimed.state, "not_eligible");
assert.equal(alreadyClaimed.eligibility.previous_claim_met, false);

const permanentOverride = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    impairment_duration_months: 0,
    long_term_care_permanence_status: "permanent",
  }),
  "long-term-care-benefit",
);
assert.equal(permanentOverride.value, 120_000);

const cognitiveQualified = valueFor(
  selectionFor(schedule, {
    policy_year: 2,
    standard_annual_premium_amount: 60_000,
    premium_payment_period_years: 20,
    long_term_care_qualification_type: "cognitive",
    cdr_score: "2",
    impairment_duration_months: 3,
    long_term_care_permanence_status: "not_permanent",
    long_term_care_medical_confirmation_status: "confirmed",
    long_term_care_previous_claim_status: "not_claimed",
    cognitive_icd_diagnosis_status: "confirmed",
  }),
  "long-term-care-benefit",
);
assert.equal(cognitiveQualified.value, 120_000);

const cognitiveMissingDiagnosis = valueFor(
  selectionFor(schedule, {
    policy_year: 2,
    standard_annual_premium_amount: 60_000,
    premium_payment_period_years: 20,
    long_term_care_qualification_type: "cognitive",
    cdr_score: "2",
    impairment_duration_months: 3,
    long_term_care_permanence_status: "not_permanent",
    long_term_care_medical_confirmation_status: "confirmed",
    long_term_care_previous_claim_status: "not_claimed",
  }),
  "long-term-care-benefit",
);
assert.equal(cognitiveMissingDiagnosis.state, "needs_policy_state");
assert(
  cognitiveMissingDiagnosis.required_fields.includes(
    "cognitive_icd_diagnosis_status",
  ),
);

const terminalState = {
  policy_year: 4,
  standard_annual_premium_amount: 100_000,
  premium_payment_period_years: 10,
  policy_reserve_value: 600_000,
  prior_long_term_care_benefit_amount: 500_000,
  death_benefit_status: "standard_death",
};
const standardTerminalSelection = selectionFor(
  schedule,
  terminalState,
);
const standardDeath = valueFor(
  standardTerminalSelection,
  "death-or-funeral-benefit",
);
assert.equal(standardDeath.value, 600_000);
assert.equal(standardDeath.state, "death_or_funeral_amount");
assert.equal(
  standardDeath.formula_type,
  "later_policy_year_greater_of_with_offset",
);
assert.deepEqual(
  standardDeath.candidates.map((candidate) => candidate.value),
  [500_000, 600_000, 0],
);
assert.equal(standardDeath.amount_stage, "gross_contract_benefit");

const zeroReserveDeath = valueFor(
  selectionFor(schedule, {
    ...terminalState,
    policy_reserve_value: 0,
    prior_long_term_care_benefit_amount: 0,
  }),
  "death-or-funeral-benefit",
);
assert.equal(zeroReserveDeath.value, 1_000_000);
assert.equal(
  zeroReserveDeath.candidates.find(
    (candidate) => candidate.key === "policy_reserve_value",
  ).value,
  0,
);

const funeralSelection = selectionFor(schedule, {
  ...terminalState,
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 300_000,
});
const funeralDeath = valueFor(
  funeralSelection,
  "death-or-funeral-benefit",
);
assert.equal(funeralDeath.value, 300_000);
assert.equal(funeralDeath.gross_value_before_funeral_cap, 600_000);

const disability = valueFor(
  standardTerminalSelection,
  "total-disability-benefit",
);
assert.equal(disability.value, 600_000);
assert.equal(disability.state, "greater_of");

const maturity = valueFor(
  selectionFor(schedule, {
    standard_annual_premium_amount: 70_000,
    premium_payment_period_years: 10,
    prior_long_term_care_benefit_amount: 500_000,
  }),
  "maturity-benefit",
);
assert.equal(maturity.value, 500_000);
assert.deepEqual(
  maturity.candidates.map((candidate) => candidate.value),
  [500_000, 242_000],
);

const waiver = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    premium_payment_period_status: "within_payment_period",
    remaining_premium_amount: 720_000,
  }),
  "premium-waiver",
);
assert.equal(waiver.value, 720_000);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.result_kind, "non_cash_effect");
assert.equal(waiver.amount_stage, "non_cash_estimate");

const waiverAfterPayment = valueFor(
  selectionFor(schedule, {
    ...baseLongTermCareState,
    premium_payment_period_status: "payment_period_ended",
    remaining_premium_amount: 720_000,
  }),
  "premium-waiver",
);
assert.equal(waiverAfterPayment.state, "not_eligible");
assert.equal(waiverAfterPayment.value, null);

const missingQualification = valueFor(
  selectionFor(schedule, {
    policy_year: 2,
    standard_annual_premium_amount: 60_000,
    premium_payment_period_years: 20,
  }),
  "long-term-care-benefit",
);
assert.equal(missingQualification.state, "needs_policy_state");
assert(
  missingQualification.required_fields.includes(
    "long_term_care_qualification_type",
  ),
);

const installmentNeedsInsurerQuote = valueFor(
  selectionFor(schedule, {
    cash_surrender_value: 900_000,
  }),
  "installment-periodic-benefit",
);
assert.equal(installmentNeedsInsurerQuote.state, "needs_policy_state");
assert.deepEqual(installmentNeedsInsurerQuote.required_fields, [
  "installment_periodic_amount",
]);

const installmentQuoted = valueFor(
  selectionFor(schedule, {
    installment_periodic_amount: 48_000,
    cash_surrender_value: 900_000,
  }),
  "installment-periodic-benefit",
);
assert.equal(installmentQuoted.value, 48_000);
assert.equal(installmentQuoted.state, "policy_state_value");
assert.equal(installmentQuoted.result_kind, "payment_method");
assert.equal(
  installmentQuoted.amount_stage,
  "insurer_quoted_amount",
);

const standardScenarios = model.coverageEventScenarios(
  standardTerminalSelection,
);
assert.deepEqual(
  standardScenarios.map((scenario) => scenario.event_key),
  [
    "death",
    "accidental-death",
    "total-disability",
    "maturity",
  ],
);
const standardDeathScenario = standardScenarios.find(
  (scenario) => scenario.event_key === "death",
);
assert.equal(standardDeathScenario.value, 600_000);
assert.deepEqual(standardDeathScenario.additive_entry_ids, []);
const standardAccidentalDeathScenario = standardScenarios.find(
  (scenario) => scenario.event_key === "accidental-death",
);
assert.equal(standardAccidentalDeathScenario.value, 1_600_000);
assert.deepEqual(
  standardAccidentalDeathScenario.additive_entry_ids,
  ["accidental-death-additional-benefit"],
);

const funeralScenarios = model.coverageEventScenarios(
  funeralSelection,
);
const funeralDeathScenario = funeralScenarios.find(
  (scenario) => scenario.event_key === "death",
);
assert.equal(
  funeralDeathScenario.gross_value_before_funeral_cap,
  600_000,
);
assert.equal(funeralDeathScenario.funeral_benefit_limit, 300_000);
assert.equal(funeralDeathScenario.value, 300_000);
const funeralAccidentalDeathScenario = funeralScenarios.find(
  (scenario) => scenario.event_key === "accidental-death",
);
assert.equal(
  funeralAccidentalDeathScenario.gross_value_before_funeral_cap,
  1_600_000,
);
assert.equal(
  funeralAccidentalDeathScenario.funeral_benefit_limit,
  300_000,
);
assert.equal(funeralAccidentalDeathScenario.value, 300_000);

console.log({
  status: "ok",
  batch_id: "tii-life-009",
  product_count: proposal.proposal_count,
  user_flow_cases: 27,
});

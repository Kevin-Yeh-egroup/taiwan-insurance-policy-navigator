const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const proposalPath = path.join(
  __dirname,
  "..",
  "work",
  "tii-benefit-proposals",
  "tii-life-053-fubon-jixiang-finance-variable-universal-life-v224.json",
);
const proposal = JSON.parse(fs.readFileSync(proposalPath, "utf8"));

function scheduleFor(productId) {
  const item = proposal.proposals.find(
    (candidate) => candidate.product_id === productId,
  );
  assert(item, productId);
  assert.equal(item.candidate_count, 1);
  return item.candidates[0].schedule;
}

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

const oldSchedule = scheduleFor("209141M31A00900");
assert.equal(
  oldSchedule.version_characteristics.terms_formula_representation,
  "direct_greater_or_sum",
);
assert.equal(oldSchedule.version_characteristics.maturity_age, 111);
const oldADeath = valueFor(
  oldSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "A型",
    policy_state: {
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 1_200_000,
      death_benefit_status: "standard_death",
    },
  },
);
assert.equal(oldADeath.value, 1_200_000);
assert.equal(oldADeath.state, "death_or_funeral_amount");
assert.equal(oldADeath.net_amount_at_risk, 0);

const oldBDeath = valueFor(
  oldSchedule,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: {
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 800_000,
      death_benefit_status: "standard_death",
    },
  },
);
assert.equal(oldBDeath.value, 1_800_000);
assert.equal(oldBDeath.state, "death_or_funeral_amount");

const oldAFuneral = valueFor(
  oldSchedule,
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
assert.equal(oldAFuneral.value, 850_000);
assert.equal(oldAFuneral.gross_value_before_funeral_cap, 1_000_000);
assert.equal(oldAFuneral.protected_amount, 400_000);
assert.equal(oldAFuneral.capped_protected_amount, 250_000);
assert.equal(oldAFuneral.account_value, 600_000);

const netRiskSchedule = scheduleFor("209141M31A00920");
assert.equal(
  netRiskSchedule.version_characteristics.terms_formula_representation,
  "net_amount_at_risk_plus_account_value",
);
assert.equal(netRiskSchedule.version_characteristics.disability_term, "完全殘廢");
const netRiskAFuneral = valueFor(
  netRiskSchedule,
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
assert.equal(netRiskAFuneral.value, 850_000);
assert.equal(netRiskAFuneral.net_amount_at_risk, 400_000);

const guardianshipSchedule = scheduleFor(
  "209191MV1A00323A11Z90000039",
);
assert.equal(
  guardianshipSchedule.version_characteristics.funeral_eligibility_rule,
  "guardianship_declaration",
);
assert.equal(
  guardianshipSchedule.version_characteristics.disability_term,
  "完全失能",
);
const newBDisability = valueFor(
  guardianshipSchedule,
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
  const minor = valueFor(guardianshipSchedule, entryId, {
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
  guardianshipSchedule,
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

const maturity = valueFor(
  guardianshipSchedule,
  "maturity-benefit",
  {
    policy_state: {
      maturity_policy_account_value: 925_000,
      policy_values_converted_to_twd: true,
    },
  },
);
assert.equal(maturity.value, 925_000);
assert.equal(maturity.state, "conditional_amount");

const requirements = model.policyStateRequirements({
  ...guardianshipSchedule,
  face_amount: 1_000_000,
  plan_name: "A型",
  policy_state: {},
});
assert(
  requirements.fields.some(
    (field) =>
      field.key === "benefit_valuation_policy_account_value",
  ),
);
assert(
  requirements.fields.some(
    (field) => field.key === "death_benefit_status",
  ),
);
assert(
  requirements.fields.some(
    (field) => field.key === "maturity_policy_account_value",
  ),
);

console.log({
  status: "ok",
  batch_id: "tii-life-053",
  product_family: "fubon-jixiang-finance-variable-universal-life",
  verified_version_count: 36,
  semantic_formula_groups: 3,
  source_gap_count: 4,
});

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const proposalPath = path.join(
  __dirname,
  "..",
  "work",
  "tii-benefit-proposals",
  "tii-life-086-hongtai-premium-waiver-rider-v239.json",
);
const proposal = JSON.parse(
  fs.readFileSync(proposalPath, "utf8"),
);

function scheduleFor(productId, planName) {
  const product = proposal.proposals.find(
    (candidate) => candidate.product_id === productId,
  );
  assert(product, productId);
  const schedule = product.candidates[0].schedule;
  return {
    ...schedule,
    product_id: productId,
    plan_name: planName,
  };
}

function entriesById(selection) {
  return Object.fromEntries(
    model
      .effectiveCoverageEntries(selection)
      .map((entry) => [entry.id, entry]),
  );
}

function value(selection, entryId, policyState) {
  const entry = entriesById(selection)[entryId];
  assert(entry, entryId);
  return model.coverageValue(entry, {
    ...selection,
    policy_state: policyState,
  });
}

const revision0A = scheduleFor("217341R11A00100", "A");
const revision0B = scheduleFor("217341R11A00100", "B");
assert.equal(revision0A.selection_type, "plan");
assert.equal(model.selectionMode(revision0A), "plan");
assert.equal(
  model.effectiveCoverageEntries({
    ...revision0A,
    plan_name: "",
  }).length,
  0,
);
assert.deepEqual(
  model.selectionRequirements({
    ...revision0A,
    plan_name: "",
  }).fields,
  ["plan_name"],
);
assert.equal(
  Object.keys(entriesById(revision0A)).length,
  3,
);
assert.equal(
  Object.keys(entriesById(revision0B)).length,
  3,
);

const baseState = {
  remaining_premium_amount: 240_000,
  unexpired_premium_refund_amount: 12_000,
  waived_premium_termination_settlement_amount: 150_000,
};
const waiver = value(
  revision0A,
  "future-premium-waiver",
  baseState,
);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 240_000);
assert.equal(waiver.result_kind, "non_cash_effect");

const refund = value(
  revision0A,
  "current-unexpired-premium-refund",
  baseState,
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 12_000);
assert.equal(refund.result_kind, "cash_payout");

const termination = value(
  revision0A,
  "waived-premium-termination-settlement",
  baseState,
);
assert.equal(termination.state, "policy_state_value");
assert.equal(termination.value, 150_000);
assert.equal(termination.result_kind, "cash_payout");

const missingTermination = value(
  revision0A,
  "waived-premium-termination-settlement",
  {
    ...baseState,
    waived_premium_termination_settlement_amount: undefined,
  },
);
assert.equal(missingTermination.state, "needs_policy_state");
assert.deepEqual(missingTermination.required_fields, [
  "waived_premium_termination_settlement_amount",
]);

const revision2A = scheduleFor("217341R11A00102", "A");
const revision2Entries = entriesById(revision2A);
assert.equal(Object.keys(revision2Entries).length, 4);
const overlappingState = {
  ...baseState,
  overlapping_waiver_settlement_amount: 180_000,
};
const overlap = value(
  revision2A,
  "overlapping-waiver-cash-settlement",
  overlappingState,
);
assert.equal(overlap.state, "policy_state_value");
assert.equal(overlap.value, 180_000);
assert.equal(overlap.result_kind, "cash_payout");

const revision10 = scheduleFor(
  "217341RZ1A00122A11Z10000011",
  "B",
);
assert.equal(
  revision10.version_characteristics.terms_revision,
  "partial_change_11",
);
assert.equal(
  revision10.version_characteristics.disability_term,
  "失能",
);
assert.equal(
  revision10.plan_options[1].label,
  "乙型（重大疾病及第二至第六級失能）",
);

const revision12 = scheduleFor(
  "217341RZ1A00122A11Z10000013",
  "A",
);
assert.equal(
  revision12.version_characteristics
    .waived_premium_settlement_discount_rate_percent,
  1,
);

const requirementKeys = model
  .policyStateRequirements(revision2A)
  .fields.map((field) => field.key);
for (const key of [
  "remaining_premium_amount",
  "unexpired_premium_refund_amount",
  "overlapping_waiver_settlement_amount",
  "waived_premium_termination_settlement_amount",
]) {
  assert(requirementKeys.includes(key), key);
}
assert.equal(
  model.POLICY_STATE_FIELDS
    .waived_premium_termination_settlement_amount.type,
  "non_negative_money",
);

console.log(
  "TII Hongtai premium waiver frontend flow tests passed.",
);

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals",
      "tii-life-080-farglory-specific-illness-whole-life-rider-v282.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 14);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (proposalItem) => proposalItem.product_id === productId,
  ).candidates[0].schedule;
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function requiredKeys(schedule, policyState = {}) {
  return model
    .policyStateRequirements({
      ...schedule,
      face_amount: 1_000_000,
      policy_state: policyState,
    })
    .fields.map((field) => field.key);
}

function valueFor(schedule, entryId, policyState = {}) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    face_amount: 1_000_000,
    policy_state: policyState,
  });
}

const revision0 = scheduleFor("216311R12G02500");
assert.equal(model.selectionRequirements(revision0).mode, "face_amount");
assert.deepEqual(requiredKeys(revision0), [
  "farglory_specific_illness_life_event_status",
]);

const illnessDuringPayment = {
  farglory_specific_illness_life_event_status:
    "specific_illness_after_waiting_during_payment_period",
};
assert.deepEqual(requiredKeys(revision0, illnessDuringPayment), [
  "farglory_specific_illness_life_event_status",
  "unexpired_premium_refund_amount",
]);
assert.equal(
  valueFor(
    revision0,
    "specific-illness-benefit",
    illnessDuringPayment,
  ).value,
  1_000_000,
);
assert.equal(
  valueFor(
    revision0,
    "death-or-funeral-benefit",
    illnessDuringPayment,
  ).state,
  "not_eligible",
);
assert.equal(
  valueFor(
    revision0,
    "total-disability-benefit",
    illnessDuringPayment,
  ).state,
  "not_eligible",
);

const standardDeath = {
  farglory_specific_illness_life_event_status:
    "death_after_payment_period",
  death_benefit_status: "standard_death",
};
assert.deepEqual(requiredKeys(revision0, standardDeath), [
  "farglory_specific_illness_life_event_status",
  "death_benefit_status",
]);
const standardDeathValue = valueFor(
  revision0,
  "death-or-funeral-benefit",
  standardDeath,
);
assert.equal(standardDeathValue.value, 1_000_000);
assert.equal(
  standardDeathValue.formula_type,
  "face_amount_percentage_standard_death",
);

const funeralDeath = {
  farglory_specific_illness_life_event_status:
    "death_after_payment_period",
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 600_000,
  funeral_excess_premium_refund_amount: 20_000,
};
assert.deepEqual(requiredKeys(revision0, funeralDeath), [
  "farglory_specific_illness_life_event_status",
  "death_benefit_status",
  "remaining_funeral_benefit_limit",
  "funeral_excess_premium_refund_amount",
]);
const funeralDeathValue = valueFor(
  revision0,
  "death-or-funeral-benefit",
  funeralDeath,
);
assert.equal(funeralDeathValue.value, 600_000);
assert.equal(
  funeralDeathValue.formula_type,
  "face_amount_percentage_funeral_cap",
);
assert.equal(
  valueFor(
    revision0,
    "funeral-excess-premium-refund",
    funeralDeath,
  ).value,
  20_000,
);
const funeralScenarios = model.coverageEventScenarios({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: funeralDeath,
});
assert.equal(funeralScenarios.length, 1);
assert.equal(funeralScenarios[0].value, 620_000);
assert.deepEqual(funeralScenarios[0].additive_entry_ids, [
  "funeral-excess-premium-refund",
]);

const funeralDuringPayment = {
  ...funeralDeath,
  farglory_specific_illness_life_event_status:
    "death_during_payment_period",
  unexpired_premium_refund_amount: 10_000,
};
const funeralDuringPaymentScenarios = model.coverageEventScenarios({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: funeralDuringPayment,
});
assert.equal(funeralDuringPaymentScenarios.length, 1);
assert.equal(funeralDuringPaymentScenarios[0].value, 630_000);
assert.deepEqual(
  funeralDuringPaymentScenarios[0].additive_entry_ids,
  [
    "funeral-excess-premium-refund",
    "unexpired-premium-refund",
  ],
);

const disabilityDuringPayment = {
  farglory_specific_illness_life_event_status:
    "total_disability_during_payment_period",
  unexpired_premium_refund_amount: 8_765,
};
assert.equal(
  valueFor(
    revision0,
    "total-disability-benefit",
    disabilityDuringPayment,
  ).value,
  1_000_000,
);
const disabilityScenarios = model.coverageEventScenarios({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: disabilityDuringPayment,
});
assert.equal(disabilityScenarios.length, 1);
assert.equal(disabilityScenarios[0].value, 1_008_765);

for (const eventStatus of [
  "disease_waiting_not_met",
  "not_eligible_or_uncertain",
  "primary_benefit_already_paid",
]) {
  const state = {
    farglory_specific_illness_life_event_status: eventStatus,
  };
  assert.deepEqual(requiredKeys(revision0, state), [
    "farglory_specific_illness_life_event_status",
  ]);
  for (const entryId of Object.keys(entriesFor(revision0))) {
    const result = valueFor(revision0, entryId, state);
    if (
      eventStatus === "not_eligible_or_uncertain" &&
      entryId === "funeral-excess-premium-refund"
    ) {
      assert.equal(
        result.state,
        "needs_insurer_confirmation",
        eventStatus,
      );
      continue;
    }
    assert.equal(result.state, "not_eligible", eventStatus);
    assert.equal(result.value, 0, eventStatus);
  }
}

const revision13 = scheduleFor(
  "216351RZ9B02523A11Z10000013",
);
assert.equal(
  revision13.version_characteristics.semantic_phase,
  "standardized_nine_illness_reinstatement_disclosure",
);
assert.equal(
  revision13.version_characteristics.specific_illness_items[0],
  "急性心肌梗塞（重度）",
);
assert.equal(
  revision13.version_characteristics.specific_illness_item_count,
  9,
);
assert.equal(
  model.POLICY_STATE_FIELDS
    .farglory_specific_illness_life_event_status.type,
  "choice",
);

console.log({
  status: "ok",
  batch_id: "tii-life-080",
  product_count: proposal.proposal_count,
  user_flow_cases: 24,
});

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
      "tii-life-080-farglory-yongkang-specific-illness-whole-life-health-rider-v281.json",
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

const revision0 = scheduleFor("216351R11A09700");
assert.equal(model.selectionRequirements(revision0).mode, "face_amount");
assert.deepEqual(requiredKeys(revision0), [
  "farglory_yongkang_event_status",
]);

const duringPayment = {
  farglory_yongkang_event_status:
    "eligible_after_waiting_during_payment_period",
};
assert.deepEqual(requiredKeys(revision0, duringPayment), [
  "farglory_yongkang_event_status",
  "unexpired_premium_refund_amount",
]);
const benefit = valueFor(
  revision0,
  "specific-illness-benefit",
  duringPayment,
);
assert.equal(benefit.state, "calculated");
assert.equal(benefit.value, 1_000_000);
const missingRefund = valueFor(
  revision0,
  "unexpired-premium-refund",
  duringPayment,
);
assert.equal(missingRefund.state, "needs_policy_state");
assert.deepEqual(missingRefund.required_fields, [
  "unexpired_premium_refund_amount",
]);
const refund = valueFor(
  revision0,
  "unexpired-premium-refund",
  {
    ...duringPayment,
    unexpired_premium_refund_amount: 12_345,
  },
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 12_345);
const duringPaymentScenarios = model.coverageEventScenarios({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: {
    ...duringPayment,
    unexpired_premium_refund_amount: 12_345,
  },
});
assert.equal(duringPaymentScenarios.length, 1);
assert.equal(duringPaymentScenarios[0].value, 1_012_345);
assert.deepEqual(
  duringPaymentScenarios[0].additive_entry_ids,
  ["unexpired-premium-refund"],
);

const afterPayment = {
  farglory_yongkang_event_status:
    "eligible_after_waiting_after_payment_period",
};
assert.deepEqual(requiredKeys(revision0, afterPayment), [
  "farglory_yongkang_event_status",
]);
assert.equal(
  valueFor(
    revision0,
    "specific-illness-benefit",
    afterPayment,
  ).value,
  1_000_000,
);
const noRefund = valueFor(
  revision0,
  "unexpired-premium-refund",
  afterPayment,
);
assert.equal(noRefund.state, "not_eligible");
assert.equal(noRefund.value, 0);
const afterPaymentScenarios = model.coverageEventScenarios({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: afterPayment,
});
assert.equal(afterPaymentScenarios.length, 1);
assert.equal(afterPaymentScenarios[0].value, 1_000_000);

const accidentDuringPayment = {
  farglory_yongkang_event_status:
    "eligible_accident_exempt_during_payment_period",
  unexpired_premium_refund_amount: 8_765,
};
assert.equal(
  valueFor(
    revision0,
    "specific-illness-benefit",
    accidentDuringPayment,
  ).value,
  1_000_000,
);
assert.equal(
  valueFor(
    revision0,
    "unexpired-premium-refund",
    accidentDuringPayment,
  ).value,
  8_765,
);

for (const eventStatus of [
  "disease_waiting_not_met",
  "not_eligible_or_uncertain",
  "benefit_already_paid",
]) {
  const state = {
    farglory_yongkang_event_status: eventStatus,
  };
  assert.deepEqual(requiredKeys(revision0, state), [
    "farglory_yongkang_event_status",
  ]);
  for (const entryId of Object.keys(entriesFor(revision0))) {
    const result = valueFor(revision0, entryId, state);
    assert.equal(result.state, "not_eligible", eventStatus);
    assert.equal(result.value, 0, eventStatus);
  }
}

const revision13 = scheduleFor(
  "216351RZ1A09723A11Z10000013",
);
assert.equal(
  revision13.version_characteristics.semantic_phase,
  "policy_period_start_and_agreed_method",
);
assert.equal(
  revision13.version_characteristics.specific_illness_items[2],
  "腦中風後障礙（重度）",
);
assert.equal(
  model.POLICY_STATE_FIELDS.farglory_yongkang_event_status.type,
  "choice",
);

console.log({
  status: "ok",
  batch_id: "tii-life-080",
  product_count: proposal.proposal_count,
  user_flow_cases: 19,
});

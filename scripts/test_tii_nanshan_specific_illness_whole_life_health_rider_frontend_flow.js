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
      "tii-life-032-nanshan-specific-illness-whole-life-health-rider-v260.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 15);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function resultFor(schedule, entryId, policyState = {}) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    face_amount: 1_000_000,
    policy_state: policyState,
  });
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

const revision0 = scheduleFor("206391R11A30100");
assert.equal(model.selectionRequirements(revision0).mode, "face_amount");
assert.deepEqual(requiredKeys(revision0), [
  "nanshan_specific_illness_event_status",
]);

const eligibleState = {
  nanshan_specific_illness_event_status:
    "eligible_after_waiting_period",
};
assert.deepEqual(requiredKeys(revision0, eligibleState), [
  "nanshan_specific_illness_event_status",
]);
const eligibleBenefit = resultFor(
  revision0,
  "specific-illness-benefit",
  eligibleState,
);
assert.equal(eligibleBenefit.value, 1_000_000);
assert.equal(eligibleBenefit.state, "calculated");
assert.equal(
  eligibleBenefit.calculation_basis,
  "percentage_of_base",
);
assert.equal(eligibleBenefit.amount_role, "payout");
assert.equal(eligibleBenefit.applied_rate, 1);
assert.equal(eligibleBenefit.gross_value, 1_000_000);
assert.deepEqual(eligibleBenefit.required_fields, [
  "nanshan_specific_illness_event_status",
]);

const initialWaitingState = {
  nanshan_specific_illness_event_status:
    "disease_within_initial_waiting_period",
};
assert.deepEqual(requiredKeys(revision0, initialWaitingState), [
  "nanshan_specific_illness_event_status",
  "paid_premium_total",
]);
assert.equal(
  resultFor(
    revision0,
    "specific-illness-benefit",
    initialWaitingState,
  ).state,
  "not_eligible",
);
assert.equal(
  resultFor(
    revision0,
    "initial-waiting-period-premium-refund",
    {
      ...initialWaitingState,
      paid_premium_total: 42_000,
    },
  ).value,
  42_000,
);

const increaseWaitingState = {
  nanshan_specific_illness_event_status:
    "disease_within_increase_waiting_period",
};
assert.deepEqual(requiredKeys(revision0, increaseWaitingState), [
  "nanshan_specific_illness_event_status",
  "increased_face_amount_premium_paid_total",
]);
assert.equal(
  resultFor(
    revision0,
    "increased-face-amount-premium-refund",
    {
      ...increaseWaitingState,
      increased_face_amount_premium_paid_total: 8_600,
    },
  ).value,
  8_600,
);

const waiverState = {
  nanshan_specific_illness_event_status:
    "qualifying_waiver_within_payment_period",
};
assert.deepEqual(requiredKeys(revision0, waiverState), [
  "nanshan_specific_illness_event_status",
  "remaining_premium_amount",
]);
const waiver = resultFor(
  revision0,
  "future-premium-waiver",
  {
    ...waiverState,
    remaining_premium_amount: 180_000,
  },
);
assert.equal(waiver.value, 180_000);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.amount_role, "premium_waiver");

const terminationState = {
  nanshan_specific_illness_event_status:
    "termination_with_unexpired_premium",
};
assert.deepEqual(requiredKeys(revision0, terminationState), [
  "nanshan_specific_illness_event_status",
  "unexpired_premium_refund_amount",
]);
assert.equal(
  resultFor(
    revision0,
    "termination-unexpired-premium-refund",
    {
      ...terminationState,
      unexpired_premium_refund_amount: 1_234,
    },
  ).value,
  1_234,
);

const uncertainState = {
  nanshan_specific_illness_event_status:
    "not_eligible_or_uncertain",
};
assert.deepEqual(requiredKeys(revision0, uncertainState), [
  "nanshan_specific_illness_event_status",
]);
for (const entryId of Object.keys(entriesFor(revision0))) {
  const result = resultFor(revision0, entryId, uncertainState);
  assert.equal(result.value, 0, entryId);
  assert.equal(result.state, "not_eligible", entryId);
}

const revision14 = scheduleFor(
  "206391RZ1A30123A11Z10000014",
);
assert.equal(
  revision14.version_characteristics.semantic_phase,
  "day31-wait-definition-revision-impairment-grade-1-to-6",
);
assert.equal(
  revision14.version_characteristics
    .premium_waiver_disability_term,
  "失能",
);
assert.equal(
  revision14.version_characteristics
    .premium_waiver_disability_grade_max,
  6,
);
assert.equal(
  entriesFor(revision14)["future-premium-waiver"].name,
  "未來保險費豁免（第 1 至 6 級失能）",
);

console.log({
  status: "ok",
  batch_id: "tii-life-032",
  product_count: proposal.proposal_count,
  user_flow_cases: 29,
});

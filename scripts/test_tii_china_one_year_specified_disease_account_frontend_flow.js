const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-026-china-one-year-specified-disease-account-v296.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);

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

function valueFor(schedule, entryId, policyState = {}) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    face_amount: 1_000_000,
    policy_state: policyState,
  });
}

const revision0 = scheduleFor("205351R11A54800");
assert.equal(model.selectionRequirements(revision0).mode, "face_amount");
assert.deepEqual(
  model.policyStateRequirements(revision0).fields.map(
    (field) => field.key,
  ),
  ["china_account_specific_illness_claim_status"],
);

const missingStatus = valueFor(
  revision0,
  "specified-disease-account-benefit",
);
assert.equal(missingStatus.state, "needs_policy_state");
assert.deepEqual(missingStatus.required_fields, [
  "china_account_specific_illness_claim_status",
]);

const eligible = {
  china_account_specific_illness_claim_status: "eligible_first_claim",
};
assert.deepEqual(
  model
    .policyStateRequirements({
      ...revision0,
      policy_state: eligible,
    })
    .fields.map((field) => field.key),
  [
    "china_account_specific_illness_claim_status",
    "unexpired_premium_refund_amount",
  ],
);
assert.equal(
  valueFor(
    revision0,
    "specified-disease-account-benefit",
    eligible,
  ).value,
  1_000_000,
);

const refund = valueFor(
  revision0,
  "unexpired-insurance-cost-refund",
  {
    ...eligible,
    unexpired_premium_refund_amount: 12_345,
  },
);
assert.equal(refund.state, "policy_state_value");
assert.equal(refund.value, 12_345);

const scenarios = model.coverageEventScenarios({
  ...revision0,
  face_amount: 1_000_000,
  policy_state: {
    ...eligible,
    unexpired_premium_refund_amount: 12_345,
  },
});
assert.equal(scenarios.length, 1);
assert.equal(scenarios[0].event_key, "specified_disease");
assert.equal(scenarios[0].value, 1_012_345);
assert.deepEqual(scenarios[0].additive_entry_ids, [
  "unexpired-insurance-cost-refund",
]);

const alreadyPaid = {
  china_account_specific_illness_claim_status: "already_paid",
};
assert.deepEqual(
  model
    .policyStateRequirements({
      ...revision0,
      policy_state: alreadyPaid,
    })
    .fields.map((field) => field.key),
  ["china_account_specific_illness_claim_status"],
);
for (const entryId of [
  "specified-disease-account-benefit",
  "unexpired-insurance-cost-refund",
]) {
  const result = valueFor(revision0, entryId, alreadyPaid);
  assert.equal(result.state, "not_eligible", entryId);
  assert.equal(result.value, 0, entryId);
}

const revision8 = scheduleFor(
  "205351RZ1A00321A11Z10000008",
);
assert.equal(
  revision8.version_characteristics.semantic_phase,
  "disability-wording-revision",
);
assert.equal(
  revision8.version_characteristics.legacy_disability_wording_present,
  false,
);

const revision12 = scheduleFor(
  "205351RZ1A00321A11Z10000012",
);
assert.equal(
  revision12.version_characteristics.semantic_phase,
  "medical-opinion-review-revision",
);
assert.equal(
  revision12.version_characteristics.medical_opinion_review_available,
  true,
);
assert.equal(
  revision12.version_characteristics.policy_account_value_is_benefit_basis,
  false,
);

console.log({
  status: "ok",
  batch_id: "tii-life-026",
  product_count: proposal.proposal_count,
  user_flow_cases: 16,
});

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
      "tii-life-026-china-life-critical-disease-specified-illness-term-rider-v258.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 15);

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

function valueFor(schedule, entryId, policyState = {}) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    face_amount: 1_000_000,
    policy_state: policyState,
  });
}

function scenariosFor(schedule, policyState = {}) {
  return model.coverageEventScenarios({
    ...schedule,
    face_amount: 1_000_000,
    policy_state: policyState,
  });
}

const revision0 = scheduleFor("205351R11A00200");
assert.equal(model.selectionRequirements(revision0).mode, "face_amount");
assert.deepEqual(
  model.policyStateRequirements(revision0).fields.map(
    (field) => field.key,
  ),
  ["critical_specified_benefit_claim_status"],
);

const missingEligibility = valueFor(
  revision0,
  "critical-disease-trigger-benefit",
);
assert.equal(missingEligibility.state, "needs_policy_state");
assert.deepEqual(
  missingEligibility.required_fields,
  ["critical_specified_benefit_claim_status"],
);

const eligibleState = {
  critical_specified_benefit_claim_status: "eligible_first_claim",
};
assert.deepEqual(
  model
    .policyStateRequirements({
      ...revision0,
      policy_state: eligibleState,
    })
    .fields.map((field) => field.key),
  [
    "critical_specified_benefit_claim_status",
    "unexpired_premium_refund_amount",
  ],
);
assert.equal(
  valueFor(
    revision0,
    "critical-disease-trigger-benefit",
    eligibleState,
  ).value,
  1_000_000,
);
assert.equal(
  valueFor(
    revision0,
    "specified-illness-trigger-benefit",
    eligibleState,
  ).value,
  1_000_000,
);

const refund = valueFor(
  revision0,
  "unexpired-premium-refund",
  {
    ...eligibleState,
    unexpired_premium_refund_amount: 12_345,
  },
);
assert.equal(refund.value, 12_345);
assert.equal(refund.state, "policy_state_value");

const scenarios = scenariosFor(revision0, {
  ...eligibleState,
  unexpired_premium_refund_amount: 12_345,
});
assert.equal(scenarios.length, 2);
assert.deepEqual(
  scenarios.map((scenario) => scenario.event_key),
  ["critical_disease", "specified_illness"],
);
assert.deepEqual(
  scenarios.map((scenario) => scenario.value),
  [1_012_345, 1_012_345],
);
assert(
  scenarios.every(
    (scenario) =>
      scenario.additive_entry_ids.join(",") ===
      "unexpired-premium-refund",
  ),
);

const alreadyPaidState = {
  critical_specified_benefit_claim_status: "already_paid",
};
assert.deepEqual(
  model
    .policyStateRequirements({
      ...revision0,
      policy_state: alreadyPaidState,
    })
    .fields.map((field) => field.key),
  ["critical_specified_benefit_claim_status"],
);
for (const entryId of [
  "critical-disease-trigger-benefit",
  "specified-illness-trigger-benefit",
  "unexpired-premium-refund",
]) {
  const result = valueFor(revision0, entryId, alreadyPaidState);
  assert.equal(result.value, 0, entryId);
  assert.equal(result.state, "not_eligible", entryId);
}
const alreadyPaidScenarios = scenariosFor(
  revision0,
  alreadyPaidState,
);
assert.equal(alreadyPaidScenarios.length, 2);
assert.deepEqual(
  alreadyPaidScenarios.map((scenario) => scenario.value),
  [0, 0],
);
assert(
  alreadyPaidScenarios.every((scenario) =>
    scenario.parts.every(
      (part) => part.state === "not_eligible",
    ),
  ),
);

const revision14 = scheduleFor(
  "205351RZ1A00222A11Z10000014",
);
assert.equal(
  revision14.version_characteristics.semantic_phase,
  "severe-critical-and-severe-specified-definitions",
);
assert.equal(
  revision14.version_characteristics.specified_illness_item_count,
  21,
);
assert.equal(
  revision14.version_characteristics.premium_waiver_available,
  false,
);

console.log({
  status: "ok",
  batch_id: "tii-life-026",
  product_count: proposal.proposal_count,
  user_flow_cases: 24,
});

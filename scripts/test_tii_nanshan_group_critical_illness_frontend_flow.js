const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-033-nanshan-group-critical-illness-v213.json",
    ),
    "utf8",
  ),
);
assert.equal(proposal.proposal_count, 16);

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

const revision4 = scheduleFor("206137M12B30104");
assert.equal(model.selectionRequirements(revision4).mode, "face_amount");
assert.deepEqual(
  model.policyStateRequirements(revision4).fields.map(
    (field) => field.key,
  ),
  ["death_benefit_status"],
);
assert.equal(
  valueFor(
    revision4,
    "critical-disease-benefit",
  ).value,
  1_000_000,
);
assert.equal(
  valueFor(
    revision4,
    "disability-benefit",
  ).value,
  1_000_000,
);
const missingDeathStatus = valueFor(
  revision4,
  "death-or-funeral-benefit",
);
assert.equal(missingDeathStatus.state, "needs_policy_state");
assert.deepEqual(
  missingDeathStatus.required_fields,
  ["death_benefit_status"],
);
const standardDeath = valueFor(
  revision4,
  "death-or-funeral-benefit",
  { death_benefit_status: "standard_death" },
);
assert.equal(standardDeath.value, 1_000_000);
assert.equal(standardDeath.state, "death_or_funeral_amount");
assert.equal(
  standardDeath.formula_type,
  "face_amount_standard_death",
);
const missingFuneralLimit = valueFor(
  revision4,
  "death-or-funeral-benefit",
  { death_benefit_status: "funeral_limited" },
);
assert.equal(missingFuneralLimit.state, "needs_policy_state");
assert.deepEqual(
  missingFuneralLimit.required_fields,
  ["remaining_funeral_benefit_limit"],
);
const funeralLimited = valueFor(
  revision4,
  "death-or-funeral-benefit",
  {
    death_benefit_status: "funeral_limited",
    remaining_funeral_benefit_limit: 300_000,
  },
);
assert.equal(funeralLimited.value, 300_000);
assert.equal(
  funeralLimited.formula_type,
  "face_amount_funeral_cap",
);
assert.equal(
  funeralLimited.gross_value_before_funeral_cap,
  1_000_000,
);
assert.equal(funeralLimited.funeral_benefit_limit, 300_000);
const revision4Scenarios = scenariosFor(revision4, {
  death_benefit_status: "standard_death",
});
assert.equal(revision4Scenarios.length, 3);
assert.deepEqual(
  revision4Scenarios.map((scenario) => scenario.value),
  [1_000_000, 1_000_000, 1_000_000],
);
assert(
  revision4Scenarios.every(
    (scenario) => scenario.additive_entry_ids.length === 0,
  ),
);

const revision7 = scheduleFor("206137M12B30107");
assert.deepEqual(
  model.policyStateRequirements(revision7).fields.map(
    (field) => field.key,
  ),
  [
    "death_benefit_status",
    "unexpired_premium_refund_amount",
  ],
);
assert.deepEqual(
  model.policyStateRequirements({
    ...revision7,
    policy_state: {
      death_benefit_status: "funeral_limited",
    },
  }).fields.map((field) => field.key),
  [
    "death_benefit_status",
    "remaining_funeral_benefit_limit",
    "unexpired_premium_refund_amount",
  ],
);
const refund = valueFor(
  revision7,
  "unexpired-premium-refund",
  {
    death_benefit_status: "standard_death",
    unexpired_premium_refund_amount: 12_345,
  },
);
assert.equal(refund.value, 12_345);
assert.equal(refund.state, "policy_state_value");
const zeroRefund = valueFor(
  revision7,
  "unexpired-premium-refund",
  {
    death_benefit_status: "standard_death",
    unexpired_premium_refund_amount: 0,
  },
);
assert.equal(zeroRefund.value, 0);
assert.equal(zeroRefund.state, "policy_state_value");
const revision7Scenarios = scenariosFor(revision7, {
  death_benefit_status: "standard_death",
  unexpired_premium_refund_amount: 12_345,
});
assert.equal(revision7Scenarios.length, 3);
assert.deepEqual(
  revision7Scenarios.map((scenario) => scenario.value),
  [1_012_345, 1_012_345, 1_012_345],
);
assert(
  revision7Scenarios.every(
    (scenario) =>
      scenario.additive_entry_ids.join(",") ===
      "unexpired-premium-refund",
  ),
);
assert.equal(
  revision7Scenarios.reduce(
    (total, scenario) => total + scenario.value,
    0,
  ),
  3_037_035,
  "scenario values remain separate alternatives and are never exposed as one combined claim",
);
const funeralScenarios = scenariosFor(revision7, {
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 300_000,
  unexpired_premium_refund_amount: 12_345,
});
assert.equal(
  funeralScenarios.find(
    (scenario) => scenario.event_key === "death_or_funeral",
  ).value,
  312_345,
);
assert.equal(
  funeralScenarios.find(
    (scenario) => scenario.event_key === "critical_disease",
  ).value,
  1_012_345,
);

const revision13 = scheduleFor(
  "206133MZ5B30121A11Z10000013",
);
assert.equal(
  entriesFor(revision13)["critical-disease-benefit"].name,
  "重度重大疾病保險金",
);
assert.equal(
  entriesFor(revision13)["disability-benefit"].name,
  "殘廢保險金",
);

const revision14 = scheduleFor(
  "206133MZ5B30121A11Z10000014",
);
assert.equal(
  entriesFor(revision14)["critical-disease-benefit"].name,
  "重度重大疾病保險金",
);
assert.equal(
  entriesFor(revision14)["disability-benefit"].name,
  "完全失能保險金",
);

console.log({
  status: "ok",
  batch_id: "tii-life-033",
  product_count: proposal.proposal_count,
  user_flow_cases: 34,
});

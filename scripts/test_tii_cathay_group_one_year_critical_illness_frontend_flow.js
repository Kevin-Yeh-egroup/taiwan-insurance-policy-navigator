const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-020-cathay-group-one-year-critical-illness-v236.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 18);

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

function valueFor(schedule, entryId, planName = "") {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    face_amount: 1_000_000,
    plan_name: planName,
  });
}

const revision0 = scheduleFor("204357M11AQD000");
assert.equal(model.selectionRequirements(revision0).mode, "face_amount");
assert.deepEqual(
  model.policyStateRequirements(revision0).fields,
  [],
);
for (const entryId of [
  "specific-critical-illness-benefit",
  "death-benefit",
  "disability-benefit",
]) {
  const result = valueFor(revision0, entryId);
  assert.equal(result.value, 1_000_000);
  assert.equal(result.state, "calculated");
}

const revision10 = scheduleFor(
  "204353MZ5BQD021A11Z10000010",
);
const revision10Requirements = model.selectionRequirements(
  revision10,
);
assert.equal(revision10Requirements.mode, "face_amount_plan");
assert.deepEqual(
  revision10Requirements.plan_options.map((plan) => plan.value),
  ["A", "B"],
);
assert.deepEqual(
  revision10Requirements.plan_options.map((plan) => plan.label),
  [
    "計畫 A（重大疾病等待 60 日）",
    "計畫 B（重大疾病等待 90 日）",
  ],
);
assert.deepEqual(
  model.policyStateRequirements(revision10).fields,
  [],
);
for (const planName of ["A", "B"]) {
  for (const entryId of [
    "specific-critical-illness-benefit",
    "death-benefit",
    "disability-benefit",
  ]) {
    assert.equal(
      valueFor(revision10, entryId, planName).value,
      1_000_000,
    );
  }
}

const revision17 = scheduleFor(
  "204353MZ5BQD021A11Z10000017",
);
assert.equal(
  revision17.version_characteristics.waiting_period_article_location,
  "article_3_definition",
);
assert.equal(
  revision17.version_characteristics.survival_condition_required,
  false,
);
assert.equal(
  entriesFor(revision17)["disability-benefit"].name,
  "失能保險金",
);

const scenarios = model.coverageEventScenarios({
  ...revision17,
  face_amount: 1_000_000,
  plan_name: "B",
});
assert.equal(scenarios.length, 3);
assert.deepEqual(
  scenarios.map((scenario) => scenario.value),
  [1_000_000, 1_000_000, 1_000_000],
);
assert.deepEqual(
  scenarios.map((scenario) => scenario.event_key),
  ["critical_illness", "death", "disability"],
);
assert(
  scenarios.every(
    (scenario) =>
      scenario.benefit_group_id ===
        "cathay-group-one-year-critical-illness-terminal-benefit" &&
      scenario.parts.length === 1 &&
      scenario.parts[0].aggregation_rule === "choose_one",
  ),
);

console.log({
  status: "ok",
  batch_id: "tii-life-020",
  product_count: proposal.proposal_count,
  user_flow_cases: 23,
});

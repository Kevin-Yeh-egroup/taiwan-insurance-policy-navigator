const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-anxin-100-critical-plan-v214.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 12);
assert.equal(proposal.proposed_count, 12);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectionFor(schedule, planName, policyState = {}) {
  return {
    ...schedule,
    plan_name: planName,
    policy_state: policyState,
  };
}

function entriesFor(selection) {
  const plan = selection.plan_options.find(
    (option) =>
      option.value === selection.plan_name ||
      option.label === selection.plan_name,
  );
  return Object.fromEntries(
    plan.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(selection, entryId) {
  return model.coverageValue(
    entriesFor(selection)[entryId],
    selection,
  );
}

const original = scheduleFor("209391R12B00100");
const latest = scheduleFor(
  "209351RZ5B00121A11Z10000011",
);

assert.deepEqual(
  model.selectionRequirements(original).fields,
  ["plan_name"],
);
assert.equal(model.selectionRequirements(original).mode, "plan");
assert.deepEqual(model.selectionRequirements(original).unit_fields, []);

const planTwo = selectionFor(original, "plan-2", {
  death_benefit_status: "standard_death",
});
assert.equal(
  valueFor(planTwo, "critical-disease-benefit").value,
  500_000,
);
assert.equal(
  valueFor(planTwo, "complete-disability-benefit").value,
  500_000,
);
assert.equal(
  valueFor(planTwo, "death-or-funeral-benefit").value,
  500_000,
);
assert.equal(
  valueFor(planTwo, "death-or-funeral-benefit").formula_type,
  "fixed_amount_standard_death",
);

const planThreeMissingStatus = selectionFor(latest, "計畫三");
const missingStatus = valueFor(
  planThreeMissingStatus,
  "death-or-funeral-benefit",
);
assert.equal(missingStatus.state, "needs_policy_state");
assert.deepEqual(missingStatus.required_fields, [
  "death_benefit_status",
]);

const planThreeStandard = selectionFor(latest, "計畫三", {
  death_benefit_status: "standard_death",
});
assert.equal(
  valueFor(
    planThreeStandard,
    "death-or-funeral-benefit",
  ).value,
  1_000_000,
);

const planThreeFuneral = selectionFor(latest, "plan-3", {
  death_benefit_status: "funeral_limited",
  remaining_funeral_benefit_limit: 240_000,
});
const funeral = valueFor(
  planThreeFuneral,
  "death-or-funeral-benefit",
);
assert.equal(funeral.value, 240_000);
assert.equal(funeral.state, "death_or_funeral_amount");
assert.equal(funeral.formula_type, "fixed_amount_funeral_cap");
assert.equal(funeral.gross_value_before_funeral_cap, 1_000_000);
assert.equal(funeral.funeral_benefit_limit, 240_000);

assert.deepEqual(
  model.policyStateRequirements(
    selectionFor(latest, "plan-3"),
  ).fields.map((field) => field.key),
  ["death_benefit_status"],
);
assert.deepEqual(
  model.policyStateRequirements(
    selectionFor(latest, "plan-3", {
      death_benefit_status: "funeral_limited",
    }),
  ).fields.map((field) => field.key),
  [
    "death_benefit_status",
    "remaining_funeral_benefit_limit",
  ],
);

const scenarios = model.coverageEventScenarios(planThreeStandard);
assert.equal(scenarios.length, 3);
assert.deepEqual(
  scenarios.map((scenario) => scenario.event_key),
  [
    "death_or_funeral",
    "complete_disability",
    "critical_disease",
  ],
);
assert.deepEqual(
  scenarios.map((scenario) => scenario.value),
  [1_000_000, 1_000_000, 1_000_000],
);
assert(
  scenarios.every(
    (scenario) => scenario.additive_entry_ids.length === 0,
  ),
);
assert.notEqual(
  scenarios.reduce(
    (total, scenario) => total + scenario.value,
    0,
  ),
  1_000_000,
  "scenario alternatives are not exposed as one additive claim total",
);

assert.equal(
  original.version_characteristics.disability_term,
  "完全殘廢",
);
assert.equal(
  latest.version_characteristics.disability_term,
  "完全失能",
);
assert.equal(
  original.version_characteristics.critical_disease_waiting_days,
  30,
);
assert.equal(
  latest.version_characteristics.critical_disease_waiting_days,
  0,
);

console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: 20,
});

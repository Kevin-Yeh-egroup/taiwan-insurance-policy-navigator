const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-050-fubon-group-one-year-critical-illness-v261.json",
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

function selectionFor(schedule, overrides = {}) {
  return {
    ...schedule,
    face_amount: 1_000_000,
    policy_state: {
      policy_effect_status_at_event: "active",
      death_benefit_status: "standard_death",
      remaining_funeral_benefit_limit: 0,
      ...(overrides.policy_state || {}),
    },
    ...overrides,
  };
}

const revision4 = scheduleFor("209357M12B00104");
assert.equal(model.selectionRequirements(revision4).mode, "face_amount");
assert.equal(
  revision4.version_characteristics.critical_disease_waiting_value,
  3,
);
assert.equal(
  revision4.version_characteristics.critical_disease_waiting_unit,
  "months",
);
assert.equal(
  entriesFor(revision4)["complete-disability-benefit"].name,
  "完全殘廢保險金",
);

const revision18 = scheduleFor(
  "209353MZ5B00121A11Z10000018",
);
const entries = entriesFor(revision18);
assert.equal(
  revision18.version_characteristics.critical_disease_waiting_value,
  90,
);
assert.equal(
  revision18.version_characteristics.critical_disease_waiting_unit,
  "days",
);
assert.equal(
  entries["complete-disability-benefit"].name,
  "完全失能保險金",
);

const missingStatus = model.coverageValue(
  entries["critical-illness-benefit"],
  {
    ...revision18,
    face_amount: 1_000_000,
  },
);
assert.equal(missingStatus.state, "needs_policy_state");
assert.deepEqual(
  missingStatus.required_fields,
  ["policy_effect_status_at_event"],
);

for (const entryId of [
  "critical-illness-benefit",
  "death-or-funeral-benefit",
  "complete-disability-benefit",
]) {
  const active = model.coverageValue(
    entries[entryId],
    selectionFor(revision18),
  );
  assert.equal(active.value, 1_000_000);

  const lapsed = model.coverageValue(
    entries[entryId],
    selectionFor(revision18, {
      policy_state: {
        policy_effect_status_at_event: "suspended_or_lapsed",
        death_benefit_status: "standard_death",
        remaining_funeral_benefit_limit: 0,
      },
    }),
  );
  assert.equal(lapsed.value, 0);
  assert.equal(lapsed.state, "not_eligible");
}

const funeralLimited = model.coverageValue(
  entries["death-or-funeral-benefit"],
  selectionFor(revision18, {
    policy_state: {
      policy_effect_status_at_event: "active",
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 300_000,
    },
  }),
);
assert.equal(funeralLimited.value, 300_000);
assert.equal(funeralLimited.state, "death_or_funeral_amount");

const scenarios = model.coverageEventScenarios(
  selectionFor(revision18),
);
assert.equal(scenarios.length, 3);
assert.deepEqual(
  scenarios.map((scenario) => scenario.value),
  [1_000_000, 1_000_000, 1_000_000],
);
assert(
  scenarios.every(
    (scenario) =>
      scenario.benefit_group_id ===
        "fubon-group-one-year-critical-illness-terminal-benefit" &&
      scenario.parts.length === 1 &&
      scenario.parts[0].aggregation_rule === "choose_one",
  ),
);

console.log({
  status: "ok",
  batch_id: "tii-life-050",
  product_count: proposal.proposal_count,
  user_flow_cases: 12,
});

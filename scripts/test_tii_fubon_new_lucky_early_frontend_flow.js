const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const proposalPath = path.join(
  __dirname,
  "..",
  "work",
  "tii-benefit-proposals",
  "tii-life-053-fubon-new-lucky-variable-universal-life-early-v227.json",
);
const proposal = JSON.parse(fs.readFileSync(proposalPath, "utf8"));

function scheduleFor(productId) {
  const item = proposal.proposals.find(
    (proposalItem) => proposalItem.product_id === productId,
  );
  assert.ok(item, productId);
  assert.equal(item.candidate_count, 1);
  return item.candidates[0].schedule;
}

function entriesFor(schedule) {
  return Object.fromEntries(
    schedule.coverage_entries.map((entry) => [entry.id, entry]),
  );
}

function valueFor(schedule, entryId, selection) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    ...selection,
  });
}

const revision10 = scheduleFor("209141M31A00110");
assert.equal(
  revision10.version_characteristics.maturity_age,
  105,
);
assert.equal(
  revision10.version_characteristics.semantic_phase,
  "legacy_under14_b_funeral_maturity105",
);
const revision10Entries = entriesFor(revision10);
assert.equal(
  revision10Entries["death-or-funeral-benefit"]
    .minor_account_value_return_age,
  undefined,
);

const revision10A = valueFor(
  revision10,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "A型",
    policy_state: {
      benefit_valuation_policy_account_value: 1_200_000,
    },
  },
);
assert.equal(revision10A.value, 1_200_000);
assert.equal(revision10A.state, "calculated");
assert.equal(
  model
    .policyStateFieldsForEntry(
      revision10Entries["death-or-funeral-benefit"],
      {
        face_amount: 1_000_000,
        plan_name: "A型",
        policy_state: {
          benefit_valuation_policy_account_value: 1_200_000,
        },
      },
    )
    .some((field) => field.key === "insured_age_at_event"),
  false,
);

const revision10BFuneral = valueFor(
  revision10,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: {
      benefit_valuation_policy_account_value: 800_000,
      death_benefit_status: "funeral_limited",
      remaining_funeral_benefit_limit: 300_000,
    },
  },
);
assert.equal(revision10BFuneral.value, 1_100_000);
assert.equal(revision10BFuneral.protected_amount, 1_000_000);
assert.equal(revision10BFuneral.account_value, 800_000);

const revision11 = scheduleFor("209141M31A00111");
const revision11Entries = entriesFor(revision11);
assert.deepEqual(Object.keys(revision11Entries).sort(), [
  "death-benefit",
  "maturity-benefit",
  "total-disability-benefit",
]);
assert.deepEqual(
  revision11.version_characteristics
    .funeral_limit_policy_type_options,
  [],
);
const revision11B = valueFor(revision11, "death-benefit", {
  face_amount: 1_000_000,
  plan_name: "B型",
  policy_state: {
    benefit_valuation_policy_account_value: 800_000,
  },
});
assert.equal(revision11B.value, 1_800_000);
assert.equal(revision11B.state, "calculated");

const revision29 = scheduleFor("209141M31A00129");
for (const entryId of [
  "death-or-funeral-benefit",
  "total-disability-benefit",
]) {
  const minor = valueFor(revision29, entryId, {
    face_amount: 1_000_000,
    plan_name: "B型",
    policy_state: {
      insured_age_at_event: 14,
      benefit_valuation_policy_account_value: 600_000,
    },
  });
  assert.equal(minor.value, 600_000);
  assert.equal(minor.state, "account_value_return");
}

const revision34 = scheduleFor("209141M31A00134");
assert.equal(
  revision34.version_characteristics.source_text_extractor,
  "windows_ocr",
);
assert.equal(
  revision34.version_characteristics.source_text_quality,
  "verified_windows_ocr_exact_hash",
);
const revision34A = valueFor(
  revision34,
  "death-or-funeral-benefit",
  {
    face_amount: 1_000_000,
    plan_name: "A型",
    policy_state: {
      insured_age_at_event: 35,
      benefit_valuation_policy_account_value: 1_200_000,
    },
  },
);
assert.equal(revision34A.value, 1_200_000);
assert.equal(revision34A.state, "calculated");

const maturity = valueFor(revision10, "maturity-benefit", {
  policy_state: {
    maturity_policy_account_value: 925_000,
    policy_values_converted_to_twd: true,
  },
});
assert.equal(maturity.value, 925_000);
assert.equal(maturity.state, "conditional_amount");

console.log({
  status: "ok",
  batch_id: "tii-life-053",
  exact_early_product_count: proposal.proposal_count,
  user_flow_cases: 9,
});

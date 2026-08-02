const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

const schedule = {
  selection_type: "policy_state",
  input_mode: "policy_state",
  selection_source: "terms",
  selection_label: "剩餘應繳保費",
  version_characteristics: {
    product_family:
      "allianz-new-peace-of-mind-premium-waiver-health-rider",
    family_fingerprint: "0b78b44efcf2e434e23825ed",
    cash_payout_available: false,
    required_policy_inputs: ["remaining_premium_amount"],
  },
  coverage_entries: [
    {
      id: "future-premium-waiver",
      name: "未來保險費豁免",
      amount: null,
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      limit_scope: "per_policy",
      aggregation_rule: "choose_one",
      source: "terms",
      note: "輸入剩餘應繳保費可估算非現金保障效果。",
      source_ref: "保單條款第十條豁免保險費",
      unit_key: "remaining_premium_amount",
      policy_state_keys: ["remaining_premium_amount"],
      result_kind: "non_cash_effect",
      amount_stage: "non_cash_estimate",
    },
  ],
};

function value(policyState) {
  return model.coverageValue(schedule.coverage_entries[0], {
    ...schedule,
    policy_state: policyState,
  });
}

const waiver = value({ remaining_premium_amount: 480_000 });
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 480_000);
assert.equal(waiver.policy_state_key, "remaining_premium_amount");

const missing = value({});
assert.equal(missing.state, "needs_policy_state");
assert.deepEqual(missing.required_fields, [
  "remaining_premium_amount",
]);

const requirements = model.policyStateRequirements(schedule);
assert.deepEqual(
  requirements.fields.map((field) => field.key),
  ["remaining_premium_amount"],
);
assert.equal(requirements.fields[0].type, "money");
assert.equal(requirements.fields[0].label, "未到期保險費合計");

assert.equal(
  schedule.coverage_entries.some(
    (entry) => entry.result_kind === "cash_payout",
  ),
  false,
);

console.log(
  "TII Allianz new peace-of-mind premium waiver frontend flow tests passed.",
);

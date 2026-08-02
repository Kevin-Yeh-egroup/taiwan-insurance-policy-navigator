const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entry(id, overrides) {
  return {
    id,
    name: id,
    basis: "policy_recorded_limit",
    calculation_basis: "policy_state_amount",
    amount_role: "payout",
    limit_scope: "per_policy",
    aggregation_rule: "separate",
    source: "terms",
    note: id,
    source_ref: "保險費的豁免",
    ...overrides,
  };
}

const waiverEligibility = {
  eligibility_state_key: "fubon_parent_child_waiver_event_status",
  ineligible_values: [
    "not_parent_policyholder",
    "no_covered_death_or_impairment",
    "confirmed_not_eligible",
  ],
  uncertain_values: ["uncertain"],
};
const schedule = {
  selection_type: "policy_state",
  input_mode: "policy_state",
  selection_source: "terms",
  version_characteristics: {
    product_family: "fubon-parent-child-premium-waiver-rider",
  },
  coverage_entries: [
    entry("future-premium-waiver", {
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      unit_key: "remaining_premium_amount",
      policy_state_keys: ["remaining_premium_amount"],
      result_kind: "non_cash_effect",
      amount_stage: "non_cash_estimate",
      ...waiverEligibility,
    }),
    entry("contract-own-waiver-periodic-refund", {
      unit_key: "fubon_parent_child_contract_own_waiver_refund_amount",
      policy_state_keys: [
        "fubon_parent_child_contract_own_waiver_refund_amount",
      ],
      eligibility_state_key: "fubon_parent_child_waiver_overlap_status",
      ineligible_values: [
        "eligible_other_waiver_only",
        "no_overlap",
        "event_not_eligible",
      ],
      uncertain_values: ["uncertain"],
    }),
    entry("other-waiver-rider-balance-refund", {
      unit_key: "fubon_parent_child_other_waiver_balance_refund_amount",
      policy_state_keys: [
        "fubon_parent_child_other_waiver_balance_refund_amount",
      ],
      eligibility_state_key: "fubon_parent_child_waiver_overlap_status",
      ineligible_values: [
        "eligible_own_contract_only",
        "no_overlap",
        "event_not_eligible",
      ],
      uncertain_values: ["uncertain"],
    }),
  ],
};

function value(entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find((candidate) => candidate.id === entryId),
    { ...schedule, policy_state: policyState },
  );
}

const policyState = {
  fubon_parent_child_waiver_event_status: "eligible_parent_death",
  remaining_premium_amount: 300_000,
  fubon_parent_child_waiver_overlap_status: "eligible_both",
  fubon_parent_child_contract_own_waiver_refund_amount: 24_000,
  fubon_parent_child_other_waiver_balance_refund_amount: 9_000,
};

const waiver = value("future-premium-waiver", policyState);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 300_000);
assert.equal(
  value("contract-own-waiver-periodic-refund", policyState).value,
  24_000,
);
assert.equal(
  value("other-waiver-rider-balance-refund", policyState).value,
  9_000,
);

const notParent = value("future-premium-waiver", {
  ...policyState,
  fubon_parent_child_waiver_event_status: "not_parent_policyholder",
});
assert.equal(notParent.state, "not_eligible");
assert.equal(notParent.value, 0);

const uncertain = value("future-premium-waiver", {
  ...policyState,
  fubon_parent_child_waiver_event_status: "uncertain",
});
assert.equal(uncertain.state, "needs_insurer_confirmation");

const ownOnly = {
  ...policyState,
  fubon_parent_child_waiver_overlap_status: "eligible_own_contract_only",
};
assert.equal(
  value("contract-own-waiver-periodic-refund", ownOnly).value,
  24_000,
);
assert.equal(
  value("other-waiver-rider-balance-refund", ownOnly).state,
  "not_eligible",
);

const noOverlap = value("contract-own-waiver-periodic-refund", {
  ...policyState,
  fubon_parent_child_waiver_overlap_status: "no_overlap",
});
assert.equal(noOverlap.state, "not_eligible");
assert.equal(noOverlap.value, 0);

const missingEligibility = value("future-premium-waiver", {
  ...policyState,
  fubon_parent_child_waiver_event_status: undefined,
});
assert.equal(missingEligibility.state, "needs_policy_state");
assert.deepEqual(missingEligibility.required_fields, [
  "fubon_parent_child_waiver_event_status",
]);

const requirementKeys = model
  .policyStateRequirements({ ...schedule, policy_state: policyState })
  .fields.map((field) => field.key);
for (const key of Object.keys(policyState)) {
  assert(requirementKeys.includes(key), key);
}
assert.equal(
  model.POLICY_STATE_FIELDS
    .fubon_parent_child_contract_own_waiver_refund_amount.type,
  "non_negative_money",
);
assert.equal(
  model.POLICY_STATE_FIELDS.fubon_parent_child_waiver_event_status.type,
  "choice",
);

console.log("TII Fubon parent-child premium waiver frontend tests passed.");

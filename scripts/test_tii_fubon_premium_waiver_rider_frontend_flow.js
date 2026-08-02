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
    source_ref: "第二章第二條",
    ...overrides,
  };
}

const coreEligibility = {
  eligibility_state_key: "fubon_premium_waiver_eligibility_status",
  ineligible_values: ["under_180_days", "not_eligible"],
  uncertain_values: ["uncertain"],
};
const schedule = {
  selection_type: "policy_state",
  input_mode: "policy_state",
  selection_source: "terms",
  version_characteristics: {
    product_family: "fubon-premium-waiver-rider",
  },
  coverage_entries: [
    entry("collected-premium-refund-within-180-days", {
      unit_key: "fubon_premium_waiver_collected_refund_amount",
      policy_state_keys: [
        "fubon_premium_waiver_collected_refund_amount",
      ],
      ...coreEligibility,
    }),
    entry("future-premium-waiver", {
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      unit_key: "remaining_premium_amount",
      policy_state_keys: ["remaining_premium_amount"],
      result_kind: "non_cash_effect",
      amount_stage: "non_cash_estimate",
      ...coreEligibility,
    }),
    entry("current-unexpired-premium-refund", {
      unit_key: "unexpired_premium_refund_amount",
      policy_state_keys: ["unexpired_premium_refund_amount"],
      eligibility_state_key:
        "fubon_premium_waiver_current_refund_status",
      ineligible_values: ["prior_waiver_already_effective"],
      uncertain_values: ["uncertain"],
    }),
    entry("overlapping-waiver-periodic-premium-refund", {
      unit_key: "fubon_premium_waiver_overlap_refund_amount",
      policy_state_keys: [
        "fubon_premium_waiver_overlap_refund_amount",
      ],
      eligibility_state_key: "fubon_premium_waiver_overlap_status",
      ineligible_values: ["no_overlapping_waiver"],
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
  fubon_premium_waiver_eligibility_status: "eligible_after_180_days",
  fubon_premium_waiver_collected_refund_amount: 36_000,
  remaining_premium_amount: 240_000,
  fubon_premium_waiver_current_refund_status:
    "eligible_no_prior_waiver",
  unexpired_premium_refund_amount: 12_000,
  fubon_premium_waiver_overlap_status: "eligible_overlapping_waiver",
  fubon_premium_waiver_overlap_refund_amount: 18_000,
};

assert.equal(
  value("collected-premium-refund-within-180-days", policyState).value,
  36_000,
);
const waiver = value("future-premium-waiver", policyState);
assert.equal(waiver.state, "premium_waiver_effect");
assert.equal(waiver.value, 240_000);
assert.equal(
  value("current-unexpired-premium-refund", policyState).value,
  12_000,
);
assert.equal(
  value("overlapping-waiver-periodic-premium-refund", policyState).value,
  18_000,
);

const missingEligibility = value("future-premium-waiver", {
  ...policyState,
  fubon_premium_waiver_eligibility_status: undefined,
});
assert.equal(missingEligibility.state, "needs_policy_state");
assert.deepEqual(missingEligibility.required_fields, [
  "fubon_premium_waiver_eligibility_status",
]);

const under180Days = value("future-premium-waiver", {
  ...policyState,
  fubon_premium_waiver_eligibility_status: "under_180_days",
});
assert.equal(under180Days.state, "not_eligible");
assert.equal(under180Days.value, 0);

const uncertain = value("future-premium-waiver", {
  ...policyState,
  fubon_premium_waiver_eligibility_status: "uncertain",
});
assert.equal(uncertain.state, "needs_insurer_confirmation");

const priorWaiver = value("current-unexpired-premium-refund", {
  ...policyState,
  fubon_premium_waiver_current_refund_status:
    "prior_waiver_already_effective",
});
assert.equal(priorWaiver.state, "not_eligible");
assert.equal(priorWaiver.value, 0);

const noOverlap = value(
  "overlapping-waiver-periodic-premium-refund",
  {
    ...policyState,
    fubon_premium_waiver_overlap_status: "no_overlapping_waiver",
  },
);
assert.equal(noOverlap.state, "not_eligible");
assert.equal(noOverlap.value, 0);

const requirementKeys = model
  .policyStateRequirements({ ...schedule, policy_state: policyState })
  .fields.map((field) => field.key);
for (const key of Object.keys(policyState)) {
  assert(requirementKeys.includes(key), key);
}
assert.equal(
  model.POLICY_STATE_FIELDS.fubon_premium_waiver_overlap_refund_amount.type,
  "non_negative_money",
);

console.log("TII Fubon premium waiver frontend flow tests passed.");

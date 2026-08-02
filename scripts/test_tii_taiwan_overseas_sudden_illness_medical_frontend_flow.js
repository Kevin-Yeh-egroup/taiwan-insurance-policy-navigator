const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

function entry(id, name, limitRatePercent, limitScope) {
  return {
    id,
    name,
    basis: "policy_recorded_limit",
    calculation_basis: "reimbursement_with_cap",
    amount_role: "limit",
    limit_scope: limitScope,
    aggregation_rule: "separate",
    limit_rate_percent: limitRatePercent,
    limit_rate_state_key:
      "overseas_medical_region_factor_percent",
    policy_state_keys: [
      "reimbursement_limit",
      "overseas_medical_region_factor_percent",
    ],
    source: "terms",
    note: name,
    source_ref: "條款第五至八條",
  };
}

const schedule = {
  selection_type: "policy_state",
  input_mode: "policy_state",
  selection_source: "terms",
  selection_label: "海外醫療保單限額與就醫地區",
  version_characteristics: {
    product_family: "taiwan-overseas-sudden-illness-medical",
  },
  coverage_entries: [
    entry(
      "inpatient",
      "海外突發疾病住院醫療費用限額",
      100,
      "per_hospitalization",
    ),
    entry(
      "emergency",
      "海外突發疾病急診醫療費用每次限額",
      20,
      "per_visit",
    ),
    entry(
      "outpatient",
      "海外突發疾病門診醫療費用每日限額",
      0.5,
      "per_day",
    ),
  ],
};

function value(entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find(
      (candidate) => candidate.id === entryId,
    ),
    {
      ...schedule,
      policy_state: policyState,
    },
  );
}

const northAmerica = {
  reimbursement_limit: 100_000,
  overseas_medical_region_factor_percent: "300",
};
assert.equal(value("inpatient", northAmerica).value, 300_000);
assert.equal(value("emergency", northAmerica).value, 60_000);
assert.equal(value("outpatient", northAmerica).value, 1_500);
assert.equal(value("outpatient", northAmerica).state, "policy_state_limit");

const europeJapan = {
  reimbursement_limit: 100_000,
  overseas_medical_region_factor_percent: "150",
};
assert.equal(value("inpatient", europeJapan).value, 150_000);
assert.equal(value("emergency", europeJapan).value, 30_000);
assert.equal(value("outpatient", europeJapan).value, 750);

const otherOverseas = {
  reimbursement_limit: 100_000,
  overseas_medical_region_factor_percent: "100",
};
assert.equal(value("inpatient", otherOverseas).value, 100_000);
assert.equal(value("emergency", otherOverseas).value, 20_000);
assert.equal(value("outpatient", otherOverseas).value, 500);

const missingLimit = value("inpatient", {
  overseas_medical_region_factor_percent: "300",
});
assert.equal(missingLimit.state, "needs_policy_state");
assert(missingLimit.required_fields.includes("reimbursement_limit"));

const missingRegion = value("inpatient", {
  reimbursement_limit: 100_000,
});
assert.equal(missingRegion.state, "needs_policy_state");
assert(
  missingRegion.required_fields.includes(
    "overseas_medical_region_factor_percent",
  ),
);

const requirementKeys = model
  .policyStateRequirements(schedule)
  .fields.map((field) => field.key);
assert(requirementKeys.includes("reimbursement_limit"));
assert(
  requirementKeys.includes(
    "overseas_medical_region_factor_percent",
  ),
);
assert.equal(
  model.POLICY_STATE_FIELDS
    .overseas_medical_region_factor_percent.type,
  "choice",
);
assert.deepEqual(
  model.POLICY_STATE_FIELDS.overseas_medical_region_factor_percent.options.map(
    (option) => option.value,
  ),
  ["300", "150", "100"],
);

console.log(
  "TII Taiwan overseas sudden illness medical frontend flow tests passed.",
);

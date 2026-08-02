const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const proposalPath = path.join(
  __dirname,
  "..",
  "work",
  "tii-benefit-proposals",
  "tii-life-026-china-new-lohas-whole-life-medical-health-v274.json",
);
const proposalPayload = JSON.parse(
  fs.readFileSync(proposalPath, "utf8"),
);

function scheduleFor(productId) {
  const proposal = proposalPayload.proposals.find(
    (candidate) => candidate.product_id === productId,
  );
  assert(proposal, productId);
  assert.equal(proposal.candidates.length, 1);
  return proposal.candidates[0].schedule;
}

function selectedPlan(schedule, planName) {
  const option = schedule.plan_options.find(
    (candidate) => candidate.value === planName,
  );
  assert(option, planName);
  return option;
}

function value(schedule, planName, entryId, policyState) {
  const option = selectedPlan(schedule, planName);
  const entry = option.coverage_entries.find(
    (candidate) => candidate.id === entryId,
  );
  assert(entry, entryId);
  return model.coverageValue(entry, {
    ...schedule,
    plan_name: planName,
    policy_state: policyState,
  });
}

const early = scheduleFor("205311M11A00800");
const modern = scheduleFor("205311M11A00805");
assert.equal(early.selection_type, "plan");
assert.equal(early.input_mode, "plan");
assert.equal(early.plan_options.length, 6);
assert.equal(
  early.version_characteristics.six_hour_treatment_qualifies,
  true,
);
assert.equal(
  modern.version_characteristics.six_hour_treatment_qualifies,
  false,
);
assert(
  selectedPlan(early, "plan-20").coverage_entries.some(
    (entry) =>
      entry.id === "emergency-medical-transport-benefit",
  ),
);
assert(
  !selectedPlan(modern, "plan-20").coverage_entries.some(
    (entry) =>
      entry.id === "emergency-medical-transport-benefit",
  ),
);

const medicalState = {
  china_new_lohas_eligible_hospital_daily_days: 3,
  intensive_care_days: 2,
  surgery_total_benefit_rate_percent: 216,
  outpatient_surgery_count: 2,
  cumulative_medical_benefit_paid_amount: 0,
};
assert.equal(
  value(
    early,
    "plan-20",
    "remaining-lifetime-medical-cap",
    medicalState,
  ).value,
  6_000_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "hospital-daily-benefit",
    medicalState,
  ).value,
  6_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "intensive-care-additional-benefit",
    medicalState,
  ).value,
  8_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "inpatient-surgery-benefit",
    medicalState,
  ).value,
  43_200,
);
assert.equal(
  value(
    early,
    "plan-20",
    "inpatient-surgery-nursing-benefit",
    medicalState,
  ).value,
  10_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "outpatient-surgery-benefit",
    medicalState,
  ).value,
  12_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "emergency-medical-transport-benefit",
    medicalState,
  ).value,
  4_000,
);

const nearlyExhaustedState = {
  ...medicalState,
  cumulative_medical_benefit_paid_amount: 5_998_000,
};
assert.equal(
  value(
    early,
    "plan-20",
    "hospital-daily-benefit",
    nearlyExhaustedState,
  ).value,
  2_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "remaining-lifetime-medical-cap",
    {
      cumulative_medical_benefit_paid_amount: 5_900_000,
    },
  ).value,
  100_000,
);

const terminalState = {
  paid_premium_total: 1_000_000,
  cumulative_medical_benefit_paid_amount: 200_000,
  death_benefit_status: "standard_death",
  death_age_band_status: "standard",
};
assert.equal(
  value(
    early,
    "plan-20",
    "terminal-age-return",
    terminalState,
  ).value,
  860_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "death-or-funeral-benefit",
    terminalState,
  ).value,
  860_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "minor-under-15-premium-refund",
    {
      paid_premium_total: 1_000_000,
      death_age_band_status: "under_15_refund",
    },
  ).value,
  1_000_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "age-15-before-16-death-premium-benefit",
    {
      paid_premium_total: 1_000_000,
      death_age_band_status:
        "age_15_before_age_16_anniversary",
    },
  ).value,
  1_000_000,
);
assert.equal(
  value(
    early,
    "plan-20",
    "death-unexpired-premium-refund",
    {
      unexpired_premium_refund_amount: 5_000,
    },
  ).value,
  5_000,
);

const requiredFields = model
  .policyStateRequirements({
    ...early,
    plan_name: "plan-20",
    policy_state: {},
  })
  .fields.map((field) => field.key);
for (const key of [
  "china_new_lohas_eligible_hospital_daily_days",
  "intensive_care_days",
  "surgery_total_benefit_rate_percent",
  "outpatient_surgery_count",
  "cumulative_medical_benefit_paid_amount",
  "paid_premium_total",
  "death_age_band_status",
  "unexpired_premium_refund_amount",
]) {
  assert(requiredFields.includes(key), key);
}

console.log(
  "TII China new Lohas whole-life medical health "
    + "frontend flow tests passed.",
);

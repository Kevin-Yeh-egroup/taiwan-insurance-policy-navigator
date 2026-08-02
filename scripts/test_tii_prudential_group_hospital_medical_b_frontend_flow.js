const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-014-prudential-group-hospital-medical-b-v256.json",
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

function valueFor(schedule, entryId, policyState) {
  return model.coverageValue(
    schedule.coverage_entries.find((entry) => entry.id === entryId),
    { ...schedule, policy_state: policyState },
  );
}

function requiredFieldKeys(schedule) {
  return model
    .policyStateRequirements(schedule)
    .fields.map((field) => field.key);
}

const currentSchedule = scheduleFor("203317M11A00202");
const currentState = {
  hospital_daily_amount: 2_000,
  surgery_fee_benefit_limit: 100_000,
  inpatient_medical_benefit_limit: 150_000,
  hospitalization_days: 10,
  post_discharge_outpatient_day_count: 4,
  inpatient_surgery_expense: 90_000,
  inpatient_medical_expense: 200_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 75,
  medical_claim_receipt_status: "original_receipt",
};

assert.equal(
  model.selectionRequirements(currentSchedule).mode,
  "policy_state",
);
assert.deepEqual(
  new Set(requiredFieldKeys(currentSchedule)),
  new Set([
    "hospital_daily_amount",
    "surgery_fee_benefit_limit",
    "inpatient_medical_benefit_limit",
    "hospitalization_days",
    "post_discharge_outpatient_day_count",
    "medical_claim_receipt_status",
  ]),
);
assert.deepEqual(
  new Set(
    requiredFieldKeys({
      ...currentSchedule,
      policy_state: currentState,
    }),
  ),
  new Set(Object.keys(currentState)),
);
assert.equal(
  valueFor(
    currentSchedule,
    "hospital-room-daily-benefit",
    currentState,
  ).value,
  20_000,
);
assert.equal(
  valueFor(
    currentSchedule,
    "surgery-expense-benefit",
    currentState,
  ).value,
  75_000,
);
assert.equal(
  valueFor(
    currentSchedule,
    "inpatient-medical-expense-benefit",
    currentState,
  ).value,
  150_000,
);
assert.equal(
  valueFor(
    currentSchedule,
    "post-discharge-outpatient-benefit",
    currentState,
  ).value,
  4_000,
);

const currentNonCovered = {
  ...currentState,
  national_health_insurance_payment_status: "not_covered",
};
assert.equal(
  valueFor(
    currentSchedule,
    "surgery-expense-benefit",
    currentNonCovered,
  ).value,
  58_500,
);
assert.equal(
  valueFor(
    currentSchedule,
    "inpatient-medical-expense-benefit",
    currentNonCovered,
  ).value,
  130_000,
);

const noOriginalReceipt = {
  ...currentState,
  medical_claim_receipt_status: "no_original_receipt_daily_cash",
};
for (const entryId of [
  "surgery-expense-benefit",
  "inpatient-medical-expense-benefit",
]) {
  const excluded = valueFor(
    currentSchedule,
    entryId,
    noOriginalReceipt,
  );
  assert.equal(excluded.value, 0);
  assert.equal(excluded.state, "not_eligible");
}
assert.equal(
  valueFor(
    currentSchedule,
    "hospital-room-daily-benefit",
    noOriginalReceipt,
  ).value,
  20_000,
);
assert.equal(
  valueFor(
    currentSchedule,
    "post-discharge-outpatient-benefit",
    noOriginalReceipt,
  ).value,
  4_000,
);

const cappedHospital = valueFor(
  currentSchedule,
  "hospital-room-daily-benefit",
  { ...currentState, hospitalization_days: 90 },
);
assert.equal(cappedHospital.value, 120_000);
assert.equal(cappedHospital.eligible_quantity, 60);
assert.equal(cappedHospital.quantity_cap, 60);

const missingSurgeryLimit = valueFor(
  currentSchedule,
  "surgery-expense-benefit",
  { ...currentState, surgery_fee_benefit_limit: undefined },
);
assert.equal(missingSurgeryLimit.state, "needs_policy_state");
assert.ok(
  missingSurgeryLimit.required_fields.includes(
    "surgery_fee_benefit_limit",
  ),
);

const legacySchedule = scheduleFor("203317M11A00200");
const legacyState = {
  hospital_daily_amount: 2_000,
  surgery_fee_benefit_limit: 100_000,
  inpatient_medical_benefit_limit: 150_000,
  hospitalization_total_benefit_limit: 300_000,
  hospitalization_days: 70,
  post_discharge_outpatient_visit_count: 4,
  inpatient_surgery_expense: 90_000,
  inpatient_medical_expense: 200_000,
  national_health_insurance_payment_status: "covered",
  surgery_benefit_rate_percent: 75,
};

assert.ok(
  !requiredFieldKeys(legacySchedule).includes(
    "medical_claim_receipt_status",
  ),
);
assert.equal(
  valueFor(
    legacySchedule,
    "hospital-room-daily-benefit",
    legacyState,
  ).value,
  140_000,
);
assert.equal(
  valueFor(
    legacySchedule,
    "post-discharge-outpatient-benefit",
    legacyState,
  ).value,
  4_000,
);
assert.equal(
  valueFor(
    legacySchedule,
    "hospitalization-total-benefit-limit",
    legacyState,
  ).value,
  300_000,
);
assert.equal(
  valueFor(
    legacySchedule,
    "hospitalization-total-benefit-limit",
    {
      ...legacyState,
      national_health_insurance_payment_status: "not_covered",
    },
  ).value,
  180_000,
);

console.log({
  status: "ok",
  batch_id: "tii-life-014",
  product_count: proposal.proposal_count,
  current_flow: "limits-and-claim-state",
  legacy_flow: "limits-and-aggregate-cap",
});

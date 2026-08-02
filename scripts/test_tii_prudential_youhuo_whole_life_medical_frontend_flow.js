const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-014-prudential-youhuo-whole-life-medical-v293.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 13);
assert.equal(proposal.proposed_count, 13);
assert.equal(proposal.manual_review_count, 0);

const byProduct = Object.fromEntries(
  proposal.proposals.map((item) => [
    item.product_id,
    item.candidates[0].schedule,
  ]),
);
const oldSchedule = byProduct["203311M11A00200"];
const newbornSchedule = byProduct["203311M11A00203"];
const modernSchedule = byProduct["203311MZ1A00123A11Z10000012"];
const eventKey = "prudential_youhuo_event_status";

function selected(schedule, selection, policyState) {
  return { ...schedule, ...selection, policy_state: policyState };
}

function entries(selection) {
  const effective =
    selection.plan_options?.find(
      (option) => option.value === selection.plan_name,
    )?.coverage_entries || selection.coverage_entries;
  return Object.fromEntries(effective.map((entry) => [entry.id, entry]));
}

function value(selection, entryId) {
  return model.coverageValue(entries(selection)[entryId], selection);
}

assert.equal(model.selectionRequirements(oldSchedule).mode, "plan");
assert.equal(model.selectionRequirements(modernSchedule).mode, "unit");
assert.equal(model.selectionRequirements(modernSchedule).label, "保險計劃數");

const oldMedical = selected(
  oldSchedule,
  { plan_name: "HCL-10" },
  {
    [eventKey]: "eligible_medical_benefit",
    prudential_youhuo_bonus_factor_percent: "100",
    cumulative_medical_benefit_paid_amount: 0,
    hospitalization_days: 5,
    intensive_care_days: 2,
    prudential_youhuo_surgery_rate_percent: 250,
    outpatient_surgery_count: 2,
  },
);
assert.equal(value(oldMedical, "hospital-daily-benefit").value, 5_000);
assert.equal(
  value(oldMedical, "intensive-care-additional-benefit").value,
  4_000,
);
assert.equal(value(oldMedical, "inpatient-surgery-benefit").value, 50_000);
assert.equal(
  value(oldMedical, "inpatient-surgery-nursing-benefit").value,
  5_000,
);
assert.equal(value(oldMedical, "outpatient-surgery-benefit").value, 6_000);
assert.equal(
  value(oldMedical, "emergency-medical-transport-benefit").value,
  2_000,
);

const oldBonus = selected(
  oldSchedule,
  { plan_name: "HCL-10" },
  {
    ...oldMedical.policy_state,
    prudential_youhuo_bonus_factor_percent: "130",
  },
);
assert.equal(value(oldBonus, "hospital-daily-benefit").value, 6_500);
assert.equal(value(oldBonus, "inpatient-surgery-benefit").value, 65_000);

const nearLifetimeCap = selected(
  oldSchedule,
  { plan_name: "HCL-10" },
  {
    ...oldBonus.policy_state,
    cumulative_medical_benefit_paid_amount: 2_980_000,
  },
);
assert.equal(value(nearLifetimeCap, "inpatient-surgery-benefit").value, 20_000);

const modernMedical = selected(
  modernSchedule,
  { unit_count: 10 },
  {
    [eventKey]: "eligible_medical_benefit",
    prudential_youhuo_bonus_factor_percent: "100",
    cumulative_medical_benefit_paid_amount: 0,
    hospitalization_days: 3,
    intensive_care_days: 1,
    prudential_youhuo_surgery_rate_percent: 490,
    outpatient_surgery_count: 1,
  },
);
assert.equal(value(modernMedical, "hospital-daily-benefit").value, 3_000);
assert.equal(value(modernMedical, "inpatient-surgery-benefit").value, 98_000);
assert.equal(
  value(modernMedical, "inpatient-surgery-aggregate-cap").value,
  98_000,
);
assert.equal(
  value(modernMedical, "remaining-lifetime-medical-cap").value,
  3_000_000,
);
assert.equal(
  entries(modernMedical)["emergency-medical-transport-benefit"],
  undefined,
);

const critical = selected(
  modernSchedule,
  { unit_count: 10 },
  {
    [eventKey]: "eligible_initial_critical_or_specific_illness",
    remaining_premium_amount: 180_000,
  },
);
assert.equal(
  value(critical, "initial-critical-or-specific-illness-benefit").value,
  300_000,
);
assert.equal(value(critical, "future-premium-waiver").value, 180_000);
assert.equal(value(critical, "future-premium-waiver").result_kind, "non_cash_effect");
assert.equal(value(critical, "hospital-daily-benefit").state, "not_eligible");

const earlyRefund = selected(
  modernSchedule,
  { unit_count: 10 },
  {
    [eventKey]: "initial_30_day_sickness_death_refund",
    prudential_youhuo_initial_sickness_death_refund_amount: 22_000,
  },
);
assert.equal(
  value(earlyRefund, "initial-sickness-death-premium-refund").value,
  22_000,
);

const uncertain = selected(
  modernSchedule,
  { unit_count: 10 },
  { [eventKey]: "not_eligible_or_uncertain" },
);
assert.equal(
  value(uncertain, "hospital-daily-benefit").state,
  "needs_insurer_confirmation",
);
assert.equal(
  value(uncertain, "hospital-daily-benefit").confirmation_reason,
  "claim_eligibility_uncertain",
);

const oldNewborn = selected(
  oldSchedule,
  { plan_name: "HCL-10" },
  {
    [eventKey]: "eligible_newborn_screening_exception",
    prudential_youhuo_bonus_factor_percent: "100",
    cumulative_medical_benefit_paid_amount: 0,
    hospitalization_days: 2,
  },
);
assert.equal(value(oldNewborn, "hospital-daily-benefit").state, "not_eligible");
const eligibleNewborn = selected(
  newbornSchedule,
  { plan_name: "HCL-10" },
  oldNewborn.policy_state,
);
assert.equal(value(eligibleNewborn, "hospital-daily-benefit").value, 2_000);

assert.equal(
  value(
    selected(modernSchedule, { unit_count: 1.5 }, modernMedical.policy_state),
    "hospital-daily-benefit",
  ).state,
  "needs_unit_count",
);
assert.equal(
  value(
    selected(modernSchedule, { unit_count: 10 }, {
      ...modernMedical.policy_state,
      prudential_youhuo_surgery_rate_percent: 491,
    }),
    "inpatient-surgery-benefit",
  ).state,
  "needs_policy_state",
);

const modernRequirements = model.policyStateRequirements(modernMedical);
const surgeryField = modernRequirements.fields.find(
  (field) => field.key === "prudential_youhuo_surgery_rate_percent",
);
assert.equal(surgeryField.min, 2);
assert.equal(surgeryField.max, 490);

console.log({
  status: "ok",
  batch_id: proposal.batch_id,
  product_count: proposal.proposal_count,
  user_flow_cases: 22,
});

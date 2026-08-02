const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-086-hongtai-group-hospital-medical-fixed-v284.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 14);

function scheduleFor(productId) {
  return proposal.proposals.find(
    (item) => item.product_id === productId,
  ).candidates[0].schedule;
}

function selectedSchedule(schedule, unitCount, policyState = {}) {
  return {
    ...schedule,
    unit_count: unitCount,
    policy_state: policyState,
  };
}

function entriesFor(item) {
  return Object.fromEntries(
    model.effectiveCoverageEntries(item).map((entry) => [
      entry.id,
      entry,
    ]),
  );
}

const revision7 = scheduleFor("217313M11A00107");
assert.equal(model.selectionRequirements(revision7).mode, "unit");
assert.deepEqual(model.selectionRequirements(revision7).fields, [
  "unit_count",
]);

const ordinary = selectedSchedule(revision7, 3, {
  hongtai_group_fixed_event_status:
    "eligible_nonoccupational_accident",
  general_ward_days: 5,
  intensive_care_days: 2,
  burn_unit_days: 1,
  home_recuperation_days: 2,
  hongtai_group_fixed_surgery_addendum_status: "attached",
  surgery_benefit_rate_percent: 50,
  unexpired_premium_refund_amount: 1_234,
});
const ordinaryEntries = entriesFor(ordinary);
assert.equal(
  model.coverageValue(
    ordinaryEntries["daily-room-medical-benefit"],
    ordinary,
  ).value,
  1_500,
);
assert.equal(
  model.coverageValue(
    ordinaryEntries["daily-intensive-care-medical-benefit"],
    ordinary,
  ).value,
  1_200,
);
assert.equal(
  model.coverageValue(
    ordinaryEntries["daily-burn-unit-medical-benefit"],
    ordinary,
  ).value,
  600,
);
assert.equal(
  model.coverageValue(
    ordinaryEntries["daily-home-recuperation-benefit"],
    ordinary,
  ).value,
  600,
);
assert.equal(
  model.coverageValue(
    ordinaryEntries[
      "inpatient-or-outpatient-surgery-medical-benefit"
    ],
    ordinary,
  ).value,
  4_500,
);
assert.equal(
  model.coverageValue(
    ordinaryEntries["unexpired-premium-refund"],
    ordinary,
  ).value,
  1_234,
);

const occupational = selectedSchedule(revision7, 3, {
  hongtai_group_fixed_event_status:
    "eligible_occupational_injury",
  general_ward_days: 5,
  intensive_care_days: 0,
  burn_unit_days: 0,
  home_recuperation_days: 0,
});
assert.equal(
  model.coverageValue(
    entriesFor(occupational)["daily-room-medical-benefit"],
    occupational,
  ).value,
  2_250,
);

const noSurgeryAddendum = selectedSchedule(revision7, 3, {
  hongtai_group_fixed_event_status:
    "eligible_nonoccupational_accident",
  hongtai_group_fixed_surgery_addendum_status: "not_attached",
  surgery_benefit_rate_percent: 50,
});
assert.equal(
  model.coverageValue(
    entriesFor(noSurgeryAddendum)[
      "inpatient-or-outpatient-surgery-medical-benefit"
    ],
    noSurgeryAddendum,
  ).state,
  "not_eligible",
);

const waitingNotMet = selectedSchedule(revision7, 3, {
  hongtai_group_fixed_event_status: "disease_waiting_not_met",
  general_ward_days: 5,
});
assert.equal(
  model.coverageValue(
    entriesFor(waitingNotMet)["daily-room-medical-benefit"],
    waitingNotMet,
  ).state,
  "not_eligible",
);

const uncertain = selectedSchedule(revision7, 3, {
  hongtai_group_fixed_event_status: "uncertain",
  general_ward_days: 5,
});
assert.equal(
  model.coverageValue(
    entriesFor(uncertain)["daily-room-medical-benefit"],
    uncertain,
  ).state,
  "needs_insurer_confirmation",
);

const missingEvent = selectedSchedule(revision7, 3, {
  general_ward_days: 5,
});
assert.deepEqual(
  model.coverageValue(
    entriesFor(missingEvent)["daily-room-medical-benefit"],
    missingEvent,
  ).required_fields,
  ["hongtai_group_fixed_event_status"],
);

const fractionalUnits = selectedSchedule(revision7, 2.5, {
  hongtai_group_fixed_event_status:
    "eligible_nonoccupational_accident",
  general_ward_days: 1,
});
assert.equal(
  model.coverageValue(
    entriesFor(fractionalUnits)["daily-room-medical-benefit"],
    fractionalUnits,
  ).state,
  "needs_unit_count",
);

const revision4 = scheduleFor("217317M11A00104");
const oldNewborn = selectedSchedule(revision4, 3, {
  hongtai_group_fixed_event_status:
    "eligible_newborn_screening_exception",
  general_ward_days: 1,
});
assert.equal(
  model.coverageValue(
    entriesFor(oldNewborn)["daily-room-medical-benefit"],
    oldNewborn,
  ).state,
  "not_eligible",
);

const revision5 = scheduleFor("217317M11A00105");
const newNewborn = selectedSchedule(revision5, 3, {
  hongtai_group_fixed_event_status:
    "eligible_newborn_screening_exception",
  general_ward_days: 1,
});
assert.equal(
  model.coverageValue(
    entriesFor(newNewborn)["daily-room-medical-benefit"],
    newNewborn,
  ).value,
  300,
);

assert.equal(model.POLICY_STATE_FIELDS.home_recuperation_days.type, "integer");
assert.equal(
  model.POLICY_STATE_FIELDS.hongtai_group_fixed_event_status.type,
  "choice",
);
assert.equal(
  model.POLICY_STATE_FIELDS
    .hongtai_group_fixed_surgery_addendum_status.type,
  "choice",
);

console.log({
  status: "ok",
  batch_id: "tii-life-086",
  product_count: proposal.proposal_count,
  user_flow_cases: 13,
});

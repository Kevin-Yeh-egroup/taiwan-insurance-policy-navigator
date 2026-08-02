const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../coverage-model.js");

const ROOT = path.resolve(__dirname, "..");
const proposal = JSON.parse(
  fs.readFileSync(
    path.join(
      ROOT,
      "work/tii-benefit-proposals/tii-life-032-nanshan-hospital-medical-rider-v237.json",
    ),
    "utf8",
  ),
);

assert.equal(proposal.proposal_count, 18);

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

function valueFor(schedule, entryId, unitCount = 10) {
  return model.coverageValue(entriesFor(schedule)[entryId], {
    ...schedule,
    unit_count: unitCount,
  });
}

function assertCommonUnitLimits(schedule) {
  assert.equal(model.selectionRequirements(schedule).mode, "unit");
  assert.deepEqual(
    model.policyStateRequirements(schedule).fields,
    [],
  );
  assert.equal(
    valueFor(schedule, "daily-room-expense-reimbursement").value,
    1_000,
  );
  assert.equal(
    valueFor(schedule, "icu-room-expense-reimbursement").value,
    2_000,
  );
  assert.equal(
    valueFor(
      schedule,
      "surgery-stay-room-expense-reimbursement",
    ).value,
    1_500,
  );
  assert.equal(
    valueFor(schedule, "hospital-misc-surgery-reimbursement")
      .value,
    50_000,
  );
  assert.equal(
    valueFor(schedule, "major-surgery-misc-reimbursement").value,
    150_000,
  );
  assert.equal(
    valueFor(
      schedule,
      "injury-pre-admission-emergency-sublimit",
    ).value,
    5_000,
  );
  assert.equal(
    valueFor(
      schedule,
      "pre-post-hospital-outpatient-reimbursement",
    ).value,
    500,
  );
  assert.equal(
    valueFor(
      schedule,
      "accident-accessory-per-item-sublimit",
    ).value,
    2_000,
  );
  assert.equal(
    valueFor(
      schedule,
      "accident-prosthetic-accessory-aggregate-limit",
    ).value,
    10_000,
  );
}

const revision0 = scheduleFor("206311R11A30100");
assertCommonUnitLimits(revision0);
assert(
  entriesFor(revision0)["hospital-cash-alternative-daily"],
);
assert.equal(
  valueFor(revision0, "hospital-cash-alternative-daily").value,
  1_000,
);
assert.equal(
  entriesFor(revision0)[
    "unnotified-other-insurance-daily-fallback"
  ],
  undefined,
);
assert.equal(
  entriesFor(revision0)[
    "unadmitted-six-hour-emergency-reimbursement"
  ],
  undefined,
);

const revision3 = scheduleFor("206311R11A30103");
assertCommonUnitLimits(revision3);
assert.equal(
  entriesFor(revision3)["hospital-cash-alternative-daily"],
  undefined,
);
assert.equal(
  valueFor(
    revision3,
    "unnotified-other-insurance-daily-fallback",
  ).value,
  1_000,
);
assert.equal(
  valueFor(
    revision3,
    "unadmitted-six-hour-emergency-reimbursement",
  ).value,
  5_000,
);

const revision9 = scheduleFor("206311R11A30109");
assertCommonUnitLimits(revision9);
assert.equal(
  valueFor(revision9, "hospital-cash-alternative-daily").value,
  1_000,
);
assert.equal(
  valueFor(
    revision9,
    "unnotified-other-insurance-daily-fallback",
  ).value,
  1_000,
);

const revision14 = scheduleFor("206311R11A30114");
assertCommonUnitLimits(revision14);
assert.equal(
  revision14.version_characteristics
    .post_expiry_readmission_excluded,
  true,
);
assert(
  entriesFor(revision14)[
    "unadmitted-six-hour-emergency-reimbursement"
  ],
);

const revision15 = scheduleFor("206311R11A30115");
assertCommonUnitLimits(revision15);
assert.equal(
  revision15.version_characteristics.day_hospital_excluded,
  true,
);
assert.equal(
  entriesFor(revision15)[
    "unadmitted-six-hour-emergency-reimbursement"
  ],
  undefined,
);

const missingUnits = model.coverageValue(
  entriesFor(revision15)[
    "daily-room-expense-reimbursement"
  ],
  revision15,
);
assert.equal(missingUnits.state, "needs_unit_count");

console.log({
  status: "ok",
  batch_id: "tii-life-032",
  product_count: proposal.proposal_count,
  user_flow_cases: 52,
});

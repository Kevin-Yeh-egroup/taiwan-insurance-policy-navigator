const assert = require("node:assert/strict");
const model = require("../coverage-model.js");

const productVersionFamilyCases = [
  ["安泰人壽防癌終身健康保險附約", "安泰人壽防癌終身健康保險附約"],
  ["安泰人壽防癌終身健康保險附約(第1次部份變更)", "安泰人壽防癌終身健康保險附約"],
  ["安泰人壽防癌終身健康保險附約（第4次部分變更）", "安泰人壽防癌終身健康保險附約"],
  ["範例保險（97.03.11第4次部分變更）", "範例保險"],
  ["範例保險(第2版修訂)", "範例保險"],
  ["防癌定期保險(B型)", "防癌定期保險(b型)"],
];

for (const [name, expected] of productVersionFamilyCases) {
  assert.equal(model.productVersionFamilyName(name), expected);
}

const selectionCases = [
  [{ selection_type: "face_amount", selection_source: "terms" }, "face_amount"],
  [{ selection_type: "plan", plan_options: [{ value: "B", label: "計畫 B", coverage_entries: [] }] }, "plan"],
  [{ selection_type: "unit", selection_source: "terms" }, "unit"],
  [{ selection_type: "multi_unit", selection_source: "terms", unit_fields: [{ key: "a", label: "A 單位" }, { key: "b", label: "B 單位" }] }, "multi_unit"],
  [{ selection_type: "plan_unit", selection_source: "terms" }, "plan_unit"],
  [{ selection_type: "fixed", selection_source: "terms" }, "fixed"],
  [{ selection_type: "unknown" }, "unknown"],
  [{ plan_options: [{ value: "B", label: "計畫 B", coverage_entries: [] }] }, "unknown"],
  [{ selection_mode: "plan", plan_name: "B" }, "unknown"],
  [{ unit_count: 2 }, "unknown"],
  [{ face_amount: 1_000_000 }, "unknown"],
  [{}, "unknown"],
];

for (const [item, expected] of selectionCases) {
  assert.equal(model.selectionMode(item), expected, `selection mode should be ${expected}`);
}

const customSelection = model.selectionRequirements({
  selection_type: "face_amount",
  selection_source: "terms",
  selection_label: "住院保險金日額",
  selection_guidance: "請填保單首頁記載的住院保險金日額。",
});
assert.equal(customSelection.label, "住院保險金日額");
assert.equal(customSelection.guidance, "請填保單首頁記載的住院保險金日額。");

const multiUnitSelection = model.selectionRequirements({
  selection_type: "multi_unit",
  selection_source: "terms",
  unit_fields: [
    { key: "hospital", label: "住院單位數" },
    { key: "surgery", label: "手術單位數" },
  ],
});
assert.deepEqual(multiUnitSelection.fields, ["unit_counts"]);
assert.deepEqual(multiUnitSelection.unit_fields, [
  { key: "hospital", label: "住院單位數" },
  { key: "surgery", label: "手術單位數" },
]);

const calculationCases = [
  [
    { amount: 1_000_000, calculation_basis: "fixed_amount", source: "terms" },
    {},
    { value: 1_000_000, state: "calculated" },
  ],
  [
    { amount: 1_000_000, calculation_basis: "percentage_of_base", rate: 0.5, source: "terms" },
    {},
    { value: 500_000, state: "calculated" },
  ],
  [
    { amount: 1_000, calculation_basis: "percentage_of_base", rate_percent: 500, limit_scope: "per_surgery", source: "terms" },
    {},
    { value: 5_000, state: "calculated" },
  ],
  [
    { amount: 10_000, basis: "per_unit", calculation_basis: "percentage_of_base", rate_percent: 300, limit_scope: "per_surgery", source: "terms" },
    { unit_count: 2 },
    { value: 60_000, state: "calculated" },
  ],
  [
    { amount: 10_000, basis: "per_unit", calculation_basis: "percentage_of_base", rate_min_percent: 2, rate_max_percent: 300, limit_scope: "per_surgery", source: "terms" },
    {},
    { value: null, state: "needs_unit_count" },
  ],
  [
    { amount: 1_000_000, calculation_basis: "percentage_of_base", rate_min_percent: 5, rate_max_percent: 100, source: "terms" },
    {},
    { value: null, state: "needs_rate_table" },
  ],
  [
    { amount: 1_000, calculation_basis: "per_unit", source: "terms" },
    { unit_count: 3 },
    { value: 3_000, state: "calculated" },
  ],
  [
    { amount: 1_000, calculation_basis: "per_unit_per_day", source: "terms" },
    { unit_count: 2 },
    { value: 2_000, state: "daily_rate" },
  ],
  [
    { amount: 500, calculation_basis: "per_unit_per_day", unit_key: "hospital", source: "terms" },
    { unit_counts: { hospital: 3, surgery: 2 } },
    { value: 1_500, state: "daily_rate" },
  ],
  [
    { amount: 1_600, calculation_basis: "per_day", source: "terms" },
    {},
    { value: 1_600, state: "daily_rate" },
  ],
  [
    { amount: 200_000, calculation_basis: "reimbursement_with_cap", amount_role: "limit", source: "terms" },
    {},
    { value: 200_000, state: "benefit_limit" },
  ],
  [
    { amount: 3_000, basis: "per_unit", calculation_basis: "reimbursement_with_cap", amount_role: "limit", source: "terms" },
    { unit_count: 3 },
    { value: 9_000, state: "benefit_limit" },
  ],
  [
    { amount: 100, basis: "daily_per_unit", calculation_basis: "reimbursement_with_cap", amount_role: "limit", source: "terms" },
    {},
    { value: null, state: "needs_unit_count" },
  ],
  [
    { basis: "policy_recorded_limit", calculation_basis: "reimbursement_with_cap", amount_role: "limit", source: "terms" },
    { face_amount: 30_000 },
    { value: 30_000, state: "benefit_limit" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_actual_expense_with_cap",
      amount_role: "payout",
      rate_percent: 65,
      source: "terms",
    },
    { face_amount: 30_000 },
    { value: 30_000, state: "benefit_limit" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_actual_expense_with_cap",
      amount_role: "payout",
      rate_percent: 65,
      source: "terms",
    },
    {},
    { value: null, state: "missing_amount" },
  ],
  [
    { calculation_basis: "table_multiplier", multiplier: 2, source: "terms" },
    { face_amount: 1_000_000 },
    { value: 2_000_000, state: "calculated" },
  ],
  [
    { calculation_basis: "percentage_of_base", rate_percent: 100, source: "terms" },
    { face_amount: 2_000 },
    { value: 2_000, state: "calculated" },
  ],
  [
    { amount: 100_000, calculation_basis: "tiered_or_stepped", source: "terms" },
    {},
    { value: null, state: "reference_only" },
  ],
  [
    {
      amount: 50_000,
      basis: "per_unit",
      calculation_basis: "tiered_or_stepped",
      amount_tiers: [
        { label: "第 1 至 20 保單年度", amount: 50_000 },
        { label: "第 21 保單年度起", amount: 75_000 },
      ],
      source: "terms",
    },
    { unit_count: 2 },
    { value: null, state: "tiered_values" },
  ],
  [
    { amount: 1_000_000, calculation_basis: "additional_benefit", source: "terms" },
    {},
    { value: 1_000_000, state: "conditional_amount" },
  ],
  [
    { amount: 100_000, calculation_basis: "unknown", source: "terms" },
    {},
    { value: null, state: "reference_only" },
  ],
  [
    { amount: 100_000, calculation_basis: "plan_schedule_lookup", source: "terms" },
    {},
    { value: null, state: "needs_plan" },
  ],
  [
    { amount: 100_000, calculation_basis: "plan_schedule_lookup", source: "terms" },
    {
      plan_name: "B",
      plan_options: [{ value: "B", label: "計畫 B", coverage_entries: [] }],
    },
    { value: 100_000, state: "calculated" },
  ],
  [
    { amount: 100_000, calculation_basis: "plan_schedule_lookup", source: "terms" },
    {
      plan_name: "不存在的計畫",
      plan_options: [{ value: "B", label: "計畫 B", coverage_entries: [] }],
    },
    { value: null, state: "needs_plan" },
  ],
  [
    { amount: 1_000_000, calculation_basis: "percentage_of_base", rate: 0.5, source: "terms" },
    { face_amount: 2_000_000 },
    { value: 1_000_000, state: "calculated" },
  ],
  [
    { amount: model.MAX_MONEY_AMOUNT, calculation_basis: "per_unit", source: "terms" },
    { unit_count: model.MAX_UNIT_COUNT },
    { value: null, state: "amount_overflow" },
  ],
];

for (const [entry, selection, expected] of calculationCases) {
  const result = model.coverageValue(entry, selection);
  assert.equal(result.value, expected.value, `${entry.calculation_basis} value mismatch`);
  assert.equal(result.state, expected.state, `${entry.calculation_basis} state mismatch`);
}

const surgeryTableEntry = model.normalizeCoverageEntry(
  {
    name: "手術費用保險金限額基數",
    amount: 5_500,
    calculation_basis: "percentage_of_base",
    limit_scope: "per_surgery",
    rate_min_percent: 10,
    rate_max_percent: 500,
    source: "terms",
  },
  0,
);
assert.equal(surgeryTableEntry.limit_scope, "per_surgery", "surgery schedules should preserve their limit scope");
assert.equal(surgeryTableEntry.rate_min, 0.1, "surgery schedules should preserve their minimum percentage");
assert.equal(surgeryTableEntry.rate_max, 5, "surgery schedules should preserve percentages above 100%");

const tieredCase = calculationCases.find(
  ([entry]) => entry.calculation_basis === "tiered_or_stepped" && Array.isArray(entry.amount_tiers),
);
const tieredResult = model.coverageValue(tieredCase[0], tieredCase[1]);
assert.deepEqual(
  tieredResult.tier_values.map((tier) => tier.value),
  [100_000, 150_000],
  "tiered per-unit amounts should calculate every displayed tier",
);

const dailyTieredResult = model.coverageValue(
  {
    amount: 100,
    basis: "daily_per_unit",
    calculation_basis: "tiered_or_stepped",
    amount_tiers: [
      { label: "住院第 1 至 30 日", amount: 100 },
      { label: "住院第 31 日起", amount: 200 },
    ],
    source: "terms",
  },
  { unit_count: 2 },
);
assert.deepEqual(
  dailyTieredResult.tier_values.map((tier) => tier.value),
  [200, 400],
  "tiered daily per-unit amounts should calculate every displayed tier",
);

const planItem = {
  selection_type: "plan",
  plan_name: "B",
  plan_options: [
    {
      value: "A",
      label: "計畫 A",
      coverage_entries: [{ name: "住院日額", amount: 1_000, calculation_basis: "per_day", source: "terms" }],
    },
    {
      value: "B",
      label: "計畫 B",
      coverage_entries: [{ name: "住院日額", amount: 2_000, calculation_basis: "per_day", source: "terms" }],
    },
  ],
};
assert.equal(model.effectiveCoverageEntries(planItem)[0].amount, 2_000, "plan lookup should select the chosen schedule");

const categoryCases = [
  ["傳統型壽險", "一般終身壽險", "life"],
  ["投資型壽險", "投資型壽險", "life"],
  ["健康保險", "住院醫療保險", "medical"],
  ["傷害保險", "個人傷害保險", "accident"],
  ["傳統型年金", "即期年金保險", "annuity"],
  ["投資型年金", "投資型年金保險", "annuity"],
  ["汽車保險", "汽車第三人責任保險", "auto"],
  ["火災保險", "住宅火災保險", "fire"],
  ["海上保險", "海上貨物運輸保險", "marine"],
  ["意外保險", "工程綜合保險", "property_other"],
  ["健康保險", "防癌終身健康保險", "cancer"],
  ["健康保險", "重大疾病保險", "critical"],
  ["健康保險", "長期照顧保險", "longterm"],
];

for (const [productType, productName, expectedBucket] of categoryCases) {
  const detected = model.detectCoverageBuckets({ product_type: productType, product_name: productName });
  assert.ok(detected.some((bucket) => bucket.id === expectedBucket), `${productType}/${productName} should include ${expectedBucket}`);
}

const officialCategoryFlowFixtures = [
  ["健康保險", "醫療計畫", "medical", "plan", {
    plan_name: "B",
    plan_options: [{ value: "B", label: "計畫 B", coverage_entries: [{ name: "住院日額", amount: 2_000, calculation_basis: "per_day", source: "terms" }] }],
  }],
  ["傳統型壽險", "定期壽險", "life", "face_amount", {
    face_amount: 1_000_000,
    coverage_entries: [{ name: "身故保險金", calculation_basis: "percentage_of_base", rate: 1, source: "terms" }],
  }],
  ["傳統型年金", "即期年金", "annuity", "fixed", {
    coverage_entries: [{ name: "年金給付", amount: 10_000, calculation_basis: "fixed_amount", source: "terms" }],
  }],
  ["傷害保險", "個人傷害保險", "accident", "unit", {
    unit_count: 2,
    coverage_entries: [{ name: "意外醫療", amount: 1_000, calculation_basis: "per_unit", source: "terms" }],
  }],
  ["投資型壽險", "投資型壽險", "life", "face_amount", {
    face_amount: 2_000_000,
    coverage_entries: [{ name: "身故保險金", calculation_basis: "percentage_of_base", rate: 1, source: "terms" }],
  }],
  ["投資型年金", "投資型年金", "annuity", "plan", {
    plan_name: "A",
    plan_options: [{ value: "A", label: "計畫 A", coverage_entries: [{ name: "年金給付", amount: 12_000, calculation_basis: "plan_schedule_lookup", source: "terms" }] }],
  }],
  ["意外保險", "公共意外責任保險", "property_other", "fixed", {
    coverage_entries: [{ name: "每次事故限額", amount: 1_000_000, calculation_basis: "reimbursement_with_cap", amount_role: "limit", source: "terms" }],
  }],
  ["汽車保險", "汽車責任保險", "auto", "face_amount", {
    face_amount: 2_000_000,
    coverage_entries: [{ name: "責任保險金", calculation_basis: "percentage_of_base", rate: 1, source: "terms" }],
  }],
  ["海上保險", "貨物運輸保險", "marine", "face_amount", {
    face_amount: 3_000_000,
    coverage_entries: [{ name: "貨物損失保險金", calculation_basis: "percentage_of_base", rate: 1, source: "terms" }],
  }],
  ["火災保險", "住宅火災保險", "fire", "face_amount", {
    face_amount: 4_000_000,
    coverage_entries: [{ name: "建築物損失保險金", calculation_basis: "percentage_of_base", rate: 1, source: "terms" }],
  }],
];

for (const [productType, productName, expectedBucket, selectionType, fixture] of officialCategoryFlowFixtures) {
  const item = { product_type: productType, product_name: productName, selection_type: selectionType, selection_source: "terms", ...fixture };
  assert.equal(model.selectionMode(item), selectionType, `${productType} should use its declared input mode`);
  assert.ok(model.detectCoverageBuckets(item).some((bucket) => bucket.id === expectedBucket), `${productType} should map to ${expectedBucket}`);
  const entries = model.effectiveCoverageEntries(item);
  assert.ok(entries.length > 0, `${productType} should expose terms-owned coverage entries`);
  assert.ok(
    ["calculated", "daily_rate", "benefit_limit", "conditional_amount"].includes(
      model.coverageValue(entries[0], item).state,
    ),
    `${productType} fixture should expose a safe numeric state`,
  );
}

const propertyWithInjuryWording = model.detectCoverageBuckets({
  product_type: "汽車保險",
  product_name: "汽車第三人責任保險（傷害）",
});
assert.ok(propertyWithInjuryWording.some((bucket) => bucket.id === "auto"), "property product should retain its property bucket");
assert.deepEqual(
  propertyWithInjuryWording.map((bucket) => bucket.id),
  ["auto"],
  "an auto policy must not also be counted as miscellaneous property insurance",
);

assert.deepEqual(
  model.detectCoverageBuckets({ product_type: "火災保險", product_name: "住宅竊盜保險附加條款" }).map((bucket) => bucket.id),
  ["fire"],
  "official property category must control its top-level bucket",
);
assert.ok(
  propertyWithInjuryWording.every((bucket) => bucket.group === "property"),
  "property products must not leak into personal coverage buckets",
);

const personalWithPropertyWording = model.detectCoverageBuckets({
  product_type: "健康保險",
  product_name: "住院醫療財產支出補償保險",
});
assert.ok(
  personalWithPropertyWording.every((bucket) => bucket.group === "personal"),
  "personal products must not leak into property coverage buckets",
);

const unknownEntry = model.normalizeCoverageEntry({ name: "待整理項目", amount: 50_000, basis: "not_supported", source: "terms" }, 0);
assert.equal(unknownEntry.calculation_basis, "unknown", "unknown basis must not fall back to a fixed payout");
assert.equal(unknownEntry.aggregation_rule, "separate", "coverage entries must not be aggregated by default");

const legacyPolicyTotal = model.normalizeCoverageEntry({ name: "舊資料", amount: 50_000, basis: "policy_total", source: "terms" }, 0);
const legacyPerEvent = model.normalizeCoverageEntry({ name: "舊資料", amount: 50_000, basis: "per_event", source: "terms" }, 0);
assert.equal(legacyPolicyTotal.calculation_basis, "unknown", "ambiguous legacy policy_total must remain unknown");
assert.equal(legacyPerEvent.calculation_basis, "unknown", "ambiguous legacy per_event must remain unknown");

console.log(
  JSON.stringify(
    {
      status: "ok",
      product_version_family_cases: productVersionFamilyCases.length,
      selection_mode_cases: selectionCases.length,
      calculation_basis_cases: calculationCases.length,
      insurance_category_cases: categoryCases.length,
      official_category_flow_cases: officialCategoryFlowFixtures.length,
    },
    null,
    2,
  ),
);

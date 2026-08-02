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
  [{ selection_type: "face_amount_plan", selection_source: "terms" }, "face_amount_plan"],
  [{ selection_type: "account_value", selection_source: "terms" }, "account_value"],
  [{ selection_type: "paid_premium_factor_plan", selection_source: "terms" }, "paid_premium_factor_plan"],
  [{ selection_type: "plan", plan_options: [{ value: "B", label: "計畫 B", coverage_entries: [] }] }, "plan"],
  [{ selection_type: "unit", selection_source: "terms" }, "unit"],
  [{ selection_type: "multi_unit", selection_source: "terms", unit_fields: [{ key: "a", label: "A 單位" }, { key: "b", label: "B 單位" }] }, "multi_unit"],
  [{ selection_type: "plan_unit", selection_source: "terms" }, "plan_unit"],
  [{ selection_type: "policy_state", selection_source: "terms" }, "policy_state"],
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

const faceAmountPlanSelection = model.selectionRequirements({
  selection_type: "face_amount_plan",
  selection_source: "terms",
  face_amount_label: "事故時有效保險金額",
  plan_options: ["甲型", "乙型"],
});
assert.deepEqual(faceAmountPlanSelection.fields, ["face_amount", "plan_name"]);
assert.equal(faceAmountPlanSelection.face_amount_label, "事故時有效保險金額");
assert.deepEqual(faceAmountPlanSelection.plan_options.map((option) => option.value), ["甲型", "乙型"]);
assert.equal(model.LIMIT_SCOPES.cross_policy, "跨保單合計");

const paidPremiumFactorSelection = model.selectionRequirements({
  selection_type: "paid_premium_factor_plan",
  selection_source: "terms",
  plan_options: ["甲型", "乙型"],
});
assert.deepEqual(paidPremiumFactorSelection.fields, ["plan_name"]);
assert.deepEqual(paidPremiumFactorSelection.plan_options.map((option) => option.value), ["甲型", "乙型"]);

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
    { value: null, state: "needs_policy_state" },
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
    { value: null, state: "needs_policy_state" },
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
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_actual_expense_with_cap",
      amount_role: "payout",
      rate_percent: 65,
      source: "terms",
    },
    { policy_state: { reimbursement_limit: 30_000 } },
    { value: 30_000, state: "policy_state_limit" },
  ],
  [
    { basis: "policy_account_value", calculation_basis: "account_value", source: "terms" },
    { account_value: 120_000 },
    { value: 120_000, state: "account_value_return" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      source: "terms",
    },
    { face_amount: 1_000_000, plan_name: "甲型", policy_state: { policy_account_value: 300_000 } },
    { value: 1_000_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      source: "terms",
    },
    { face_amount: 1_000_000, plan_name: "乙型", policy_state: { policy_account_value: 300_000 } },
    { value: 1_300_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      source: "terms",
    },
    { face_amount: 1_000_000, plan_name: "甲型" },
    { value: null, state: "needs_account_value" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      currency_state_key: "contract_currency",
      source: "terms",
    },
    {
      face_amount: 1_000_000,
      plan_name: "乙型",
      policy_state: { policy_account_value: 300_000 },
    },
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      currency_state_key: "contract_currency",
      source: "terms",
    },
    {
      face_amount: 1_000_000,
      plan_name: "乙型",
      policy_state: {
        contract_currency: "USD",
        policy_account_value: 300_000,
      },
    },
    { value: 1_300_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      minor_account_value_return_age: 15,
      source: "terms",
    },
    {
      policy_state: {
        insured_age_at_event: 14,
        policy_account_value: 300_000,
      },
    },
    { value: 300_000, state: "account_value_return" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "net_amount_at_risk_plus_policy_account_value",
      minor_account_value_return_age: 15,
      source: "terms",
    },
    {
      face_amount: 1_000_000,
      plan_name: "甲型",
      policy_state: {
        insured_age_at_event: 15,
        policy_account_value: 300_000,
      },
    },
    { value: 1_000_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      source: "terms",
    },
    {
      plan_name: "甲型",
      policy_state: {
        paid_premium_total: 1_000_000,
        partial_termination_amount_total: 0,
        specified_percent_or_multiplier: 130,
        policy_account_value: 800_000,
      },
    },
    { value: 1_300_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      source: "terms",
    },
    {
      plan_name: "乙型",
      policy_state: {
        paid_premium_total: 1_000_000,
        partial_termination_amount_total: 100_000,
        specified_percent_or_multiplier: 1.2,
        policy_account_value: 800_000,
      },
    },
    { value: 1_880_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      source: "terms",
    },
    {
      plan_name: "甲型",
      policy_state: {
        paid_premium_total: 1_000_000,
        specified_percent_or_multiplier: 130,
        policy_account_value: 800_000,
      },
    },
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      currency_state_key: "contract_currency",
      source: "terms",
    },
    {
      plan_name: "甲型",
      policy_state: {
        paid_premium_total: 1_000_000,
        partial_termination_amount_total: 0,
        specified_percent_or_multiplier: 130,
        policy_account_value: 800_000,
      },
    },
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      currency_state_key: "contract_currency",
      source: "terms",
    },
    {
      plan_name: "甲型",
      policy_state: {
        contract_currency: "USD",
        paid_premium_total: 1_000_000,
        partial_termination_amount_total: 0,
        specified_percent_or_multiplier: 130,
        policy_account_value: 800_000,
      },
    },
    { value: 1_300_000, state: "calculated" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      minor_account_value_return_age: 15,
      source: "terms",
    },
    {
      policy_state: {
        insured_age_at_event: 14,
        policy_account_value: 800_000,
      },
    },
    { value: 800_000, state: "account_value_return" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "paid_premium_factor_account_value_formula",
      minor_account_value_return_age: 15,
      source: "terms",
    },
    {
      plan_name: "乙型",
      policy_state: {
        insured_age_at_event: 15,
        paid_premium_total: 1_000_000,
        partial_termination_amount_total: 100_000,
        specified_percent_or_multiplier: 1.2,
        policy_account_value: 800_000,
      },
    },
    { value: 1_880_000, state: "calculated" },
  ],
  [
    { basis: "policy_account_value", calculation_basis: "account_value_annuity_factor", source: "terms" },
    { account_value: 120_000 },
    { value: null, state: "needs_annuity_factor" },
  ],
  [
    { basis: "policy_account_value", calculation_basis: "account_value_annuity_factor", source: "terms" },
    { account_value: 120_000, policy_state: { annuity_payment_amount: 8_000 } },
    { value: 8_000, state: "policy_state_value" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "single_premium_minus_paid_annuity_total",
      unit_key: "unpaid_annuity_balance",
      policy_state_keys: [
        "single_premium_amount",
        "annuity_paid_total_amount",
      ],
      source: "terms",
    },
    {
      face_amount: 100_000,
      policy_state: {
        single_premium_amount: 1_000_000,
        annuity_paid_total_amount: 197_932,
      },
    },
    { value: 802_068, state: "calculated_annuity_balance" },
  ],
  [
    {
      basis: "policy_recorded_limit",
      calculation_basis: "reserve_minus_policy_loan_and_interest",
      unit_key: "policy_reserve_value",
      policy_state_keys: [
        "policy_reserve_value",
        "policy_loan_and_interest_amount",
      ],
      source: "terms",
    },
    {
      policy_state: {
        policy_reserve_value: 1_000_000,
        policy_loan_and_interest_amount: 125_000,
      },
    },
    { value: 875_000, state: "calculated" },
  ],
  [
    {
      id: "unpaid-annuity-balance",
      name: "未支領之年金餘額",
      basis: "policy_recorded_limit",
      calculation_basis: "unknown",
      amount_role: "payout",
      limit_scope: "per_policy",
      source: "terms",
      unit_key: "unpaid_annuity_balance",
      conditions: ["提前給付時，貼現利率依計算年金金額所採用之預定利率。"],
    },
    {},
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      id: "unpaid-annuity-balance",
      name: "未支領之年金餘額",
      basis: "policy_recorded_limit",
      calculation_basis: "unknown",
      amount_role: "payout",
      limit_scope: "per_policy",
      source: "terms",
      unit_key: "unpaid_annuity_balance",
      conditions: ["提前給付時，貼現利率依計算年金金額所採用之預定利率。"],
    },
    { policy_state: { unpaid_annuity_balance: 220_000 } },
    { value: 220_000, state: "policy_state_value" },
  ],
  [
    {
      name: "增值回饋分享金",
      basis: "policy_recorded_limit",
      calculation_basis: "unknown",
      note: "依宣告利率與預定利率差額乘以前一保單年度末保單價值準備金計算。",
      source: "terms",
    },
    {
      policy_state: {
        previous_policy_reserve_value: 1_000_000,
        declared_interest_rate_percent: 3,
        scheduled_interest_rate_percent: 2,
      },
    },
    { value: 10_000, state: "value_sharing_bonus" },
  ],
  [
    {
      name: "身故保險金或喪葬費用保險金",
      basis: "policy_recorded_limit",
      calculation_basis: "greater_of",
      rate_percent: 106,
      note: "按身故日年繳應繳保險費總和 1.06 倍與身故日保單價值準備金二者取其大給付。",
      source: "terms",
    },
    {
      policy_state: {
        policy_reserve_value: 500_000,
        premium_total_amount: 600_000,
      },
    },
    { value: 636_000, state: "greater_of" },
  ],
  [
    {
      name: "滿期保險金",
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_base",
      rate_percent: 100,
      unit_key: "current_policy_amount",
      note: "按當時之保險金額給付。",
      source: "terms",
    },
    {},
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      name: "滿期保險金",
      basis: "policy_recorded_limit",
      calculation_basis: "percentage_of_base",
      rate_percent: 100,
      unit_key: "current_policy_amount",
      note: "按當時之保險金額給付。",
      source: "terms",
    },
    { policy_state: { current_policy_amount: 1_200_000 } },
    { value: 1_200_000, state: "policy_state_percentage" },
  ],
  [
    {
      name: "二至六級殘廢豁免基本保險費",
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      source: "terms",
    },
    {},
    { value: null, state: "needs_policy_state" },
  ],
  [
    {
      name: "二至六級殘廢豁免基本保險費",
      basis: "policy_premium",
      calculation_basis: "waiver",
      amount_role: "premium_waiver",
      source: "terms",
    },
    { policy_state: { remaining_premium_amount: 240_000 } },
    { value: 240_000, state: "premium_waiver_effect" },
  ],
  [
    {
      name: "每年保險金給付總限額",
      amount: 500_000,
      basis: "annual_limit",
      calculation_basis: "aggregate_cap",
      amount_role: "limit",
      source: "terms",
    },
    {},
    { value: 500_000, state: "aggregate_cap" },
  ],
  [
    {
      name: "意外傷害住院保險金",
      basis: "hospital_daily_amount",
      calculation_basis: "unknown",
      amount_role: "payout",
      source: "terms",
    },
    { policy_state: { hospital_daily_amount: 1_500 } },
    { value: 1_500, state: "policy_state_daily_rate" },
  ],
  [
    {
      name: "骨折未住院醫療保險金",
      basis: "hospital_daily_amount",
      calculation_basis: "unknown",
      multiplier: 0.5,
      amount_role: "reference",
      source: "terms",
    },
    { policy_state: { hospital_daily_amount: 1_500 } },
    { value: 750, state: "policy_state_multiplier" },
  ],
  [
    {
      name: "意外傷害住院手術費用保險金",
      basis: "hospital_daily_amount",
      calculation_basis: "unknown",
      multiplier: 20,
      rate_min_percent: 2,
      rate_max_percent: 300,
      amount_role: "reference",
      source: "terms",
    },
    { policy_state: { hospital_daily_amount: 1_500 } },
    { value: null, state: "policy_state_rate_table" },
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

const typedHospitalDailyEntry = {
  amount: 2_000,
  calculation_basis: "per_day",
  quantity_state_key: "hospitalization_days",
  source: "terms",
};
assert.deepEqual(
  model.policyStateFieldsForEntry(typedHospitalDailyEntry).map((field) => field.key),
  ["hospitalization_days"],
);
assert.deepEqual(
  {
    value: model.coverageValue(typedHospitalDailyEntry, {
      policy_state: { hospitalization_days: 5 },
    }).value,
    state: model.coverageValue(typedHospitalDailyEntry, {
      policy_state: { hospitalization_days: 5 },
    }).state,
  },
  { value: 10_000, state: "calculated" },
);

const typedReimbursementItem = {
  plan_name: "2",
  plan_options: [
    {
      value: "2",
      label: "計畫二",
      coverage_entries: [
        {
          id: "inpatient-medical-limit",
          amount: 100_000,
          basis: "per_event",
          calculation_basis: "reimbursement_with_cap",
          amount_role: "limit",
          expense_state_key: "inpatient_medical_expense",
          rate_percent: 70,
          rate_condition_state_key: "national_health_insurance_payment_status",
          rate_condition_value: "not_covered",
          cumulative_paid_state_key: "annual_medical_benefit_paid_amount",
          aggregate_limit_entry_id: "annual-medical-cap",
          source: "terms",
        },
        {
          id: "annual-medical-cap",
          amount: 150_000,
          basis: "annual_limit",
          calculation_basis: "reimbursement_with_cap",
          amount_role: "limit",
          aggregation_rule: "cumulative_cap",
          source: "terms",
        },
      ],
    },
  ],
  policy_state: {
    inpatient_medical_expense: 120_000,
    national_health_insurance_payment_status: "not_covered",
    annual_medical_benefit_paid_amount: 80_000,
  },
};
const typedReimbursementResult = model.coverageValue(
  typedReimbursementItem.plan_options[0].coverage_entries[0],
  typedReimbursementItem,
);
assert.equal(typedReimbursementResult.state, "calculated");
assert.equal(typedReimbursementResult.eligible_expense, 84_000);
assert.equal(typedReimbursementResult.remaining_aggregate_limit, 70_000);
assert.equal(typedReimbursementResult.value, 70_000);

const progressiveHospitalEntry = {
  amount: 1_000,
  basis: "per_unit",
  calculation_basis: "tiered_or_stepped",
  quantity_state_key: "hospitalization_days",
  amount_tiers: [
    { label: "第 1 至 30 日", amount: 1_000, min_quantity: 1, max_quantity: 30 },
    { label: "第 31 至 90 日", amount: 1_500, min_quantity: 31, max_quantity: 90 },
    { label: "第 91 日起", amount: 2_000, min_quantity: 91 },
  ],
  source: "terms",
};
const progressiveHospitalResult = model.coverageValue(
  progressiveHospitalEntry,
  {
    unit_count: 2,
    policy_state: { hospitalization_days: 35 },
  },
);
assert.equal(progressiveHospitalResult.state, "calculated");
assert.equal(progressiveHospitalResult.value, 75_000);
assert.deepEqual(
  progressiveHospitalResult.tier_values.map((tier) => tier.quantity),
  [30, 5, 0],
);

const surgeryRateResult = model.coverageValue(
  {
    amount: 10_000,
    basis: "per_unit",
    calculation_basis: "percentage_of_base",
    rate_state_key: "surgery_benefit_rate_percent",
    source: "terms",
  },
  {
    unit_count: 2,
    policy_state: { surgery_benefit_rate_percent: 17.5 },
  },
);
assert.equal(surgeryRateResult.state, "calculated");
assert.equal(surgeryRateResult.applied_rate, 0.175);
assert.equal(surgeryRateResult.value, 3_500);

const cancerDiagnosisEntry = {
  amount: 50_000,
  basis: "per_unit",
  calculation_basis: "tiered_or_stepped",
  amount_tiers: [
    { label: "第 1 至 20 保單年度", amount: 50_000, min_quantity: 1, max_quantity: 20 },
    { label: "第 21 保單年度起", amount: 75_000, min_quantity: 21 },
  ],
  tier_selection_state_key: "policy_year",
  rate: 0.15,
  rate_condition_state_key: "cancer_benefit_category",
  rate_condition_value: "reduced_benefit_cancer",
  cumulative_paid_state_key: "prior_cancer_diagnosis_benefit_paid_amount",
  source: "terms",
};
const reducedCancerDiagnosisResult = model.coverageValue(
  cancerDiagnosisEntry,
  {
    unit_count: 2,
    policy_state: {
      policy_year: 21,
      cancer_benefit_category: "reduced_benefit_cancer",
      prior_cancer_diagnosis_benefit_paid_amount: 10_000,
    },
  },
);
assert.equal(reducedCancerDiagnosisResult.state, "calculated");
assert.equal(reducedCancerDiagnosisResult.gross_value, 150_000);
assert.equal(reducedCancerDiagnosisResult.rate_adjusted_value, 22_500);
assert.equal(reducedCancerDiagnosisResult.value, 12_500);
assert.equal(reducedCancerDiagnosisResult.selected_tier.label, "第 21 保單年度起");

const fullCancerDiagnosisResult = model.coverageValue(
  cancerDiagnosisEntry,
  {
    unit_count: 2,
    policy_state: {
      policy_year: 10,
      cancer_benefit_category: "full_benefit_cancer",
      prior_cancer_diagnosis_benefit_paid_amount: 20_000,
    },
  },
);
assert.equal(fullCancerDiagnosisResult.value, 80_000);

const cancerHospitalTieredResult = model.coverageValue(
  {
    amount: 1_200,
    basis: "daily_per_unit",
    calculation_basis: "tiered_or_stepped",
    quantity_state_key: "cancer_hospitalization_days",
    amount_tiers: [
      { label: "同一次住院第 1 至 90 日", amount: 1_200, min_quantity: 1, max_quantity: 90 },
      { label: "同一次住院第 91 日起", amount: 1_800, min_quantity: 91 },
    ],
    source: "terms",
  },
  {
    unit_count: 2,
    policy_state: { cancer_hospitalization_days: 95 },
  },
);
assert.equal(cancerHospitalTieredResult.value, 234_000);
assert.deepEqual(
  cancerHospitalTieredResult.tier_values.map((tier) => tier.quantity),
  [90, 5],
);

const policyStateAmountWithRateResult = model.coverageValue(
  {
    basis: "policy_recorded_limit",
    calculation_basis: "policy_state_amount",
    policy_state_keys: ["cancer_hospital_daily_amount"],
    unit_key: "cancer_hospital_daily_amount",
    quantity_state_key: "cancer_hospitalization_days",
    quantity_cap: 365,
    rate_percent: 60,
    source: "terms",
  },
  {
    policy_state: {
      cancer_hospital_daily_amount: 3_000,
      cancer_hospitalization_days: 20,
    },
  },
);
assert.equal(policyStateAmountWithRateResult.state, "policy_state_value");
assert.equal(policyStateAmountWithRateResult.value, 36_000);
assert.equal(policyStateAmountWithRateResult.applied_rate, 0.6);

const reducedCancerSurgeryResult = model.coverageValue(
  {
    amount: 15_000,
    basis: "per_unit",
    calculation_basis: "per_unit",
    quantity_state_key: "cancer_surgery_count",
    rate: 0.15,
    rate_condition_state_key: "cancer_benefit_category",
    rate_condition_value: "reduced_benefit_cancer",
    source: "terms",
  },
  {
    unit_count: 2,
    policy_state: {
      cancer_benefit_category: "reduced_benefit_cancer",
      cancer_surgery_count: 2,
    },
  },
);
assert.equal(reducedCancerSurgeryResult.value, 9_000);

const cancerHospiceEntry = {
  amount: 20_000,
  basis: "per_unit",
  calculation_basis: "per_unit",
  quantity_state_key: "cancer_hospice_anniversary_count",
  exclusion_state_key: "cancer_benefit_category",
  exclusion_values: [
    "reduced_benefit_cancer",
    "full_benefit_hospice_excluded",
  ],
  source: "terms",
};
assert.equal(
  model.coverageValue(cancerHospiceEntry, {
    unit_count: 2,
    policy_state: {
      cancer_benefit_category: "reduced_benefit_cancer",
      cancer_hospice_anniversary_count: 3,
    },
  }).state,
  "not_eligible",
);
assert.equal(
  model.coverageValue(cancerHospiceEntry, {
    unit_count: 2,
    policy_state: {
      cancer_benefit_category: "full_benefit_cancer",
      cancer_hospice_anniversary_count: 3,
    },
  }).value,
  120_000,
);

const foreignCurrencyFormulaResult = model.coverageValue(
  {
    calculation_basis: "paid_premium_factor_account_value_formula",
    currency_state_key: "contract_currency",
    source: "terms",
  },
  {
    plan_name: "甲型",
    policy_state: {
      contract_currency: "USD",
      paid_premium_total: 1_000_000,
      partial_termination_amount_total: 0,
      specified_percent_or_multiplier: 130,
      policy_account_value: 800_000,
    },
  },
);
assert.equal(foreignCurrencyFormulaResult.currency_label, "USD", "foreign-currency calculations should preserve the contract currency");

const minorReturnResult = model.coverageValue(
  {
    calculation_basis: "paid_premium_factor_account_value_formula",
    minor_account_value_return_age: 15,
    source: "terms",
  },
  { policy_state: { insured_age_at_event: 14, policy_account_value: 800_000 } },
);
assert.equal(minorReturnResult.formula_type, "minor_account_value_return", "under-age branch should use account-value return");

const foreignCurrencyNetRiskResult = model.coverageValue(
  {
    calculation_basis: "net_amount_at_risk_plus_policy_account_value",
    currency_state_key: "contract_currency",
    source: "terms",
  },
  {
    face_amount: 1_000_000,
    plan_name: "乙型",
    policy_state: {
      contract_currency: "USD",
      policy_account_value: 300_000,
    },
  },
);
assert.equal(foreignCurrencyNetRiskResult.currency_label, "USD", "net-risk calculations should preserve contract currency");
assert.equal(foreignCurrencyNetRiskResult.net_amount_at_risk, 1_000_000, "type B net risk should equal face amount");
assert.equal(foreignCurrencyNetRiskResult.account_value, 300_000, "net-risk result should expose the account value used");

const currentInsuranceAmountNetRiskResult = model.coverageValue(
  {
    calculation_basis: "net_amount_at_risk_plus_policy_account_value",
    source: "terms",
  },
  {
    face_amount: 1_200_000,
    face_amount_label: "事故時有效保險金額",
    plan_name: "甲型",
    policy_state: { policy_account_value: 1_500_000 },
  },
);
assert.equal(currentInsuranceAmountNetRiskResult.value, 1_500_000, "type A should use the higher current insurance amount or account value");
assert.equal(currentInsuranceAmountNetRiskResult.face_amount_label, "事故時有效保險金額");

const allianzAge111Entry = {
  name: "身故保險金",
  calculation_basis: "net_amount_at_risk_plus_policy_account_value",
  source: "terms",
};
const allianzAge111Version = {
  product_family: "allianz-age111-variable-universal-life-face-amount",
  threshold_factor_schedule: [
    { min_age: 15, max_age: 40, factor: 0.6 },
    { min_age: 41, max_age: 70, factor: 0.2 },
    { min_age: 71, max_age: 130, factor: 0 },
  ],
};
const allianzAge111Cases = [
  [
    "甲型",
    {
      face_amount: 1_000_000,
      policy_state: {
        policy_account_value: 300_000,
        insurance_deduction_amount: 100_000,
      },
    },
    900_000,
  ],
  [
    "乙型",
    {
      face_amount: 1_000_000,
      policy_state: { policy_account_value: 300_000 },
    },
    1_300_000,
  ],
  [
    "丙型",
    {
      face_amount: 600_000,
      policy_state: {
        policy_account_value: 500_000,
        insurance_deduction_amount: 100_000,
        insured_age_at_event: 35,
      },
    },
    800_000,
  ],
  [
    "丁型",
    {
      face_amount: 300_000,
      policy_state: {
        policy_account_value: 1_000_000,
        insured_age_at_event: 35,
      },
    },
    1_600_000,
  ],
  [
    "戊型",
    {
      face_amount: 500_000,
      policy_state: {
        policy_account_value: 400_000,
        insurance_deduction_amount: 50_000,
        insured_age_at_event: 35,
        paid_premium_total: 1_200_000,
        partial_termination_amount_total: 100_000,
      },
    },
    1_100_000,
  ],
];
for (const [policyType, selection, expectedValue] of allianzAge111Cases) {
  const result = model.coverageValue(allianzAge111Entry, {
    ...selection,
    plan_name: policyType,
    version_characteristics: allianzAge111Version,
  });
  assert.equal(result.state, "calculated", `Allianz ${policyType} should calculate`);
  assert.equal(result.value, expectedValue, `Allianz ${policyType} amount mismatch`);
  assert.equal(result.formula_type, policyType.replace("型", ""));
}

const allianzMissingDeduction = model.coverageValue(allianzAge111Entry, {
  face_amount: 1_000_000,
  plan_name: "甲型",
  policy_state: { policy_account_value: 300_000 },
  version_characteristics: allianzAge111Version,
});
assert.equal(allianzMissingDeduction.state, "needs_policy_state");
assert.deepEqual(allianzMissingDeduction.required_fields, ["insurance_deduction_amount"]);

const allianzTypeERequirements = model
  .policyStateRequirements({
    plan_name: "戊型",
    coverage_entries: [allianzAge111Entry],
    version_characteristics: allianzAge111Version,
  })
  .fields.map((field) => field.key);
assert.deepEqual(
  allianzTypeERequirements,
  [
    "policy_account_value",
    "insurance_deduction_amount",
    "insured_age_at_event",
    "paid_premium_total",
    "partial_termination_amount_total",
  ],
  "Allianz type E should request only the policy state needed by its formula",
);

const fixedPlanDailyRequirements = model
  .policyStateRequirements({
    selection_type: "plan",
    plan_name: "計畫二",
    plan_options: [
      {
        value: "計畫二",
        label: "計畫二",
        coverage_entries: [
          {
            name: "住院日額保險金",
            amount: 2_000,
            calculation_basis: "per_day",
            source: "terms",
          },
        ],
      },
    ],
  })
  .fields.map((field) => field.key);
assert.deepEqual(
  fixedPlanDailyRequirements,
  [],
  "a terms-owned fixed daily amount should not request the same policy daily amount again",
);

const formulaPolicyStateKeys = model
  .policyStateFieldsForEntry({
    calculation_basis: "paid_premium_factor_account_value_formula",
    currency_state_key: "contract_currency",
    minor_account_value_return_age: 15,
    source: "terms",
  })
  .map((field) => field.key);
assert.deepEqual(
  formulaPolicyStateKeys,
  [
    "policy_account_value",
    "paid_premium_total",
    "partial_termination_amount_total",
    "specified_percent_or_multiplier",
    "contract_currency",
    "insured_age_at_event",
  ],
  "formula requirements should expose every user input needed for exact calculation",
);

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

const immediateAnnuityBase = {
  selection_type: "face_amount_plan",
  selection_source: "terms",
  face_amount: 100_000,
  plan_options: [
    {
      value: "level-monthly-guarantee-10",
      label: "平準型｜月領｜甲型保證 10 年",
      coverage_entries: [
        {
          name: "月領年金給付",
          basis: "face_amount",
          calculation_basis: "annuity_face_amount_schedule",
          rate_percent: 8.1987,
          annuity_payment_pattern: "level",
          annuity_guarantee_years: 10,
          source: "terms",
        },
      ],
    },
    {
      value: "increasing-annual-guarantee-10",
      label: "增額型｜年領｜甲型保證 10 年",
      coverage_entries: [
        {
          name: "年領年金給付",
          basis: "face_amount",
          calculation_basis: "annuity_face_amount_schedule",
          rate_percent: 100,
          annuity_payment_pattern: "increasing",
          annuity_growth_rate_percent: 3,
          annuity_guarantee_years: 10,
          policy_state_keys: ["annuity_payment_year"],
          source: "terms",
        },
      ],
    },
  ],
};
const levelAnnuity = {
  ...immediateAnnuityBase,
  plan_name: "level-monthly-guarantee-10",
};
assert.equal(
  model.coverageValue(model.effectiveCoverageEntries(levelAnnuity)[0], levelAnnuity).value,
  8_198,
  "level monthly annuity should apply the exact terms coefficient",
);

const increasingAnnuity = {
  ...immediateAnnuityBase,
  plan_name: "increasing-annual-guarantee-10",
  policy_state: { annuity_payment_year: 3 },
};
const increasingYearThree = model.coverageValue(
  model.effectiveCoverageEntries(increasingAnnuity)[0],
  increasingAnnuity,
);
assert.equal(increasingYearThree.value, 106_000, "year three should apply two years of 3% simple growth");
assert.equal(increasingYearThree.annuity_growth_multiplier, 1.06);

const postGuaranteeAnnuity = {
  ...increasingAnnuity,
  policy_state: { annuity_payment_year: 12 },
};
assert.equal(
  model.coverageValue(
    model.effectiveCoverageEntries(postGuaranteeAnnuity)[0],
    postGuaranteeAnnuity,
  ).value,
  130_000,
  "growth should stop after the ten-year guarantee period",
);

const missingAnnuityYear = {
  ...immediateAnnuityBase,
  plan_name: "increasing-annual-guarantee-10",
};
const missingAnnuityYearResult = model.coverageValue(
  model.effectiveCoverageEntries(missingAnnuityYear)[0],
  missingAnnuityYear,
);
assert.equal(missingAnnuityYearResult.state, "needs_policy_state");
assert.deepEqual(missingAnnuityYearResult.required_fields, ["annuity_payment_year"]);
assert.deepEqual(
  model.policyStateRequirements(missingAnnuityYear).fields.map((field) => field.key),
  ["annuity_payment_year"],
  "increasing annuity should request the current annuity payment year",
);

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

const structureStatusCases = [
  [
    { coverage_entries: [{ name: "住院日額", amount: 1_000, calculation_basis: "per_day", source: "terms" }] },
    "calculated",
  ],
  [
    { coverage_entries: [{ name: "身故保險金", calculation_basis: "percentage_of_base", rate_percent: 100, source: "terms" }] },
    "needs_user_input",
  ],
  [
    { reader_focus: [{ key: "coverage", summary: "含住院醫療保障。", terms: ["住院", "醫療費用"] }] },
    "pending_structure",
  ],
  [
    { source_kind: "tii", source_batch_id: "tii-life-001" },
    "source_pending",
  ],
  [
    { structure_status: "confirmed_no_amount" },
    "confirmed_no_amount",
  ],
];

for (const [item, expected] of structureStatusCases) {
  assert.equal(model.structureStatus(item).id, expected, `structure status should be ${expected}`);
}

console.log(
  JSON.stringify(
    {
      status: "ok",
      product_version_family_cases: productVersionFamilyCases.length,
      selection_mode_cases: selectionCases.length,
      calculation_basis_cases: calculationCases.length,
      insurance_category_cases: categoryCases.length,
      official_category_flow_cases: officialCategoryFlowFixtures.length,
      structure_status_cases: structureStatusCases.length,
    },
    null,
    2,
  ),
);

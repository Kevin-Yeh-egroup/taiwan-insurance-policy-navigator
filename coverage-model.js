(function initPolicyCoverageModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.PolicyCoverageModel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createPolicyCoverageModel() {
  "use strict";

  const MAX_MONEY_AMOUNT = 999999999999;
  const MAX_UNIT_COUNT = 9999;
  const MAX_RATE = 10;

  const SELECTION_MODES = {
    face_amount: { label: "契約保險金額", fields: ["face_amount"] },
    plan: { label: "計畫別", fields: ["plan_name"] },
    unit: { label: "投保單位數", fields: ["unit_count"] },
    multi_unit: { label: "多組投保單位數", fields: ["unit_counts"] },
    plan_unit: { label: "計畫別與投保單位數", fields: ["plan_name", "unit_count"] },
    fixed: { label: "條款固定給付", fields: [] },
    unknown: { label: "金額尚待整理", fields: [] },
  };

  const CALCULATION_BASES = {
    fixed_amount: "固定給付",
    percentage_of_base: "依基準額比例",
    plan_schedule_lookup: "依計畫附表",
    per_unit: "每單位",
    per_unit_per_day: "每單位／每日",
    per_day: "每日給付",
    reimbursement_with_cap: "實際支出限額內",
    percentage_of_actual_expense_with_cap: "實際支出比例限額內",
    table_multiplier: "依條款倍數表",
    tiered_or_stepped: "依級距或階梯表",
    additional_benefit: "額外給付",
    unknown: "計算方式尚待整理",
  };

  const AMOUNT_ROLES = {
    payout: "給付金額",
    base: "計算基準",
    limit: "最高限額",
    reference: "條款參考值",
    unknown: "金額角色尚待整理",
  };

  const LIMIT_SCOPES = {
    per_policy: "本保單",
    per_event: "每次事故",
    per_injury: "每次傷害",
    per_surgery: "每次手術",
    per_day: "每日",
    per_hospitalization: "每次住院",
    annual: "每保單年度",
    lifetime: "保險期間累計",
    unknown: "適用範圍尚待整理",
  };

  const AGGREGATION_RULES = {
    separate: "分開呈現",
    conditional_additive: "符合條款時可併計",
    choose_one: "擇一給付",
    highest: "取較高給付",
    cumulative_cap: "受累計上限限制",
    unknown: "是否併計尚待條款確認",
  };

  const LEGACY_BASIS_MAP = {
    per_unit: "per_unit",
    daily_per_unit: "per_unit_per_day",
    daily_total: "per_day",
    annual_limit: "reimbursement_with_cap",
    benefit_base: "percentage_of_base",
    per_injury_limit: "reimbursement_with_cap",
    additional_benefit: "additional_benefit",
  };

  const COVERAGE_BUCKETS = [
    {
      id: "life",
      group: "personal",
      label: "壽險",
      summary: "身故、完全失能、壽險主約或投資型壽險。",
      categories: ["傳統型壽險", "投資型壽險"],
      keywords: ["壽險", "身故", "死亡", "完全失能", "生死合險", "定期壽", "終身壽"],
    },
    {
      id: "medical",
      group: "personal",
      label: "醫療險",
      summary: "住院、手術、實支實付、日額、門診或健康醫療。",
      categories: ["健康保險"],
      keywords: ["醫療", "健康", "住院", "手術", "實支", "日額", "門診", "病房", "雜費"],
    },
    {
      id: "accident",
      group: "personal",
      label: "意外險",
      summary: "傷害、意外、平安、燒燙傷、骨折或意外失能。",
      categories: ["傷害保險"],
      keywords: ["傷害", "意外", "平安", "燒燙傷", "骨折", "意外失能", "旅行平安"],
    },
    {
      id: "cancer",
      group: "personal",
      label: "癌症險",
      summary: "癌症、惡性腫瘤、防癌或癌症醫療給付。",
      categories: [],
      keywords: ["癌", "癌症", "防癌", "抗癌", "惡性腫瘤", "原位癌", "初期癌"],
    },
    {
      id: "critical",
      group: "personal",
      label: "重大疾病險",
      summary: "重大疾病、重大傷病、特定傷病或一次金保障。",
      categories: [],
      keywords: ["重大疾病", "重大傷病", "特定傷病", "心肌梗塞", "腦中風", "癱瘓", "洗腎"],
    },
    {
      id: "longterm",
      group: "personal",
      label: "長照險",
      summary: "長期照顧、失智、認知功能障礙或長期看護。",
      categories: [],
      keywords: ["長期照顧", "長照", "長期看護", "失智", "認知功能障礙", "照護", "扶助"],
    },
    {
      id: "annuity",
      group: "personal",
      label: "年金／退休",
      summary: "年金、退休、生存金或長期現金流安排。",
      categories: ["傳統型年金", "投資型年金"],
      keywords: ["年金", "退休", "生存金", "養老", "即期年金", "利率變動型年金"],
    },
    {
      id: "auto",
      group: "property",
      label: "汽車險",
      summary: "車體、竊盜、第三人責任、乘客或駕駛人保障。",
      categories: ["汽車保險"],
      keywords: ["汽車", "機車", "車體", "竊盜", "第三人責任", "駕駛人", "乘客責任"],
    },
    {
      id: "fire",
      group: "property",
      label: "住宅／火災險",
      summary: "住宅、商業火災、地震、颱風洪水或財物損失保障。",
      categories: ["火災保險"],
      keywords: ["住宅", "火災", "地震", "颱風", "洪水", "財物", "建築物", "動產"],
    },
    {
      id: "marine",
      group: "property",
      label: "海上／運輸險",
      summary: "船舶、貨物運輸、海運或相關責任保障。",
      categories: ["海上保險"],
      keywords: ["海上", "船舶", "貨物運輸", "海運", "貨運", "航空貨物"],
    },
    {
      id: "property_other",
      group: "property",
      label: "其他產險",
      summary: "責任、工程、保證、信用、旅遊不便及其他財產風險。",
      categories: ["意外保險"],
      keywords: ["責任保險", "工程保險", "保證保險", "信用保險", "旅遊不便", "寵物保險", "農業保險"],
    },
  ];

  const OFFICIAL_CATEGORY_GROUPS = {
    personal: new Set(["健康保險", "傳統型壽險", "傳統型年金", "傷害保險", "投資型壽險", "投資型年金"]),
    property: new Set(["意外保險", "汽車保險", "海上保險", "火災保險"]),
  };

  function normalizeText(value) {
    return String(value ?? "").trim().toLowerCase();
  }

  function productVersionFamilyName(value) {
    return normalizeText(value)
      .replace(/\s*[（(][^()（）]*第[^()（）]*(?:次|版)[^()（）]*(?:變更|修訂|修正|改訂)[^()（）]*[)）]\s*$/u, "")
      .trim();
  }

  function normalizeInteger(value, max) {
    if (value === "" || value === null || value === undefined) return null;
    const number = Number(String(value).replaceAll(",", ""));
    if (!Number.isSafeInteger(number) || number <= 0 || number > max) return null;
    return number;
  }

  function normalizeUnitCount(value) {
    return normalizeInteger(value, MAX_UNIT_COUNT);
  }

  function normalizeMoneyAmount(value) {
    return normalizeInteger(value, MAX_MONEY_AMOUNT);
  }

  function normalizeRate(value, percentValue) {
    const candidate = percentValue !== undefined && percentValue !== null ? Number(percentValue) / 100 : Number(value);
    return Number.isFinite(candidate) && candidate > 0 && candidate <= MAX_RATE ? candidate : null;
  }

  function safeIntegerProduct(left, right) {
    const result = Number(left) * Number(right);
    return Number.isSafeInteger(result) && result > 0 ? result : null;
  }

  function canonicalSelectionMode(value) {
    const mode = normalizeText(value).replace(/[\s/+]+/g, "_");
    if (!mode) return "";
    if (["face_amount", "amount", "sum_insured", "insured_amount", "保額", "保險金額"].includes(mode)) return "face_amount";
    if (["multi_unit", "multiple_units", "多組單位", "多單位"].includes(mode)) return "multi_unit";
    if (["plan_unit", "plan_and_unit", "計畫_單位", "計畫與單位"].includes(mode)) return "plan_unit";
    if (mode.includes("plan") || mode.includes("方案") || mode.includes("計畫")) return "plan";
    if (mode.includes("unit") || mode.includes("單位")) return "unit";
    if (["fixed", "none", "no_input", "固定", "免輸入"].includes(mode)) return "fixed";
    if (["unknown", "unsupported", "pending", "待整理", "未知"].includes(mode)) return "unknown";
    return "";
  }

  function canonicalCalculationBasis(value) {
    const basis = normalizeText(value);
    if (CALCULATION_BASES[basis]) return basis;
    return LEGACY_BASIS_MAP[basis] || "unknown";
  }

  function defaultAmountRole(basis) {
    if (basis === "percentage_of_base") return "base";
    if (["reimbursement_with_cap", "percentage_of_actual_expense_with_cap"].includes(basis)) return "limit";
    if (["table_multiplier", "tiered_or_stepped", "unknown"].includes(basis)) return "reference";
    return "payout";
  }

  function defaultLimitScope(basis, legacyBasis) {
    if (["per_day", "per_unit_per_day"].includes(basis)) return "per_day";
    if (legacyBasis === "annual_limit") return "annual";
    if (legacyBasis === "per_injury_limit") return "per_injury";
    if (
      [
        "fixed_amount",
        "percentage_of_base",
        "additional_benefit",
        "reimbursement_with_cap",
        "percentage_of_actual_expense_with_cap",
      ].includes(basis)
    ) return "per_event";
    return "unknown";
  }

  function normalizeCoverageEntry(entry, index) {
    const source = entry || {};
    const legacyBasis = normalizeText(source.basis);
    const calculationBasis = canonicalCalculationBasis(source.calculation_basis || legacyBasis);
    const amountRole = AMOUNT_ROLES[source.amount_role] ? source.amount_role : defaultAmountRole(calculationBasis);
    const limitScope = LIMIT_SCOPES[source.limit_scope]
      ? source.limit_scope
      : defaultLimitScope(calculationBasis, legacyBasis);
    const aggregationRule = AGGREGATION_RULES[source.aggregation_rule] ? source.aggregation_rule : "separate";
    const conditions = Array.isArray(source.conditions)
      ? source.conditions.map((value) => String(value || "").trim()).filter(Boolean)
      : String(source.conditions || "").trim()
        ? [String(source.conditions).trim()]
        : [];
    const amountTiers = Array.isArray(source.amount_tiers)
      ? source.amount_tiers
          .map((tier) => ({
            label: String(tier?.label || "").trim(),
            amount: normalizeMoneyAmount(tier?.amount),
          }))
          .filter((tier) => tier.label && tier.amount)
      : [];
    return {
      id: String(source.id || `coverage-${index + 1}`),
      name: String(source.name || "").trim(),
      amount: normalizeMoneyAmount(source.amount),
      basis: legacyBasis || calculationBasis,
      calculation_basis: calculationBasis,
      amount_role: amountRole,
      limit_scope: limitScope,
      aggregation_rule: aggregationRule,
      rate: normalizeRate(source.rate, source.rate_percent),
      rate_min: normalizeRate(source.rate_min, source.rate_min_percent),
      rate_max: normalizeRate(source.rate_max, source.rate_max_percent),
      multiplier: Number.isFinite(Number(source.multiplier)) && Number(source.multiplier) > 0 ? Number(source.multiplier) : null,
      unit_key: String(source.unit_key || "").trim(),
      amount_tiers: amountTiers,
      source: source.source === "user" ? "user" : "terms",
      note: String(source.note || "").trim(),
      conditions,
      source_ref: String(source.source_ref || "").trim(),
    };
  }

  function normalizeCoverageEntries(entries) {
    if (!Array.isArray(entries)) return [];
    return entries
      .filter((entry) => entry?.source !== "user")
      .map(normalizeCoverageEntry)
      .filter((entry) => entry.name || entry.amount);
  }

  function normalizePlanOptions(item) {
    const rawOptions = item?.plan_options || item?.benefit_schedule?.plans || [];
    if (!Array.isArray(rawOptions)) return [];
    const options = rawOptions
      .map((option) => {
        const source = typeof option === "string" ? { value: option, label: option } : option || {};
        const value = String(source.value || source.id || source.code || source.name || source.label || "").trim();
        const label = String(source.label || source.name || value).trim();
        return {
          value,
          label,
          coverage_entries: normalizeCoverageEntries(source.coverage_entries || source.benefits),
        };
      })
      .filter((option) => option.value && option.label);
    return [...new Map(options.map((option) => [option.value, option])).values()];
  }

  function normalizeUnitFields(item) {
    if (!Array.isArray(item?.unit_fields)) return [];
    const fields = item.unit_fields
      .map((field) => ({
        key: String(field?.key || "").trim(),
        label: String(field?.label || "").trim(),
      }))
      .filter((field) => field.key && field.label);
    return [...new Map(fields.map((field) => [field.key, field])).values()];
  }

  function declaredSelectionMode(item) {
    const explicit = canonicalSelectionMode(item?.selection_type || item?.input_mode || item?.quantity_mode);
    if (!explicit) return "";
    if (explicit === "unknown") return explicit;
    const hasReviewedPlanOptions = normalizePlanOptions(item).length > 0;
    const isTermsDeclared = normalizeText(item?.selection_source) === "terms";
    if (hasReviewedPlanOptions || isTermsDeclared) return explicit;
    return "";
  }

  function selectionMode(item) {
    const declared = declaredSelectionMode(item);
    if (declared) return declared;
    return "unknown";
  }

  function selectionRequirements(item) {
    const mode = selectionMode(item);
    return {
      mode,
      label: String(item?.selection_label || "").trim() || SELECTION_MODES[mode].label,
      guidance: String(item?.selection_guidance || "").trim(),
      fields: [...SELECTION_MODES[mode].fields],
      plan_options: normalizePlanOptions(item),
      unit_fields: normalizeUnitFields(item),
      is_verified: Boolean(declaredSelectionMode(item)) && mode !== "unknown",
    };
  }

  function effectiveCoverageEntries(item) {
    const options = normalizePlanOptions(item);
    const selectedPlan = options.find((option) => option.value === item?.plan_name || option.label === item?.plan_name);
    if (selectedPlan?.coverage_entries?.length) return selectedPlan.coverage_entries;
    return normalizeCoverageEntries(item?.coverage_entries || item?.benefit_rules);
  }

  function coverageValue(entry, selection) {
    const normalizedEntry = normalizeCoverageEntry(entry, 0);
    const item = selection || {};
    const amount = normalizedEntry.amount;
    const units = normalizeUnitCount(
      normalizedEntry.unit_key ? item.unit_counts?.[normalizedEntry.unit_key] : item.unit_count,
    );
    const faceAmount = normalizeMoneyAmount(item.face_amount);
    const result = {
      value: null,
      reference_amount: amount,
      state: amount ? "reference_only" : "missing_amount",
      calculation_basis: normalizedEntry.calculation_basis,
      amount_role: normalizedEntry.amount_role,
      limit_scope: normalizedEntry.limit_scope,
    };
    if (normalizedEntry.calculation_basis === "plan_schedule_lookup") {
      const options = normalizePlanOptions(item);
      const selectedPlan = options.find(
        (option) => option.value === item.plan_name || option.label === item.plan_name,
      );
      if (!selectedPlan) return { ...result, state: "needs_plan" };
    }
    if (!amount && !faceAmount) return result;

    if (["per_unit", "per_unit_per_day"].includes(normalizedEntry.calculation_basis)) {
      if (!amount || !units) return { ...result, state: "needs_unit_count" };
      const value = safeIntegerProduct(amount, units);
      return value
        ? {
            ...result,
            value,
            state: normalizedEntry.calculation_basis === "per_unit_per_day" ? "daily_rate" : "calculated",
          }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "percentage_of_base") {
      const unitBased = ["per_unit", "daily_per_unit"].includes(normalizedEntry.basis);
      if (unitBased && amount && !units && !faceAmount) {
        return { ...result, state: "needs_unit_count" };
      }
      const unitBase = unitBased && amount && units ? safeIntegerProduct(amount, units) : null;
      const base = faceAmount || unitBase || amount;
      if (!base) return { ...result, state: "needs_face_amount" };
      if (!normalizedEntry.rate) return { ...result, reference_amount: base, state: "needs_rate_table" };
      return { ...result, reference_amount: base, value: Math.trunc(base * normalizedEntry.rate), state: "calculated" };
    }
    if (normalizedEntry.calculation_basis === "table_multiplier") {
      const base = faceAmount || amount;
      if (!base) return { ...result, state: "needs_face_amount" };
      if (!normalizedEntry.multiplier) return { ...result, reference_amount: base, state: "needs_multiplier_table" };
      const value = safeIntegerProduct(base, normalizedEntry.multiplier);
      return value
        ? { ...result, reference_amount: base, value, state: "calculated" }
        : { ...result, reference_amount: base, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "tiered_or_stepped") {
      if (!normalizedEntry.amount_tiers.length) return result;
      const unitBased = ["per_unit", "daily_per_unit"].includes(normalizedEntry.basis);
      const tierValues = normalizedEntry.amount_tiers.map((tier) => ({
        label: tier.label,
        reference_amount: tier.amount,
        value: unitBased && units ? safeIntegerProduct(tier.amount, units) : null,
      }));
      if (unitBased && !units) return { ...result, state: "needs_unit_count", tier_values: tierValues };
      if (tierValues.some((tier) => unitBased && !tier.value)) {
        return { ...result, state: "amount_overflow", tier_values: tierValues };
      }
      return { ...result, state: "tiered_values", tier_values: tierValues };
    }
    if (
      [
        "reimbursement_with_cap",
        "percentage_of_actual_expense_with_cap",
      ].includes(normalizedEntry.calculation_basis)
    ) {
      const unitBased = ["per_unit", "daily_per_unit"].includes(normalizedEntry.basis);
      if (unitBased && !units) return { ...result, state: "needs_unit_count" };
      const policyRecordedLimit = normalizedEntry.basis === "policy_recorded_limit";
      const baseLimit = policyRecordedLimit ? (faceAmount || amount) : amount;
      if (!baseLimit) return result;
      const value = unitBased ? safeIntegerProduct(baseLimit, units) : baseLimit;
      return value
        ? { ...result, value, reference_amount: value, state: "benefit_limit" }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "unknown") return result;
    if (!amount) return result;
    if (normalizedEntry.calculation_basis === "per_day") {
      return { ...result, value: amount, state: "daily_rate" };
    }
    if (normalizedEntry.calculation_basis === "additional_benefit") {
      return { ...result, value: amount, state: "conditional_amount" };
    }
    return { ...result, value: amount, state: "calculated" };
  }

  function coverageDetectionText(item) {
    return normalizeText(
      [item?.product_name, item?.product_id, item?.sale_status, item?.display_version, ...(item?.coverage_tags || []), ...(item?.flags || [])].join(" "),
    );
  }

  function detectCoverageBuckets(item) {
    const text = coverageDetectionText(item);
    const category = normalizeText(item?.product_type);
    const officialGroup = Object.entries(OFFICIAL_CATEGORY_GROUPS).find(([, categories]) =>
      [...categories].some((itemCategory) => category === normalizeText(itemCategory)),
    )?.[0];
    if (officialGroup === "property") {
      return COVERAGE_BUCKETS.filter(
        (bucket) => bucket.group === "property" && bucket.categories.some((itemCategory) => category === normalizeText(itemCategory)),
      ).map((bucket) => ({ ...bucket, matchedKeywords: [] }));
    }
    return COVERAGE_BUCKETS.map((bucket) => {
      if (officialGroup && bucket.group !== officialGroup) return null;
      const categoryMatched = bucket.categories.some((itemCategory) => category === normalizeText(itemCategory));
      const matchedKeywords = bucket.keywords.filter((keyword) => text.includes(normalizeText(keyword)));
      return categoryMatched || matchedKeywords.length ? { ...bucket, matchedKeywords } : null;
    }).filter(Boolean);
  }

  return {
    MAX_MONEY_AMOUNT,
    MAX_UNIT_COUNT,
    MAX_RATE,
    SELECTION_MODES,
    CALCULATION_BASES,
    AMOUNT_ROLES,
    LIMIT_SCOPES,
    AGGREGATION_RULES,
    COVERAGE_BUCKETS,
    normalizeUnitCount,
    normalizeMoneyAmount,
    productVersionFamilyName,
    normalizeCoverageEntry,
    normalizeCoverageEntries,
    normalizePlanOptions,
    normalizeUnitFields,
    declaredSelectionMode,
    selectionMode,
    selectionRequirements,
    effectiveCoverageEntries,
    coverageValue,
    detectCoverageBuckets,
  };
});

const DEFAULT_FILTERS = {
  search: "",
  company: "all",
  kind: "all",
  crawl: "all",
};

const state = {
  sourceIndex: null,
  taxonomy: null,
  crawlStatus: null,
  policyInsights: null,
  tiiMetadata: null,
  tiiResults: null,
  tiiManifest: null,
  tiiIndexRecords: null,
  tiiIndexLoadPromise: null,
  tiiDocumentSummaryCache: new Map(),
  tiiDocumentSummaryPromises: new Map(),
  tiiExecutionProgress: null,
  siteSummary: null,
  batchPlan: null,
  batchProgress: null,
  policyContentExtracts: null,
  crawlByUrlId: new Map(),
  openSourceId: null,
  search: DEFAULT_FILTERS.search,
  company: DEFAULT_FILTERS.company,
  kind: DEFAULT_FILTERS.kind,
  crawl: DEFAULT_FILTERS.crawl,
  tiiMode: "property",
  portfolioItems: [],
  portfolioSuggestions: [],
  portfolioDetailItem: null,
  editingPortfolioId: null,
  portfolioCompany: "all",
  portfolioBucket: "all",
  portfolioSuggestionPage: 1,
  portfolioSuggestionPageSize: 10,
  policyPage: 1,
  policyPageSize: 20,
};

const formatNumber = new Intl.NumberFormat("zh-Hant-TW", {
  maximumFractionDigits: 4,
});
const PORTFOLIO_STORAGE_KEY = "taiwanPolicyNavigator.portfolio.v1";
const PORTFOLIO_PAGE_SIZES = [5, 10, 20, 50, 100];
const POLICY_PAGE_SIZES = [20, 50, 100, 200];
const coverageModel = window.PolicyCoverageModel;
if (!coverageModel) throw new Error("保障計算模組載入失敗");
const COVERAGE_AMOUNT_BASES = coverageModel.CALCULATION_BASES;
const coverageBuckets = coverageModel.COVERAGE_BUCKETS;
let portfolioCompanyFilterTimer = null;
let portfolioSearchGeneration = 0;

const crawlLabels = {
  all: "全部",
  ok: "可開啟",
  blocked: "網站限制",
  error: "需人工確認",
  unchecked: "尚未檢查",
};

const policyFocusLabels = {
  all: "全部",
  complete: "四項都有",
  special: "有特殊項目",
  needs_review: "需回官方確認",
};

const focusOrder = ["coverage", "definitions", "special", "claims"];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

function matchesQuery(searchText, query) {
  const normalizedQuery = normalize(query);
  if (!normalizedQuery) return true;
  const haystack = normalize(searchText);
  return normalizedQuery.split(/\s+/).filter(Boolean).every((term) => haystack.includes(term));
}

function clampNumber(value, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return min;
  return Math.min(Math.max(number, min), max);
}

function normalizeUnitCount(value) {
  return coverageModel.normalizeUnitCount(value);
}

function unitText(value) {
  const units = normalizeUnitCount(value);
  return units ? `${formatNumber.format(units)} 單位` : "未填單位數";
}

function planText(value, item) {
  const plan = String(value || "").trim();
  if (!plan) return "";
  const option = normalizePlanOptions(item).find(
    (candidate) => candidate.value === plan || candidate.label === plan,
  );
  if (option) return option.label;
  const indexedPlan = /^plan-(\d+)$/i.exec(plan);
  const indexedLabels = [
    "計畫一",
    "計畫二",
    "計畫三",
    "計畫四",
    "計畫五",
    "計畫六",
    "計畫七",
    "計畫八",
    "計畫九",
    "計畫十",
    "計畫十一",
    "計畫十二",
  ];
  if (indexedPlan) return indexedLabels[Number(indexedPlan[1]) - 1] || `計畫 ${indexedPlan[1]}`;
  return /^(計畫|方案)/.test(plan) ? plan : `計畫 ${plan}`;
}

function normalizeCoverageAmount(value, item) {
  const decimalPlaces = coverageModel.moneyDecimalPlaces(item);
  return decimalPlaces
    ? coverageModel.normalizeDecimalMoneyAmount(
        value,
        decimalPlaces,
      )
    : coverageModel.normalizeMoneyAmount(value);
}

function itemCurrencyLabel(item) {
  const requiresIsoCode =
    item?.version_characteristics?.contract_currency_code_format ===
    "iso_4217_alpha3";
  const contractCurrency = requiresIsoCode
    ? coverageModel.normalizeContractCurrencyCode(
        item?.policy_state?.contract_currency,
      )
    : coverageModel.normalizePolicyText(
        item?.policy_state?.contract_currency,
        20,
      );
  const requiresContractCurrency = coverageModel
    .policyStateRequirements(item)
    .fields
    .some((field) => field.key === "contract_currency");
  return contractCurrency || (requiresContractCurrency ? "契約幣別" : "元");
}

function faceAmountText(item) {
  const amount = normalizeCoverageAmount(item?.face_amount, item);
  const label = coverageModel.selectionRequirements(item).label;
  return amount
    ? `${label} ${formatNumber.format(amount)} ${itemCurrencyLabel(item)}`
    : `未填${label}`;
}

function accountValueText(item) {
  const amount = normalizeCoverageAmount(
    item?.account_value || item?.policy_state?.policy_account_value,
    item,
  );
  const label = coverageModel.selectionRequirements(item).label || "保單帳戶價值";
  return amount
    ? `${label} ${formatNumber.format(amount)} ${itemCurrencyLabel(item)}`
    : `未填${label}`;
}

function policyStateFieldLabel(key) {
  return coverageModel.POLICY_STATE_FIELDS?.[key]?.label || key;
}

function policyStateFieldsText(keys) {
  const labels = [...new Set(keys || [])].map(policyStateFieldLabel).filter(Boolean);
  return labels.length ? labels.join("、") : "必要保單狀態";
}

function policyStateValueText(field, value) {
  const normalizedValue = String(value ?? "").trim();
  if (!normalizedValue) return "";
  if (field.type === "rate") return `${normalizedValue}%`;
  if (["number", "integer"].includes(field.type)) {
    return `${normalizedValue}${field.unit ? ` ${field.unit}` : ""}`;
  }
  if (field.type === "boolean") return value === true || normalizedValue === "true" ? "已確認" : "";
  if (field.type === "choice") {
    return field.options?.find((option) => option.value === normalizedValue)?.label || normalizedValue;
  }
  if (field.type === "text") return normalizedValue;
  const amount = normalizeCoverageAmount(normalizedValue);
  return amount ? `${formatNumber.format(amount)} 元` : normalizedValue;
}

function normalizedPolicyStateValue(field, input, item) {
  if (field.type === "boolean") return input?.checked ? true : null;
  const rawValue = String(input?.value || "").trim();
  input?.setCustomValidity("");
  if (!rawValue) return null;
  if (field.type === "choice") {
    const valid = field.options?.some((option) => option.value === rawValue);
    input?.setCustomValidity(valid ? "" : `請選擇${field.label}`);
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return rawValue;
  }
  if (field.type === "text") {
    const value = coverageModel.normalizePolicyText(rawValue, field.max_length);
    const pattern = field.pattern ? new RegExp(field.pattern, "u") : null;
    const valid = Boolean(value) && (!pattern || pattern.test(value));
    input?.setCustomValidity(
      valid
        ? ""
        : field.key === "contract_currency"
          ? `${field.label}請輸入三碼英文字母，例如 USD`
          : `${field.label}請輸入有效文字`,
    );
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return value;
  }
  if (field.type === "integer") {
    const value = Number(rawValue.replaceAll(",", ""));
    const max = Number(field.max || coverageModel.MAX_INSURED_AGE);
    const min = field.allow_zero ? 0 : 1;
    const valid = Number.isSafeInteger(value) && value >= min && value <= max;
    input?.setCustomValidity(valid ? "" : `${field.label}請輸入 ${min} 到 ${formatNumber.format(max)} 的整數`);
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return value;
  }
  if (field.type === "number") {
    const value = Number(rawValue.replaceAll(",", ""));
    const max = Number(field.max || coverageModel.MAX_RATE * 100);
    const min = field.allow_zero ? 0 : Number.EPSILON;
    const valid = Number.isFinite(value) && value >= min && value <= max;
    input?.setCustomValidity(valid ? "" : `${field.label}請輸入 ${field.allow_zero ? "0" : "大於 0"} 到 ${formatNumber.format(max)} 之間的數字`);
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return value;
  }
  if (field.type === "rate") {
    const value = Number(rawValue.replaceAll(",", ""));
    const maxPercent = coverageModel.MAX_RATE * 100;
    const valid = Number.isFinite(value) && value >= 0 && value <= maxPercent;
    input?.setCustomValidity(valid ? "" : `${field.label}請輸入 0 到 ${formatNumber.format(maxPercent)} 的百分比`);
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return value;
  }
  if (field.type === "non_negative_money") {
    const decimalPlaces = coverageModel.moneyDecimalPlaces(item);
    if (decimalPlaces) {
      const value = coverageModel.normalizeDecimalMoneyAmount(
        rawValue,
        decimalPlaces,
        true,
      );
      const valid = value !== null;
      input?.setCustomValidity(
        valid
          ? ""
          : `${field.label}請輸入 0 到 ${formatNumber.format(coverageModel.MAX_MONEY_AMOUNT)}、最多 ${decimalPlaces} 位小數的金額`,
      );
      if (!valid) {
        input?.reportValidity();
        return undefined;
      }
      return value;
    }
    const value = Number(rawValue.replaceAll(",", ""));
    const valid = Number.isSafeInteger(value) && value >= 0 && value <= coverageModel.MAX_MONEY_AMOUNT;
    input?.setCustomValidity(valid ? "" : `${field.label}請輸入 0 到 ${formatNumber.format(coverageModel.MAX_MONEY_AMOUNT)} 的整數金額`);
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return value;
  }
  const decimalPlaces = coverageModel.moneyDecimalPlaces(item);
  if (decimalPlaces) {
    const value = coverageModel.normalizeDecimalMoneyAmount(
      rawValue,
      decimalPlaces,
    );
    const valid = value !== null;
    input?.setCustomValidity(
      valid
        ? ""
        : `${field.label}請輸入大於 0、最多 ${decimalPlaces} 位小數的金額`,
    );
    if (!valid) {
      input?.reportValidity();
      return undefined;
    }
    return value;
  }
  const amount = positiveIntegerInputValue(input, field.label, coverageModel.MAX_MONEY_AMOUNT, true);
  return amount === null ? null : amount;
}

function normalizePolicyStateForItem(container, item) {
  const stateValues = {};
  const fields = coverageModel.policyStateRequirements(item).fields;
  for (const field of fields) {
    const input = container.querySelector(`[data-policy-state-key="${CSS.escape(field.key)}"]`);
    if (!input) continue;
    const value = normalizedPolicyStateValue(field, input, item);
    if (value === undefined) return null;
    if (value !== null) stateValues[field.key] = value;
  }
  return stateValues;
}

const TWD_CONFIRMATION_DEPENDENT_FIELDS = new Set([
  "benefit_valuation_policy_account_value",
  "benefit_valuation_basic_premium_policy_account_value",
  "maturity_policy_account_value",
  "maturity_basic_premium_policy_account_value",
  "policy_value_component",
  "general_death_disability_insurance_amount",
  "accidental_death_disability_insurance_amount",
  "unallocated_net_premium_amount",
]);

function policyStateWithFieldUpdate(item, key, value) {
  const policyState = {
    ...(item?.policy_state || {}),
    [key]: value,
  };
  if (TWD_CONFIRMATION_DEPENDENT_FIELDS.has(key)) {
    policyState.policy_values_converted_to_twd = false;
  }
  return policyState;
}

function syncPolicyStateConfirmationControl(container, item, changedKey) {
  if (!TWD_CONFIRMATION_DEPENDENT_FIELDS.has(changedKey)) return;
  const confirmation = container?.querySelector(
    `[data-policy-state-key="${CSS.escape("policy_values_converted_to_twd")}"]`,
  );
  if (confirmation) {
    confirmation.checked = item?.policy_state?.policy_values_converted_to_twd === true;
  }
}

function policyStateInputHtml(field, item) {
  const value = item?.policy_state?.[field.key] ?? "";
  if (field.type === "boolean") {
    return `
      <label class="policy-state-field policy-state-confirmation">
        <span>${escapeHtml(field.label)}</span>
        <span class="check-control">
          <input type="checkbox" ${value === true ? "checked" : ""} data-policy-state-key="${escapeHtml(field.key)}">
          <span>已確認</span>
        </span>
        <small>${escapeHtml(field.guidance || "")}</small>
      </label>
    `;
  }
  if (field.type === "choice") {
    return `
      <label class="policy-state-field">
        <span>${escapeHtml(field.label)}</span>
        <select data-policy-state-key="${escapeHtml(field.key)}">
          <option value="">請選擇</option>
          ${(field.options || [])
            .map(
              (option) =>
                `<option value="${escapeHtml(option.value)}" ${String(value) === String(option.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>`,
            )
            .join("")}
        </select>
        <small>${escapeHtml(field.guidance || "")}</small>
      </label>
    `;
  }
  const isCurrencyAmount = field.type?.includes("money") && coverageModel
    .policyStateRequirements(item)
    .fields
    .some((requiredField) => requiredField.key === "contract_currency");
  const displayUnit = isCurrencyAmount ? itemCurrencyLabel(item) : field.unit || "";
  const moneyDecimalPlaces = coverageModel.moneyDecimalPlaces(item);
  const moneyStep = moneyDecimalPlaces
    ? `0.${"0".repeat(moneyDecimalPlaces - 1)}1`
    : "1";
  const moneyInputMode = moneyDecimalPlaces ? "decimal" : "numeric";
  const inputAttrs = field.type === "rate"
    ? `type="number" min="0" max="${coverageModel.MAX_RATE * 100}" step="0.01" inputmode="decimal"`
    : field.type === "text"
      ? `type="text" maxlength="${escapeHtml(field.max_length || 100)}" autocomplete="off"`
      : field.type === "integer"
        ? `type="number" min="${field.allow_zero ? 0 : 1}" max="${escapeHtml(field.max || coverageModel.MAX_INSURED_AGE)}" step="1" inputmode="numeric"`
    : field.type === "number"
      ? `type="number" min="0" max="${escapeHtml(field.max || coverageModel.MAX_RATE * 100)}" step="${escapeHtml(field.step || "0.01")}" inputmode="decimal"`
      : field.type === "non_negative_money"
        ? `type="number" min="0" max="${coverageModel.MAX_MONEY_AMOUNT}" step="${moneyStep}" inputmode="${moneyInputMode}"`
        : `type="number" min="${moneyStep}" max="${coverageModel.MAX_MONEY_AMOUNT}" step="${moneyStep}" inputmode="${moneyInputMode}"`;
  const placeholder = field.type === "rate"
    ? "例如：2.25"
    : field.key === "contract_currency" &&
        field.pattern
      ? "例如：USD"
    : field.type === "text"
      ? "例如：USD 或美元"
      : field.type === "integer"
        ? `請輸入${field.unit || "正整數"}`
    : field.type === "number"
      ? "例如：1.3 或 130"
      : "請輸入保單列示金額";
  return `
    <label class="policy-state-field">
      <span>${escapeHtml(field.label)}</span>
      <div class="money-input">
        <input ${inputAttrs} value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}" data-policy-state-key="${escapeHtml(field.key)}">
        <span>${escapeHtml(displayUnit)}</span>
      </div>
      <small>${escapeHtml(field.guidance || "")}</small>
    </label>
  `;
}

function policyStateFieldsHtml(item) {
  const selectionFields = coverageModel.selectionRequirements(item).fields;
  const fields = coverageModel
    .policyStateRequirements(item)
    .fields
    .filter((field) => !(field.key === "policy_account_value" && selectionFields.includes("account_value")));
  if (!fields.length) return "";
  return `
    <details class="policy-state-fields" data-policy-state-fields ${fields.length <= 2 ? "open" : ""}>
      <summary class="policy-state-guidance">
        <strong>這張保單還需要補 ${formatNumber.format(fields.length)} 項資料才能完整計算</strong>
        <span>可先留白；系統會在對應保障項目旁提示缺哪一項。</span>
      </summary>
      <p class="policy-state-note">這些資料會隨保單現況、事故日或保險公司試算而變動，不會被當成條款固定金額。</p>
      <div class="policy-state-grid">
        ${fields.map((field) => policyStateInputHtml(field, item)).join("")}
      </div>
    </details>
  `;
}

function normalizeCoverageEntries(entries) {
  return coverageModel.normalizeCoverageEntries(entries);
}

function normalizePlanOptions(item) {
  return coverageModel.normalizePlanOptions(item);
}

function declaredSelectionMode(item) {
  return coverageModel.declaredSelectionMode(item);
}

function portfolioSelectionMode(item) {
  return coverageModel.selectionMode(item);
}

function effectiveCoverageEntries(item) {
  return coverageModel.effectiveCoverageEntries(item);
}

function coverageSelection(value) {
  return value && typeof value === "object" ? value : { unit_count: value };
}

function coverageEntryUnitCount(entry, selection) {
  const key = String(entry?.unit_key || "").trim();
  return normalizeUnitCount(key ? selection?.unit_counts?.[key] : selection?.unit_count);
}

function coverageFormulaCandidateLabel(candidate) {
  const labels = {
    annual_premium_total_times_rate: "年繳應繳保險費總和乘以條款倍數",
    annual_premium_total_times_rate_minus_prior_long_term_care:
      "年繳應繳保險費總和乘以條款倍數後扣除已領長照金",
    face_amount_minus_prior_long_term_care:
      "保險金額扣除已領長照金",
    policy_reserve_value: "保單價值準備金",
  };
  return labels[candidate?.key] || policyStateFieldLabel(candidate?.key);
}

function paidPremiumFactorCoverageText(name, result, currencyLabel) {
  const factorText = result.specified_factor
    ? `${formatNumber.format(result.specified_factor)} 倍`
    : "指定倍數";
  const basisText =
    result.paid_premium_basis !== undefined
      ? `已繳保費基礎 ${formatNumber.format(result.paid_premium_basis)} ${currencyLabel}`
      : "已繳保費基礎";
  const accountText =
    result.account_value !== undefined
      ? `保單帳戶價值 ${formatNumber.format(result.account_value)} ${currencyLabel}`
      : "保單帳戶價值";
  const formulaText =
    result.formula_type === "A"
      ? `${basisText} × ${factorText} 與 ${accountText} 取高者`
      : `${basisText} × ${factorText} + ${accountText}`;
  const offsetText = [
    ["保單借款及利息", result.policy_loan_and_interest_amount],
    ["其他未償費用", result.unpaid_policy_charge_amount],
    ["匯款相關費用", result.remittance_fee_amount],
  ]
    .filter(([, value]) => value)
    .map(
      ([label, value]) =>
        ` - ${label} ${formatNumber.format(value)} ${currencyLabel}`,
    )
    .join("");
  const funeralText =
    result.funeral_benefit_limit !== null &&
    result.funeral_benefit_limit !== undefined
      ? `；非投資保障部分以喪葬費用剩餘額度 ${formatNumber.format(result.funeral_benefit_limit)} ${currencyLabel}為限`
      : "";
  const grossText =
    result.gross_value_before_offsets !== undefined
      ? `，毛額 ${formatNumber.format(result.gross_value_before_offsets)} ${currencyLabel}`
      : "";
  return `${name}：${formulaText}${funeralText}${grossText}${offsetText} = ${formatNumber.format(result.value)} ${currencyLabel}`;
}

function coverageEntryText(entry, selectedValues) {
  const normalized = coverageModel.normalizeCoverageEntry(entry, 0);
  const selection = coverageSelection(selectedValues);
  const amount = normalized.amount;
  const result = coverageModel.coverageValue(normalized, selection);
  const name = normalized.name || "保障項目";
  const currencyLabel = String(result.currency_label || "元").trim() || "元";
  const formattedAmount = amount ? `${formatNumber.format(amount)} 元` : "待補條款金額";
  const units = coverageEntryUnitCount(normalized, selection);
  const rateRange = [normalized.rate_min, normalized.rate_max]
    .filter(Boolean)
    .map((rate) => `${formatNumber.format(rate * 100)}%`)
    .join("～");

  if (result.state === "needs_plan") return `${name}：請先選擇計畫，再依條款附表顯示金額`;
  if (result.state === "amount_overflow") return `${name}：金額超出可安全計算範圍，請回條款確認`;
  if (result.state === "needs_policy_state") {
    return `${name}：請輸入${policyStateFieldsText(result.required_fields)}後計算${normalized.note ? `；${normalized.note}` : ""}`;
  }
  if (result.state === "needs_insurer_confirmation") {
    if (result.confirmation_reason === "contract_not_confirmed_active") {
      return `${name}：給付時點的契約不是已確認有效狀態，無法直接套用有效契約的條款公式；請由保險公司確認復效、終止或實際可領金額`;
    }
    if (result.confirmation_reason === "offsets_exceed_gross_benefit") {
      return `${name}：保單借款、利息或尚未扣除費用合計高於本次試算毛額，不能直接算成 0 元；請向保險公司確認正式結算金額`;
    }
    if (
      result.confirmation_reason ===
      "disability_status_after_waiting_period_uncertain"
    ) {
      return `${name}：條款要求殘廢確定滿 180 日後狀態仍持續存在；目前尚未確認，請依醫療與理賠文件補充後再計算`;
    }
    if (
      result.confirmation_reason ===
      "fractional_monthly_amount_rounding_undefined"
    ) {
      return `${name}：主約金額的 1% 為 ${formatNumber.format(result.raw_monthly_amount)} 元，但條款未載明元以下如何處理，請向保險公司確認正式月給付金額`;
    }
    if (
      result.confirmation_reason ===
      "fractional_policy_amount_rounding_undefined"
    ) {
      return `${name}：條款公式會產生元以下數值，但本版條款未載明如何取捨；系統不會自行四捨五入，請向保險公司確認正式給付金額`;
    }
    if (
      result.confirmation_reason ===
      "benefit_exclusion_requires_review"
    ) {
      return `${name}：可能適用除外責任或尚未確認，不能直接套用一般給付公式；請由保險公司確認是否給付及帳戶價值返還方式`;
    }
    if (
      result.confirmation_reason ===
      "total_disability_not_confirmed"
    ) {
      return `${name}：尚未確認符合本版條款第一級七項全殘之一，不能直接換算全殘保險金；請依診斷及理賠認定確認`;
    }
    if (
      result.confirmation_reason ===
      "aggregate_cap_allocation_required"
    ) {
      return `${name}：本保單依條款為 ${formatNumber.format(result.gross_value)} 元，同公司其他保單為 ${formatNumber.format(result.other_benefit_amount)} 元，合計 ${formatNumber.format(result.combined_benefit_amount)} 元已超過跨契約上限 ${formatNumber.format(result.aggregate_limit)} 元；目前剩餘額度為 ${formatNumber.format(result.marginal_capacity)} 元，但條款未載明各契約如何分配，請由保險公司確認本保單實際金額`;
    }
    return `${name}：目前保單狀態超出本版條款可安全自動換算的範圍，請向保險公司確認`;
  }
  if (result.state === "not_eligible") {
    if (
      result.exclusion_state_key ===
      "disability_support_claim_status"
    ) {
      return `${name}：這不是目前選擇的給付情境，因此不列入本次試算`;
    }
    if (
      result.eligibility_reason ===
      "insured_age_above_maximum"
    ) {
      return `${name}：事故時保險年齡為 ${formatNumber.format(result.insured_age_at_event)} 歲，超過本版條款列示的 ${formatNumber.format(result.maximum_eligible_age)} 歲範圍，試算為 0 元`;
    }
    if (
      result.eligibility_reason ===
      "disability_not_persisting_after_waiting_period"
    ) {
      return `${name}：殘廢確定滿 ${formatNumber.format(result.waiting_period_days)} 日後狀態未持續存在，不符合本項月給付條件，試算為 0 元`;
    }
    return `${name}：依你選擇的${policyStateFieldLabel(result.exclusion_state_key)}，本項不符合條款給付條件，保障試算為 0 元`;
  }
  if (result.state === "needs_account_value") {
    return `${name}：請輸入保單帳戶價值後呈現${normalized.note ? `；${normalized.note}` : ""}`;
  }
  if (result.state === "outside_terms_formula_age_range") {
    return `${name}：本版條款的保險金最低比率表自滿 ${formatNumber.format(result.minimum_formula_age || 15)} 足歲起適用；事故時年齡為 ${formatNumber.format(result.insured_age_at_event || 0)} 歲，無法由該表自動換算，請向保險公司確認實際給付金額`;
  }
  if (result.state === "needs_annuity_factor") {
    return `${name}：保單帳戶價值 ${formatNumber.format(result.reference_amount)} 元；年金金額仍需依年金生命表、預定利率與給付方式換算，若已有保險公司試算可填入年金給付金額`;
  }
  if (
    normalized.calculation_basis ===
      "protected_amount_plus_policy_account_value" &&
    Number.isSafeInteger(result.value)
  ) {
    const faceLabel = selection.face_amount_label || "基本保險金額";
    const protectedText = result.formula_type === "minor_account_value_return"
      ? `事故時未滿 ${formatNumber.format(result.minor_account_value_return_age || 15)} 足歲，條款保障額不計入`
      : result.formula_type === "funeral_cap_plus_account_value"
        ? `${faceLabel} ${formatNumber.format(result.face_amount)} 元受本保單喪葬費用剩餘額度 ${formatNumber.format(result.remaining_funeral_benefit_limit || 0)} 元限制，保障部分為 ${formatNumber.format(result.protected_amount)} 元`
        : `${faceLabel} ${formatNumber.format(result.protected_amount)} 元`;
    const accountLabel = policyStateFieldLabel(
      result.policy_state_key ||
        "benefit_valuation_policy_account_value",
    );
    const accountText = `${accountLabel} ${formatNumber.format(result.benefit_valuation_policy_account_value)} 元`;
    const pendingText = result.investment_allocation_status === "awaiting_allocation"
      ? ` + 已收取尚未投入之淨保險費 ${formatNumber.format(result.unallocated_net_premium_amount)} 元`
      : "";
    const insuranceCostRefundAmount =
      result.post_event_insurance_cost_refund_amount ||
      result.unexpired_premium_refund_amount ||
      0;
    const insuranceCostRefundText = insuranceCostRefundAmount
      ? ` + 事故後已收取保險成本返還 ${formatNumber.format(insuranceCostRefundAmount)} 元`
      : "";
    const offsets = (result.policy_loan_and_interest_amount || 0) +
      (result.unpaid_policy_charge_amount || 0);
    const offsetText = offsets
      ? ` - 保單借款及利息 ${formatNumber.format(result.policy_loan_and_interest_amount || 0)} 元 - 尚未扣除費用 ${formatNumber.format(result.unpaid_policy_charge_amount || 0)} 元`
      : "";
    return `${name}：${protectedText} + ${accountText}${pendingText}${insuranceCostRefundText}${offsetText} = ${formatNumber.format(result.value)} 元；帳戶價值及事故後已收取保險成本須以保險公司正式列示金額為準`;
  }
  if (result.state === "account_value_return") {
    if (
      result.formula_type === "low_annual_annuity_lump_sum"
    ) {
      return `${name}：保險公司試算的每年年金 ${formatNumber.format(result.annual_annuity_amount)} 元，低於條款門檻 ${formatNumber.format(result.minimum_annual_annuity_amount)} 元，改為一次給付年金開始日保單帳戶價值 ${formatNumber.format(result.value)} ${currencyLabel}`;
    }
    const ageText = result.formula_type === "minor_account_value_return"
      ? "事故時未滿 15 足歲，依條款返還"
      : "依";
    if (
      result.product_family ===
      "global-new-excellence-variable-universal-life"
    ) {
      const refundText = result.delayed_notice_policy_fee_refund_amount
        ? `；事故後應退保單費用 ${formatNumber.format(result.delayed_notice_policy_fee_refund_amount)} ${currencyLabel}已併入帳戶價值重算`
        : "";
      const loanText = `；再扣除保單借款及利息 ${formatNumber.format(result.policy_loan_and_interest_amount || 0)} ${currencyLabel}`;
      const confirmationText =
        result.minor_funeral_precedence_requires_insurer_confirmation
          ? "；若同時涉及條款所列心智狀態，適用先後請向保險公司確認"
          : "";
      return `${name}：${ageText}調整後保單帳戶價值 ${formatNumber.format(result.gross_value_before_loan_offset)} ${currencyLabel}${refundText}${loanText} = ${formatNumber.format(result.value)} ${currencyLabel}${confirmationText}`;
    }
    return `${name}：${ageText}保單帳戶價值 ${formatNumber.format(result.value)} ${currencyLabel}`;
  }
  if (
    result.formula_type ===
      "disability_support_monthly_schedule" &&
    Number.isSafeInteger(result.value)
  ) {
    const baseLabel =
      result.policy_type === "investment"
        ? "投資型主約基本保額"
        : result.policy_type === "non_investment"
          ? "非投資型主約保險金額"
          : "主約保險金額";
    const capText =
      result.allocation_state === "needs_insurer_confirmation"
        ? `；另有同一保險公司其他同類月給付 ${formatNumber.format(result.other_disability_support_monthly_amount)} 元，合計 ${formatNumber.format(result.combined_monthly_total)} 元已超過每月 ${formatNumber.format(result.combined_monthly_cap_amount)} 元上限；本附約邊際可納入額度為 ${formatNumber.format(result.marginal_monthly_capacity)} 元，實際跨契約分配須由保險公司確認`
        : result.other_disability_support_monthly_amount
          ? `；另有同一保險公司其他同類月給付 ${formatNumber.format(result.other_disability_support_monthly_amount)} 元，合計 ${formatNumber.format(result.combined_monthly_total)} 元，未超過每月 ${formatNumber.format(result.combined_monthly_cap_amount)} 元上限`
          : `；本附約與同一保險公司同類給付合計每月上限 ${formatNumber.format(result.combined_monthly_cap_amount)} 元`;
    const priorText =
      result.prior_disability_status === "exists"
        ? `；有既往殘廢時依保險公司核定剩餘 ${formatNumber.format(result.payable_payment_months)} 個月，可申領名目總額為 ${formatNumber.format(result.payable_nominal_total)} 元`
        : `；名目總額 ${formatNumber.format(result.payable_nominal_total)} 元`;
    return `${name}：${baseLabel} ${formatNumber.format(result.face_amount)} 元 × ${formatNumber.format(result.monthly_rate * 100)}% = 本附約條款月額 ${formatNumber.format(result.value)} 元${capText}；第 ${escapeHtml(result.disability_grade)} 級最長 ${formatNumber.format(result.payment_months)} 個月${priorText}；須符合殘廢確定滿 ${formatNumber.format(result.waiting_period_days)} 日後仍持續存在等條款條件`;
  }
  if (
    normalized.calculation_basis === "maturity_policy_account_value" &&
    result.state === "conditional_amount"
  ) {
    if (result.gross_value_before_offsets !== undefined) {
      const interestText = result.maturity_interest_amount
        ? ` + 保險公司列示利息 ${formatNumber.format(result.maturity_interest_amount)} ${currencyLabel}`
        : "";
      const loanText = result.policy_loan_and_interest_amount
        ? ` - 保單借款及應付利息 ${formatNumber.format(result.policy_loan_and_interest_amount)} ${currencyLabel}`
        : "";
      const chargeText = result.unpaid_policy_charge_amount
        ? ` - 尚未扣除費用 ${formatNumber.format(result.unpaid_policy_charge_amount)} ${currencyLabel}`
        : "";
      const remittanceText = result.remittance_fee_amount
        ? ` - 匯款相關費用 ${formatNumber.format(result.remittance_fee_amount)} ${currencyLabel}`
        : "";
      const maturityAccountLabel = policyStateFieldLabel(
        result.policy_state_key || "maturity_policy_account_value",
      );
      return `${name}：${maturityAccountLabel} ${formatNumber.format(result.maturity_policy_account_value)} ${currencyLabel}${interestText}${loanText}${chargeText}${remittanceText} = ${formatNumber.format(result.value)} ${currencyLabel}；實際金額仍依保險公司滿期評價日、匯率與正式結算為準`;
    }
    return `${name}：契約於滿期時仍有效且被保險人生存時，依保險公司按實際投資標的、評價日與匯率列示的滿期保單帳戶價值 ${formatNumber.format(result.value)} 元；不可用目前帳戶價值推定；這是保障試算，不代表滿期時一定給付此金額`;
  }
  if (result.state === "policy_state_value") {
    if (
      normalized.id ===
      "chubb-disability-support-death-balance"
    ) {
      return `${name}：依保險公司按未支領期數及條款預定利率 2% 正式列示的折現金額，呈現為 ${formatNumber.format(result.value)} 元；這不是另一筆月給付，不能與扶助金名目總額重複加總`;
    }
    if (
      result.formula_type === "insurer_quoted_annual_annuity"
    ) {
      return `${name}：保險公司試算的每年年金為 ${formatNumber.format(result.value)} ${currencyLabel}；條款門檻為 ${formatNumber.format(result.minimum_annual_annuity_amount)} 元，年領上限為 ${formatNumber.format(result.maximum_annual_annuity_amount)} 元，實際給付仍依保險公司正式通知`;
    }
    if (normalized.result_kind === "payment_method") {
      return `${name}：依保險公司實際列示的每期金額 ${formatNumber.format(result.value)} ${currencyLabel}呈現；這是給付方式，不是額外保障`;
    }
    if (
      result.quantity_state_key &&
      Number.isSafeInteger(result.eligible_quantity)
    ) {
      const quantityLabel = policyStateFieldLabel(
        result.quantity_state_key,
      );
      const cappedText =
        result.quantity_cap &&
        result.quantity > result.eligible_quantity
          ? `（${result.quantity_cap_state_key ? "保單記載上限" : "條款上限"} ${formatNumber.format(result.quantity_cap)}，本次輸入 ${formatNumber.format(result.quantity)}）`
          : "";
      return `${name}：${policyStateFieldLabel(result.policy_state_key)} ${formatNumber.format(result.reference_amount)} 元 × ${formatNumber.format(result.eligible_quantity)} ${quantityLabel}${cappedText} = ${formatNumber.format(result.value)} 元`;
    }
    return `${name}：依你輸入的${policyStateFieldLabel(result.policy_state_key)} ${formatNumber.format(result.value)} 元呈現`;
  }
  if (result.state === "value_sharing_bonus") {
    const reserve = result.reference_amount || 0;
    const spread = result.rate_spread || 0;
    const formula = `${formatNumber.format(reserve)} 元 × (${formatNumber.format((result.declared_rate || 0) * 100)}% - ${formatNumber.format((result.scheduled_rate || 0) * 100)}%)`;
    return result.value
      ? `${name}：${formula} = ${formatNumber.format(result.value)} 元`
      : `${name}：${formula}，宣告利率未高於預定利率，本年度無給付`;
  }
  if (result.state === "value_added_account_credit") {
    if (result.formula_type === "qualification_lost") {
      return `${name}：依你選擇的保單狀態，目前已喪失加值給付資格，本期加值為 0 元`;
    }
    if (
      normalized.calculation_basis ===
      "installment_premium_value_addition"
    ) {
      const frequencyText =
        result.payment_frequency === "annual" ? "年繳" : "月繳";
      return `${name}：${frequencyText}，前期累積分期保險費平均值 ${formatNumber.format(result.previous_average_installment_premium || 0)} 元 × 本期適用給付率合計 ${formatNumber.format((result.applicable_rate_sum || 0) * 100)}% = ${formatNumber.format(result.value || 0)} 元；此金額投入新臺幣貨幣帳戶，入帳後不再與事故或滿期保障重複加總`;
    }
    const average = result.average_target_premium || 0;
    const rateSum = result.applicable_rate_sum || 0;
    return `${name}：累積所繳目標保險費平均值 ${formatNumber.format(average)} 元 × 本期新增繳費次數對應給付率合計 ${formatNumber.format(rateSum * 100)}% = ${formatNumber.format(result.value || 0)} 元；此金額依條款投入新臺幣貨幣帳戶，不另加到身故保障`;
  }
  if (result.state === "death_or_funeral_amount") {
    if (
      normalized.calculation_basis ===
      "paid_premium_factor_account_value_formula"
    ) {
      return paidPremiumFactorCoverageText(
        name,
        result,
        currencyLabel,
      );
    }
    if (result.formula_type === "face_amount_funeral_cap") {
      return `${name}：保險金額 ${formatNumber.format(result.gross_value_before_funeral_cap)} 元與本保單可用喪葬費用剩餘額度 ${formatNumber.format(result.funeral_benefit_limit)} 元取低者 = ${formatNumber.format(result.value)} 元`;
    }
    if (
      result.formula_type ===
        "face_amount_percentage_funeral_cap" ||
      result.formula_type ===
        "face_amount_percentage_standard_death"
    ) {
      const rateText = formatNumber.format(
        (result.applied_rate || 0) * 100,
      );
      const grossText = `保險金額 ${formatNumber.format(result.face_amount)} 元 × ${rateText}% = ${formatNumber.format(result.gross_value_before_funeral_cap)} 元`;
      const priorText = result.same_accident_prior_paid_amount
        ? `，再扣除同一事故先前已領失能／殘廢保險金 ${formatNumber.format(result.same_accident_prior_paid_amount)} 元`
        : "";
      const funeralText =
        result.formula_type ===
        "face_amount_percentage_funeral_cap"
          ? `，並受本保單可用喪葬費用剩餘額度 ${formatNumber.format(result.funeral_benefit_limit)} 元限制`
          : "";
      return `${name}：${grossText}${priorText}${funeralText} = ${formatNumber.format(result.value)} 元`;
    }
    if (
      result.formula_type ===
        "policy_state_percentage_funeral_cap" ||
      result.formula_type ===
        "policy_state_percentage_standard_death"
    ) {
      const baseLabel = policyStateFieldLabel(
        result.policy_state_key,
      );
      const rateText = formatNumber.format(
        (result.applied_rate || 0) * 100,
      );
      const paidText = result.cumulative_paid_amount
        ? `，再扣除累計手術醫療保險金 ${formatNumber.format(result.cumulative_paid_amount)} 元`
        : "";
      const funeralText =
        result.formula_type ===
        "policy_state_percentage_funeral_cap"
          ? `，並受本保單可用喪葬費用剩餘額度 ${formatNumber.format(result.funeral_benefit_limit)} 元限制`
          : "";
      return `${name}：${baseLabel} ${formatNumber.format(result.reference_amount)} 元 × ${rateText}%${paidText}${funeralText} = ${formatNumber.format(result.value)} 元`;
    }
    if (result.candidates?.length) {
      const candidates = result.candidates
        .map((candidate) => {
          const label = coverageFormulaCandidateLabel(candidate);
          if (candidate.base_value !== undefined && candidate.rate) {
            return `${label} ${formatNumber.format(candidate.value)} 元`;
          }
          return `${label} ${formatNumber.format(candidate.value)} 元`;
        })
        .join("；");
      const grossAmount =
        result.gross_value_before_funeral_cap ?? result.value;
      if (result.funeral_benefit_limit !== undefined) {
        return `${name}：條款保障毛額取較高值 ${formatNumber.format(grossAmount)} 元（${candidates}），再受本保單可用喪葬費用剩餘額度 ${formatNumber.format(result.funeral_benefit_limit)} 元限制，結果為 ${formatNumber.format(result.value)} 元`;
      }
      return `${name}：條款保障毛額取較高值 ${formatNumber.format(result.value)} 元（${candidates}）`;
    }
    return `${name}：依保險金額給付 ${formatNumber.format(result.value)} 元`;
  }
  if (
    normalized.calculation_basis ===
      "paid_premium_factor_account_value_formula" &&
    Number.isSafeInteger(result.value)
  ) {
    return paidPremiumFactorCoverageText(name, result, currencyLabel);
  }
  if (result.state === "greater_of") {
    if (result.formula_type === "funeral_cap_plus_account_value_return") {
      const accountValue = result.account_value_return || 0;
      const protectedAmount = result.protected_amount || 0;
      const funeralLimit = result.funeral_benefit_limit || 0;
      const cappedProtectedAmount =
        result.capped_protected_amount ?? Math.min(protectedAmount, funeralLimit);
      const offsetText = [
        ["保單借款及利息", result.policy_loan_and_interest_amount],
        ["其他未償費用", result.unpaid_policy_charge_amount],
        ["匯款相關費用", result.remittance_fee_amount],
      ]
        .filter(([, value]) => value)
        .map(([label, value]) => ` - ${label} ${formatNumber.format(value)} ${currencyLabel}`)
        .join("");
      return `${name}：保單帳戶價值返還 ${formatNumber.format(accountValue)} ${currencyLabel} + 非投資保障部分 ${formatNumber.format(protectedAmount)} ${currencyLabel}與本保單可用喪葬費用剩餘額度 ${formatNumber.format(funeralLimit)} ${currencyLabel}取低者 ${formatNumber.format(cappedProtectedAmount)} ${currencyLabel}${offsetText} = ${formatNumber.format(result.value)} ${currencyLabel}`;
    }
    const candidates = (result.candidates || [])
      .map((candidate) => {
        const label = coverageFormulaCandidateLabel(candidate);
        if (candidate.base_value && candidate.rate) {
          return `${label} ${formatNumber.format(candidate.base_value)} 元 × ${formatNumber.format(candidate.rate * 100)}% = ${formatNumber.format(candidate.value)} 元`;
        }
        return `${label} ${formatNumber.format(candidate.value)} 元`;
      })
      .join("；");
    const grossText =
      result.gross_value_before_offsets !== undefined
        ? `，毛額 ${formatNumber.format(result.gross_value_before_offsets)} ${currencyLabel}`
        : "";
    const offsetText = [
      ["保單借款及利息", result.policy_loan_and_interest_amount],
      ["其他未償費用", result.unpaid_policy_charge_amount],
      ["匯款相關費用", result.remittance_fee_amount],
    ]
      .filter(([, value]) => value)
      .map(([label, value]) => ` - ${label} ${formatNumber.format(value)} ${currencyLabel}`)
      .join("");
    return `${name}：取較高值${grossText || ` ${formatNumber.format(result.value)} ${currencyLabel}`}${candidates ? `（${candidates}）` : ""}${offsetText}${grossText ? ` = ${formatNumber.format(result.value)} ${currencyLabel}` : ""}`;
  }
  if (result.state === "premium_waiver_effect") {
    return `${name}：這不是可領現金；依你輸入的${policyStateFieldLabel(result.policy_state_key)} ${formatNumber.format(result.value)} 元，呈現為可免繳保費的保障效果`;
  }
  if (result.state === "aggregate_cap") {
    const scope = coverageModel.LIMIT_SCOPES[normalized.limit_scope] || coverageModel.LIMIT_SCOPES.unknown;
    return `${name}：${scope}總限額 ${formatNumber.format(result.value)} 元；這是累計上限，不是額外給付`;
  }
  if (result.state === "policy_state_daily_rate") {
    return `${name}：依你輸入的${policyStateFieldLabel(result.policy_state_key)}，每日 ${formatNumber.format(result.value)} 元`;
  }
  if (result.state === "policy_state_multiplier") {
    const baseLabel = result.policy_state_key
      ? policyStateFieldLabel(result.policy_state_key)
      : "基準額";
    const multiplierLabel = policyStateFieldLabel(
      result.multiplier_state_key,
    );
    return `${name}：${baseLabel} ${formatNumber.format(result.reference_amount)} 元 × ${multiplierLabel} ${result.multiplier} 倍 = ${formatNumber.format(result.value)} 元`;
  }
  if (result.state === "policy_state_rate_table") {
    const multiplierText = result.multiplier && result.multiplier !== 1 ? ` × ${result.multiplier}` : "";
    const baseText = `${policyStateFieldLabel(result.policy_state_key)}${multiplierText} = ${formatNumber.format(result.reference_amount)} 元`;
    return `${name}：${baseText}；${rateRange ? `再依條款比例 ${rateRange}` : "再依條款比例表"}計算`;
  }
  if (result.state === "policy_state_percentage") {
    const label = policyStateFieldLabel(result.policy_state_key);
    const multiplierText = result.multiplier && result.multiplier !== 1 ? ` × ${result.multiplier}` : "";
    return `${name}：依你輸入的${label}${multiplierText}，基準額 ${formatNumber.format(result.reference_amount)} 元 × ${formatNumber.format((normalized.rate || 0) * 100)}% = ${formatNumber.format(result.value)} 元`;
  }
  if (
    normalized.calculation_basis ===
      "net_amount_at_risk_plus_policy_account_value" &&
    Number.isFinite(result.value)
  ) {
    const faceText = `${result.face_amount_label || "基本保額"} ${formatNumber.format(result.face_amount)} ${currencyLabel}`;
    const accountText = `保單帳戶價值 ${formatNumber.format(result.account_value)} ${currencyLabel}`;
    const riskText = `淨危險保額 ${formatNumber.format(result.net_amount_at_risk)} ${currencyLabel}`;
    const deductionText = `保險金扣除額 ${formatNumber.format(result.insurance_deduction_amount || 0)} ${currencyLabel}`;
    const thresholdText = `帳戶價值 × ${formatNumber.format((result.threshold_factor || 0) * 100)}%`;
    const paidPremiumText = `累計已繳保費 ${formatNumber.format(result.paid_premium_total || 0)} ${currencyLabel}`;
    const withdrawalText = `累計已提領 ${formatNumber.format(result.partial_termination_amount_total || 0)} ${currencyLabel}`;
    let formulaText = `${result.policy_type}：${riskText}；再加${accountText}`;
    if (
      result.product_family ===
      "global-new-excellence-variable-universal-life"
    ) {
      const policyType = String(result.policy_type || "").replace("型", "");
      const rawAccountText = `事故時保單帳戶價值 ${formatNumber.format(result.raw_account_value || 0)} ${currencyLabel}`;
      const adjustedAccountText = `公式帳戶價值 ${formatNumber.format(result.adjusted_account_value || 0)} ${currencyLabel}`;
      if (result.semantic_phase === "premium_three_way_ab") {
        const premiumCandidateText = `${paidPremiumText} × 112% - ${withdrawalText}`;
        formulaText = policyType === "A"
          ? `A 型：${rawAccountText} × 110%、${faceText}、${premiumCandidateText}三者取高`
          : `B 型：${faceText} + ${rawAccountText}，與${premiumCandidateText}取高`;
      } else if (policyType === "A") {
        formulaText = `A 型：${faceText}與${thresholdText}取高`;
      } else if (policyType === "B") {
        formulaText = `B 型：${faceText}加${adjustedAccountText}，與${thresholdText}取高`;
      } else if (policyType === "C") {
        formulaText = `C 型：${faceText}與${adjustedAccountText}取高`;
      } else {
        formulaText = `D 型：${faceText}加${adjustedAccountText}`;
      }
      const refundText =
        result.delayed_notice_policy_fee_refund_rule ===
        "restore_account_value_then_recalculate"
          ? `；事故後應退保單費用 ${formatNumber.format(result.delayed_notice_policy_fee_refund_amount || 0)} ${currencyLabel}先併入帳戶價值重算`
          : `；公式結果另加事故後應退保單費用 ${formatNumber.format(result.delayed_notice_policy_fee_refund_amount || 0)} ${currencyLabel}`;
      const funeralText =
        result.formula_type?.includes("funeral_limited")
          ? `；喪葬費用保障部分以剩餘額度 ${formatNumber.format(result.funeral_benefit_limit || 0)} ${currencyLabel}為限，帳戶價值不計入上限`
          : "";
      const loanText = `；扣除保單借款及利息 ${formatNumber.format(result.policy_loan_and_interest_amount || 0)} ${currencyLabel}`;
      return `${name}：${formulaText}${refundText}${funeralText}${loanText} = ${formatNumber.format(result.value)} ${currencyLabel}`;
    } else if (
      result.product_family ===
      "allianz-worldview-foreign-currency-variable-universal-life"
    ) {
      const refundText = result.post_event_insurance_cost_refund_amount
        ? `；保單帳戶價值已加回事故後收取的保險成本 ${formatNumber.format(result.post_event_insurance_cost_refund_amount)} ${currencyLabel}`
        : "";
      const offsetText = [
        ["保單借款及利息", result.policy_loan_and_interest_amount],
        ["寬限期間欠繳的每月扣除額", result.unpaid_monthly_deduction_amount],
      ]
        .filter(([, value]) => value)
        .map(
          ([label, value]) =>
            ` - ${label} ${formatNumber.format(value)} ${currencyLabel}`,
        )
        .join("");
      if (result.formula_type === "minor_account_value_return") {
        return `${name}：事故時未滿 15 足歲，依條款返還保單帳戶價值 ${formatNumber.format(result.account_value)} ${currencyLabel}${offsetText} = ${formatNumber.format(result.value)} ${currencyLabel}${refundText}`;
      }
      const adjustedAccountText = `公式帳戶價值 ${formatNumber.format(result.adjusted_account_value)} ${currencyLabel}`;
      if (
        result.semantic_phase ===
        "legacy-annual-insurance-amount-abc"
      ) {
        if (result.policy_type === "甲型") {
          formulaText = `甲型：當年度保險金額 ${formatNumber.format(result.annual_insurance_amount)} ${currencyLabel}扣除${deductionText}，與${adjustedAccountText}取高`;
        } else if (result.policy_type === "乙型") {
          formulaText = `乙型：${faceText}加${adjustedAccountText}`;
        } else {
          formulaText = `丙型：${faceText}扣除${deductionText}，與${adjustedAccountText}取高`;
        }
      } else if (result.policy_type === "A型") {
        formulaText = `A 型：${faceText}扣除${deductionText}，與${thresholdText}取高`;
      } else if (result.policy_type === "B型") {
        formulaText = `B 型：${faceText}加${adjustedAccountText}，與${thresholdText}取高`;
      } else if (result.policy_type === "C型") {
        formulaText = `C 型：${faceText}加${adjustedAccountText}`;
      } else {
        formulaText = `D 型：${faceText}扣除${deductionText}，與${adjustedAccountText}取高`;
      }
      return `${name}：${formulaText}${offsetText} = ${formatNumber.format(result.value)} ${currencyLabel}${refundText}`;
    } else if (
      result.product_family ===
      "global-excellence-variable-universal-life"
    ) {
      if (
        result.minimum_rate_formula_variant === "fixed_110_percent" &&
        result.policy_type.includes("A")
      ) {
        formulaText = `A 型：${faceText}與${accountText} × 110% 取高者`;
      } else if (
        result.minimum_rate_formula_variant === "fixed_110_percent"
      ) {
        formulaText = `B 型：${faceText}加${accountText}`;
      } else if (result.policy_type.includes("A")) {
        formulaText = `A 型：${faceText}與${thresholdText}取高者`;
      } else {
        formulaText = `B 型：${faceText}加${accountText}，與${thresholdText}取高者`;
      }
    } else if (result.formula_type === "甲") {
      formulaText = `甲型：${faceText}扣除${deductionText}及${accountText}，最低為 0，得${riskText}；再加${accountText}`;
    } else if (result.formula_type === "乙") {
      formulaText = `乙型：${riskText}等於${faceText}；再加${accountText}`;
    } else if (result.formula_type === "丙") {
      formulaText = `丙型：${faceText}扣除${deductionText}及${accountText}，與${thresholdText}取高者，得${riskText}；再加${accountText}`;
    } else if (result.formula_type === "丁") {
      formulaText = `丁型：${faceText}與${thresholdText}取高者，得${riskText}；再加${accountText}`;
    } else if (result.formula_type === "戊") {
      formulaText = `戊型：${faceText}扣除${deductionText}及${accountText}、${paidPremiumText}扣除${withdrawalText}及${accountText}、${thresholdText}三者取高，得${riskText}；再加${accountText}`;
    }
    return `${name}：${formulaText} = ${formatNumber.format(result.value)} ${currencyLabel}`;
  }
  if (
    [
      "policy_value_plus_general_insurance_amount",
      "policy_value_plus_general_and_accidental_insurance_amount",
    ].includes(normalized.calculation_basis) &&
    result.value
  ) {
    const parts = [
      `事故時保單價值部分 ${formatNumber.format(result.policy_value_component)} 元`,
      `一般身故／完全殘廢保險金額 ${formatNumber.format(result.general_insurance_amount)} 元`,
    ];
    if (result.accidental_insurance_amount) {
      parts.push(
        `意外傷害身故／完全殘廢保險金額 ${formatNumber.format(result.accidental_insurance_amount)} 元`,
      );
    }
    return `${name}：在契約有效、請求權與事故認定等條款條件成立時，${parts.join(" + ")} = ${formatNumber.format(result.value)} 元；這是保障試算，不代表個案一定理賠`;
  }
  if (normalized.calculation_basis === "annuity_face_amount_schedule" && result.value) {
    const frequencyRate = formatNumber.format((result.annuity_frequency_rate || 0) * 100);
    const patternText = result.annuity_payment_pattern === "increasing"
      ? `第 ${formatNumber.format(result.annuity_payment_year || 1)} 年，3% 單利增額係數 ${formatNumber.format(result.annuity_growth_multiplier || 1)}`
      : "平準給付";
    return `${name}：年金投保金額 ${formatNumber.format(result.reference_amount)} 元 × 領取頻率換算係數 ${frequencyRate}% × ${patternText} = 試算每期 ${formatNumber.format(result.value)} 元；元以下處理與實際給付以保單或保險公司列示為準`;
  }
  if (
    normalized.calculation_basis ===
      "single_premium_minus_paid_annuity_total" &&
    result.state === "calculated_annuity_balance"
  ) {
    const settlementText = normalized.result_kind === "payment_method"
      ? "此為身故後按原頻率續領的剩餘總額，不是身故當下一次給付"
      : "此版本於被保險人身故後一次給付餘額";
    return `${name}：躉繳保險費 ${formatNumber.format(result.single_premium_amount)} 元 - 累計實際已領年金 ${formatNumber.format(result.paid_annuity_total)} 元 = ${formatNumber.format(result.value)} 元；${settlementText}`;
  }
  if (
    normalized.calculation_basis ===
      "reserve_minus_policy_loan_and_interest" &&
    result.formula_type === "reserve_minus_policy_loan_and_interest"
  ) {
    return `${name}：保單價值準備金 ${formatNumber.format(result.policy_reserve_value)} 元 - 保單借款及應付利息 ${formatNumber.format(result.policy_loan_and_interest_amount)} 元 = ${formatNumber.format(result.value)} 元`;
  }
  if (!amount && !normalizeCoverageAmount(selection.face_amount, selection) && !result.value && !result.reference_amount) {
    return normalized.note ? `${name}：${normalized.note}` : `${name}：待補條款金額`;
  }
  if (normalized.calculation_basis === "per_unit") {
    if (
      normalized.quantity_state_key &&
      Number.isSafeInteger(result.value)
    ) {
      const rateText =
        result.applied_rate !== undefined &&
        result.applied_rate !== 1
          ? ` × ${formatNumber.format(result.applied_rate * 100)}%`
          : "";
      const paidText =
        result.cumulative_paid_amount !== null &&
        result.cumulative_paid_amount !== undefined
          ? ` - 本次事故前已領 ${formatNumber.format(result.cumulative_paid_amount)} 元`
          : "";
      return `${name}：每單位 ${formattedAmount} × ${formatNumber.format(units)} 單位 × ${formatNumber.format(result.quantity)} ${policyStateFieldLabel(normalized.quantity_state_key)}${rateText}${paidText} = ${formatNumber.format(result.value)} 元`;
    }
    return Number.isSafeInteger(result.value)
      ? `${name}：每單位 ${formattedAmount} × ${formatNumber.format(units)} 單位 = ${formatNumber.format(result.value)} 元`
      : `${name}：每單位 ${formattedAmount}；請補上單位數`;
  }
  if (normalized.calculation_basis === "per_unit_per_day") {
    if (normalized.quantity_state_key && Number.isSafeInteger(result.value)) {
      return `${name}：每單位／每日 ${formattedAmount} × ${formatNumber.format(units)} 單位 × ${formatNumber.format(result.quantity)} ${policyStateFieldLabel(normalized.quantity_state_key)} = ${formatNumber.format(result.value)} 元`;
    }
    return Number.isSafeInteger(result.value)
      ? `${name}：每單位／每日 ${formattedAmount} × ${formatNumber.format(units)} 單位 = 每日 ${formatNumber.format(result.value)} 元`
      : `${name}：每單位／每日 ${formattedAmount}；請補上單位數`;
  }
  if (normalized.calculation_basis === "percentage_of_base") {
    const base = result.reference_amount || normalizeCoverageAmount(selection.face_amount, selection);
    const unitBased = ["per_unit", "daily_per_unit"].includes(normalized.basis);
    if (result.state === "needs_unit_count") {
      return `${name}：每單位基準額 ${formattedAmount}；請補上單位數後依條款比例表計算`;
    }
    const appliedRate = result.applied_rate || normalized.rate;
    if (Number.isSafeInteger(result.value) && appliedRate) {
      return `${name}：${unitBased && units ? `${formatNumber.format(units)} 單位，` : ""}基準額 ${formatNumber.format(base)} 元 × ${formatNumber.format(appliedRate * 100)}% = ${formatNumber.format(result.value)} 元`;
    }
    return `${name}：${unitBased && units ? `${formatNumber.format(units)} 單位，` : ""}基準額 ${formatNumber.format(base)} 元；${rateRange ? `依條款比例 ${rateRange}` : "依條款比例表計算"}`;
  }
  if (normalized.calculation_basis === "table_multiplier") {
    const base = result.reference_amount || amount;
    const multiplier =
      result.applied_multiplier ||
      result.multiplier ||
      normalized.multiplier;
    return result.value
      ? `${name}：基準額 ${formatNumber.format(base)} 元 × ${multiplier} 倍 = ${formatNumber.format(result.value)} 元`
      : `${name}：基準額 ${formatNumber.format(base)} 元；依條款倍數表計算`;
  }
  if (normalized.calculation_basis === "reimbursement_with_cap") {
    const scope = coverageModel.LIMIT_SCOPES[normalized.limit_scope] || coverageModel.LIMIT_SCOPES.unknown;
    const unitBased = ["per_unit", "daily_per_unit"].includes(normalized.basis);
    if (result.state === "needs_unit_count") {
      return `${name}：每單位 ${scope}最高 ${formattedAmount}；請補上單位數`;
    }
    if (normalized.amount_tiers.length) {
      const caps = normalized.amount_tiers
        .map((tier) => `${tier.label} ${scope}最高 ${formatNumber.format(tier.amount)} 元`)
        .join("；");
      return `${name}：${caps}；實際給付依支出與條款`;
    }
    if (normalized.expense_state_key && Number.isSafeInteger(result.value)) {
      const rateText =
        result.applied_rate && result.applied_rate !== 1
          ? ` × ${formatNumber.format(result.applied_rate * 100)}%`
          : "";
      const annualText =
        result.remaining_aggregate_limit === null ||
        result.remaining_aggregate_limit === undefined
          ? ""
          : `，再受本年度剩餘限額 ${formatNumber.format(result.remaining_aggregate_limit)} 元限制`;
      return `${name}：實際費用 ${formatNumber.format(result.expense_amount)} 元${rateText}，與${scope}限額 ${formatNumber.format(result.reference_amount)} 元取低${annualText} = ${formatNumber.format(result.value)} 元`;
    }
    const limit = result.value || amount;
    const statePrefix = result.state === "policy_state_limit"
      ? `依你輸入的${policyStateFieldLabel(result.policy_state_key)}，`
      : "";
    return `${name}：${statePrefix}${unitBased && units ? `${formatNumber.format(units)} 單位，` : ""}${scope}最高 ${formatNumber.format(limit)} 元；實際給付依支出與條款`;
  }
  if (normalized.calculation_basis === "percentage_of_actual_expense_with_cap") {
    const scope = coverageModel.LIMIT_SCOPES[normalized.limit_scope] || coverageModel.LIMIT_SCOPES.unknown;
    const limit = result.value || amount || normalizeCoverageAmount(selection.face_amount, selection);
    const rateText = normalized.rate ? `${formatNumber.format(normalized.rate * 100)}%` : "條款比例";
    const statePrefix = result.state === "policy_state_limit"
      ? `依你輸入的${policyStateFieldLabel(result.policy_state_key)}，`
      : "";
    if (normalized.expense_state_key && Number.isSafeInteger(result.value)) {
      const annualText =
        result.remaining_aggregate_limit === null ||
        result.remaining_aggregate_limit === undefined
          ? ""
          : `，再受本年度剩餘限額 ${formatNumber.format(result.remaining_aggregate_limit)} 元限制`;
      return `${name}：實際費用 ${formatNumber.format(result.expense_amount)} 元 × ${formatNumber.format((result.applied_rate || 0) * 100)}%，與${scope}限額 ${formatNumber.format(result.reference_amount)} 元取低${annualText} = ${formatNumber.format(result.value)} 元`;
    }
    return `${name}：${statePrefix}實際支出 ${rateText}，${scope}最高 ${formatNumber.format(limit)} 元；實際給付依支出與條款`;
  }
  if (normalized.calculation_basis === "per_day") {
    return normalized.quantity_state_key && Number.isSafeInteger(result.value)
      ? `${name}：每日 ${formattedAmount} × ${formatNumber.format(result.quantity)} 日 = ${formatNumber.format(result.value)} 元`
      : `${name}：每日 ${formattedAmount}`;
  }
  if (
    normalized.calculation_basis === "fixed_amount" &&
    normalized.quantity_state_key &&
    Number.isSafeInteger(result.value)
  ) {
    return `${name}：每次 ${formattedAmount} × ${formatNumber.format(result.quantity)} 次 = ${formatNumber.format(result.value)} 元`;
  }
  if (normalized.calculation_basis === "additional_benefit") return `${name}：額外給付 ${formattedAmount}`;
  if (normalized.calculation_basis === "tiered_or_stepped") {
    if (
      result.selected_tier &&
      Number.isSafeInteger(result.value)
    ) {
      const rateText =
        result.applied_rate !== undefined &&
        result.applied_rate !== 1
          ? ` × ${formatNumber.format(result.applied_rate * 100)}%`
          : "";
      const paidText =
        result.cumulative_paid_amount !== null &&
        result.cumulative_paid_amount !== undefined
          ? ` - 本次事故前已領 ${formatNumber.format(result.cumulative_paid_amount)} 元`
          : "";
      if (
        normalized.basis === "face_amount" &&
        result.selected_tier.multiplier &&
        Number.isSafeInteger(result.reference_amount)
      ) {
        return `${name}：${policyStateFieldLabel(result.tier_selection_state_key)} ${formatNumber.format(result.tier_selection_value)}，適用「${result.selected_tier.label}」保險金額 ${formatNumber.format(result.reference_amount)} 元 × ${formatNumber.format(result.selected_tier.multiplier * 100)}%${rateText}${paidText} = ${formatNumber.format(result.value)} 元`;
      }
      return `${name}：${policyStateFieldLabel(result.tier_selection_state_key)} ${formatNumber.format(result.tier_selection_value)}，適用「${result.selected_tier.label}」每單位 ${formatNumber.format(result.selected_tier.amount)} 元 × ${formatNumber.format(units)} 單位${rateText}${paidText} = ${formatNumber.format(result.value)} 元`;
    }
    if (result.tier_values?.length) {
      const tiers = result.tier_values
        .map((tier) =>
          Number.isSafeInteger(tier.value)
            ? `${tier.label}${Number.isSafeInteger(tier.quantity) ? `共 ${formatNumber.format(tier.quantity)} 日` : ""} ${formatNumber.format(tier.value)} 元`
            : `${tier.label}每單位 ${formatNumber.format(tier.reference_amount)} 元`,
        )
        .join("；");
      const total =
        result.state === "calculated" && Number.isSafeInteger(result.value)
          ? `；合計 ${formatNumber.format(result.value)} 元`
          : "";
      return `${name}：${units ? `${formatNumber.format(units)} 單位，` : ""}${tiers}${total}${units ? "" : "；請補上單位數"}`;
    }
    return `${name}：${formattedAmount}；依條款級距或階梯表計算`;
  }
  if (normalized.calculation_basis === "unknown" && normalized.note) return `${name}：${normalized.note}`;
  if (normalized.calculation_basis === "unknown") return `${name}：${formattedAmount}；計算方式尚待條款整理`;
  const role = coverageModel.AMOUNT_ROLES[normalized.amount_role] || coverageModel.AMOUNT_ROLES.unknown;
  return `${name}：${role} ${formattedAmount}`;
}

function coverageEntryValueText(entry, selectedValues) {
  const text = coverageEntryText(entry, selectedValues);
  const separator = text.indexOf("：");
  return separator >= 0 ? text.slice(separator + 1) : text;
}

function positiveIntegerInputValue(input, label = "單位數", max = 9999, allowBlank = false) {
  const rawValue = String(input?.value || "").trim();
  if (allowBlank && !rawValue) {
    input?.setCustomValidity("");
    return null;
  }
  const value = Number(rawValue);
  const valid = /^[1-9]\d*$/.test(rawValue) && value <= max;
  input?.setCustomValidity(valid ? "" : `${label}請輸入 1 到 ${formatNumber.format(max)} 的正整數`);
  if (!valid) input?.reportValidity();
  return valid ? value : null;
}

function moneyInputValue(
  input,
  item,
  label,
  allowBlank = false,
  allowZero = false,
) {
  const rawValue = String(input?.value || "").trim();
  if (allowBlank && !rawValue) {
    input?.setCustomValidity("");
    return null;
  }
  const decimalPlaces = coverageModel.moneyDecimalPlaces(item);
  if (!decimalPlaces) {
    return positiveIntegerInputValue(
      input,
      label,
      coverageModel.MAX_MONEY_AMOUNT,
      allowBlank,
    );
  }
  const value = coverageModel.normalizeDecimalMoneyAmount(
    rawValue,
    decimalPlaces,
    allowZero,
  );
  const valid = value !== null;
  input?.setCustomValidity(
    valid
      ? ""
      : `${label}請輸入${allowZero ? "不小於" : "大於"} 0、最多 ${decimalPlaces} 位小數的金額`,
  );
  if (!valid) input?.reportValidity();
  return valid ? value : null;
}

function portfolioSelectionFieldsHtml(item) {
  const requirements = coverageModel.selectionRequirements(item);
  const planOptions = requirements.plan_options;
  const mode = requirements.mode;
  const selectedPlan = String(item?.plan_name || "").trim();
  const currencyLabel = itemCurrencyLabel(item);
  const moneyDecimalPlaces = coverageModel.moneyDecimalPlaces(item);
  const moneyStep = moneyDecimalPlaces
    ? `0.${"0".repeat(moneyDecimalPlaces - 1)}1`
    : "1";
  const moneyInputMode = moneyDecimalPlaces ? "decimal" : "numeric";
  const planControl = planOptions.length
    ? `<select data-selection-plan>
        <option value="">請選擇計畫／方案</option>
        ${planOptions
          .map(
            (option) =>
              `<option value="${escapeHtml(option.value)}" ${option.value === selectedPlan || option.label === selectedPlan ? "selected" : ""}>${escapeHtml(option.label)}</option>`,
          )
          .join("")}
      </select>`
    : `<input type="text" maxlength="60" value="${escapeHtml(selectedPlan)}" placeholder="例如：計畫 B" data-selection-plan>`;
  const defaultGuidance = {
    face_amount: "依這個版本的條款，請填保單首頁記載的契約保險金額。",
    face_amount_plan: "依這個版本的條款，請填保單首頁記載的基本保額，並選擇保險型態。",
    account_value: "依這個版本的條款，請填保單帳戶價值；投資型壽險或年金常需要用這個金額呈現返還或換算結果。",
    paid_premium_factor_plan: "請選擇保險型態，並在下方輸入條款公式需要的已繳保費、部分終止金額、指定百分比或倍數與保單帳戶價值。",
    plan: "依這個版本的條款選擇計畫；保障項目與金額會自動帶入。",
    unit: "依這個版本的條款填投保單位數；只能輸入正整數。",
    multi_unit: "這個商品有兩組以上的投保單位，請依保單首頁分別填寫。",
    plan_unit: "這個商品的條款同時使用計畫與單位，兩項都需填寫。",
    policy_state: "這個商品需依保單當時狀態計算，請填下方條款要求的保單欄位。",
    fixed: "條款已整理為固定給付，不需輸入保額、計畫或單位。",
    unknown: "金額輸入方式尚未從條款確認；可以先加入集合，系統不會推估金額。",
  }[mode];
  const guidance = requirements.guidance || defaultGuidance;
  const unitFields = requirements.unit_fields
    .map(
      (field) => `
        <label data-selection-field="unit_counts">
          <span>${escapeHtml(field.label)}</span>
          <input type="number" min="1" max="9999" step="1" inputmode="numeric" value="${escapeHtml(normalizeUnitCount(item?.unit_counts?.[field.key]) || "")}" placeholder="請輸入正整數" data-selection-unit-key="${escapeHtml(field.key)}">
        </label>`,
    )
    .join("");

  return `
    <div class="portfolio-selection-fields" data-selection-fields>
      <div class="selection-guidance ${mode === "unknown" ? "pending" : ""}">
        <strong>${escapeHtml(requirements.label)}</strong>
        <span>${escapeHtml(guidance)}</span>
      </div>
      <input type="hidden" value="${escapeHtml(mode)}" data-selection-mode>
      <label data-selection-field="face_amount" ${requirements.fields.includes("face_amount") ? "" : "hidden"}>
        <span>${escapeHtml(requirements.face_amount_label)}</span>
        <div class="money-input">
          <input type="number" min="${moneyStep}" max="${coverageModel.MAX_MONEY_AMOUNT}" step="${moneyStep}" inputmode="${moneyInputMode}" value="${escapeHtml(normalizeCoverageAmount(item?.face_amount, item) || "")}" placeholder="請輸入保單記載金額" data-selection-face-amount>
          <span>${escapeHtml(currencyLabel)}</span>
        </div>
      </label>
      <label data-selection-field="account_value" ${requirements.fields.includes("account_value") ? "" : "hidden"}>
        <span>${escapeHtml(mode === "account_value" ? requirements.label : "保單帳戶價值")}</span>
        <div class="money-input">
          <input type="number" min="${moneyStep}" max="${coverageModel.MAX_MONEY_AMOUNT}" step="${moneyStep}" inputmode="${moneyInputMode}" value="${escapeHtml(normalizeCoverageAmount(item?.account_value || item?.policy_state?.policy_account_value, item) || "")}" placeholder="請輸入保單帳戶價值" data-selection-account-value>
          <span>${escapeHtml(currencyLabel)}</span>
        </div>
      </label>
      <label data-selection-field="unit" ${requirements.fields.includes("unit_count") ? "" : "hidden"}>
        <span>單位數</span>
        <input type="number" min="1" max="9999" step="1" inputmode="numeric" value="${escapeHtml(normalizeUnitCount(item?.unit_count) || "")}" placeholder="請輸入正整數" data-selection-unit>
      </label>
      ${requirements.fields.includes("unit_counts") ? unitFields : ""}
      <label data-selection-field="plan" ${requirements.fields.includes("plan_name") ? "" : "hidden"}>
        <span>${escapeHtml(["face_amount_plan", "paid_premium_factor_plan"].includes(mode) ? "保險型態" : "計畫別")}</span>
        ${planControl}
      </label>
      ${policyStateFieldsHtml(item)}
    </div>
  `;
}

function readPortfolioSelection(container, item) {
  const requirements = coverageModel.selectionRequirements(item);
  const mode = container.querySelector("[data-selection-mode]")?.value || requirements.mode;
  const selection = {
    selection_mode: mode,
    selection_type: mode,
    face_amount: null,
    account_value: null,
    unit_count: null,
    unit_counts: {},
    plan_name: "",
    policy_state: normalizePolicyStateForItem(container, item),
  };
  if (selection.policy_state === null) return null;
  if (requirements.fields.includes("plan_name")) {
    const planInput = container.querySelector("[data-selection-plan]");
    const planName = String(planInput?.value || "").trim();
    planInput?.setCustomValidity(planName ? "" : "請選擇或輸入計畫別");
    if (!planName) {
      planInput?.reportValidity();
      return null;
    }
    selection.plan_name = planName;
  }
  if (requirements.fields.includes("unit_count")) {
    const unitInput = container.querySelector("[data-selection-unit]");
    const unitCount = positiveIntegerInputValue(unitInput);
    if (unitCount === null) return null;
    selection.unit_count = unitCount;
  }
  if (requirements.fields.includes("unit_counts")) {
    for (const field of requirements.unit_fields) {
      const unitInput = container.querySelector(`[data-selection-unit-key="${CSS.escape(field.key)}"]`);
      const unitCount = positiveIntegerInputValue(unitInput, field.label);
      if (unitCount === null) return null;
      selection.unit_counts[field.key] = unitCount;
    }
  }
  if (requirements.fields.includes("face_amount")) {
    const amountInput = container.querySelector("[data-selection-face-amount]");
    const faceAmount = moneyInputValue(
      amountInput,
      item,
      requirements.label,
    );
    if (faceAmount === null) return null;
    selection.face_amount = faceAmount;
  }
  if (requirements.fields.includes("account_value")) {
    const amountInput = container.querySelector("[data-selection-account-value]");
    const accountValue = moneyInputValue(
      amountInput,
      item,
      requirements.label,
    );
    if (accountValue === null) return null;
    selection.account_value = accountValue;
    selection.policy_state = {
      ...selection.policy_state,
      policy_account_value: accountValue,
    };
  }
  return selection;
}

function syncPortfolioSelectionFields(container) {
  if (!container) return;
  const mode = container.querySelector("[data-selection-mode]")?.value || "unknown";
  const requiredFields = coverageModel.SELECTION_MODES[mode]?.fields || [];
  container.querySelectorAll("[data-selection-field]").forEach((field) => {
    const fieldKey = field.dataset.selectionField === "plan" ? "plan_name" : field.dataset.selectionField === "unit" ? "unit_count" : field.dataset.selectionField;
    field.hidden = !requiredFields.includes(fieldKey);
  });
}

function portfolioSelectionText(item) {
  const mode = portfolioSelectionMode(item);
  if (mode === "face_amount") return faceAmountText(item);
  if (mode === "account_value") return accountValueText(item);
  if (mode === "paid_premium_factor_plan") return planText(item?.plan_name, item) || "尚未選擇保險型態";
  if (mode === "plan") return planText(item?.plan_name, item) || "尚未選擇計畫";
  if (mode === "unit") return unitText(item?.unit_count);
  if (mode === "multi_unit") {
    const fields = coverageModel.selectionRequirements(item).unit_fields;
    return fields
      .map((field) => `${field.label} ${normalizeUnitCount(item?.unit_counts?.[field.key]) || "未填"} 單位`)
      .join("、");
  }
  if (mode === "plan_unit") {
    return [planText(item?.plan_name, item) || "尚未選擇計畫", unitText(item?.unit_count)].join("、");
  }
  if (mode === "policy_state") return "依保單狀態計算";
  if (mode === "fixed") return "條款固定給付";
  return "待補條款金額";
}

function clampPage(page, totalPages) {
  return Math.min(Math.max(Number(page) || 1, 1), Math.max(totalPages, 1));
}

function paginationRange(totalCount, page, pageSize) {
  if (!totalCount) return { start: 0, end: 0 };
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalCount);
  return { start, end };
}

function paginationHtml(scope, totalCount, page, pageSize, pageSizeOptions) {
  const totalPages = Math.max(Math.ceil(totalCount / pageSize), 1);
  const currentPage = clampPage(page, totalPages);
  const range = paginationRange(totalCount, currentPage, pageSize);
  const pageOptions = Array.from({ length: totalPages }, (_, index) => index + 1)
    .map((pageNumber) => `<option value="${pageNumber}" ${pageNumber === currentPage ? "selected" : ""}>第 ${formatNumber.format(pageNumber)} 頁</option>`)
    .join("");
  const sizeOptions = pageSizeOptions
    .map((size) => `<option value="${size}" ${size === pageSize ? "selected" : ""}>每頁 ${formatNumber.format(size)} 筆</option>`)
    .join("");

  return `
    <div class="pagination-row" data-pagination="${escapeHtml(scope)}">
      <p>第 ${formatNumber.format(currentPage)} / ${formatNumber.format(totalPages)} 頁，顯示 ${formatNumber.format(range.start)}-${formatNumber.format(range.end)} / ${formatNumber.format(totalCount)} 筆</p>
      <div class="pagination-controls">
        <button class="button ghost compact" type="button" data-page-action="${escapeHtml(scope)}" data-page-target="${currentPage - 1}" ${currentPage <= 1 ? "disabled" : ""}>上一頁</button>
        <label>
          <span>頁碼</span>
          <select data-page-select="${escapeHtml(scope)}">${pageOptions}</select>
        </label>
        <label>
          <span>每頁筆數</span>
          <select data-page-size="${escapeHtml(scope)}">${sizeOptions}</select>
        </label>
        <button class="button ghost compact" type="button" data-page-action="${escapeHtml(scope)}" data-page-target="${currentPage + 1}" ${currentPage >= totalPages ? "disabled" : ""}>下一頁</button>
      </div>
    </div>
  `;
}

function kindLabel(kind) {
  const labels = {
    pdf_or_file: "PDF/檔案",
    product_page: "商品頁",
    web_page: "網頁",
    law_source: "法規/公會",
    social_insurance: "社會保險",
    local_file: "本機檔案",
    private_document: "私有文件",
    unsupported: "不支援",
  };
  return labels[kind] || kind;
}

function crawlLabel(result) {
  if (!result) {
    return {
      label: "尚未檢查",
      className: "unchecked",
      note: "等待下一批來源檢查。",
    };
  }
  if (result.robots_allowed === false) {
    return {
      label: "網站限制",
      className: "blocked",
      note: "站方規則不允許自動抓取，請手動回官方頁複核。",
    };
  }
  if (result.ok) {
    return {
      label: "可開啟",
      className: "ok",
      note: "已確認來源可連線；內容仍以官方頁面為準。",
    };
  }
  return {
    label: "需人工確認",
    className: "error",
    note: "連線或格式異常，建議人工複核。",
  };
}

function kindPurpose(kind) {
  const labels = {
    pdf_or_file: "適合回查條款、費率表、要保文件或官方附件。",
    product_page: "適合先看商品介紹，再回官方文件確認細節。",
    web_page: "適合查找保險公司或公開頁面的原始說明。",
    law_source: "適合確認主管機關、法規或公會公開資料。",
    social_insurance: "適合查找社會保險制度與官方說明。",
    local_file: "來自使用者提供文件，目前不列入公開抓取。",
    private_document: "私有文件來源，目前不列入公開抓取。",
    unsupported: "此來源類型目前只保留索引，不做自動抓取。",
  };
  return labels[kind] || "可作為回到原始來源的入口。";
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function renderSiteSummary(summary) {
  const tii = summary?.tii || {};
  const latest = tii.latest_completed_batch || {};
  const waiting = tii.current_waiting_batch || {};
  const detailSaved = tii.detail_saved_count || 0;
  const detailExpected = tii.detail_expected_count || 0;
  const latestTitle = [latest.batch_id, latest.company_label, latest.category_label].filter(Boolean).join(" / ");
  const waitingTitle = [waiting.batch_id, waiting.company_label, waiting.category_label].filter(Boolean).join(" / ");

  setText("publicMetricImported", formatNumber.format(tii.imported_policy_records || 0));
  setText("publicMetricDetails", `${formatNumber.format(detailSaved)} / ${formatNumber.format(detailExpected)}`);
  setText(
    "publicMetricBatches",
    `${formatNumber.format(tii.completed_batches || 0)} / ${formatNumber.format(tii.total_manual_batches || 0)}`,
  );
  setText("publicMetricWaiting", formatNumber.format(tii.waiting_captcha_batches || 0));
  setText(
    "publicSummaryNote",
    `最新完成 ${latestTitle || "待匯入"}：${formatNumber.format(
      latest.imported_record_count || 0,
    )} 張卡，明細 ${formatNumber.format(latest.detail_saved_count || 0)} / ${formatNumber.format(
      latest.detail_expected_count || 0,
    )}。下一批 ${waitingTitle || "尚未準備"}。同名不同版本會保留為不同卡片。`,
  );
}

async function loadSiteSummary() {
  try {
    const response = await fetch("./data/site-summary.json");
    if (!response.ok) throw new Error("site-summary not available");
    state.siteSummary = await response.json();
    renderSiteSummary(state.siteSummary);
  } catch {
    setText("publicSummaryNote", "公開摘要暫時無法載入；下方完整資料載入後仍可查詢。");
  }
}

async function fetchJsonOrFallback(path, fallback) {
  const response = await fetch(path);
  return response.ok ? response.json() : fallback;
}

async function loadData() {
  const [
    sourceIndex,
    taxonomy,
    crawlStatus,
    policyInsights,
    tiiMetadata,
    tiiResults,
    tiiManifest,
    tiiExecutionProgress,
    batchPlan,
    batchProgress,
    policyContentExtracts,
  ] = await Promise.all([
    fetch("./data/source-index.json").then((response) => response.json()),
    fetch("./data/consumer-taxonomy.json").then((response) => response.json()),
    fetch("./data/crawl-status.json").then((response) => response.json()),
    fetch("./data/policy-insights.json").then((response) => response.json()),
    fetch("./data/tii-query-metadata.json").then((response) => response.json()),
    fetchJsonOrFallback("./data/tii-policy-results.json", { record_count: 0, records: [], completed_batches: [] }),
    fetchJsonOrFallback("./data/tii/manifest.json", { record_count: 0, index_shards: [], record_shards: [] }),
    fetchJsonOrFallback(
      "./data/tii-execution-progress.json",
      { summary: { attempted_batches: 0, completed_batches: 0, captcha_required_batches: 0 }, runs: [] },
    ),
    fetch("./data/batch-plan.json").then((response) => response.json()),
    fetch("./data/batch-progress.json").then((response) => (response.ok ? response.json() : null)),
    fetch("./data/policy-content-extracts.json").then((response) => (response.ok ? response.json() : null)),
  ]);
  state.sourceIndex = sourceIndex;
  state.taxonomy = taxonomy;
  state.crawlStatus = crawlStatus;
  state.policyInsights = policyInsights;
  state.tiiMetadata = tiiMetadata;
  state.tiiResults = tiiResults;
  state.tiiManifest = tiiManifest;
  state.tiiExecutionProgress = tiiExecutionProgress;
  state.batchPlan = batchPlan;
  state.batchProgress = batchProgress;
  state.policyContentExtracts = policyContentExtracts;
  state.crawlByUrlId = new Map(crawlStatus.results.map((item) => [item.url_id, item]));
}

function populateFilters() {
  const companyFilter = document.getElementById("companyFilter");
  const kindFilter = document.getElementById("kindFilter");

  const policyRecords = state.policyContentExtracts?.records || [];
  const tiiCompanies = (state.tiiManifest?.company_counts || []).map((item) => item.company).filter(Boolean);
  const tiiCategories = (state.tiiManifest?.category_counts || []).map((item) => item.category).filter(Boolean);
  const companies = [...new Set([...policyRecords.map((item) => item.company).filter(Boolean), ...tiiCompanies])].sort(
    (a, b) => a.localeCompare(b, "zh-Hant-TW"),
  );
  const kinds = [
    ...new Set([...policyRecords.map((item) => item.product_type || "其他"), ...tiiCategories]),
  ].sort((a, b) => a.localeCompare(b, "zh-Hant-TW"));

  companyFilter.innerHTML = [
    '<option value="all">全部公司</option>',
    ...companies.map((company) => `<option value="${escapeHtml(company)}">${escapeHtml(company)}</option>`),
  ].join("");

  kindFilter.innerHTML = [
    '<option value="all">全部類型</option>',
    ...kinds.map((kind) => `<option value="${escapeHtml(kind)}">${escapeHtml(kind)}</option>`),
  ].join("");
}

function hasOption(selectId, value) {
  return [...document.getElementById(selectId).options].some((option) => option.value === value);
}

function loadFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const company = params.get("company") || DEFAULT_FILTERS.company;
  const kind = params.get("kind") || DEFAULT_FILTERS.kind;
  const crawl = params.get("status") || DEFAULT_FILTERS.crawl;

  state.search = params.get("q") || DEFAULT_FILTERS.search;
  state.company = hasOption("companyFilter", company) ? company : DEFAULT_FILTERS.company;
  state.kind = hasOption("kindFilter", kind) ? kind : DEFAULT_FILTERS.kind;
  state.crawl = policyFocusLabels[crawl] ? crawl : DEFAULT_FILTERS.crawl;
  state.openSourceId = params.get("open");
}

function syncControls() {
  document.getElementById("searchInput").value = state.search;
  document.getElementById("companyFilter").value = state.company;
  document.getElementById("kindFilter").value = state.kind;
  document.getElementById("crawlFilter").value = state.crawl;

  document.querySelectorAll(".status-chip").forEach((button) => {
    const isActive = button.dataset.crawl === state.crawl;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function updateUrl() {
  const params = new URLSearchParams();
  if (state.search) params.set("q", state.search);
  if (state.company !== DEFAULT_FILTERS.company) params.set("company", state.company);
  if (state.kind !== DEFAULT_FILTERS.kind) params.set("kind", state.kind);
  if (state.crawl !== DEFAULT_FILTERS.crawl) params.set("status", state.crawl);
  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}`;
  window.history.replaceState({}, "", nextUrl);
}

function renderMetrics() {
  const summary = state.crawlStatus.summary;
  setText("metricSources", formatNumber.format(state.sourceIndex.source_file_count));
  setText("metricUrls", formatNumber.format(state.sourceIndex.total_unique_url_count));
  setText("metricCandidates", formatNumber.format(state.sourceIndex.public_crawl_candidate_count));
  setText("metricChecked", formatNumber.format(summary.checked));
  setText(
    "metricUnchecked",
    formatNumber.format(
      summary.unchecked ?? Math.max(0, state.sourceIndex.public_crawl_candidate_count - summary.checked),
    ),
  );
  setText("metricCrawlOk", formatNumber.format(summary.ok));
}

function renderTaxonomy() {
  const container = document.getElementById("taxonomyList");
  container.innerHTML = state.taxonomy.sections
    .map(
      (section) => `
        <article class="taxonomy-item">
          <h3>${escapeHtml(section.label)}</h3>
          <p>${escapeHtml(section.reader_question)}</p>
          <div class="chips">
            ${section.fields.map((field) => `<span class="chip">${escapeHtml(field)}</span>`).join("")}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderDomainChart() {
  const container = document.getElementById("domainChart");
  const rows = state.sourceIndex.top_domains.slice(0, 12);
  const max = Math.max(...rows.map((row) => row.count), 1);
  container.innerHTML = rows
    .map(
      (row) => `
        <div class="domain-row">
          <span class="domain-name">${escapeHtml(row.domain)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${(row.count / max) * 100}%"></span></span>
          <span class="domain-count">${formatNumber.format(row.count)}</span>
        </div>
      `,
    )
    .join("");
}

function renderInsightMetrics() {
  const summary = state.policyInsights.summary;
  setText("policyMetricTotal", formatNumber.format(summary.policy_count));
  setText("policyMetricDiscontinued", formatNumber.format(summary.discontinued_count));
  setText("policyMetricCurrent", formatNumber.format(summary.current_count));
  setText("policyMetricUnknown", formatNumber.format(summary.unknown_count));
}

function barRows(rows, options = {}) {
  const max = Math.max(...rows.map((row) => row.count), 1);
  return rows
    .map((row) => {
      const percent = Math.max((row.count / max) * 100, 3);
      return `
        <div class="insight-row">
          <div class="insight-label">
            <span>${escapeHtml(row.label)}</span>
            <strong>${formatNumber.format(row.count)}</strong>
          </div>
          <span class="bar-track"><span class="bar-fill ${escapeHtml(options.className || "")}" style="width:${percent}%"></span></span>
        </div>
      `;
    })
    .join("");
}

function tiiDetailUrl(productId) {
  return productId ? `https://insprod.tii.org.tw/DetailList.aspx?productId=${encodeURIComponent(productId)}` : "";
}

function expandTiiIndexRecord(record) {
  const versionCount = Number(record.v || 1);
  return {
    product_name: record.n,
    company: record.c,
    product_type: record.k || "TII 匯入",
    sale_status: record.s,
    product_id: record.p,
    sale_date: record.sd,
    discontinued_date: record.dd,
    policy_url: state.tiiMetadata?.source_url,
    detail_url: tiiDetailUrl(record.p),
    origin: "保發中心",
    version_note:
      versionCount > 1
        ? `同公司同名商品有 ${formatNumber.format(versionCount)} 個不同版本；請依銷售日、停售日與官方明細分別判讀。`
        : "",
    display_version:
      record.e ||
      `銷售日 ${record.sd || "未標示"}｜停售日 ${record.dd || "未標示"}`,
    flags: [
      "TII 匯入",
      record.b || "人工批次",
      versionCount > 1 ? `同名不同版 ${versionCount}` : "",
      record.d ? "明細已保存" : "明細待抓取",
    ].filter(Boolean),
  };
}

function localDiscontinuedPolicies() {
  return (state.policyInsights.discontinued_policies || []).map((policy) => ({
    ...policy,
    origin: "來源文件",
    display_version: policy.version_text || "版本未標示",
    flags: policy.content_flags || [],
  }));
}

function discontinuedSearchText(policy) {
  return normalize(
    [
      policy.product_name,
      policy.company,
      policy.product_type,
      policy.sale_status,
      policy.product_id,
      policy.sale_date,
      policy.discontinued_date,
      policy.display_version,
      policy.origin,
      ...(policy.flags || []),
    ].join(" "),
  );
}

function discontinuedMatchesFilters(policy) {
  const query = normalize(state.search);
  if (state.company !== "all" && policy.company !== state.company) return false;
  if (state.kind !== "all" && policy.product_type !== state.kind) return false;
  if (!query) return true;
  return matchesQuery(discontinuedSearchText(policy), query);
}

function tiiIndexShardsForCurrentFilters() {
  return state.tiiManifest?.index_shards || [];
}

async function ensureTiiIndexLoaded() {
  if (state.tiiIndexRecords) return state.tiiIndexRecords;
  if (state.tiiIndexLoadPromise) return state.tiiIndexLoadPromise;
  const shards = tiiIndexShardsForCurrentFilters();
  state.tiiIndexLoadPromise = Promise.all(
    shards.map((shard) =>
      fetch(`./${shard.path}`).then((response) => {
        if (!response.ok) throw new Error(`TII index shard not available: ${shard.path}`);
        return response.json();
      }),
    ),
  )
    .then((payloads) => {
      const records = payloads.flatMap((payload) => payload.records || []);
      state.tiiIndexRecords = records;
      state.tiiIndexLoadPromise = null;
      return records;
    })
    .catch((error) => {
      state.tiiIndexLoadPromise = null;
      throw error;
    });
  return state.tiiIndexLoadPromise;
}

function loadPortfolioItems() {
  try {
    const saved = JSON.parse(localStorage.getItem(PORTFOLIO_STORAGE_KEY) || "[]");
    state.portfolioItems = Array.isArray(saved)
      ? saved
          .filter((item) => item?.product_name)
          .map((item) => {
            const selectionMode = portfolioSelectionMode(item);
            const selectionFields = coverageModel.SELECTION_MODES[selectionMode]?.fields || [];
            const requiresVersionRefresh =
              item.source_kind === "tii" &&
              item.source_batch_id &&
              item.product_id;
            return {
              ...item,
              id: portfolioItemId(item),
              selection_mode: selectionMode,
              selection_type: selectionMode,
              selection_source: item.selection_source || "",
              face_amount: selectionFields.includes("face_amount") ? normalizeCoverageAmount(item.face_amount, item) : null,
              account_value: selectionFields.includes("account_value")
                ? normalizeCoverageAmount(item.account_value || item.policy_state?.policy_account_value, item)
                : null,
              unit_count: selectionFields.includes("unit_count") ? normalizeUnitCount(item.unit_count ?? item.units) : null,
              unit_counts: selectionFields.includes("unit_counts")
                ? Object.fromEntries(
                    coverageModel
                      .normalizeUnitFields(item)
                      .map((field) => [field.key, normalizeUnitCount(item.unit_counts?.[field.key])])
                      .filter(([, value]) => value),
                  )
                : {},
              plan_name: selectionFields.includes("plan_name") ? String(item.plan_name || "").trim() : "",
              policy_state: Object.fromEntries(
                Object.entries(item.policy_state || {}).filter(([, value]) => value !== null && value !== undefined && value !== ""),
              ),
              plan_options: requiresVersionRefresh ? [] : item.plan_options || [],
              coverage_entries: requiresVersionRefresh
                ? []
                : normalizeCoverageEntries(item.coverage_entries),
              document_summary_loaded: false,
            };
          })
      : [];
  } catch {
    state.portfolioItems = [];
  }
}

function savePortfolioItems() {
  try {
    localStorage.setItem(PORTFOLIO_STORAGE_KEY, JSON.stringify(state.portfolioItems));
  } catch {
    // Local storage can be unavailable in privacy modes; the in-memory set still works.
  }
}

function populatePortfolioFilters() {
  const companyInput = document.getElementById("portfolioCompanyFilter");
  const companyOptions = document.getElementById("portfolioCompanyOptions");
  const localCompanies = (state.policyContentExtracts?.records || []).map((item) => item.company).filter(Boolean);
  const tiiCompanies = (state.tiiManifest?.company_counts || []).map((item) => item.company).filter(Boolean);
  const companies = [...new Set([...tiiCompanies, ...localCompanies])].sort((a, b) => a.localeCompare(b, "zh-Hant-TW"));
  companyOptions.innerHTML = companies.map((company) => `<option value="${escapeHtml(company)}"></option>`).join("");
  companyInput.value = state.portfolioCompany === "all" ? "" : state.portfolioCompany;
  document.getElementById("portfolioBucketFilter").value = state.portfolioBucket;
}

function portfolioKey(value) {
  return normalize(value).replace(/\s+/g, " ").slice(0, 180);
}

function inferPortfolioBucket(item) {
  const sourceBatch = String(item.source_batch_id || item.source_batch || item.record_id || "");
  const company = String(item.company || "");
  const type = String(item.product_type || item.insurance_category || "");
  if (item.bucket) return item.bucket;
  if (sourceBatch.includes("tii-property")) return "property";
  if (sourceBatch.includes("tii-life")) return "life";
  if (/產物|產險|火災|海上|汽車|車體|強制汽車/.test(`${company} ${type}`)) return "property";
  return "life";
}

function portfolioBucketLabel(bucket) {
  return bucket === "property" ? "產險 / 財產保險" : "壽險 / 人身保險";
}

function companyMatchesFilter(company, selectedCompany) {
  if (!selectedCompany || selectedCompany === "all") return true;
  const current = normalize(company);
  const selected = normalize(selectedCompany);
  return current === selected || current.includes(selected) || selected.includes(current);
}

function itemMatchesPortfolioFilters(item) {
  if (!companyMatchesFilter(item.company, state.portfolioCompany)) return false;
  if (state.portfolioBucket !== "all" && inferPortfolioBucket(item) !== state.portfolioBucket) return false;
  return true;
}

function portfolioIdentityFingerprint(item) {
  return portfolioKey(
    [
      item.source_batch_id || "",
      item.product_id || "no-product-id",
      item.source_document_sha256 || "",
      item.company || "",
      inferPortfolioBucket(item),
      item.product_type || "",
      item.product_name || "",
      item.sale_date || "",
      item.discontinued_date || "",
      item.display_version || "",
    ].join("|"),
  );
}

function portfolioItemId(item) {
  if (item.product_id) return `product:${item.product_id}:${portfolioIdentityFingerprint(item)}`;
  if (item.record_id) return `record:${item.record_id}:${portfolioIdentityFingerprint(item)}`;
  if (item.policy_url) return `url:${item.policy_url}`;
  return `manual:${portfolioKey([item.company, item.product_name, item.display_version].join("|"))}`;
}

function policyContentToPortfolioItem(record) {
  const item = {
    id: "",
    record_id: record.url_id || record.id,
    source_kind: "content",
    product_name: record.product_name || "未命名保單",
    company: record.company || "未標示公司",
    product_type: record.product_type || "其他",
    bucket: inferPortfolioBucket(record),
    sale_status: record.sale_status || "狀態待確認",
    product_id: record.product_id || "",
    display_version: record.version_text || record.extracted_at || "條款解析",
    policy_url: record.policy_url || "",
    detail_url: record.detail_url || "",
    origin: "條款解析",
    focus_score: record.focus_score || 0,
    matched_terms: record.matched_terms || [],
    field_hits: record.field_hits || [],
    reader_focus: record.reader_focus || [],
    flags: [
      record.document_kind ? record.document_kind.toUpperCase() : "",
      `${formatNumber.format(record.focus_score || 0)}/4 重點`,
      record.confidence || "",
    ].filter(Boolean),
    search_text: policySearchText(record),
  };
  item.id = portfolioItemId(item);
  return item;
}

function tiiIndexToPortfolioItem(record) {
  const expanded = expandTiiIndexRecord(record);
  const item = {
    id: "",
    record_id: record.i,
    source_kind: "tii",
    product_name: expanded.product_name || "未命名保單",
    company: expanded.company || "未標示公司",
    product_type: expanded.product_type || "TII 匯入",
    bucket: String(record.b || "").includes("tii-property") ? "property" : "life",
    source_batch_id: record.b || "",
    sale_status: expanded.sale_status || "狀態待確認",
    product_id: expanded.product_id || "",
    sale_date: expanded.sale_date || "",
    discontinued_date: expanded.discontinued_date || "",
    display_version: expanded.display_version || "",
    policy_url: expanded.policy_url || "",
    detail_url: expanded.detail_url || "",
    origin: expanded.origin || "保發中心",
    version_note: expanded.version_note || "",
    flags: expanded.flags || [],
    search_text: tiiSearchText(record),
  };
  item.id = portfolioItemId(item);
  return item;
}

function manualPortfolioItem(query) {
  const item = {
    id: "",
    source_kind: "manual",
    product_name: query,
    company: "自行輸入",
    product_type: "待分類",
    bucket: state.portfolioBucket === "all" ? "" : state.portfolioBucket,
    sale_status: "待對照資料庫",
    product_id: "",
    display_version: "手動加入",
    origin: "自行輸入",
    flags: ["手動項目", "待官方複核"],
    matched_terms: [query],
    field_hits: [],
    reader_focus: [],
    search_text: normalize(query),
    selection_type: "unknown",
    selection_mode: "unknown",
    face_amount: null,
    unit_count: null,
    unit_counts: {},
  };
  item.id = portfolioItemId(item);
  return item;
}

function tiiSearchText(record) {
  return normalize([record.n, record.c, record.k, record.p, record.s, record.sd, record.dd, record.e, record.b].join(" "));
}

function portfolioSearchText(item, options = {}) {
  const focusText = (item.reader_focus || [])
    .flatMap((focus) => [focus.label, focus.reader_question, focus.summary, ...(focus.terms || [])])
    .join(" ");
  return normalize(
    [
      options.excludeCompany ? "" : item.company,
      item.product_name,
      item.product_type,
      item.sale_status,
      item.product_id,
      item.sale_date,
      item.discontinued_date,
      item.display_version,
      item.origin,
      ...(item.flags || []),
      ...(item.field_hits || []),
      ...(item.matched_terms || []),
      focusText,
      item.search_text,
    ].join(" "),
  );
}

function coverageDetectionText(item) {
  return normalize(
    [
      item.product_name,
      item.product_type,
      item.product_id,
      item.sale_status,
      item.display_version,
      ...(item.coverage_tags || []),
      ...(item.flags || []),
    ].join(" "),
  );
}

function portfolioMatchScore(item, query) {
  const normalizedQuery = normalize(query);
  const productName = normalize(item.product_name);
  const productId = normalize(item.product_id);
  const productType = normalize(item.product_type);
  let score = 0;
  if (productId && productId === normalizedQuery) score += 120;
  if (productId && productId.includes(normalizedQuery)) score += 70;
  if (productName === normalizedQuery) score += 90;
  if (productName.includes(normalizedQuery)) score += 45;
  if (productType.includes(normalizedQuery)) score += 24;
  if (matchesQuery(portfolioSearchText(item), query)) score += 18;
  if (item.source_kind === "content") score += 8 + (item.focus_score || 0);
  if (item.detail_url) score += 5;
  if ((item.flags || []).some((flag) => String(flag).includes("同名不同版"))) score += 2;
  return score;
}

function isLikelyProductCode(query) {
  const compact = String(query || "").replace(/\s+/g, "");
  return compact.length >= 8 && /[A-Za-z]/.test(compact) && /\d/.test(compact);
}

function uniquePortfolioCandidates(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = portfolioIdentityFingerprint(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function exactProductIdMatches(items, query) {
  const normalizedQuery = normalize(query);
  return items.filter((item) => item.product_id && normalize(item.product_id) === normalizedQuery);
}

function exactNameMatches(items, query) {
  const normalizedQuery = normalize(query);
  return items.filter((item) => normalize(item.product_name) === normalizedQuery);
}

function exactNameVersionFamilyMatches(items, query) {
  const normalizedQuery = normalize(query);
  const familyName = coverageModel.productVersionFamilyName(query);
  if (!familyName || familyName !== normalizedQuery) return exactNameMatches(items, query);
  return items.filter((item) => coverageModel.productVersionFamilyName(item.product_name) === familyName);
}

async function findPortfolioMatches(query) {
  const localMatches = (state.policyContentExtracts?.records || [])
    .map(policyContentToPortfolioItem)
    .filter(itemMatchesPortfolioFilters)
    .filter((item) => matchesQuery(portfolioSearchText(item), query))
    .map((item) => ({ ...item, match_score: portfolioMatchScore(item, query) }))
    .filter((item) => item.match_score > 0);

  const shouldLoadTii =
    isLikelyProductCode(query) || localMatches.length < 5 || state.portfolioCompany !== "all" || state.portfolioBucket !== "all";
  let tiiMatches = [];
  if (shouldLoadTii) {
    const records = await ensureTiiIndexLoaded();
    tiiMatches = records
      .filter((record) => matchesQuery(tiiSearchText(record), query))
      .map(tiiIndexToPortfolioItem)
      .filter(itemMatchesPortfolioFilters)
      .map((item) => ({ ...item, match_score: portfolioMatchScore(item, query) }))
      .filter((item) => item.match_score > 0);
  }

  return uniquePortfolioCandidates([...localMatches, ...tiiMatches])
    .sort((a, b) => {
      const scoreDiff = (b.match_score || 0) - (a.match_score || 0);
      if (scoreDiff) return scoreDiff;
      const companyDiff = String(a.company || "").localeCompare(String(b.company || ""), "zh-Hant-TW");
      if (companyDiff) return companyDiff;
      return String(a.product_name || "").localeCompare(String(b.product_name || ""), "zh-Hant-TW");
    });
}

function detectCoverageBuckets(item) {
  return coverageModel.detectCoverageBuckets(item);
}

function coverageBadgeHtml(item) {
  const buckets = detectCoverageBuckets(item);
  if (!buckets.length) return '<span class="chip muted">待分類</span>';
  return buckets.map((bucket) => `<span class="chip">${escapeHtml(bucket.label)}</span>`).join("");
}

function structureStatusForItem(item) {
  return coverageModel.structureStatus(item);
}

function structureStatusBadgeHtml(item) {
  const status = structureStatusForItem(item);
  return `<span class="chip structure-status status-${escapeHtml(status.id)}">${escapeHtml(status.short_label || status.label)}</span>`;
}

function selectionModeBadgeHtml(item) {
  const requirements = coverageModel.selectionRequirements(item);
  if (requirements.mode === "unknown") return "";
  return `<span class="chip">${escapeHtml(requirements.label)}</span>`;
}

function policyCodeBadgeHtml(item) {
  return "";
}

function policyTitleHtml(item) {
  return `<span class="policy-title-text">${escapeHtml(item.product_name)}</span>${policyCodeBadgeHtml(item)}`;
}

function identityMetaHtml(item) {
  const rows = [
    portfolioBucketLabel(inferPortfolioBucket(item)),
    item.sale_date ? `銷售日 ${item.sale_date}` : "",
    item.discontinued_date ? `停售日 ${item.discontinued_date}` : item.sale_status || "",
  ].filter(Boolean);
  return rows.map((row) => `<span>${escapeHtml(row)}</span>`).join("");
}

function identityWarningHtml(item) {
  const messages = [];
  if (item.version_note) messages.push(item.version_note);
  if (!messages.length) return "";
  return `<p class="identity-warning">${messages.map(escapeHtml).join(" ")}</p>`;
}

function addPortfolioItem(item) {
  const selectionMode = portfolioSelectionMode(item);
  const selectionFields = coverageModel.SELECTION_MODES[selectionMode]?.fields || [];
  const normalizedItem = {
    ...item,
    id: item.id || portfolioItemId(item),
    selection_mode: selectionMode,
    selection_type: item.selection_type || selectionMode,
    face_amount: selectionFields.includes("face_amount") ? normalizeCoverageAmount(item.face_amount, item) : null,
    account_value: selectionFields.includes("account_value")
      ? normalizeCoverageAmount(item.account_value || item.policy_state?.policy_account_value, item)
      : null,
    unit_count: selectionFields.includes("unit_count") ? normalizeUnitCount(item.unit_count) : null,
    unit_counts: selectionFields.includes("unit_counts")
      ? Object.fromEntries(
          coverageModel
            .normalizeUnitFields(item)
            .map((field) => [field.key, normalizeUnitCount(item.unit_counts?.[field.key])])
            .filter(([, value]) => value),
        )
      : {},
    plan_name: selectionFields.includes("plan_name") ? String(item.plan_name || "").trim() : "",
    policy_state: Object.fromEntries(
      Object.entries(item.policy_state || {}).filter(([, value]) => value !== null && value !== undefined && value !== ""),
    ),
    coverage_entries: normalizeCoverageEntries(item.coverage_entries),
  };
  const existingIndex = state.portfolioItems.findIndex((current) => current.id === normalizedItem.id);
  if (existingIndex >= 0) {
    state.portfolioItems = state.portfolioItems.map((current, index) =>
      index === existingIndex
        ? {
            ...current,
            ...normalizedItem,
            selection_mode: normalizedItem.selection_mode,
            selection_type: normalizedItem.selection_type,
            face_amount: normalizedItem.face_amount,
            account_value: normalizedItem.account_value,
            unit_count: normalizedItem.unit_count,
            unit_counts: normalizedItem.unit_counts,
            plan_name: normalizedItem.plan_name,
            policy_state: normalizedItem.policy_state,
            coverage_entries:
              normalizedItem.source_kind === "tii"
                ? normalizedItem.coverage_entries
                : normalizedItem.coverage_entries.length
                  ? normalizedItem.coverage_entries
                  : normalizeCoverageEntries(current.coverage_entries),
          }
        : current,
    );
    savePortfolioItems();
    renderPortfolio();
    return "updated";
  }
  if (existingIndex < 0) {
    state.portfolioItems = [...state.portfolioItems, normalizedItem];
    savePortfolioItems();
  }
  renderPortfolio();
  return "added";
}

function removePortfolioItem(id) {
  state.portfolioItems = state.portfolioItems.filter((item) => item.id !== id);
  if (state.editingPortfolioId === id) state.editingPortfolioId = null;
  savePortfolioItems();
  renderPortfolio();
}

function clearPortfolio() {
  state.portfolioItems = [];
  state.portfolioSuggestions = [];
  state.portfolioDetailItem = null;
  state.editingPortfolioId = null;
  savePortfolioItems();
  renderPortfolio();
  renderPortfolioDetail(null);
  setText("portfolioHint", "已清空集合。可以重新輸入保單名稱或險種。");
}

function renderPortfolioSuggestions(matches, query) {
  const container = document.getElementById("portfolioSuggestions");
  state.portfolioSuggestions = matches;
  if (!matches.length) {
    container.innerHTML = "";
    return;
  }
  const totalPages = Math.max(Math.ceil(matches.length / state.portfolioSuggestionPageSize), 1);
  state.portfolioSuggestionPage = clampPage(state.portfolioSuggestionPage, totalPages);
  const startIndex = (state.portfolioSuggestionPage - 1) * state.portfolioSuggestionPageSize;
  const visibleMatches = matches.slice(startIndex, startIndex + state.portfolioSuggestionPageSize);
  const shouldPaginate = matches.length > state.portfolioSuggestionPageSize;
  const portfolioPagination = shouldPaginate
    ? paginationHtml("portfolio", matches.length, state.portfolioSuggestionPage, state.portfolioSuggestionPageSize, PORTFOLIO_PAGE_SIZES)
    : "";
  container.innerHTML = `
    <div class="suggestion-heading">
      <strong>找到 ${formatNumber.format(matches.length)} 個候選</strong>
      <span>請先查看保障與金額，再加入集合。</span>
    </div>
    ${portfolioPagination}
    <div class="suggestion-list">
      ${visibleMatches
        .map(
          (item, visibleIndex) => {
            const index = startIndex + visibleIndex;
            return `
            <article class="suggestion-item">
              <div>
                <strong class="policy-title-line">${policyTitleHtml(item)}</strong>
                <div class="policy-meta">
                  <span>${escapeHtml(item.company)}</span>
                  <span>${escapeHtml(item.product_type)}</span>
                  ${identityMetaHtml(item)}
                </div>
                <div class="policy-flags">${coverageBadgeHtml(item)}${structureStatusBadgeHtml(item)}${selectionModeBadgeHtml(item)}</div>
              </div>
              <div class="suggestion-actions">
                <button class="button primary" type="button" data-view-suggestion="${index}">查看保障與金額</button>
              </div>
            </article>
          `;
          },
        )
        .join("")}
    </div>
    ${portfolioPagination}
    <p class="result-summary">「${escapeHtml(query)}」共有 ${formatNumber.format(matches.length)} 個候選；若同名很多，請用公司與銷售日期核對版本。</p>
  `;
}

function focusByKeyForPortfolio(item, key) {
  return (item.reader_focus || []).find((focus) => focus.key === key);
}

function coverageSummaryForItem(item) {
  const buckets = detectCoverageBuckets(item).map((bucket) => bucket.label);
  const status = structureStatusForItem(item);
  const categoryText = buckets.length
    ? `系統依商品名稱與險種判斷，這張保單可能對應 ${buckets.join("、")}。`
    : item.product_type && item.product_type !== "待分類"
      ? `目前可確認的險種為 ${item.product_type}。`
      : "目前先保留為待分類項目，建議用完整保單名稱或公司再查一次。";
  return `${categoryText}${status.description}`;
}

function focusSummaryHtml(item) {
  const missingSummary = item.document_summary_loading
    ? "正在載入已整理的條款摘要。"
    : "目前沒有已解析條款摘要；可先用官方明細確認條款內容。";
  const cards = [
    ["coverage", "保障項目"],
    ["definitions", "重要定義"],
    ["special", "特殊項目"],
    ["claims", "理賠申請"],
  ].map(([key, label]) => {
    const focus = focusByKeyForPortfolio(item, key);
    const terms = focus?.terms?.length ? focus.terms.slice(0, 6) : [];
    return `
      <article class="portfolio-summary-card">
        <strong>${escapeHtml(focus?.label || label)}</strong>
        <p>${escapeHtml(focus?.summary || missingSummary)}</p>
        ${
          terms.length
            ? `<div class="chips">${terms.map((term) => `<span class="chip">${escapeHtml(term)}</span>`).join("")}</div>`
            : ""
        }
      </article>
    `;
  });
  return cards.join("");
}

function coveragePreviewHtml(item) {
  const options = normalizePlanOptions(item);
  const selectedPlan = options.find(
    (option) => option.value === item?.plan_name || option.label === item?.plan_name,
  );
  const entries = effectiveCoverageEntries(item);
  const needsPlan = options.length && !selectedPlan;
  const status = structureStatusForItem(item);
  return `
    <section class="portfolio-benefit-preview" data-plan-benefit-preview>
      <div class="portfolio-benefit-preview-top">
        <div>
          <p class="eyebrow">${escapeHtml(status.label)}</p>
          <h4>${selectedPlan ? `${escapeHtml(selectedPlan.label)} 的保障與金額` : needsPlan ? "選擇計畫後查看保障與金額" : "條款保障與金額"}</h4>
        </div>
        ${entries.length ? `<span class="chip">${formatNumber.format(entries.length)} 項保障</span>` : `<span class="chip structure-status status-${escapeHtml(status.id)}">${escapeHtml(status.short_label || status.label)}</span>`}
      </div>
      ${
        needsPlan
          ? '<p class="portfolio-benefit-empty">請先選擇計畫；系統會依條款附表顯示該計畫的保障項目、金額與給付基準。</p>'
          : portfolioCoverageEntriesHtml(selectedPlan ? { ...item, plan_name: selectedPlan.value } : item)
      }
    </section>
  `;
}

function refreshPortfolioBenefitPreview() {
  if (!state.portfolioDetailItem) return;
  const preview = document.querySelector("#portfolioDetail [data-plan-benefit-preview]");
  if (!preview) return;
  preview.outerHTML = coveragePreviewHtml(state.portfolioDetailItem);
}

function hasVerifiedBenefits(item) {
  if (normalizeCoverageEntries(item?.coverage_entries || item?.benefit_rules).length) return true;
  return normalizePlanOptions(item).some((option) => option.coverage_entries.length > 0);
}

function renderPortfolioDetail(item) {
  const container = document.getElementById("portfolioDetail");
  state.portfolioDetailItem = item || null;
  if (!item) {
    container.innerHTML = "";
    return;
  }
  const detailLink = item.detail_url || item.policy_url || "";
  const showFallbackSummary = !hasVerifiedBenefits(item);
  const isInPortfolio = state.portfolioItems.some(
    (portfolioItem) => portfolioItem.id === portfolioItemId(item),
  );
  container.innerHTML = `
    <article class="portfolio-detail-card">
      <div class="portfolio-detail-top">
        <div>
          <p class="eyebrow">保障摘要</p>
          <h3 class="policy-title-line">${policyTitleHtml(item)}</h3>
        </div>
        <button class="button ghost" type="button" data-close-portfolio-detail>關閉</button>
      </div>
      <div class="policy-meta detail-meta">
        <span>${escapeHtml(item.company)}</span>
        <span>${escapeHtml(item.product_type)}</span>
        ${identityMetaHtml(item)}
      </div>
      <div class="portfolio-detail-grid">
        <section>
          <h4>保障摘要</h4>
          <p>${escapeHtml(coverageSummaryForItem(item))}</p>
          <div class="policy-flags">${coverageBadgeHtml(item)}${structureStatusBadgeHtml(item)}${selectionModeBadgeHtml(item)}</div>
        </section>
        <section>
          <h4>核對資訊</h4>
          <dl class="identity-list">
            <div><dt>公司</dt><dd>${escapeHtml(item.company)}</dd></div>
            <div><dt>險種</dt><dd>${escapeHtml(item.product_type)}</dd></div>
            ${item.sale_date ? `<div><dt>銷售日</dt><dd>${escapeHtml(item.sale_date)}</dd></div>` : ""}
            ${item.discontinued_date ? `<div><dt>停售日</dt><dd>${escapeHtml(item.discontinued_date)}</dd></div>` : ""}
          </dl>
        </section>
      </div>
      ${
        showFallbackSummary
          ? `<details class="coverage-detail">
              <summary>文件摘要</summary>
              <div class="portfolio-summary-grid">${focusSummaryHtml(item)}</div>
            </details>`
          : ""
      }
      ${identityWarningHtml(item)}
      ${portfolioSelectionFieldsHtml(item)}
      ${coveragePreviewHtml(item)}
      <div class="portfolio-detail-actions">
        <button class="button primary" type="button" data-confirm-add-portfolio ${item.document_summary_loading ? "disabled aria-busy=\"true\"" : ""}>${item.document_summary_loading ? "載入條款摘要中" : isInPortfolio ? "更新保單集合" : "加入我的保單集合"}</button>
        ${detailLink ? `<a class="button secondary" href="${escapeHtml(detailLink)}" target="_blank" rel="noreferrer">官方來源</a>` : ""}
      </div>
    </article>
  `;
}

async function loadTiiDocumentSummaryBatch(batchId) {
  if (!/^tii-(life|property)-\d{3}$/.test(batchId)) return null;
  if (state.tiiDocumentSummaryCache.has(batchId)) return state.tiiDocumentSummaryCache.get(batchId);
  if (state.tiiDocumentSummaryPromises.has(batchId)) return state.tiiDocumentSummaryPromises.get(batchId);

  const promise = fetch(`./data/tii/document-summaries/${encodeURIComponent(batchId)}.json`)
    .then((response) => {
      if (response.status === 404) return null;
      if (!response.ok) throw new Error(`條款摘要載入失敗：${response.status}`);
      return response.json();
    })
    .then((payload) => {
      state.tiiDocumentSummaryCache.set(batchId, payload);
      state.tiiDocumentSummaryPromises.delete(batchId);
      return payload;
    })
    .catch((error) => {
      state.tiiDocumentSummaryPromises.delete(batchId);
      throw error;
    });
  state.tiiDocumentSummaryPromises.set(batchId, promise);
  return promise;
}

async function enrichPortfolioItemWithDocumentSummary(item) {
  const batchId = String(item.source_batch_id || "");
  if (item.source_kind !== "tii" || !batchId || !item.product_id) return item;
  const payload = await loadTiiDocumentSummaryBatch(batchId);
  const summary = payload?.records?.find((record) => record.product_id === item.product_id);
  if (!summary) return item;
  const verifiedSourceSha = String(summary.source_document_sha256 || "");
  const verifiedSchedule =
    summary.review_status === "verified_reference" &&
    Boolean(verifiedSourceSha);
  return {
    ...item,
    coverage_tags: summary.coverage_tags || [],
    reader_focus: summary.reader_focus || [],
    selection_type: verifiedSchedule ? summary.selection_type || summary.input_mode || "" : "",
    input_mode: verifiedSchedule ? summary.input_mode || "" : "",
    selection_source: verifiedSchedule ? summary.selection_source || "" : "",
    selection_label: verifiedSchedule ? summary.selection_label || "" : "",
    face_amount_label: verifiedSchedule ? summary.face_amount_label || "" : "",
    selection_guidance: verifiedSchedule ? summary.selection_guidance || "" : "",
    unit_fields: verifiedSchedule ? summary.unit_fields || [] : [],
    plan_options: verifiedSchedule ? summary.plan_options || [] : [],
    coverage_entries: verifiedSchedule
      ? normalizeCoverageEntries(summary.coverage_entries)
      : [],
    parser_id: verifiedSchedule ? summary.parser_id || "" : "",
    source_file: verifiedSchedule ? summary.source_file || "" : "",
    source_document_sha256: verifiedSchedule ? verifiedSourceSha : "",
    schedule_sha256: verifiedSchedule ? summary.schedule_sha256 || "" : "",
    review_status: verifiedSchedule ? summary.review_status : "",
    reviewed_at: verifiedSchedule ? summary.reviewed_at || "" : "",
    document_summary_loaded: true,
  };
}

async function refreshSavedTiiPortfolioItems() {
  const refreshed = await Promise.all(
    state.portfolioItems.map(async (item) => {
      if (item.source_kind !== "tii" || !item.source_batch_id || !item.product_id) {
        return item;
      }
      try {
        return await enrichPortfolioItemWithDocumentSummary(item);
      } catch {
        return {
          ...item,
          plan_options: [],
          coverage_entries: [],
          source_document_sha256: "",
          schedule_sha256: "",
          review_status: "",
          document_summary_loaded: false,
        };
      }
    }),
  );
  state.portfolioItems = refreshed;
  savePortfolioItems();
}

async function openPortfolioDetail(item) {
  if (item.source_kind !== "tii" || !item.source_batch_id || !item.product_id) {
    renderPortfolioDetail(item);
    return item;
  }

  renderPortfolioDetail({ ...item, document_summary_loading: true });
  try {
    const enriched = await enrichPortfolioItemWithDocumentSummary(item);
    const suggestionIndex = state.portfolioSuggestions.findIndex((candidate) => candidate.id === item.id);
    if (suggestionIndex >= 0) state.portfolioSuggestions[suggestionIndex] = enriched;
    renderPortfolioDetail(enriched);
    return enriched;
  } catch (error) {
    renderPortfolioDetail(item);
    setText("portfolioHint", `${error.message}；仍可使用官方明細確認。`);
    return item;
  }
}

function portfolioCoverageEntriesHtml(item, options = {}) {
  const entries = effectiveCoverageEntries(item);
  const status = structureStatusForItem(item);
  if (entries.length) {
    const eventScenarios = coverageModel.coverageEventScenarios(item);
    const visibleEntries = options.compact ? entries.slice(0, 3) : entries;
    const remainingEntries = options.compact ? entries.slice(3) : [];
    const eventScenarioHtml = eventScenarios.length
      ? `
        <section class="portfolio-event-scenarios">
          <strong>事故別條款保障毛額</strong>
          <small>各事故互斥，不可彼此相加；意外附加給付只列入意外事故。此處是條款毛額，實際給付仍可能有欠繳保費、保單借款或其他條款扣除。</small>
          <dl>
            ${eventScenarios
              .map((scenario) => {
                const parts = scenario.parts
                  .map((part) =>
                    Number.isSafeInteger(part.value)
                      ? `${part.name} ${formatNumber.format(part.value)} 元`
                      : part.name,
                  )
                  .join(" + ");
                const value = scenario.state === "calculated"
                  ? `${formatNumber.format(scenario.value)} 元`
                  : scenario.state === "amount_overflow"
                    ? "金額超出可安全計算範圍"
                    : `請輸入${policyStateFieldsText(scenario.required_fields)}後計算`;
                return `<div><dt>${escapeHtml(scenario.label)}</dt><dd><strong>${escapeHtml(value)}</strong><small>${escapeHtml(parts)}</small></dd></div>`;
              })
              .join("")}
          </dl>
        </section>
      `
      : "";
    const entryHtml = (entry) => {
      const valueText = coverageEntryValueText(entry, item);
      const aggregationLabel =
        coverageModel.AGGREGATION_RULES[entry.aggregation_rule] ||
        coverageModel.AGGREGATION_RULES.unknown;
      const resultKindLabel =
        coverageModel.RESULT_KINDS[entry.result_kind] ||
        coverageModel.RESULT_KINDS.reference;
      const amountStageLabel =
        coverageModel.AMOUNT_STAGES[entry.amount_stage] ||
        coverageModel.AMOUNT_STAGES.not_applicable;
      return `
        <div>
          <dt>${escapeHtml(entry.name || "保障項目")}</dt>
          <dd>
            <strong>${escapeHtml(valueText)}</strong>
            <span class="benefit-meta">${escapeHtml(resultKindLabel)} · ${escapeHtml(amountStageLabel)} · ${escapeHtml(coverageModel.LIMIT_SCOPES[entry.limit_scope] || coverageModel.LIMIT_SCOPES.unknown)} · ${escapeHtml(aggregationLabel)}</span>
            ${entry.note && entry.note !== valueText ? `<small>${escapeHtml(entry.note)}</small>` : ""}
            ${entry.conditions?.length ? `<small>${escapeHtml(entry.conditions.join("；"))}</small>` : ""}
            ${entry.source_ref ? `<small class="portfolio-benefit-reference">${escapeHtml(entry.source_ref)}</small>` : ""}
          </dd>
        </div>
      `;
    };
    return `
      ${eventScenarioHtml}
      <p class="portfolio-benefit-source">依條款資料整理</p>
      <dl class="portfolio-benefit-list">
        ${visibleEntries.map(entryHtml).join("")}
      </dl>
      ${
        remainingEntries.length
          ? `<details class="portfolio-benefit-more"><summary>查看其餘 ${formatNumber.format(remainingEntries.length)} 項保障</summary><dl class="portfolio-benefit-list">${remainingEntries.map(entryHtml).join("")}</dl></details>`
          : ""
      }
    `;
  }

  const coverageFocus = focusByKeyForPortfolio(item, "coverage");
  if (coverageFocus?.summary) {
    const terms = coverageFocus.terms?.slice(0, 6) || [];
    return `
      <div class="portfolio-terms-summary">
        <p class="portfolio-benefit-source">${escapeHtml(status.label)}</p>
        <p>${escapeHtml(status.description)}</p>
        <p>${escapeHtml(coverageFocus.summary)}</p>
        ${terms.length ? `<div class="chips">${terms.map((term) => `<span class="chip">${escapeHtml(term)}</span>`).join("")}</div>` : ""}
      </div>
    `;
  }

  return `<p class="portfolio-benefit-empty">${escapeHtml(status.description)}</p>`;
}

function portfolioEditFormHtml(item) {
  return `
    <form class="portfolio-edit-form" data-portfolio-edit-form="${escapeHtml(item.id)}">
      <p class="portfolio-edit-note">只調整條款指定的契約保險金額、計畫或單位；保障項目不可自行修改。</p>
      ${portfolioSelectionFieldsHtml(item)}
      <div class="portfolio-edit-actions">
        <button class="button ghost" type="button" data-cancel-portfolio-edit>取消</button>
        <button class="button primary" type="submit">儲存</button>
      </div>
    </form>
  `;
}

function renderPortfolioList() {
  const container = document.getElementById("portfolioList");
  setText("portfolioCount", `${formatNumber.format(state.portfolioItems.length)} 個險種`);
  if (!state.portfolioItems.length) {
    container.innerHTML =
      '<div class="empty"><strong>尚未加入保單。</strong><span>從上方輸入保單名稱或險種，就會形成自己的保障集合。</span></div>';
    return;
  }
  container.innerHTML = state.portfolioItems
    .map((item) => {
      const isEditing = state.editingPortfolioId === item.id;
      return `
        <article class="portfolio-item">
          <div>
            <strong class="policy-title-line">${policyTitleHtml(item)}</strong>
            <div class="policy-meta">
              <span>${escapeHtml(item.company)}</span>
              <span>${escapeHtml(item.product_type)}</span>
              ${identityMetaHtml(item)}
              <span>${escapeHtml(portfolioSelectionText(item))}</span>
            </div>
            <div class="policy-flags">
              ${coverageBadgeHtml(item)}${structureStatusBadgeHtml(item)}${selectionModeBadgeHtml(item)}
            </div>
            ${portfolioCoverageEntriesHtml(item, { compact: true })}
          </div>
          <div class="portfolio-actions">
            ${
              item.detail_url
                ? `<a class="button secondary" href="${escapeHtml(item.detail_url)}" target="_blank" rel="noreferrer">官方明細</a>`
                : item.policy_url
                  ? `<a class="button secondary" href="${escapeHtml(item.policy_url)}" target="_blank" rel="noreferrer">官方來源</a>`
                  : ""
            }
            <button class="button secondary" type="button" data-edit-portfolio="${escapeHtml(item.id)}">編輯</button>
            <button class="button ghost" type="button" data-remove-portfolio="${escapeHtml(item.id)}">移除</button>
          </div>
          ${isEditing ? portfolioEditFormHtml(item) : ""}
        </article>
      `;
    })
    .join("");
}

function renderCoverageBuckets() {
  const container = document.getElementById("coverageBuckets");
  const bucketMatches = coverageBuckets.map((bucket) => ({
    ...bucket,
    items: state.portfolioItems.filter((item) => detectCoverageBuckets(item).some((match) => match.id === bucket.id)),
  }));
  const activeCount = bucketMatches.filter((bucket) => bucket.items.length).length;
  setText("coverageScore", `${formatNumber.format(activeCount)}/${formatNumber.format(coverageBuckets.length)} 類`);
  const groupLabels = {
    personal: ["人身保障", "壽險、醫療、意外、癌症、重大疾病、長照與年金"],
    property: ["財產保障", "汽車、住宅火災、海上運輸與其他產險"],
  };
  const structureStatusCounts = (items) =>
    items.reduce((counts, item) => {
      const statusId = structureStatusForItem(item).id;
      counts[statusId] = (counts[statusId] || 0) + 1;
      return counts;
    }, {});
  const structureStatusSummaryParts = (items) => {
    const counts = structureStatusCounts(items);
    const order = ["calculated", "needs_user_input", "pending_structure", "source_pending", "confirmed_no_amount"];
    return order
      .filter((statusId) => counts[statusId])
      .map((statusId) => {
        const status = coverageModel.STRUCTURE_STATUSES[statusId] || { short_label: statusId };
        return {
          id: statusId,
          label: status.short_label || status.label,
          count: counts[statusId],
        };
      });
  };
  const structureStatusSummaryText = (items) =>
    structureStatusSummaryParts(items)
      .map((part) => `${part.label} ${formatNumber.format(part.count)}`)
      .join("、");
  const structureStatusSummaryHtml = (items) => {
    const parts = structureStatusSummaryParts(items).map(
      (part) =>
        `<span class="status-${escapeHtml(part.id)}">${escapeHtml(part.label)} ${formatNumber.format(part.count)}</span>`,
    );
    return parts.length ? `<div class="coverage-status-summary">${parts.join("")}</div>` : "";
  };
  const bucketHtml = (bucket) => {
    const hasItems = bucket.items.length > 0;
    const visibleItems = bucket.items.slice(0, 3);
    const hiddenItems = bucket.items.slice(3);
    const itemSummaryHtml = (item) => {
      const entries = effectiveCoverageEntries(item);
      const visibleEntries = entries.slice(0, 2);
      const remainingEntries = entries.length - visibleEntries.length;
      const coverageDetails = visibleEntries
        .map(
          (entry) =>
            `<small>${escapeHtml(coverageEntryText(entry, item))}${entry.note ? `；${escapeHtml(entry.note)}` : ""}</small>`,
        )
        .join("");
      const remainingText = remainingEntries > 0
        ? `<small>另有 ${formatNumber.format(remainingEntries)} 項保障，請在保單集合內查看。</small>`
        : "";
      const coverageFocus = focusByKeyForPortfolio(item, "coverage");
      const status = structureStatusForItem(item);
      const fallbackSummary = !coverageDetails && coverageFocus?.summary
        ? `<small>${escapeHtml(coverageFocus.summary)}</small>`
        : `<small class="amount-pending">${escapeHtml(status.description)}</small>`;
      return `<span><strong>${escapeHtml(item.product_name)}</strong><small>${escapeHtml(portfolioSelectionText(item))}</small><small>${escapeHtml(status.short_label || status.label)}</small>${coverageDetails || fallbackSummary}${coverageDetails ? remainingText : ""}</span>`;
    };
    return `
      <details class="coverage-bucket ${hasItems ? "active" : ""}">
        <summary class="coverage-bucket-top">
          <strong>${escapeHtml(bucket.label)}</strong>
          <span>${formatNumber.format(bucket.items.length)} 個險種${hasItems ? ` · ${escapeHtml(structureStatusSummaryText(bucket.items))}` : ""}</span>
        </summary>
        <p>${escapeHtml(bucket.summary)}</p>
        ${hasItems ? structureStatusSummaryHtml(bucket.items) : ""}
        <div class="coverage-meter" aria-hidden="true"><span style="width:${hasItems ? "100" : "0"}%"></span></div>
        <div class="coverage-examples">
          ${
            hasItems
              ? `${visibleItems.map(itemSummaryHtml).join("")}${
                  hiddenItems.length
                    ? `<details class="coverage-hidden-items"><summary>查看其餘 ${formatNumber.format(hiddenItems.length)} 個險種</summary>${hiddenItems.map(itemSummaryHtml).join("")}</details>`
                    : ""
                }`
              : "<span>尚未加入對應保單</span>"
          }
        </div>
      </details>
    `;
  };
  container.innerHTML = Object.entries(groupLabels)
    .map(([group, [label, summary]]) => {
      const buckets = bucketMatches.filter((bucket) => bucket.group === group);
      const groupActiveCount = buckets.filter((bucket) => bucket.items.length).length;
      return `
        <section class="coverage-bucket-group" aria-label="${escapeHtml(label)}">
          <div class="coverage-group-heading">
            <div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(summary)}</span></div>
            <span>${formatNumber.format(groupActiveCount)}/${formatNumber.format(buckets.length)} 類</span>
          </div>
          <div class="coverage-group-list">${buckets.map(bucketHtml).join("")}</div>
        </section>
      `;
    })
    .join("");
}

function renderPortfolio() {
  renderPortfolioList();
  renderCoverageBuckets();
}

async function runPortfolioSearch(query) {
  const searchGeneration = ++portfolioSearchGeneration;
  const cleanedQuery = String(query || "").trim();
  if (!cleanedQuery) {
    state.portfolioSuggestions = [];
    state.portfolioDetailItem = null;
    renderPortfolioSuggestions([], "");
    renderPortfolioDetail(null);
    setText("portfolioHint", "請先輸入保單名稱或險種。");
    document.getElementById("portfolioInput").focus();
    return;
  }
  state.portfolioSuggestionPage = 1;
  state.portfolioDetailItem = null;
  renderPortfolioDetail(null);
  setText("portfolioHint", "正在查找可加入的保單。");
  renderPortfolioSuggestions([], cleanedQuery);
  try {
    const matches = await findPortfolioMatches(cleanedQuery);
    if (searchGeneration !== portfolioSearchGeneration) return;
    const productIdMatches = exactProductIdMatches(matches, cleanedQuery);
    if (productIdMatches.length === 1) {
      renderPortfolioSuggestions(productIdMatches, cleanedQuery);
      setText(
        "portfolioHint",
        `已找到「${productIdMatches[0].product_name}」。請點「查看保障與金額」確認後再加入。`,
      );
      return;
    }
    if (productIdMatches.length > 1) {
      renderPortfolioSuggestions(productIdMatches, cleanedQuery);
      setText("portfolioHint", "找到多筆候選，請先核對公司、險種、銷售日/停售日與官方明細，不要自動加入。");
      return;
    }

    const nameMatches = exactNameVersionFamilyMatches(matches, cleanedQuery);
    if (nameMatches.length === 1) {
      renderPortfolioSuggestions(nameMatches, cleanedQuery);
      setText(
        "portfolioHint",
        `已找到「${nameMatches[0].product_name}」。請點「查看保障與金額」確認後再加入。`,
      );
      return;
    }
    if (nameMatches.length > 1) {
      renderPortfolioSuggestions(nameMatches, cleanedQuery);
      setText("portfolioHint", "同名商品有多個候選，請用公司、險種與銷售日期確認真正版本。");
      return;
    }
    if (matches.length === 1) {
      renderPortfolioSuggestions(matches, cleanedQuery);
      setText("portfolioHint", `已找到「${matches[0].product_name}」。請點「查看保障與金額」確認後再加入。`);
      return;
    }
    if (matches.length) {
      renderPortfolioSuggestions(matches, cleanedQuery);
      setText("portfolioHint", "找到多個候選，請選擇正確的公司或版本後加入。");
      return;
    }
    const manualItem = manualPortfolioItem(cleanedQuery);
    renderPortfolioSuggestions([], cleanedQuery);
    renderPortfolioDetail(manualItem);
    setText("portfolioHint", `沒有直接對到資料庫，已建立手動項目摘要；確認名稱無誤後可加入集合。`);
  } catch (error) {
    if (searchGeneration !== portfolioSearchGeneration) return;
    setText("portfolioHint", `查找時發生問題：${error.message}`);
  }
}

function renderDiscontinuedPolicyItem(policy, versionTimelineMap) {
  return `
    <article class="policy-item">
      <div>
        <strong>${escapeHtml(policy.product_name)}</strong>
        <div class="policy-meta">
          <span>${escapeHtml(policy.company)}</span>
          <span>${escapeHtml(policy.product_type)}</span>
          <span>${escapeHtml(policy.display_version || "版本未標示")}</span>
          <span>${escapeHtml(policy.origin)}</span>
        </div>
        <div class="policy-flags">
          ${(policy.flags || []).map((flag) => `<span class="chip">${escapeHtml(flag)}</span>`).join("")}
        </div>
        ${policy.version_note ? `<p class="version-note">${escapeHtml(policy.version_note)}</p>` : ""}
        ${renderVersionTimeline(policy, versionTimelineMap)}
      </div>
      <div class="policy-card-actions">
        ${
          policy.detail_url
            ? `<a class="button secondary" href="${escapeHtml(policy.detail_url)}" target="_blank" rel="noreferrer">官方明細</a>`
            : ""
        }
        ${
          policy.policy_url
            ? `<a class="button secondary" href="${escapeHtml(policy.policy_url)}" target="_blank" rel="noreferrer">官方查詢</a>`
            : '<span class="badge muted">待補來源</span>'
        }
      </div>
    </article>
  `;
}

function renderDiscontinuedList() {
  const localPolicies = localDiscontinuedPolicies();
  const tiiTotal = Number(state.tiiManifest?.record_count || state.tiiResults?.record_count || 0);
  const tiiPolicies = state.tiiIndexRecords ? state.tiiIndexRecords.map(expandTiiIndexRecord) : [];
  const allPolicies = [...localPolicies, ...tiiPolicies];
  const rows = allPolicies.filter(discontinuedMatchesFilters);
  const displayCount = state.tiiIndexRecords ? rows.length : localPolicies.length + tiiTotal;
  const versionTimelineMap = buildVersionTimelineMap(rows);
  const container = document.getElementById("discontinuedList");
  setText("discontinuedCount", `${formatNumber.format(displayCount)} 筆`);

  if (!state.tiiIndexRecords) {
    const localRows = localPolicies.filter(discontinuedMatchesFilters);
    const localHtml = localRows.slice(0, 12).map((policy) => renderDiscontinuedPolicyItem(policy, versionTimelineMap)).join("");
    const loadingText = state.tiiIndexLoadPromise ? "TII 索引載入中。" : `TII 已分片保存 ${formatNumber.format(tiiTotal)} 筆。`;
    container.innerHTML = `
      ${localHtml}
      <div class="empty">
        <strong>${escapeHtml(loadingText)}</strong>
        <span>輸入關鍵字查詢，或先載入 compact 索引後再看保發中心清單。</span>
        ${state.tiiIndexLoadPromise ? "" : '<button class="button secondary" type="button" data-load-tii-index>載入 TII 索引</button>'}
      </div>
    `;
    return;
  }

  if (!rows.length) {
    container.innerHTML =
      '<div class="empty"><strong>找不到符合條件的停售保單。</strong><span>請改用公司、商品名稱、銷售日或停售日查詢。</span></div>';
    return;
  }

  container.innerHTML = rows.slice(0, 120).map((policy) => renderDiscontinuedPolicyItem(policy, versionTimelineMap)).join("");
  if (rows.length > 120) {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="empty"><strong>目前先顯示前 120 筆。</strong><span>符合條件共 ${formatNumber.format(
        rows.length,
      )} 筆；請用公司、類別或日期縮小範圍。</span></div>`,
    );
  }
}

function renderPolicyInsights() {
  renderInsightMetrics();
  document.getElementById("statusBars").innerHTML = barRows(state.policyInsights.status_counts, {
    className: "status-fill",
  });
  document.getElementById("typeBars").innerHTML = barRows(state.policyInsights.type_counts.slice(0, 8));
  document.getElementById("companyBars").innerHTML = barRows(state.policyInsights.company_counts.slice(0, 8));
  renderDiscontinuedList();

  const metadata = state.tiiMetadata;
  const tiiManualCount =
    state.batchPlan?.summary?.tii_manual_matrix_batch_count || state.batchPlan?.summary?.tii_full_estimated_batch_count || 0;
  const tiiAttemptedBatches = state.tiiExecutionProgress?.summary?.attempted_batches || 0;
  const tiiCaptchaRequiredBatches = state.tiiExecutionProgress?.summary?.captcha_required_batches || 0;
  const tiiIndexedBatches = state.tiiResults?.indexed_batch_count || state.tiiResults?.indexed_batches?.length || 0;
  const tiiCompletedBatches = state.tiiResults?.completed_batch_count || state.tiiResults?.completed_batches?.length || 0;
  const tiiImportedPolicies = state.tiiResults?.record_count || state.tiiResults?.records?.length || 0;
  const tiiDetailSaved = state.tiiResults?.detail_saved_count || 0;
  const tiiDetailExpected = state.tiiResults?.detail_expected_count || 0;
  const tiiDetailMissing = state.tiiResults?.detail_missing_count || 0;
  const tiiBatchSummaries = state.tiiResults?.batch_summaries || [];
  const tiiOfficialRows = tiiBatchSummaries.reduce((total, batch) => total + (batch.official_row_count || 0), 0);
  const tiiDuplicateProductRows = tiiBatchSummaries.reduce(
    (total, batch) => total + (batch.duplicate_product_id_count || 0),
    0,
  );
  const latestDuplicateBatch = [...tiiBatchSummaries]
    .reverse()
    .find((batch) => (batch.duplicate_product_id_count || 0) > 0);
  const tiiSameNameVersionedCardCount =
    state.tiiResults?.same_name_version_card_count || state.tiiManifest?.same_name_version_card_count || 0;
  const tiiSameNameVersionedGroupCount =
    state.tiiResults?.same_name_version_group_count || state.tiiManifest?.same_name_version_group_count || 0;
  const duplicateNote = latestDuplicateBatch
    ? `<p class="tii-status-note">官方結果目前累計 ${formatNumber.format(
        tiiOfficialRows,
      )} 列；本站依官方商品識別去重呈現 ${formatNumber.format(
        tiiImportedPolicies,
      )} 張保單卡，已辨識 ${formatNumber.format(tiiDuplicateProductRows)} 列官方重複資料。最新重複批次 ${
        latestDuplicateBatch.batch_id
      }：官方 ${formatNumber.format(latestDuplicateBatch.official_row_count || 0)} 列 / 去重 ${formatNumber.format(
        latestDuplicateBatch.unique_product_id_count || 0,
      )} 張。</p>`
    : "";
  const sameNameVersionNote = tiiSameNameVersionedGroupCount
    ? `<p class="tii-status-note">已辨識 ${formatNumber.format(
        tiiSameNameVersionedGroupCount,
      )} 組同公司同名但不同版本的商品，共 ${formatNumber.format(
        tiiSameNameVersionedCardCount,
      )} 張卡；本站會依銷售日、停售日與官方明細分別呈現，不以名稱合併。</p>`
    : "";
  const detailGapNote = tiiDetailMissing
    ? `<p class="tii-status-note">已保存 ${formatNumber.format(tiiDetailSaved)} / ${formatNumber.format(
        tiiDetailExpected,
      )} 個官方明細頁；另有 ${formatNumber.format(
        tiiDetailMissing,
      )} 個明細頁在當次 TII session 回傳失效，保單卡仍保留官方清單資料，後續可用新驗證碼補抓明細。</p>`
    : "";
  document.getElementById("tiiStatus").innerHTML = `
    <div class="tii-grid">
      <span><strong>${formatNumber.format(metadata.companies.length)}</strong><small>公司選項</small></span>
      <span><strong>${formatNumber.format(metadata.insurance_categories.length)}</strong><small>保險類別</small></span>
      <span><strong>${metadata.captcha_required ? "需要" : "不需要"}</strong><small>圖形驗證碼</small></span>
      <span><strong>${formatNumber.format(tiiManualCount)}</strong><small>人工批次</small></span>
      <span><strong>${formatNumber.format(tiiAttemptedBatches)}</strong><small>已啟動批次</small></span>
      <span><strong>${formatNumber.format(tiiCaptchaRequiredBatches)}</strong><small>等待驗證碼</small></span>
      <span><strong>${formatNumber.format(tiiIndexedBatches)}</strong><small>已索引批次</small></span>
      <span><strong>${formatNumber.format(tiiCompletedBatches)}</strong><small>完整批次</small></span>
      <span><strong>${formatNumber.format(tiiImportedPolicies)}</strong><small>已匯入保單</small></span>
      <span><strong>${formatNumber.format(tiiDetailSaved)}</strong><small>已保存明細</small></span>
      <span><strong>${formatNumber.format(tiiDetailMissing)}</strong><small>待補明細</small></span>
      <span><strong>${formatNumber.format(tiiOfficialRows)}</strong><small>官方結果列</small></span>
      <span><strong>${formatNumber.format(tiiDuplicateProductRows)}</strong><small>官方重複列</small></span>
    </div>
    ${duplicateNote}
    ${sameNameVersionNote}
    ${detailGapNote}
    <p>官方查詢支援公司、保險類別、銷售日、停售日與關鍵字。TII 目前採本機操作台執行：人工輸入驗證碼後，自動翻完整結果頁、抓可用明細頁並匯入本站；本專案不自動破解驗證碼。</p>
    <a href="${escapeHtml(metadata.source_url)}" target="_blank" rel="noreferrer">開啟保發中心查詢</a>
  `;
  renderBatchPlan();
  renderPolicyContentExtracts();
}

function versionTimelineKey(policy) {
  if (!policy || policy.origin !== "保發中心") return "";
  return `${policy.company || ""}||${policy.product_name || ""}`;
}

function parseTaiwanDateForSort(value) {
  const match = String(value || "").match(/^(\d{2,3})\/(\d{1,2})\/(\d{1,2})$/);
  if (!match) return Number.MAX_SAFE_INTEGER;
  const year = Number(match[1]) + 1911;
  const month = Number(match[2]);
  const day = Number(match[3]);
  return year * 10000 + month * 100 + day;
}

function buildVersionTimelineMap(policies) {
  const groups = new Map();
  policies
    .filter((policy) => policy.origin === "保發中心" && policy.product_name && policy.company)
    .forEach((policy) => {
      const key = versionTimelineKey(policy);
      if (!key) return;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(policy);
    });

  groups.forEach((items, key) => {
    const unique = new Map();
    items.forEach((item) => {
      const id = item.product_id || item.display_version || item.detail_url;
      if (id && !unique.has(id)) unique.set(id, item);
    });
    const sorted = [...unique.values()].sort((a, b) => {
      const saleDiff = parseTaiwanDateForSort(a.sale_date) - parseTaiwanDateForSort(b.sale_date);
      if (saleDiff) return saleDiff;
      const discontinueDiff =
        parseTaiwanDateForSort(a.discontinued_date) - parseTaiwanDateForSort(b.discontinued_date);
      if (discontinueDiff) return discontinueDiff;
      return String(a.product_id || "").localeCompare(String(b.product_id || ""), "zh-Hant-TW");
    });
    groups.set(key, sorted);
  });
  return groups;
}

function renderVersionTimeline(policy, timelineMap) {
  const key = versionTimelineKey(policy);
  const versions = key ? timelineMap.get(key) || [] : [];
  if (versions.length < 2) return "";
  const visible = versions.slice(0, 8);
  const hiddenCount = Math.max(versions.length - visible.length, 0);
  return `
    <div class="version-timeline" aria-label="同名保單版本時間軸">
      <div class="version-timeline-head">
        <strong>同名版本時間軸</strong>
        <span>${formatNumber.format(versions.length)} 個版本</span>
      </div>
      <ol>
        ${visible
          .map((version) => {
            const isCurrent =
              version.product_id && policy.product_id
                ? version.product_id === policy.product_id
                : version.display_version === policy.display_version;
            return `
              <li class="${isCurrent ? "current" : ""}">
                <span class="timeline-dot"></span>
                <div>
                  <strong>${escapeHtml(version.sale_date || "銷售日未標示")}</strong>
                  <span>停售 ${escapeHtml(version.discontinued_date || "未標示")}</span>
                </div>
              </li>
            `;
          })
          .join("")}
      </ol>
      ${hiddenCount ? `<p>另有 ${formatNumber.format(hiddenCount)} 個較早或較晚版本，請用商品名稱搜尋完整展開。</p>` : ""}
    </div>
  `;
}

function renderBatchPlan() {
  const plan = state.batchPlan;
  const summary = plan.summary;
  const progress = state.batchProgress?.summary || {};
  const processed = progress.policy_url_items_processed || 0;
  const successRate = processed ? Math.round(((progress.policy_url_ok || 0) / processed) * 1000) / 10 : 0;
  const tiiManualCount =
    summary.tii_manual_matrix_batch_count || summary.tii_full_estimated_batch_count || summary.tii_priority_batch_count || 0;
  const completedUrlBatches = progress.completed_policy_url_batches || 0;
  const tiiAttemptedBatches = state.tiiExecutionProgress?.summary?.attempted_batches || 0;
  const tiiCaptchaRequiredBatches = state.tiiExecutionProgress?.summary?.captcha_required_batches || 0;
  const tiiIndexedBatches = state.tiiResults?.indexed_batch_count || state.tiiResults?.indexed_batches?.length || 0;
  const tiiCompletedBatches = state.tiiResults?.completed_batch_count || state.tiiResults?.completed_batches?.length || 0;
  const tiiPendingBatches = Math.max(tiiManualCount - tiiCompletedBatches, 0);
  const tiiImportedPolicies = state.tiiResults?.record_count || state.tiiResults?.records?.length || 0;
  const totalPlanned = summary.policy_url_batch_count + tiiManualCount;
  setText("batchPlanCount", `${formatNumber.format(totalPlanned)} 批次`);
  setText(
    "batchPlanNote",
    `批次分成兩種：${formatNumber.format(summary.policy_url_batch_count)} 個保單 URL 自動批次已執行 ${formatNumber.format(
      completedUrlBatches,
    )} 個；保發中心 TII 另有 ${formatNumber.format(tiiManualCount)} 個人工驗證碼查詢批次，目前已啟動 ${formatNumber.format(
      tiiAttemptedBatches,
    )} 個、等待驗證碼 ${formatNumber.format(tiiCaptchaRequiredBatches)} 個、已索引 ${formatNumber.format(
      tiiIndexedBatches,
    )} 個、完整批次 ${formatNumber.format(
      tiiCompletedBatches,
    )} 個、待人工處理 ${formatNumber.format(tiiPendingBatches)} 個。`,
  );
  document.getElementById("batchSummary").innerHTML = `
    <article>
      <strong>${formatNumber.format(summary.policy_url_batch_count)}</strong>
      <span>保單 URL 自動批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(completedUrlBatches)}</strong>
      <span>已執行 URL 批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiManualCount)}</strong>
      <span>TII 人工批次全量</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiAttemptedBatches)}</strong>
      <span>TII 已啟動批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiCaptchaRequiredBatches)}</strong>
      <span>TII 等待驗證碼</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiIndexedBatches)}</strong>
      <span>TII 已索引批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiCompletedBatches)}</strong>
      <span>TII 完整批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiPendingBatches)}</strong>
      <span>TII 待人工批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(tiiImportedPolicies)}</strong>
      <span>已匯入 TII 保單</span>
    </article>
    <article>
      <strong>${formatNumber.format(processed)}</strong>
      <span>已處理保單 URL</span>
    </article>
    <article>
      <strong>${formatNumber.format(progress.policy_url_ok || 0)}</strong>
      <span>可抓取頁面</span>
    </article>
    <article>
      <strong>${successRate}%</strong>
      <span>可抓取比例</span>
    </article>
    <article>
      <strong>${formatNumber.format(progress.policy_url_robots_blocked || 0)}</strong>
      <span>robots 擋下筆數</span>
    </article>
    <article>
      <strong>${formatNumber.format(progress.policy_url_errors || 0)}</strong>
      <span>錯誤或逾時</span>
    </article>
  `;
  renderTiiMatrix(plan);

  const completed = new Set((state.batchProgress?.batches || []).map((batch) => batch.id));
  const completedRows = (state.batchProgress?.batches || []).slice(-3).reverse().map((batch) => ({
    id: batch.id,
    kind: "已執行",
    title: `${formatNumber.format(batch.item_count)} 筆，${formatNumber.format(batch.robots_blocked)} 筆 robots 擋下`,
    meta: `可抓取 ${formatNumber.format(batch.ok)} 筆｜錯誤 ${formatNumber.format(batch.errors)} 筆｜${batch.ran_at}`,
    priority: "完成",
  }));
  const nextPolicyBatches = plan.policy_url_batches.filter((batch) => !completed.has(batch.id)).slice(0, 2);
  const nextTiiBatches = plan.tii_priority_batches.slice(0, 3);
  const rows = [
    ...completedRows,
    ...nextPolicyBatches.map((batch) => ({
      id: batch.id,
      kind: "保單 URL",
      title: batch.sample_products.join("、"),
      meta: `${formatNumber.format(batch.item_count)} 筆｜${Object.entries(batch.status_mix)
        .map(([label, count]) => `${label} ${count}`)
        .join("、")}`,
      priority: batch.priority === "high" ? "優先" : "一般",
    })),
    ...nextTiiBatches.map((batch) => ({
      id: batch.id,
      kind: "TII 待人工",
      title: `${batch.company_label} / ${batch.category_label}`,
      meta: "人工輸入驗證碼後保存結果，再匯入整理",
      priority: "優先",
    })),
  ];

  document.getElementById("nextBatches").innerHTML = rows
    .map(
      (batch) => `
        <article class="batch-item">
          <div>
            <div class="source-heading">
              <strong>${escapeHtml(batch.id)}</strong>
              <span class="badge">${escapeHtml(batch.kind)}</span>
              <span class="badge ${
                batch.priority === "優先" ? "error" : batch.priority === "完成" ? "ok" : "muted"
              }">${escapeHtml(batch.priority)}</span>
            </div>
            <h3>${escapeHtml(batch.title)}</h3>
            <p>${escapeHtml(batch.meta)}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderTiiMatrix(plan) {
  const container = document.getElementById("tiiMatrix");
  if (!container) return;

  const groups = plan.tii_company_type_groups || [];
  const batches = plan.tii_manual_matrix_batches || [];
  if (!groups.length || !batches.length) {
    container.innerHTML = "";
    return;
  }

  const activeGroup = groups.find((group) => group.key === state.tiiMode) || groups[0];
  state.tiiMode = activeGroup.key;
  const activeBatches = batches.filter((batch) => batch.company_type === activeGroup.key).slice(0, 8);
  const categoryLabels = (activeGroup.insurance_categories || []).map((item) => item.label).join("、");

  container.innerHTML = `
    <div class="tii-matrix-header">
      <div>
        <p class="eyebrow">TII Click-through Matrix</p>
        <h3>產險 / 壽險逐批查詢</h3>
      </div>
      <div class="tii-toggle" role="tablist" aria-label="保發中心公司類別">
        ${groups
          .map(
            (group) => `
              <button type="button" class="${group.key === activeGroup.key ? "active" : ""}" data-tii-mode="${escapeHtml(
                group.key,
              )}" role="tab" aria-selected="${group.key === activeGroup.key}">
                ${escapeHtml(group.short_label)}
              </button>
            `,
          )
          .join("")}
      </div>
    </div>
    <div class="tii-matrix-summary">
      <article>
        <strong>${formatNumber.format(activeGroup.company_count)}</strong>
        <span>${escapeHtml(activeGroup.short_label)}公司</span>
      </article>
      <article>
        <strong>${formatNumber.format(activeGroup.category_count)}</strong>
        <span>保險類別</span>
      </article>
      <article>
        <strong>${formatNumber.format(activeGroup.manual_batch_count)}</strong>
        <span>人工查詢批次</span>
      </article>
    </div>
    <p class="tii-matrix-note">
      ${escapeHtml(activeGroup.label)}會搭配：${escapeHtml(
        categoryLabels,
      )}。下方只是待執行的官方查詢入口；每一批都需要人工輸入驗證碼、保存結果並匯入後，才會算完成。
    </p>
    <div class="tii-matrix-list">
      ${activeBatches
        .map(
          (batch) => `
            <article class="tii-matrix-item">
              <div>
                <div class="source-heading">
                  <strong>${escapeHtml(batch.id)}</strong>
                  <span class="badge">${escapeHtml(batch.company_type_short_label)}</span>
                </div>
                <h4>${escapeHtml(batch.company_label)}</h4>
                <p>${escapeHtml(batch.category_label)}｜categoryId ${escapeHtml(
                  batch.query_hint?.categoryId || "",
                )}｜CompanyID ${escapeHtml(batch.company_code)}｜f_CategoryId1 ${escapeHtml(batch.category_value)}</p>
              </div>
              <a class="button secondary" href="${escapeHtml(batch.source_url)}" target="_blank" rel="noreferrer">開啟查詢頁</a>
            </article>
          `,
        )
        .join("")}
    </div>
  `;

  container.querySelectorAll("[data-tii-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.tiiMode = button.getAttribute("data-tii-mode") || state.tiiMode;
      renderTiiMatrix(plan);
    });
  });
}

function renderPolicyContentExtracts() {
  const data = state.policyContentExtracts;
  const summaryContainer = document.getElementById("contentExtractSummary");
  const fieldContainer = document.getElementById("contentFieldBars");
  const sampleContainer = document.getElementById("contentExtractSamples");
  if (!summaryContainer || !fieldContainer || !sampleContainer) return;

  if (!data?.summary) {
    setText("contentExtractCount", "尚未產生");
    summaryContainer.innerHTML =
      '<div class="empty"><strong>尚未產生內容抽取資料。</strong><span>執行 build_policy_content_extracts.py 後會顯示 PDF/HTML 解析結果。</span></div>';
    fieldContainer.innerHTML = "";
    sampleContainer.innerHTML = "";
    return;
  }

  const summary = data.summary;
  setText("contentExtractCount", `${formatNumber.format(summary.extracted_text_count || 0)} 筆已抽文字`);
  summaryContainer.innerHTML = `
    <article>
      <strong>${formatNumber.format(summary.record_count || 0)}</strong>
      <span>可抓取來源</span>
    </article>
    <article>
      <strong>${formatNumber.format(summary.pdf_record_count || 0)}</strong>
      <span>PDF 已解析</span>
    </article>
    <article>
      <strong>${formatNumber.format(summary.html_record_count || 0)}</strong>
      <span>HTML 已解析</span>
    </article>
    <article>
      <strong>${formatNumber.format(summary.records_with_field_hits || 0)}</strong>
      <span>命中重點欄位</span>
    </article>
    <article>
      <strong>${formatNumber.format(summary.total_text_characters || 0)}</strong>
      <span>抽取字元數</span>
    </article>
  `;

  fieldContainer.innerHTML = barRows(summary.field_counts || [], { className: "status-fill" });

  const samples = (data.records || [])
    .filter((record) => record.extraction_status === "extracted")
    .sort((a, b) => {
      const fieldDiff = (b.field_hits || []).length - (a.field_hits || []).length;
      if (fieldDiff) return fieldDiff;
      return (b.text_char_count || 0) - (a.text_char_count || 0);
    })
    .slice(0, 8);

  sampleContainer.innerHTML = samples
    .map(
      (record) => `
        <article class="content-sample">
          <div>
            <div class="source-heading">
              <strong>${escapeHtml(record.company)}</strong>
              <span class="badge">${escapeHtml(record.document_kind?.toUpperCase() || "DOC")}</span>
              <span class="badge ok">${formatNumber.format(record.text_char_count || 0)} 字</span>
            </div>
            <h3>${escapeHtml(record.product_name)}</h3>
            <p>${escapeHtml(record.product_type)}｜解析 ${escapeHtml(record.pages_parsed || 0)} ${
              record.document_kind === "pdf" ? "頁" : "頁面"
            }${record.page_count ? ` / 共 ${escapeHtml(record.page_count)} 頁` : ""}</p>
            <div class="policy-flags">
              ${(record.field_hits || []).map((field) => `<span class="chip">${escapeHtml(field)}</span>`).join("")}
            </div>
            ${
              record.matched_terms?.length
                ? `<p class="matched-terms">命中詞：${escapeHtml(record.matched_terms.slice(0, 8).join("、"))}</p>`
                : ""
            }
          </div>
          <a class="button secondary" href="${escapeHtml(record.policy_url)}" target="_blank" rel="noreferrer">官方來源</a>
        </article>
      `,
    )
    .join("");
}

function focusByKey(record, key) {
  return (record.reader_focus || []).find((item) => item.key === key);
}

function pageText(pages) {
  if (!pages?.length) return "頁碼待複核";
  return `p. ${pages.slice(0, 4).join("、")}${pages.length > 4 ? "…" : ""}`;
}

function policySourceMeta(record) {
  const docKind = String(record.document_kind || "doc").toUpperCase();
  const parsedUnit = record.document_kind === "pdf" ? "頁" : "頁面";
  const totalPages = record.page_count ? ` / 共 ${formatNumber.format(record.page_count)} 頁` : "";
  return `${docKind}｜解析 ${formatNumber.format(record.pages_parsed || 0)} ${parsedUnit}${totalPages}｜${formatNumber.format(
    record.text_char_count || 0,
  )} 字`;
}

function focusStatusBadge(card) {
  if (!card || card.status !== "detected") return '<span class="focus-status muted">待複核</span>';
  return '<span class="focus-status ok">已命中</span>';
}

function renderFocusCard(record, key) {
  const card = focusByKey(record, key);
  const terms = card?.terms || [];
  const summary = card?.summary || "未在已解析頁面命中，請回官方條款確認。";
  return `
    <article class="policy-focus-card ${card?.status === "detected" ? "detected" : "missing"}">
      <div class="policy-focus-head">
        <strong>${escapeHtml(card?.label || key)}</strong>
        ${focusStatusBadge(card)}
      </div>
      <p>${escapeHtml(summary)}</p>
      <div class="policy-focus-terms">
        ${
          terms.length
            ? terms.slice(0, 7).map((term) => `<span class="chip">${escapeHtml(term)}</span>`).join("")
            : '<span class="chip muted">需官方複核</span>'
        }
      </div>
      <small>${escapeHtml(pageText(card?.pages))}</small>
    </article>
  `;
}

function policySearchText(record) {
  const focusText = (record.reader_focus || [])
    .flatMap((item) => [item.label, item.reader_question, item.summary, ...(item.terms || [])])
    .join(" ");
  return normalize(
    [
      record.company,
      record.product_name,
      record.product_type,
      record.sale_status,
      record.document_kind,
      record.policy_url,
      ...(record.field_hits || []),
      ...(record.matched_terms || []),
      focusText,
    ].join(" "),
  );
}

function passesPolicyFocus(record) {
  if (state.crawl === "all") return true;
  if (state.crawl === "complete") return (record.focus_score || 0) >= 4;
  if (state.crawl === "special") return focusByKey(record, "special")?.status === "detected";
  if (state.crawl === "needs_review") return (record.focus_score || 0) < 4;
  return true;
}

function filteredPolicyRecords() {
  const query = normalize(state.search);
  return (state.policyContentExtracts?.records || [])
    .filter((record) => {
      if (state.company !== "all" && record.company !== state.company) return false;
      if (state.kind !== "all" && (record.product_type || "其他") !== state.kind) return false;
      if (!passesPolicyFocus(record)) return false;
      if (!query) return true;
      return matchesQuery(policySearchText(record), query);
    })
    .sort((a, b) => {
      const scoreDiff = (b.focus_score || 0) - (a.focus_score || 0);
      if (scoreDiff) return scoreDiff;
      const hitDiff = (b.field_hits || []).length - (a.field_hits || []).length;
      if (hitDiff) return hitDiff;
      const textDiff = (b.text_char_count || 0) - (a.text_char_count || 0);
      if (textDiff) return textDiff;
      const companyDiff = String(a.company || "").localeCompare(String(b.company || ""), "zh-Hant-TW");
      if (companyDiff) return companyDiff;
      return String(a.product_name || "").localeCompare(String(b.product_name || ""), "zh-Hant-TW");
    });
}

function renderPolicyResultSummary(rowCount) {
  const summary = state.policyContentExtracts?.summary || {};
  const filterParts = [];
  if (state.search) filterParts.push(`關鍵字「${state.search}」`);
  if (state.company !== "all") filterParts.push(state.company);
  if (state.kind !== "all") filterParts.push(state.kind);
  if (state.crawl !== "all") filterParts.push(policyFocusLabels[state.crawl]);
  const activeText = filterParts.length ? `條件：${filterParts.join(" / ")}。` : "條件：全部已解析保單。";
  setText(
    "resultSummary",
    `${activeText} 顯示 ${formatNumber.format(rowCount)} 張快讀卡；目前已解析 ${formatNumber.format(
      summary.extracted_text_count || 0,
    )} 張保單，${formatNumber.format(summary.records_with_field_hits || 0)} 張命中重點欄位。`,
  );
}

function renderPolicyCard(record) {
  const focusCards = focusOrder.map((key) => renderFocusCard(record, key)).join("");
  const scoreText = `${formatNumber.format(record.focus_score || 0)}/4 重點`;
  const matchedTerms = record.matched_terms?.length
    ? record.matched_terms.slice(0, 12).map((term) => `<span class="chip">${escapeHtml(term)}</span>`).join("")
    : '<span class="chip muted">尚無命中詞</span>';
  return `
    <article class="policy-card">
      <div class="policy-card-main">
        <div class="policy-card-kicker">
          <strong>${escapeHtml(record.company)}</strong>
          <span class="badge">${escapeHtml(record.product_type || "其他")}</span>
          <span class="badge ok">${escapeHtml(record.sale_status || "狀態待確認")}</span>
          <span class="badge">${escapeHtml(scoreText)}</span>
        </div>
        <h3>${escapeHtml(record.product_name)}</h3>
        <p class="policy-card-meta">${escapeHtml(policySourceMeta(record))}</p>
        <div class="policy-focus-grid">${focusCards}</div>
        <details class="policy-detail">
          <summary>查看命中詞與來源資料</summary>
          <div class="policy-detail-body">
            <div>
              <strong>命中詞</strong>
              <div class="chips">${matchedTerms}</div>
            </div>
            <dl>
              <div><dt>來源類型</dt><dd>${escapeHtml(record.document_kind?.toUpperCase() || "DOC")}</dd></div>
              <div><dt>解析頁數</dt><dd>${escapeHtml(record.pages_parsed || 0)}${record.page_count ? ` / ${escapeHtml(record.page_count)}` : ""}</dd></div>
              <div><dt>資料信心</dt><dd>${escapeHtml(record.confidence || "parsed")}</dd></div>
              <div><dt>更新時間</dt><dd>${escapeHtml(record.extracted_at || "n/a")}</dd></div>
            </dl>
          </div>
        </details>
      </div>
      <div class="policy-card-actions">
        <a class="button primary" href="${escapeHtml(record.policy_url)}" target="_blank" rel="noreferrer">官方來源</a>
      </div>
    </article>
  `;
}

function renderPolicyCards() {
  const rows = filteredPolicyRecords();
  const container = document.getElementById("policyList");
  const totalPages = Math.max(Math.ceil(rows.length / state.policyPageSize), 1);
  state.policyPage = clampPage(state.policyPage, totalPages);
  const startIndex = (state.policyPage - 1) * state.policyPageSize;
  const visibleRows = rows.slice(startIndex, startIndex + state.policyPageSize);
  setText("policyResultCount", `${formatNumber.format(rows.length)} 張 / ${formatNumber.format(totalPages)} 頁`);
  renderPolicyResultSummary(rows.length);
  syncControls();

  if (!rows.length) {
    container.innerHTML =
      '<div class="empty"><strong>找不到符合條件的保單。</strong><span>請改用公司、商品、住院、手術、等待期或除外責任等關鍵字。</span></div>';
    return;
  }

  const pager = paginationHtml("policy", rows.length, state.policyPage, state.policyPageSize, POLICY_PAGE_SIZES);
  container.innerHTML = `${pager}${visibleRows.map(renderPolicyCard).join("")}${totalPages > 1 ? pager : ""}`;
}

function passesCrawlFilter(item) {
  if (state.crawl === "all") return true;
  const result = state.crawlByUrlId.get(item.id);
  if (state.crawl === "unchecked") return !result;
  if (!result) return false;
  if (state.crawl === "ok") return Boolean(result.ok);
  if (state.crawl === "blocked") return result.robots_allowed === false;
  if (state.crawl === "error") return result.robots_allowed !== false && !result.ok;
  return true;
}

function resultSortScore(item) {
  const result = state.crawlByUrlId.get(item.id);
  const statusScore = result?.ok ? 0 : result?.robots_allowed === false ? 2 : result ? 3 : 4;
  const kindScore = {
    product_page: 0,
    pdf_or_file: 1,
    web_page: 2,
    law_source: 3,
    social_insurance: 3,
    local_file: 5,
    private_document: 5,
    unsupported: 6,
  }[item.kind] ?? 4;
  return statusScore * 10 + kindScore;
}

function filteredUrls() {
  const query = normalize(state.search);
  return state.sourceIndex.urls
    .filter((item) => {
      if (state.company !== "all" && item.company !== state.company) return false;
      if (!query) return true;
      const result = state.crawlByUrlId.get(item.id);
      return matchesQuery(
        [
          item.company,
          item.domain,
          item.kind,
          kindLabel(item.kind),
          item.source_file_title,
          item.source_label,
          item.url,
          result?.title,
          result?.content_type,
        ].join(" "),
        query,
      );
    })
    .sort((a, b) => {
      const scoreDiff = resultSortScore(a) - resultSortScore(b);
      if (scoreDiff) return scoreDiff;
      const companyDiff = a.company.localeCompare(b.company, "zh-Hant-TW");
      if (companyDiff) return companyDiff;
      return a.id.localeCompare(b.id);
    });
}

function sourceTitle(item, result) {
  if (result?.title) return result.title;
  if (item.source_label) return item.source_label;
  return `${item.company} ${kindLabel(item.kind)}來源`;
}

function formatBytes(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return "n/a";
  if (number >= 1024 * 1024) return `${(number / 1024 / 1024).toFixed(1)} MB`;
  if (number >= 1024) return `${Math.round(number / 1024)} KB`;
  return `${number} B`;
}

function renderResultSummary(rowCount) {
  const summary = state.crawlStatus.summary;
  const filterParts = [];
  if (state.search) filterParts.push(`關鍵字「${state.search}」`);
  if (state.company !== "all") filterParts.push(state.company);
  const activeText = filterParts.length ? `來源清冊同步條件：${filterParts.join(" / ")}。` : "來源清冊同步條件：全部來源。";

  setText(
    "sourceResultSummary",
    `${activeText} 顯示 ${formatNumber.format(rowCount)} 筆；目前收錄 ${formatNumber.format(
      state.sourceIndex.total_unique_url_count,
    )} 筆來源，${formatNumber.format(summary.ok)} 筆可開啟。`,
  );
}

function renderSourceCard(item) {
  const result = state.crawlByUrlId.get(item.id);
  const status = crawlLabel(result);
  const isPublic = item.should_crawl ? "公開候選" : "不列入公開爬取";
  const detailsOpen = state.openSourceId === item.id ? " open" : "";
  return `
    <article class="source-item" id="source-${escapeHtml(item.id)}">
      <div class="source-main">
        <div class="source-heading">
          <strong>${escapeHtml(item.company)}</strong>
          <span class="badge ${status.className}">${escapeHtml(status.label)}</span>
        </div>
        <h3>${escapeHtml(sourceTitle(item, result))}</h3>
        <div class="source-badges">
          <span class="badge">${escapeHtml(kindLabel(item.kind))}</span>
          <span class="badge">${escapeHtml(isPublic)}</span>
          <span class="badge muted">${escapeHtml(item.domain)}</span>
        </div>
        <p class="source-purpose">${escapeHtml(kindPurpose(item.kind))}</p>
        <details class="source-details"${detailsOpen}>
          <summary>來源資訊</summary>
          <dl>
            <div><dt>原始連結</dt><dd><a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a></dd></div>
            <div><dt>來源文件</dt><dd>${escapeHtml(item.source_file_title)}</dd></div>
            <div><dt>來源 ID</dt><dd>${escapeHtml(item.id)}</dd></div>
            <div><dt>HTTP</dt><dd>${result ? escapeHtml(result.status ?? "n/a") : "尚未檢查"}</dd></div>
            <div><dt>內容類型</dt><dd>${escapeHtml(result?.content_type || "n/a")}</dd></div>
            <div><dt>大小</dt><dd>${escapeHtml(formatBytes(result?.content_length))}</dd></div>
            <div><dt>檢查時間</dt><dd>${escapeHtml(result?.checked_at || "尚未檢查")}</dd></div>
            <div><dt>狀態說明</dt><dd>${escapeHtml(status.note)}</dd></div>
          </dl>
        </details>
      </div>
      <div class="source-actions">
        <a class="button primary source-open" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">開啟來源</a>
        <button class="button ghost copy-link" type="button" data-url="${escapeHtml(item.url)}">複製連結</button>
      </div>
    </article>
  `;
}

function renderSources(options = {}) {
  const rows = filteredUrls();
  const container = document.getElementById("sourceList");
  setText("resultCount", `${formatNumber.format(rows.length)} 筆`);
  if (document.getElementById("sourceResultSummary")) renderResultSummary(rows.length);

  if (!rows.length) {
    container.innerHTML =
      '<div class="empty"><strong>找不到符合條件的來源。</strong><span>請改用保險公司名稱、商品關鍵字或較短的 PDF/網域片段。</span></div>';
    return;
  }

  container.innerHTML = rows.slice(0, 120).map(renderSourceCard).join("");

  if (rows.length > 120) {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="empty"><strong>目前先顯示前 120 筆。</strong><span>請用查詢或篩選縮小範圍；符合條件共 ${formatNumber.format(rows.length)} 筆。</span></div>`,
    );
  }

  if (options.scroll) document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function shouldAutoLoadTiiIndex() {
  return Boolean(state.search || state.company !== "all" || state.kind !== "all");
}

async function refreshTiiDiscontinuedForFilters() {
  renderDiscontinuedList();
  if (state.tiiIndexRecords || !shouldAutoLoadTiiIndex()) return;
  try {
    const loadPromise = ensureTiiIndexLoaded();
    renderDiscontinuedList();
    await loadPromise;
    renderDiscontinuedList();
  } catch (error) {
    document.getElementById("discontinuedList").insertAdjacentHTML(
      "beforeend",
      `<div class="empty"><strong>TII 索引載入失敗。</strong><span>${escapeHtml(error.message)}</span></div>`,
    );
  }
}

function runSearch(options = {}) {
  state.openSourceId = null;
  state.search = document.getElementById("searchInput").value.trim();
  renderPolicyCards();
  renderSources(options);
  refreshTiiDiscontinuedForFilters();
  updateUrl();
}

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    const original = button.textContent;
    button.textContent = "已複製";
    setTimeout(() => {
      button.textContent = original;
    }, 1400);
  } catch {
    window.prompt("複製這個連結", text);
  }
}

function resetFilters() {
  Object.assign(state, DEFAULT_FILTERS);
  state.openSourceId = null;
  state.policyPage = 1;
  syncControls();
  renderPolicyCards();
  renderSources();
  renderDiscontinuedList();
  updateUrl();
  document.getElementById("searchInput").focus();
}

function rerenderPortfolioSuggestions() {
  const query = document.getElementById("portfolioInput").value.trim();
  renderPortfolioSuggestions(state.portfolioSuggestions, query);
}

function setPortfolioSuggestionPage(page) {
  const totalPages = Math.max(Math.ceil(state.portfolioSuggestions.length / state.portfolioSuggestionPageSize), 1);
  state.portfolioSuggestionPage = clampPage(page, totalPages);
  rerenderPortfolioSuggestions();
}

function setPortfolioSuggestionPageSize(pageSize) {
  state.portfolioSuggestionPageSize = PORTFOLIO_PAGE_SIZES.includes(Number(pageSize))
    ? Number(pageSize)
    : state.portfolioSuggestionPageSize;
  state.portfolioSuggestionPage = 1;
  rerenderPortfolioSuggestions();
}

function setPolicyPage(page) {
  const totalPages = Math.max(Math.ceil(filteredPolicyRecords().length / state.policyPageSize), 1);
  state.policyPage = clampPage(page, totalPages);
  renderPolicyCards();
}

function setPolicyPageSize(pageSize) {
  state.policyPageSize = POLICY_PAGE_SIZES.includes(Number(pageSize)) ? Number(pageSize) : state.policyPageSize;
  state.policyPage = 1;
  renderPolicyCards();
}

function savePortfolioEdits(form) {
  const itemId = form.dataset.portfolioEditForm;
  const current = state.portfolioItems.find((item) => item.id === itemId);
  if (!current) return false;
  const selection = readPortfolioSelection(form, current);
  if (!selection) return false;
  const updated = {
    ...current,
    ...selection,
    coverage_entries: normalizeCoverageEntries(current.coverage_entries),
  };
  state.portfolioItems = state.portfolioItems.map((item) => (item.id === itemId ? updated : item));
  state.editingPortfolioId = null;
  savePortfolioItems();
  renderPortfolio();
  setText("portfolioHint", `已更新「${updated.product_name}」的投保資料。`);
  return true;
}

function updatePortfolioCompanyFilter(value) {
  state.portfolioCompany = String(value || "").trim() || "all";
  state.portfolioDetailItem = null;
  state.portfolioSuggestionPage = 1;
  renderPortfolioDetail(null);
  const query = document.getElementById("portfolioInput").value.trim();
  if (query) runPortfolioSearch(query);
}

function bindEvents() {
  document.getElementById("portfolioForm").addEventListener("submit", (event) => {
    event.preventDefault();
    window.clearTimeout(portfolioCompanyFilterTimer);
    state.portfolioCompany = document.getElementById("portfolioCompanyFilter").value.trim() || "all";
    state.portfolioSuggestionPage = 1;
    runPortfolioSearch(document.getElementById("portfolioInput").value);
  });

  document.getElementById("clearPortfolio").addEventListener("click", clearPortfolio);

  document.getElementById("portfolioQuickAdds").addEventListener("click", (event) => {
    const button = event.target.closest("[data-portfolio-query]");
    if (!button) return;
    state.portfolioSuggestionPage = 1;
    document.getElementById("portfolioInput").value = button.dataset.portfolioQuery;
    runPortfolioSearch(button.dataset.portfolioQuery);
  });

  document.getElementById("portfolioCompanyFilter").addEventListener("input", (event) => {
    window.clearTimeout(portfolioCompanyFilterTimer);
    portfolioCompanyFilterTimer = window.setTimeout(() => updatePortfolioCompanyFilter(event.target.value), 250);
  });

  document.getElementById("portfolioBucketFilter").addEventListener("change", (event) => {
    state.portfolioBucket = event.target.value;
    state.portfolioDetailItem = null;
    state.portfolioSuggestionPage = 1;
    renderPortfolioDetail(null);
    const query = document.getElementById("portfolioInput").value.trim();
    if (query) runPortfolioSearch(query);
  });

  document.getElementById("portfolioSuggestions").addEventListener("click", async (event) => {
    const pageButton = event.target.closest("[data-page-action='portfolio']");
    if (pageButton) {
      setPortfolioSuggestionPage(pageButton.dataset.pageTarget);
      return;
    }
    const button = event.target.closest("[data-view-suggestion]");
    if (!button) return;
    const item = state.portfolioSuggestions[Number(button.dataset.viewSuggestion)];
    if (!item) return;
    await openPortfolioDetail(item);
    document.getElementById("portfolioDetail").scrollIntoView({ behavior: "smooth", block: "start" });
    setText("portfolioHint", `正在查看「${item.product_name}」的保障與金額。確認後可加入集合。`);
  });

  document.getElementById("portfolioSuggestions").addEventListener("change", (event) => {
    if (event.target.matches("[data-page-select='portfolio']")) {
      setPortfolioSuggestionPage(event.target.value);
      return;
    }
    if (event.target.matches("[data-page-size='portfolio']")) {
      setPortfolioSuggestionPageSize(event.target.value);
    }
  });

  document.getElementById("portfolioDetail").addEventListener("click", (event) => {
    const closeButton = event.target.closest("[data-close-portfolio-detail]");
    if (closeButton) {
      renderPortfolioDetail(null);
      return;
    }
    const addButton = event.target.closest("[data-confirm-add-portfolio]");
    if (!addButton || !state.portfolioDetailItem) return;
    const detailContainer = document.getElementById("portfolioDetail");
    const selection = readPortfolioSelection(detailContainer, state.portfolioDetailItem);
    if (!selection) return;
    const item = { ...state.portfolioDetailItem, ...selection };
    const result = addPortfolioItem(item);
    renderPortfolioDetail(item);
    setText(
      "portfolioHint",
      result === "added"
        ? `已加入「${item.product_name}」，${portfolioSelectionText(item)}。`
        : `已更新「${item.product_name}」為 ${portfolioSelectionText(item)}。`,
    );
    document.querySelector(".portfolio-layout")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  document.getElementById("portfolioDetail").addEventListener("change", (event) => {
    if (event.target.matches("[data-selection-mode]")) {
      syncPortfolioSelectionFields(event.target.closest("[data-selection-fields]"));
      return;
    }
    if (!state.portfolioDetailItem) return;
    if (event.target.matches("[data-selection-plan]")) {
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        plan_name: String(event.target.value || "").trim(),
      };
      renderPortfolioDetail(state.portfolioDetailItem);
      return;
    }
    if (event.target.matches("[data-selection-unit]")) {
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        unit_count: normalizeUnitCount(event.target.value),
      };
      renderPortfolioDetail(state.portfolioDetailItem);
      return;
    }
    if (event.target.matches("[data-selection-unit-key]")) {
      const key = event.target.dataset.selectionUnitKey;
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        unit_counts: {
          ...(state.portfolioDetailItem.unit_counts || {}),
          [key]: normalizeUnitCount(event.target.value),
        },
      };
      renderPortfolioDetail(state.portfolioDetailItem);
      return;
    }
    if (event.target.matches("[data-selection-face-amount]")) {
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        face_amount: normalizeCoverageAmount(
          event.target.value,
          state.portfolioDetailItem,
        ),
      };
      renderPortfolioDetail(state.portfolioDetailItem);
      return;
    }
    if (event.target.matches("[data-selection-account-value]")) {
      const accountValue = normalizeCoverageAmount(
        event.target.value,
        state.portfolioDetailItem,
      );
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        account_value: accountValue,
        policy_state: {
          ...(state.portfolioDetailItem.policy_state || {}),
          policy_account_value: accountValue,
        },
      };
      refreshPortfolioBenefitPreview();
      return;
    }
    if (event.target.matches("[data-policy-state-key]")) {
      const key = event.target.dataset.policyStateKey;
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        policy_state: policyStateWithFieldUpdate(
          state.portfolioDetailItem,
          key,
          event.target.type === "checkbox"
            ? event.target.checked
          : String(event.target.value || "").trim(),
        ),
      };
      syncPolicyStateConfirmationControl(
        event.currentTarget,
        state.portfolioDetailItem,
        key,
      );
      if (
        key === "death_benefit_status" ||
        key === "investment_allocation_status" ||
        key === "injury_medical_rider_status" ||
        key === "prior_same_insurer_major_burn_claim_status" ||
        key === "disability_support_claim_status" ||
        key === "prior_disability_status"
      ) {
        renderPortfolioDetail(state.portfolioDetailItem);
        return;
      }
      refreshPortfolioBenefitPreview();
    }
  });

  document.getElementById("portfolioDetail").addEventListener("input", (event) => {
    if (!state.portfolioDetailItem) return;
    if (event.target.matches("[data-selection-unit]")) {
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        unit_count: normalizeUnitCount(event.target.value),
      };
      refreshPortfolioBenefitPreview();
      return;
    }
    if (event.target.matches("[data-selection-unit-key]")) {
      const key = event.target.dataset.selectionUnitKey;
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        unit_counts: {
          ...(state.portfolioDetailItem.unit_counts || {}),
          [key]: normalizeUnitCount(event.target.value),
        },
      };
      refreshPortfolioBenefitPreview();
      return;
    }
    if (event.target.matches("[data-selection-face-amount]")) {
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        face_amount: normalizeCoverageAmount(
          event.target.value,
          state.portfolioDetailItem,
        ),
      };
      refreshPortfolioBenefitPreview();
      return;
    }
    if (event.target.matches("[data-selection-account-value]")) {
      const accountValue = normalizeCoverageAmount(
        event.target.value,
        state.portfolioDetailItem,
      );
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        account_value: accountValue,
        policy_state: {
          ...(state.portfolioDetailItem.policy_state || {}),
          policy_account_value: accountValue,
        },
      };
      refreshPortfolioBenefitPreview();
      return;
    }
    if (event.target.matches("[data-policy-state-key]")) {
      const key = event.target.dataset.policyStateKey;
      state.portfolioDetailItem = {
        ...state.portfolioDetailItem,
        policy_state: policyStateWithFieldUpdate(
          state.portfolioDetailItem,
          key,
          event.target.type === "checkbox"
            ? event.target.checked
          : String(event.target.value || "").trim(),
        ),
      };
      syncPolicyStateConfirmationControl(
        event.currentTarget,
        state.portfolioDetailItem,
        key,
      );
      refreshPortfolioBenefitPreview();
    }
  });

  document.getElementById("portfolioList").addEventListener("click", (event) => {
    const editButton = event.target.closest("[data-edit-portfolio]");
    if (editButton) {
      state.editingPortfolioId = editButton.dataset.editPortfolio;
      renderPortfolioList();
      document.querySelector(`[data-portfolio-edit-form="${CSS.escape(state.editingPortfolioId)}"]`)?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
      return;
    }
    if (event.target.closest("[data-cancel-portfolio-edit]")) {
      state.editingPortfolioId = null;
      renderPortfolioList();
      return;
    }
    const removeButton = event.target.closest("[data-remove-portfolio]");
    if (!removeButton) return;
    removePortfolioItem(removeButton.dataset.removePortfolio);
    setText("portfolioHint", "已從集合移除。");
  });

  document.getElementById("portfolioList").addEventListener("submit", (event) => {
    const form = event.target.closest("[data-portfolio-edit-form]");
    if (!form) return;
    event.preventDefault();
    savePortfolioEdits(form);
  });

  document.getElementById("portfolioList").addEventListener("change", (event) => {
    if (!event.target.matches("[data-selection-mode]")) return;
    syncPortfolioSelectionFields(event.target.closest("[data-selection-fields]"));
  });

  document.getElementById("searchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    state.policyPage = 1;
    runSearch();
  });

  document.getElementById("clearFilters").addEventListener("click", resetFilters);

  document.getElementById("companyFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.company = event.target.value;
    state.policyPage = 1;
    renderPolicyCards();
    renderSources();
    refreshTiiDiscontinuedForFilters();
    updateUrl();
  });

  document.getElementById("kindFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.kind = event.target.value;
    state.policyPage = 1;
    renderPolicyCards();
    renderSources();
    refreshTiiDiscontinuedForFilters();
    updateUrl();
  });

  document.getElementById("crawlFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.crawl = event.target.value;
    state.policyPage = 1;
    renderPolicyCards();
    renderSources();
    renderDiscontinuedList();
    updateUrl();
  });

  document.querySelector(".status-chips").addEventListener("click", (event) => {
    const button = event.target.closest("[data-crawl]");
    if (!button) return;
    state.openSourceId = null;
    state.crawl = button.dataset.crawl;
    state.policyPage = 1;
    renderPolicyCards();
    renderSources();
    renderDiscontinuedList();
    updateUrl();
  });

  document.getElementById("sourceList").addEventListener("click", (event) => {
    const button = event.target.closest(".copy-link");
    if (!button) return;
    copyText(button.dataset.url, button);
  });

  document.getElementById("policyList").addEventListener("click", (event) => {
    const pageButton = event.target.closest("[data-page-action='policy']");
    if (!pageButton) return;
    setPolicyPage(pageButton.dataset.pageTarget);
  });

  document.getElementById("policyList").addEventListener("change", (event) => {
    if (event.target.matches("[data-page-select='policy']")) {
      setPolicyPage(event.target.value);
      return;
    }
    if (event.target.matches("[data-page-size='policy']")) {
      setPolicyPageSize(event.target.value);
    }
  });

  document.getElementById("discontinuedList").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-load-tii-index]");
    if (!button) return;
    button.disabled = true;
    try {
      const loadPromise = ensureTiiIndexLoaded();
      renderDiscontinuedList();
      await loadPromise;
      renderDiscontinuedList();
    } catch (error) {
      document.getElementById("discontinuedList").insertAdjacentHTML(
        "beforeend",
        `<div class="empty"><strong>TII 索引載入失敗。</strong><span>${escapeHtml(error.message)}</span></div>`,
      );
    }
  });
}

async function main() {
  await loadSiteSummary();
  try {
    await loadData();
    populateFilters();
    loadFiltersFromUrl();
    renderMetrics();
    renderPolicyInsights();
    renderTaxonomy();
    renderDomainChart();
    loadPortfolioItems();
    await refreshSavedTiiPortfolioItems();
    populatePortfolioFilters();
    renderPortfolio();
    renderPolicyCards();
    renderSources();
    bindEvents();
    if (shouldAutoLoadTiiIndex()) refreshTiiDiscontinuedForFilters();
  } catch (error) {
    document.querySelector("main").innerHTML = `
      <section class="notice">
        <strong>資料載入失敗</strong>
        <p>${escapeHtml(error.message)}</p>
      </section>
    `;
  }
}

main();

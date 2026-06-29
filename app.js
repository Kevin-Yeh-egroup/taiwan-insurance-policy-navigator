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
  portfolioCompany: "all",
  portfolioBucket: "all",
};

const formatNumber = new Intl.NumberFormat("zh-Hant-TW");
const PORTFOLIO_STORAGE_KEY = "taiwanPolicyNavigator.portfolio.v1";

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

const coverageBuckets = [
  {
    id: "life",
    label: "壽險",
    summary: "身故、完全失能、壽險主約或投資型壽險。",
    categories: ["傳統型壽險", "投資型壽險"],
    keywords: ["壽險", "身故", "死亡", "完全失能", "生死合險", "定期壽", "終身壽", "投資型壽險"],
  },
  {
    id: "medical",
    label: "醫療險",
    summary: "住院、手術、實支實付、日額、門診或健康醫療。",
    categories: ["健康保險"],
    keywords: ["醫療", "健康", "住院", "手術", "實支", "日額", "門診", "病房", "雜費", "住院醫療"],
  },
  {
    id: "accident",
    label: "意外險",
    summary: "傷害、意外、平安、燒燙傷、骨折或意外失能。",
    categories: ["傷害保險", "意外保險"],
    keywords: ["傷害", "意外", "平安", "燒燙傷", "骨折", "意外失能", "旅行平安"],
  },
  {
    id: "cancer",
    label: "癌症險",
    summary: "癌症、惡性腫瘤、防癌或癌症醫療給付。",
    categories: [],
    keywords: ["癌", "癌症", "防癌", "抗癌", "惡性腫瘤", "原位癌", "初期癌"],
  },
  {
    id: "critical",
    label: "重大疾病險",
    summary: "重大疾病、重大傷病、特定傷病或一次金保障。",
    categories: [],
    keywords: ["重大疾病", "重大傷病", "特定傷病", "重大疾", "心肌梗塞", "腦中風", "癱瘓", "洗腎", "冠狀動脈"],
  },
  {
    id: "longterm",
    label: "長照險",
    summary: "長期照顧、失智、認知功能障礙或長期看護。",
    categories: [],
    keywords: ["長期照顧", "長照", "長期看護", "失智", "認知功能障礙", "照護", "扶助"],
  },
  {
    id: "annuity",
    label: "年金/退休",
    summary: "年金、退休、生存金或長期現金流安排。",
    categories: ["傳統型年金", "投資型年金"],
    keywords: ["年金", "退休", "生存金", "養老", "即期年金", "利率變動型年金"],
  },
];

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
      ? saved.filter((item) => item?.product_name).map((item) => ({ ...item, id: portfolioItemId(item) }))
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
  const companySelect = document.getElementById("portfolioCompanyFilter");
  const localCompanies = (state.policyContentExtracts?.records || []).map((item) => item.company).filter(Boolean);
  const tiiCompanies = (state.tiiManifest?.company_counts || []).map((item) => item.company).filter(Boolean);
  const companies = [...new Set([...tiiCompanies, ...localCompanies])].sort((a, b) => a.localeCompare(b, "zh-Hant-TW"));
  companySelect.innerHTML = [
    '<option value="all">全部公司</option>',
    ...companies.map((company) => `<option value="${escapeHtml(company)}">${escapeHtml(company)}</option>`),
  ].join("");
  companySelect.value = state.portfolioCompany;
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
  if (selectedCompany === "all") return true;
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
      item.product_id || "no-product-id",
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
    })
    .slice(0, 18);
}

function detectCoverageBuckets(item) {
  const text = coverageDetectionText(item);
  const category = normalize(item.product_type);
  return coverageBuckets
    .map((bucket) => {
      const categoryMatched = (bucket.categories || []).some((itemCategory) => category === normalize(itemCategory));
      const matchedKeywords = bucket.keywords.filter((keyword) => text.includes(normalize(keyword)));
      const isMatched = categoryMatched || matchedKeywords.length > 0;
      return isMatched ? { ...bucket, matchedKeywords } : null;
    })
    .filter(Boolean);
}

function coverageBadgeHtml(item) {
  const buckets = detectCoverageBuckets(item);
  if (!buckets.length) return '<span class="chip muted">待分類</span>';
  return buckets.map((bucket) => `<span class="chip">${escapeHtml(bucket.label)}</span>`).join("");
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
  const normalizedItem = { ...item, id: item.id || portfolioItemId(item) };
  const exists = state.portfolioItems.some((current) => current.id === normalizedItem.id);
  if (!exists) {
    state.portfolioItems = [...state.portfolioItems, normalizedItem];
    savePortfolioItems();
  }
  renderPortfolio();
  return !exists;
}

function removePortfolioItem(id) {
  state.portfolioItems = state.portfolioItems.filter((item) => item.id !== id);
  savePortfolioItems();
  renderPortfolio();
}

function clearPortfolio() {
  state.portfolioItems = [];
  state.portfolioSuggestions = [];
  state.portfolioDetailItem = null;
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
  container.innerHTML = `
    <div class="suggestion-heading">
      <strong>找到 ${formatNumber.format(matches.length)} 個候選</strong>
      <span>請選擇要加入集合的保單。</span>
    </div>
    <div class="suggestion-list">
      ${matches
        .slice(0, 8)
        .map(
          (item, index) => `
            <article class="suggestion-item">
              <div>
                <strong class="policy-title-line">${policyTitleHtml(item)}</strong>
                <div class="policy-meta">
                  <span>${escapeHtml(item.company)}</span>
                  <span>${escapeHtml(item.product_type)}</span>
                  ${identityMetaHtml(item)}
                </div>
                <div class="policy-flags">${coverageBadgeHtml(item)}</div>
              </div>
              <button class="button secondary" type="button" data-view-suggestion="${index}">查看摘要</button>
            </article>
          `,
        )
        .join("")}
    </div>
    ${
      matches.length > 8
        ? `<p class="result-summary">「${escapeHtml(query)}」還有更多候選，請用公司或完整名稱縮小範圍。</p>`
        : ""
    }
  `;
}

function focusByKeyForPortfolio(item, key) {
  return (item.reader_focus || []).find((focus) => focus.key === key);
}

function coverageSummaryForItem(item) {
  const buckets = detectCoverageBuckets(item).map((bucket) => bucket.label);
  if (buckets.length) return `系統依商品名稱與險種判斷，這張保單可能對應 ${buckets.join("、")}。`;
  if (item.product_type && item.product_type !== "待分類") return `目前可確認的險種為 ${item.product_type}。`;
  return "目前先保留為待分類項目，建議用完整保單名稱或公司再查一次。";
}

function focusSummaryHtml(item) {
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
        <p>${escapeHtml(focus?.summary || "目前沒有已解析條款摘要；可先用官方明細確認條款內容。")}</p>
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

function renderPortfolioDetail(item) {
  const container = document.getElementById("portfolioDetail");
  state.portfolioDetailItem = item || null;
  if (!item) {
    container.innerHTML = "";
    return;
  }
  const detailLink = item.detail_url || item.policy_url || "";
  container.innerHTML = `
    <article class="portfolio-detail-card">
      <div class="portfolio-detail-top">
        <div>
          <p class="eyebrow">Policy Summary</p>
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
          <div class="policy-flags">${coverageBadgeHtml(item)}</div>
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
      <section>
        <h4>保障內容摘要</h4>
        <div class="portfolio-summary-grid">${focusSummaryHtml(item)}</div>
      </section>
      ${identityWarningHtml(item)}
      <div class="portfolio-detail-actions">
        <button class="button primary" type="button" data-confirm-add-portfolio>確認加入集合</button>
        ${detailLink ? `<a class="button secondary" href="${escapeHtml(detailLink)}" target="_blank" rel="noreferrer">官方來源</a>` : ""}
      </div>
    </article>
  `;
}

function renderPortfolioList() {
  const container = document.getElementById("portfolioList");
  setText("portfolioCount", `${formatNumber.format(state.portfolioItems.length)} 張`);
  if (!state.portfolioItems.length) {
    container.innerHTML =
      '<div class="empty"><strong>尚未加入保單。</strong><span>從上方輸入保單名稱或險種，就會形成自己的保障集合。</span></div>';
    return;
  }
  container.innerHTML = state.portfolioItems
    .map(
      (item) => `
        <article class="portfolio-item">
          <div>
            <strong class="policy-title-line">${policyTitleHtml(item)}</strong>
            <div class="policy-meta">
              <span>${escapeHtml(item.company)}</span>
              <span>${escapeHtml(item.product_type)}</span>
              ${identityMetaHtml(item)}
            </div>
            <div class="policy-flags">
              ${coverageBadgeHtml(item)}
              ${(item.flags || []).slice(0, 3).map((flag) => `<span class="chip muted">${escapeHtml(flag)}</span>`).join("")}
            </div>
          </div>
          <div class="portfolio-actions">
            ${
              item.detail_url
                ? `<a class="button secondary" href="${escapeHtml(item.detail_url)}" target="_blank" rel="noreferrer">官方明細</a>`
                : item.policy_url
                  ? `<a class="button secondary" href="${escapeHtml(item.policy_url)}" target="_blank" rel="noreferrer">官方來源</a>`
                  : ""
            }
            <button class="button ghost" type="button" data-remove-portfolio="${escapeHtml(item.id)}">移除</button>
          </div>
        </article>
      `,
    )
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
  container.innerHTML = bucketMatches
    .map((bucket) => {
      const hasItems = bucket.items.length > 0;
      return `
        <article class="coverage-bucket ${hasItems ? "active" : ""}">
          <div class="coverage-bucket-top">
            <strong>${escapeHtml(bucket.label)}</strong>
            <span>${formatNumber.format(bucket.items.length)} 張</span>
          </div>
          <p>${escapeHtml(bucket.summary)}</p>
          <div class="coverage-meter" aria-hidden="true"><span style="width:${hasItems ? "100" : "0"}%"></span></div>
          <div class="coverage-examples">
            ${
              hasItems
                ? bucket.items
                    .slice(0, 4)
                    .map((item) => `<span>${escapeHtml(item.product_name)}</span>`)
                    .join("")
                : "<span>尚未加入對應保單</span>"
            }
          </div>
        </article>
      `;
    })
    .join("");
}

function renderPortfolio() {
  renderPortfolioList();
  renderCoverageBuckets();
}

async function runPortfolioSearch(query) {
  const cleanedQuery = String(query || "").trim();
  if (!cleanedQuery) {
    setText("portfolioHint", "請先輸入保單名稱或險種。");
    document.getElementById("portfolioInput").focus();
    return;
  }
  setText("portfolioHint", "正在查找可加入的保單。");
  renderPortfolioSuggestions([], cleanedQuery);
  try {
    const matches = await findPortfolioMatches(cleanedQuery);
    const productIdMatches = exactProductIdMatches(matches, cleanedQuery);
    if (productIdMatches.length === 1) {
      renderPortfolioSuggestions(productIdMatches, cleanedQuery);
      renderPortfolioDetail(productIdMatches[0]);
      setText(
        "portfolioHint",
        `已找到「${productIdMatches[0].product_name}」。請先看摘要，確認後再加入集合。`,
      );
      return;
    }
    if (productIdMatches.length > 1) {
      renderPortfolioSuggestions(productIdMatches, cleanedQuery);
      setText("portfolioHint", "找到多筆候選，請先核對公司、險種、銷售日/停售日與官方明細，不要自動加入。");
      return;
    }

    const nameMatches = exactNameMatches(matches, cleanedQuery);
    if (nameMatches.length === 1) {
      renderPortfolioSuggestions(nameMatches, cleanedQuery);
      renderPortfolioDetail(nameMatches[0]);
      setText(
        "portfolioHint",
        `已找到「${nameMatches[0].product_name}」。請先看摘要，確認後再加入集合。`,
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
      renderPortfolioDetail(matches[0]);
      setText("portfolioHint", `已找到「${matches[0].product_name}」。請先看摘要，確認後再加入集合。`);
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
  setText("policyResultCount", `${formatNumber.format(rows.length)} 張`);
  renderPolicyResultSummary(rows.length);
  syncControls();

  if (!rows.length) {
    container.innerHTML =
      '<div class="empty"><strong>找不到符合條件的保單。</strong><span>請改用公司、商品、住院、手術、等待期或除外責任等關鍵字。</span></div>';
    return;
  }

  container.innerHTML = rows.slice(0, 80).map(renderPolicyCard).join("");
  if (rows.length > 80) {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="empty"><strong>目前先顯示前 80 張。</strong><span>請用公司、保單類型或關鍵字縮小範圍；符合條件共 ${formatNumber.format(rows.length)} 張。</span></div>`,
    );
  }
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
  syncControls();
  renderPolicyCards();
  renderSources();
  renderDiscontinuedList();
  updateUrl();
  document.getElementById("searchInput").focus();
}

function bindEvents() {
  document.getElementById("portfolioForm").addEventListener("submit", (event) => {
    event.preventDefault();
    runPortfolioSearch(document.getElementById("portfolioInput").value);
  });

  document.getElementById("clearPortfolio").addEventListener("click", clearPortfolio);

  document.getElementById("portfolioQuickAdds").addEventListener("click", (event) => {
    const button = event.target.closest("[data-portfolio-query]");
    if (!button) return;
    document.getElementById("portfolioInput").value = button.dataset.portfolioQuery;
    runPortfolioSearch(button.dataset.portfolioQuery);
  });

  document.getElementById("portfolioCompanyFilter").addEventListener("change", (event) => {
    state.portfolioCompany = event.target.value;
    state.portfolioDetailItem = null;
    renderPortfolioDetail(null);
    const query = document.getElementById("portfolioInput").value.trim();
    if (query) runPortfolioSearch(query);
  });

  document.getElementById("portfolioBucketFilter").addEventListener("change", (event) => {
    state.portfolioBucket = event.target.value;
    state.portfolioDetailItem = null;
    renderPortfolioDetail(null);
    const query = document.getElementById("portfolioInput").value.trim();
    if (query) runPortfolioSearch(query);
  });

  document.getElementById("portfolioSuggestions").addEventListener("click", (event) => {
    const button = event.target.closest("[data-view-suggestion]");
    if (!button) return;
    const item = state.portfolioSuggestions[Number(button.dataset.viewSuggestion)];
    if (!item) return;
    renderPortfolioDetail(item);
    setText("portfolioHint", `正在查看「${item.product_name}」摘要。確認後可加入集合。`);
  });

  document.getElementById("portfolioDetail").addEventListener("click", (event) => {
    const closeButton = event.target.closest("[data-close-portfolio-detail]");
    if (closeButton) {
      renderPortfolioDetail(null);
      return;
    }
    const addButton = event.target.closest("[data-confirm-add-portfolio]");
    if (!addButton || !state.portfolioDetailItem) return;
    const item = state.portfolioDetailItem;
    const added = addPortfolioItem(item);
    setText("portfolioHint", added ? `已加入「${item.product_name}」。` : `「${item.product_name}」已在集合中。`);
  });

  document.getElementById("portfolioList").addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-portfolio]");
    if (!button) return;
    removePortfolioItem(button.dataset.removePortfolio);
    setText("portfolioHint", "已從集合移除。");
  });

  document.getElementById("searchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    runSearch();
  });

  document.getElementById("clearFilters").addEventListener("click", resetFilters);

  document.getElementById("companyFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.company = event.target.value;
    renderPolicyCards();
    renderSources();
    refreshTiiDiscontinuedForFilters();
    updateUrl();
  });

  document.getElementById("kindFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.kind = event.target.value;
    renderPolicyCards();
    renderSources();
    refreshTiiDiscontinuedForFilters();
    updateUrl();
  });

  document.getElementById("crawlFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.crawl = event.target.value;
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

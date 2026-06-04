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
  tiiExecutionProgress: null,
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
};

const formatNumber = new Intl.NumberFormat("zh-Hant-TW");

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

async function loadData() {
  const [
    sourceIndex,
    taxonomy,
    crawlStatus,
    policyInsights,
    tiiMetadata,
    tiiResults,
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
    fetch("./data/tii-policy-results.json").then((response) =>
      response.ok ? response.json() : { record_count: 0, records: [], completed_batches: [] },
    ),
    fetch("./data/tii-execution-progress.json").then((response) =>
      response.ok ? response.json() : { summary: { attempted_batches: 0, completed_batches: 0, captcha_required_batches: 0 }, runs: [] },
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
  const companies = [...new Set(policyRecords.map((item) => item.company).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant-TW"),
  );
  const kinds = [...new Set(policyRecords.map((item) => item.product_type || "其他"))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant-TW"),
  );

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

function renderPolicyInsights() {
  renderInsightMetrics();
  document.getElementById("statusBars").innerHTML = barRows(state.policyInsights.status_counts, {
    className: "status-fill",
  });
  document.getElementById("typeBars").innerHTML = barRows(state.policyInsights.type_counts.slice(0, 8));
  document.getElementById("companyBars").innerHTML = barRows(state.policyInsights.company_counts.slice(0, 8));

  const discontinued = state.policyInsights.discontinued_policies || [];
  setText("discontinuedCount", `${formatNumber.format(discontinued.length)} 筆`);
  document.getElementById("discontinuedList").innerHTML = discontinued.length
    ? discontinued
        .map(
          (policy) => `
            <article class="policy-item">
              <div>
                <strong>${escapeHtml(policy.product_name)}</strong>
                <div class="policy-meta">
                  <span>${escapeHtml(policy.company)}</span>
                  <span>${escapeHtml(policy.product_type)}</span>
                  <span>${escapeHtml(policy.version_text || "版本未標示")}</span>
                </div>
                <div class="policy-flags">
                  ${(policy.content_flags || []).map((flag) => `<span class="chip">${escapeHtml(flag)}</span>`).join("")}
                </div>
              </div>
              ${
                policy.policy_url
                  ? `<a class="button secondary" href="${escapeHtml(policy.policy_url)}" target="_blank" rel="noreferrer">官方來源</a>`
                  : '<span class="badge muted">待補來源</span>'
              }
            </article>
          `,
        )
        .join("")
    : '<div class="empty"><strong>目前沒有已停售保單資料。</strong><span>完成 TII 人工驗證碼查詢匯入後會出現在這裡。</span></div>';

  const metadata = state.tiiMetadata;
  const tiiManualCount =
    state.batchPlan?.summary?.tii_manual_matrix_batch_count || state.batchPlan?.summary?.tii_full_estimated_batch_count || 0;
  const tiiAttemptedBatches = state.tiiExecutionProgress?.summary?.attempted_batches || 0;
  const tiiCaptchaRequiredBatches = state.tiiExecutionProgress?.summary?.captcha_required_batches || 0;
  const tiiCompletedBatches =
    state.tiiExecutionProgress?.summary?.completed_batches ||
    state.tiiResults?.completed_batch_count ||
    state.tiiResults?.completed_batches?.length ||
    0;
  const tiiImportedPolicies = state.tiiResults?.record_count || state.tiiResults?.records?.length || 0;
  document.getElementById("tiiStatus").innerHTML = `
    <div class="tii-grid">
      <span><strong>${formatNumber.format(metadata.companies.length)}</strong><small>公司選項</small></span>
      <span><strong>${formatNumber.format(metadata.insurance_categories.length)}</strong><small>保險類別</small></span>
      <span><strong>${metadata.captcha_required ? "需要" : "不需要"}</strong><small>圖形驗證碼</small></span>
      <span><strong>${formatNumber.format(tiiManualCount)}</strong><small>人工批次</small></span>
      <span><strong>${formatNumber.format(tiiAttemptedBatches)}</strong><small>已啟動批次</small></span>
      <span><strong>${formatNumber.format(tiiCaptchaRequiredBatches)}</strong><small>等待驗證碼</small></span>
      <span><strong>${formatNumber.format(tiiCompletedBatches)}</strong><small>已完成批次</small></span>
      <span><strong>${formatNumber.format(tiiImportedPolicies)}</strong><small>已匯入保單</small></span>
    </div>
    <p>官方查詢支援公司、保險類別、銷售日、停售日與關鍵字。TII 目前是待人工執行狀態：必須人工輸入驗證碼、保存結果，再匯入本站；本專案不自動破解驗證碼。</p>
    <a href="${escapeHtml(metadata.source_url)}" target="_blank" rel="noreferrer">開啟保發中心查詢</a>
  `;
  renderBatchPlan();
  renderPolicyContentExtracts();
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
  const tiiCompletedBatches =
    state.tiiExecutionProgress?.summary?.completed_batches ||
    state.tiiResults?.completed_batch_count ||
    state.tiiResults?.completed_batches?.length ||
    0;
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
    )} 個、等待驗證碼 ${formatNumber.format(tiiCaptchaRequiredBatches)} 個、已完成人工批次 ${formatNumber.format(
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
      <strong>${formatNumber.format(tiiCompletedBatches)}</strong>
      <span>TII 已完成人工批次</span>
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
      return policySearchText(record).includes(query);
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
      return normalize(
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
      ).includes(query);
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

function runSearch(options = {}) {
  state.openSourceId = null;
  state.search = document.getElementById("searchInput").value.trim();
  renderPolicyCards();
  renderSources(options);
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
  updateUrl();
  document.getElementById("searchInput").focus();
}

function bindEvents() {
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
    updateUrl();
  });

  document.getElementById("kindFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.kind = event.target.value;
    renderPolicyCards();
    renderSources();
    updateUrl();
  });

  document.getElementById("crawlFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.crawl = event.target.value;
    renderPolicyCards();
    renderSources();
    updateUrl();
  });

  document.querySelector(".status-chips").addEventListener("click", (event) => {
    const button = event.target.closest("[data-crawl]");
    if (!button) return;
    state.openSourceId = null;
    state.crawl = button.dataset.crawl;
    renderPolicyCards();
    renderSources();
    updateUrl();
  });

  document.getElementById("sourceList").addEventListener("click", (event) => {
    const button = event.target.closest(".copy-link");
    if (!button) return;
    copyText(button.dataset.url, button);
  });
}

async function main() {
  try {
    await loadData();
    populateFilters();
    loadFiltersFromUrl();
    renderMetrics();
    renderPolicyInsights();
    renderTaxonomy();
    renderDomainChart();
    renderPolicyCards();
    renderSources();
    bindEvents();
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

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
  batchPlan: null,
  batchProgress: null,
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
  const [sourceIndex, taxonomy, crawlStatus, policyInsights, tiiMetadata, batchPlan, batchProgress] = await Promise.all([
    fetch("./data/source-index.json").then((response) => response.json()),
    fetch("./data/consumer-taxonomy.json").then((response) => response.json()),
    fetch("./data/crawl-status.json").then((response) => response.json()),
    fetch("./data/policy-insights.json").then((response) => response.json()),
    fetch("./data/tii-query-metadata.json").then((response) => response.json()),
    fetch("./data/batch-plan.json").then((response) => response.json()),
    fetch("./data/batch-progress.json").then((response) => (response.ok ? response.json() : null)),
  ]);
  state.sourceIndex = sourceIndex;
  state.taxonomy = taxonomy;
  state.crawlStatus = crawlStatus;
  state.policyInsights = policyInsights;
  state.tiiMetadata = tiiMetadata;
  state.batchPlan = batchPlan;
  state.batchProgress = batchProgress;
  state.crawlByUrlId = new Map(crawlStatus.results.map((item) => [item.url_id, item]));
}

function populateFilters() {
  const companyFilter = document.getElementById("companyFilter");
  const kindFilter = document.getElementById("kindFilter");

  const companies = [...new Set(state.sourceIndex.urls.map((item) => item.company))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant-TW"),
  );
  const kinds = [...new Set(state.sourceIndex.urls.map((item) => item.kind))].sort();

  companyFilter.innerHTML = [
    '<option value="all">全部公司</option>',
    ...companies.map((company) => `<option value="${escapeHtml(company)}">${escapeHtml(company)}</option>`),
  ].join("");

  kindFilter.innerHTML = [
    '<option value="all">全部類型</option>',
    ...kinds.map((kind) => `<option value="${escapeHtml(kind)}">${escapeHtml(kindLabel(kind))}</option>`),
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
  state.crawl = crawlLabels[crawl] ? crawl : DEFAULT_FILTERS.crawl;
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
  document.getElementById("tiiStatus").innerHTML = `
    <div class="tii-grid">
      <span><strong>${formatNumber.format(metadata.companies.length)}</strong><small>公司選項</small></span>
      <span><strong>${formatNumber.format(metadata.insurance_categories.length)}</strong><small>保險類別</small></span>
      <span><strong>${metadata.captcha_required ? "需要" : "不需要"}</strong><small>圖形驗證碼</small></span>
    </div>
    <p>官方查詢支援公司、保險類別、銷售日、停售日與關鍵字。因有圖形驗證碼，本專案只做人工完成驗證後的結果匯入，不自動破解。</p>
    <a href="${escapeHtml(metadata.source_url)}" target="_blank" rel="noreferrer">開啟保發中心查詢</a>
  `;
  renderBatchPlan();
}

function renderBatchPlan() {
  const plan = state.batchPlan;
  const summary = plan.summary;
  const progress = state.batchProgress?.summary || {};
  const processed = progress.policy_url_items_processed || 0;
  const successRate = processed ? Math.round(((progress.policy_url_ok || 0) / processed) * 1000) / 10 : 0;
  const totalPlanned = summary.policy_url_batch_count + (summary.tii_manual_matrix_batch_count || summary.tii_priority_batch_count);
  setText("batchPlanCount", `${formatNumber.format(totalPlanned)} 批次`);
  document.getElementById("batchSummary").innerHTML = `
    <article>
      <strong>${formatNumber.format(summary.policy_url_batch_count)}</strong>
      <span>保單 URL 自動批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(summary.tii_priority_batch_count)}</strong>
      <span>TII 優先人工批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(summary.tii_full_estimated_batch_count)}</strong>
      <span>TII 全量估算批次</span>
    </article>
    <article>
      <strong>${formatNumber.format(progress.completed_policy_url_batches || 0)}</strong>
      <span>已執行 URL 批次</span>
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
      kind: "TII 人工",
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
      ${escapeHtml(activeGroup.label)}會搭配：${escapeHtml(categoryLabels)}。查詢結果需要人工輸入驗證碼後匯入，系統不繞過驗證碼。
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
      if (state.kind !== "all" && item.kind !== state.kind) return false;
      if (!passesCrawlFilter(item)) return false;
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
  if (state.kind !== "all") filterParts.push(kindLabel(state.kind));
  if (state.crawl !== "all") filterParts.push(crawlLabels[state.crawl]);
  const activeText = filterParts.length ? `條件：${filterParts.join(" / ")}。` : "條件：全部來源。";

  setText(
    "resultSummary",
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
  renderResultSummary(rows.length);
  syncControls();

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

  if (options.scroll) {
    document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function runSearch(options = {}) {
  state.openSourceId = null;
  state.search = document.getElementById("searchInput").value.trim();
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
  renderSources();
  updateUrl();
  document.getElementById("searchInput").focus();
}

function bindEvents() {
  document.getElementById("searchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    runSearch({ scroll: true });
  });

  document.getElementById("clearFilters").addEventListener("click", resetFilters);

  document.getElementById("companyFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.company = event.target.value;
    renderSources();
    updateUrl();
  });

  document.getElementById("kindFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.kind = event.target.value;
    renderSources();
    updateUrl();
  });

  document.getElementById("crawlFilter").addEventListener("change", (event) => {
    state.openSourceId = null;
    state.crawl = event.target.value;
    renderSources();
    updateUrl();
  });

  document.querySelector(".status-chips").addEventListener("click", (event) => {
    const button = event.target.closest("[data-crawl]");
    if (!button) return;
    state.openSourceId = null;
    state.crawl = button.dataset.crawl;
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

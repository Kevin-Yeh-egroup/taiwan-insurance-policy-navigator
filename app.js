const state = {
  sourceIndex: null,
  taxonomy: null,
  crawlStatus: null,
  crawlByUrlId: new Map(),
  search: "",
  company: "all",
  kind: "all",
  crawl: "all",
};

const formatNumber = new Intl.NumberFormat("zh-Hant-TW");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
  if (!result) return { label: "尚未批次檢查", className: "unchecked" };
  if (result.robots_allowed === false) return { label: "robots 擋下", className: "blocked" };
  if (result.ok) return { label: "已驗證可取", className: "ok" };
  return { label: "錯誤/待複核", className: "error" };
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

async function loadData() {
  const [sourceIndex, taxonomy, crawlStatus] = await Promise.all([
    fetch("./data/source-index.json").then((response) => response.json()),
    fetch("./data/consumer-taxonomy.json").then((response) => response.json()),
    fetch("./data/crawl-status.json").then((response) => response.json()),
  ]);
  state.sourceIndex = sourceIndex;
  state.taxonomy = taxonomy;
  state.crawlStatus = crawlStatus;
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

function renderMetrics() {
  setText("metricSources", formatNumber.format(state.sourceIndex.source_file_count));
  setText("metricUrls", formatNumber.format(state.sourceIndex.total_unique_url_count));
  setText("metricCandidates", formatNumber.format(state.sourceIndex.public_crawl_candidate_count));
  setText("metricCrawlOk", formatNumber.format(state.crawlStatus.summary.ok));
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

function filteredUrls() {
  const query = state.search.trim().toLowerCase();
  return state.sourceIndex.urls.filter((item) => {
    if (state.company !== "all" && item.company !== state.company) return false;
    if (state.kind !== "all" && item.kind !== state.kind) return false;
    if (!passesCrawlFilter(item)) return false;
    if (!query) return true;
    return [item.company, item.domain, item.kind, item.source_file_title, item.source_label, item.url]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });
}

function renderSources() {
  const rows = filteredUrls();
  const container = document.getElementById("sourceList");
  setText("resultCount", `${formatNumber.format(rows.length)} 筆`);

  if (!rows.length) {
    container.innerHTML = '<div class="empty">沒有符合條件的來源。</div>';
    return;
  }

  container.innerHTML = rows
    .slice(0, 120)
    .map((item) => {
      const result = state.crawlByUrlId.get(item.id);
      const status = crawlLabel(result);
      const isPublic = item.should_crawl ? "公開候選" : "不列入公開爬取";
      return `
        <article class="source-item">
          <div>
            <div class="source-title">
              <strong>${escapeHtml(item.company)}</strong>
              <span class="badge">${escapeHtml(kindLabel(item.kind))}</span>
              <span class="badge">${escapeHtml(isPublic)}</span>
            </div>
            <a class="source-url" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>
            <div class="source-meta">
              <span>${escapeHtml(item.domain)}</span>
              <span>${escapeHtml(item.source_file_title)}</span>
              <span>${escapeHtml(item.id)}</span>
            </div>
          </div>
          <div class="crawl-status">
            <span class="badge ${status.className}">${escapeHtml(status.label)}</span>
            <span>${result ? `HTTP ${escapeHtml(result.status ?? "n/a")}` : "等待下一批"}</span>
            <span>${result?.title ? escapeHtml(result.title) : escapeHtml(result?.content_type || "")}</span>
          </div>
        </article>
      `;
    })
    .join("");

  if (rows.length > 120) {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="empty">目前先顯示前 120 筆；請用搜尋或篩選縮小範圍。總數 ${formatNumber.format(rows.length)} 筆。</div>`,
    );
  }
}

function bindEvents() {
  document.getElementById("searchInput").addEventListener("input", (event) => {
    state.search = event.target.value;
    renderSources();
  });
  document.getElementById("companyFilter").addEventListener("change", (event) => {
    state.company = event.target.value;
    renderSources();
  });
  document.getElementById("kindFilter").addEventListener("change", (event) => {
    state.kind = event.target.value;
    renderSources();
  });
  document.getElementById("crawlFilter").addEventListener("change", (event) => {
    state.crawl = event.target.value;
    renderSources();
  });
}

async function main() {
  try {
    await loadData();
    populateFilters();
    renderMetrics();
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

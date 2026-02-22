const fileEl = document.getElementById("feedbackFile");
const compareFileEl = document.getElementById("compareFile");
const refreshBtn = document.getElementById("refreshBtn");
const compareBtn = document.getElementById("compareBtn");
const searchBtn = document.getElementById("searchBtn");
const exportBtn = document.getElementById("exportBtn");
const exportSummaryBtn = document.getElementById("exportSummaryBtn");
const keywordEl = document.getElementById("keyword");
const caseSensitiveEl = document.getElementById("caseSensitive");
const matchModeEl = document.getElementById("matchMode");
const sentimentFilterEl = document.getElementById("sentimentFilter");
const minRatingEl = document.getElementById("minRating");
const statusEl = document.getElementById("status");
const loadingEl = document.getElementById("loading");
const themeToggleEl = document.getElementById("themeToggle");

let latestSearch = [];
let latestKeyword = "";
let latestAnalysis = null;
let currentTheme = "light";

function applyTheme(theme) {
  currentTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", currentTheme);
  if (themeToggleEl) {
    themeToggleEl.textContent = currentTheme === "dark" ? "Light Mode" : "Dark Glass";
  }
}

function initTheme() {
  const saved = localStorage.getItem("theme");
  applyTheme(saved === "dark" ? "dark" : "light");
}

function toggleTheme() {
  const next = currentTheme === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem("theme", next);
}

function selectedFile(inputEl) {
  return inputEl.files && inputEl.files.length > 0 ? inputEl.files[0] : null;
}

function setStatus(message, type = "info") {
  statusEl.textContent = message;
  statusEl.classList.remove("ok", "error", "muted");
  if (type === "ok") statusEl.classList.add("ok");
  else if (type === "error") statusEl.classList.add("error");
  else statusEl.classList.add("muted");
}

function setLoading(flag) {
  loadingEl.classList.toggle("hidden", !flag);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function highlightText(text, keyword, caseSensitive) {
  if (!keyword) return escapeHtml(text);
  const flags = caseSensitive ? "g" : "gi";
  const safeKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(safeKeyword, flags);
  return escapeHtml(text).replace(regex, (match) => `<mark>${match}</mark>`);
}

async function apiPost(url, formData) {
  const res = await fetch(url, { method: "POST", body: formData });
  const contentType = res.headers.get("content-type") || "";
  let body = null;
  if (contentType.includes("application/json")) {
    body = await res.json();
  } else {
    const text = await res.text();
    body = { ok: false, error: { message: text || "Request failed" } };
  }
  if (!res.ok || !body.ok) {
    const message = body?.error?.message || "Request failed";
    throw new Error(message);
  }
  return body.data;
}

async function loadAnalysis() {
  const file = selectedFile(fileEl);
  if (!file) {
    setStatus("Please upload a .txt or .csv file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("feedback_file", file);

  try {
    setLoading(true);
    setStatus(`Analyzing ${file.name}...`);
    const data = await apiPost("/api/analyze", formData);
    latestAnalysis = data;
    renderDashboard(data);
    setStatus(`Analysis complete for ${data.file.name}.`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(false);
  }
}

async function compareFiles() {
  const file = selectedFile(fileEl);
  const compareFile = selectedFile(compareFileEl);
  if (!file || !compareFile) {
    setStatus("Upload both primary and compare files.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("feedback_file", file);
  formData.append("feedback_file_compare", compareFile);

  try {
    setLoading(true);
    setStatus(`Comparing ${file.name} vs ${compareFile.name}...`);
    const data = await apiPost("/api/compare", formData);
    const d = data.delta;
    const compareEl = document.getElementById("compareSummary");
    compareEl.innerHTML = `
      <div>Total delta: <b>${d.total_feedback_delta}</b></div>
      <div>Positive % delta: <b>${d.positive_pct_delta}</b></div>
      <div>Negative % delta: <b>${d.negative_pct_delta}</b></div>
      <div>Avg rating delta: <b>${d.avg_rating_delta ?? "N/A"}</b></div>
    `;
    setStatus("Comparison complete.", "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(false);
  }
}

async function runSearch() {
  const keyword = keywordEl.value.trim();
  if (!keyword) {
    setStatus("Enter a keyword to search.", "error");
    return;
  }

  const file = selectedFile(fileEl);
  if (!file) {
    setStatus("Please upload a .txt or .csv file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("feedback_file", file);
  formData.append("keyword", keyword);
  formData.append("case_sensitive", String(caseSensitiveEl.checked));
  formData.append("match_mode", matchModeEl.value);
  formData.append("sentiment_filter", sentimentFilterEl.value);
  if (minRatingEl.value) {
    formData.append("min_rating", minRatingEl.value);
  }

  try {
    setLoading(true);
    setStatus("Searching feedback...");
    const data = await apiPost("/api/search", formData);
    const meta = document.getElementById("searchMeta");
    const list = document.getElementById("searchResults");
    latestSearch = data.matches || [];
    latestKeyword = data.keyword || "";

    meta.textContent = `Found ${data.count} result(s) for "${data.keyword}"`;
    list.innerHTML = "";
    latestSearch.forEach((text) => {
      const li = document.createElement("li");
      li.innerHTML = highlightText(text, data.keyword, data.options.case_sensitive);
      list.appendChild(li);
    });
    if (latestSearch.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No matching feedback found.";
      list.appendChild(li);
    }

    setStatus(`Search complete: ${data.count} match(es).`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(false);
  }
}

function exportSearch() {
  if (!latestSearch.length) {
    setStatus("No search results to export.", "error");
    return;
  }
  const lines = [`Keyword: ${latestKeyword}`, `Matches: ${latestSearch.length}`, ""];
  latestSearch.forEach((item, idx) => lines.push(`${idx + 1}. ${item}`));
  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "search_results.txt";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  setStatus("Search results exported.", "ok");
}

function exportExecutiveSummary() {
  if (!latestAnalysis) {
    setStatus("Run analysis first to export PDF summary.", "error");
    return;
  }

  fetch("/api/export-summary-pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysis: latestAnalysis }),
  })
    .then(async (res) => {
      if (!res.ok) {
        let message = "PDF export failed";
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          const body = await res.json();
          message = body.error?.message || message;
        }
        throw new Error(message);
      }
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "executive_summary.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setStatus("Executive summary PDF exported.", "ok");
    })
    .catch((err) => {
      setStatus(err.message || "PDF export failed", "error");
    });
}

function renderDashboard(data) {
  renderStats(data.stats, data.average_rating, data.file);
  renderSentiment(data.sentiment_percent, data.sentiment_series);
  renderTopWords(data.top_words, "topWords");
  renderTopWords(data.negative_top_words, "negativeWords");
  renderCategories(data.categories);
  renderRatings(data.rating_distribution);
  renderSuggestions(data.suggestions);
  renderPriorityInsights(data.priority_insights);
}

function renderStats(stats, avgRating, fileMeta) {
  const wrap = document.getElementById("stats");
  const cards = [
    ["File", fileMeta.name],
    ["Rows", stats.total],
    ["Avg Length", stats.avg_length],
    ["Avg Rating", avgRating ?? "N/A"]
  ];
  wrap.innerHTML = cards
    .map(([label, value]) => `<div class="stat"><small class="muted">${label}</small><b>${escapeHtml(String(value))}</b></div>`)
    .join("");
}

function renderSentiment(sentimentPercent) {
  const container = document.getElementById("sentimentBars");
  container.innerHTML = "";
  ["Positive", "Negative", "Neutral"].forEach((key) => {
    const pct = sentimentPercent[key] || 0;
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="bar-row">
        <div class="bar-meta"><span>${key}</span><strong>${pct}%</strong></div>
        <div class="bar"><div class="fill" style="width:${pct}%"></div></div>
      </div>`
    );
  });
}

function renderTopWords(words, elementId) {
  const list = document.getElementById(elementId);
  list.innerHTML = "";
  (words || []).forEach((entry) => {
    const li = document.createElement("li");
    li.textContent = `${entry.word}: ${entry.count}`;
    list.appendChild(li);
  });
  if (!list.children.length) {
    const li = document.createElement("li");
    li.textContent = "No data";
    list.appendChild(li);
  }
}

function renderCategories(categories) {
  const list = document.getElementById("categories");
  const entries = Object.entries(categories || {});
  if (!entries.length) {
    list.innerHTML = "<li>No data</li>";
    return;
  }
  const max = Math.max(...entries.map(([, count]) => count), 1);
  list.innerHTML = entries
    .map(
      ([name, count]) => `<li class="meter-row">
        <span>${name} (${count})</span>
        <div class="meter-track"><div class="meter-fill" style="width:${(count / max) * 100}%"></div></div>
      </li>`
    )
    .join("");
}

function renderRatings(distribution) {
  const el = document.getElementById("ratings");
  if (!distribution) {
    el.innerHTML = `<p class="muted">Upload CSV file to view rating distribution.</p>`;
    return;
  }
  const max = Math.max(...Object.values(distribution), 1);
  el.innerHTML = [5, 4, 3, 2, 1]
    .map(
      (star) => `<div class="meter-row">
        <span>${star} star (${distribution[star]})</span>
        <div class="meter-track"><div class="meter-fill" style="width:${(distribution[star] / max) * 100}%"></div></div>
      </div>`
    )
    .join("");
}

function renderSuggestions(items) {
  const list = document.getElementById("suggestions");
  list.innerHTML = "";
  (items || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function renderPriorityInsights(items) {
  const list = document.getElementById("priorityInsights");
  list.innerHTML = "";
  (items || []).forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(item.title)}</strong><br><small class="muted">${escapeHtml(item.evidence)}</small>`;
    list.appendChild(li);
  });
  if (!list.children.length) {
    const li = document.createElement("li");
    li.textContent = "No priority insights yet.";
    list.appendChild(li);
  }
}

refreshBtn.addEventListener("click", loadAnalysis);
compareBtn.addEventListener("click", compareFiles);
searchBtn.addEventListener("click", runSearch);
exportBtn.addEventListener("click", exportSearch);
exportSummaryBtn.addEventListener("click", exportExecutiveSummary);
if (themeToggleEl) {
  themeToggleEl.addEventListener("click", toggleTheme);
}
initTheme();

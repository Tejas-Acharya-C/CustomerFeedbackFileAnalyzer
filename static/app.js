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

let latestSearch = [];
let latestKeyword = "";
let latestAnalysis = null;
let currentTheme = "light";

// Session State Fetching
const urlParams = new URLSearchParams(window.location.search);
const currentSid = urlParams.get("sid");

function selectedFile(inputEl) {
  return inputEl && inputEl.files && inputEl.files.length > 0 ? inputEl.files[0] : null;
}

function setStatus(message, type = "info") {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.remove("ok", "error", "muted", "text-cyan-400", "text-error", "text-zinc-500");
  if (type === "ok") statusEl.classList.add("text-cyan-400");
  else if (type === "error") statusEl.classList.add("text-error");
  else statusEl.classList.add("text-zinc-500");
}

function setLoading(flag) {
  if(loadingEl) loadingEl.classList.toggle("hidden", !flag);
}

function escapeHtml(value) {
  if(!value) return "";
  return value
    .toString()
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
  return escapeHtml(text).replace(regex, (match) => `<mark class="bg-primary/20 text-primary">${match}</mark>`);
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
    setStatus(`Analyzing ${file.name} to memory...`);
    const res = await fetch("/api/analyze", { method: "POST", body: formData });
    let body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Analysis failed");
    
    // Redirect to Dashboard with active Session ID
    window.location.href = `/dashboard?sid=${body.data.session_id}`;
  } catch (err) {
    setStatus(err.message, "error");
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
    setStatus("Running differential analysis...");
    const res = await fetch("/api/compare", { method: "POST", body: formData });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Comparison failed");
    const delta = body.data.delta;
    setStatus(
      `Differential complete — Δ Volume: ${delta.total_feedback_delta > 0 ? '+' : ''}${delta.total_feedback_delta} | Δ Positive: ${delta.positive_pct_delta > 0 ? '+' : ''}${delta.positive_pct_delta}% | Δ Rating: ${delta.avg_rating_delta ?? 'N/A'}`,
      "ok"
    );
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(false);
  }
}

async function runSearch() {
  if (!currentSid) {
    setStatus("No active session! Start from Home.", "error");
    return;
  }
  
  const keyword = keywordEl ? keywordEl.value.trim() : "";
  const formData = new FormData();
  formData.append("sid", currentSid);
  formData.append("keyword", keyword);
  if(caseSensitiveEl) formData.append("case_sensitive", String(caseSensitiveEl.checked));
  if(matchModeEl) formData.append("match_mode", matchModeEl.value);
  if(sentimentFilterEl) formData.append("sentiment_filter", sentimentFilterEl.value);
  if(minRatingEl && minRatingEl.value) formData.append("min_rating", minRatingEl.value);

  try {
    setLoading(true);
    setStatus("Searching raw dataset...");
    const res = await fetch("/api/search", { method: "POST", body: formData });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Search failed");
    
    const data = body.data;
    latestSearch = data.matches || [];
    latestKeyword = data.keyword || "";
    const meta = document.getElementById("searchMeta");
    const list = document.getElementById("searchResults");
    
    if(meta) meta.textContent = `Found ${data.count} result(s) for "${data.keyword}"`;
    if(list) {
        list.innerHTML = "";
        latestSearch.forEach((text) => {
          const li = document.createElement("li");
          li.className = "text-sm p-3 bg-surface-container-highest/20 border-l-2 border-cyan-400 rounded-sm";
          li.innerHTML = highlightText(text, data.keyword, data.options.case_sensitive);
          list.appendChild(li);
        });
        if (latestSearch.length === 0) list.innerHTML = '<li class="text-zinc-500 p-4 text-center font-headline uppercase tracking-widest text-[10px]">No matching feedback found in the DATAMATRIX.</li>';
    }
    setStatus(`Search complete: ${data.count} match(es).`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(false);
  }
}

// ---------------------------------------------------------
// DOM Rendering (Safe null checks for Multi-Page operation)
// ---------------------------------------------------------
function renderDashboard(data) {
  renderStats(data.stats);
  renderSentiment(data.sentiment_percent);
  renderCategories(data.categories);
  renderRatings(data.ratings);
  renderSuggestions(data.suggestions);
  renderPriorityInsights(data.priority);
  renderTopWords(data.top_words);
  renderNegativeWords(data.negative_words);
  setStatus("Analysis Rendered Successfully", "ok");
}

function renderStats(stats) {
  const el = document.getElementById("stats");
  if (!el || !stats) return;
  el.innerHTML = `
    <div class="flex justify-between items-end">
        <div class="text-[10px] uppercase font-headline text-zinc-500">Volumetric Sum</div>
        <div class="text-3xl font-bold font-headline text-primary">${stats.total}</div>
    </div>
    <div class="flex justify-between items-end">
        <div class="text-[10px] uppercase font-headline text-zinc-500">Signal Ratio</div>
        <div class="text-xl font-bold font-headline text-zinc-300">${stats.processed}/${stats.failed}</div>
    </div>
  `;
}

function renderSentiment(dist) {
  const el = document.getElementById("sentimentBars");
  if (!el || !dist) return;
  el.className = "flex w-full h-4 rounded-full overflow-hidden";
  el.innerHTML = `
    <div style="width: ${dist.Positive || 0}%" class="bg-cyan-400"></div>
    <div style="width: ${dist.Neutral || 0}%" class="bg-secondary"></div>
    <div style="width: ${dist.Negative || 0}%" class="bg-error"></div>
  `;
}

function renderTopWords(words) {
  const list = document.getElementById("topWords");
  if (!list || !words) return;
  list.innerHTML = "";
  words.forEach(({ word, count }) => {
    const li = document.createElement("li");
    li.className = "flex justify-between items-center text-sm p-2 bg-surface-container-highest/20 hover:bg-surface-container-highest/60 transition-colors rounded-sm";
    li.innerHTML = `<span class="text-on-surface-variant font-medium">${escapeHtml(word)}</span><span class="text-cyan-400 font-headline text-xs">${count}</span>`;
    list.appendChild(li);
  });
}

function renderNegativeWords(words) {
  const list = document.getElementById("negativeWords");
  if (!list || !words) return;
  list.innerHTML = "";
  words.forEach(({ word, count }) => {
    const li = document.createElement("li");
    li.className = "flex justify-between items-center text-sm p-2 bg-error-container/20 border-l border-error hover:bg-error-container/50 transition-colors rounded-sm";
    li.innerHTML = `<span class="text-error font-medium">${escapeHtml(word)}</span><span class="text-error/70 font-headline text-xs">${count}</span>`;
    list.appendChild(li);
  });
}

function renderCategories(distribution) {
  const el = document.getElementById("categories");
  if (!el || !distribution) return;
  el.innerHTML = "";
  const max = Math.max(...Object.values(distribution), 1);
  for (const [name, count] of Object.entries(distribution)) {
    const li = document.createElement("li");
    li.className = "flex items-center gap-4";
    li.innerHTML = `
    <div class="flex-1">
        <div class="flex justify-between text-[10px] uppercase font-headline mb-1">
            <span>${escapeHtml(name)}</span>
            <span class="text-cyan-400">${count}</span>
        </div>
        <div class="h-1 bg-surface-container-lowest rounded-full overflow-hidden">
            <div class="h-full bg-cyan-400" style="width:${(count / max) * 100}%"></div>
        </div>
    </div>`;
    el.appendChild(li);
  }
}

function renderRatings(distribution) {
  const el = document.getElementById("ratings");
  if (!el || !distribution) return;
  const max = Math.max(...Object.values(distribution), 1);
  el.innerHTML = [5, 4, 3, 2, 1].map(star => `
      <div class="flex items-center gap-4">
        <div class="w-10 h-10 rounded-sm bg-surface-container-highest flex items-center justify-center">
            <span class="material-symbols-outlined text-secondary">star</span>
        </div>
        <div class="flex-1">
            <div class="flex justify-between text-[10px] uppercase font-headline mb-1">
                <span>${star} Star</span>
                <span class="text-secondary">${distribution[star] || 0}</span>
            </div>
            <div class="h-1 bg-surface-container-lowest rounded-full overflow-hidden">
                <div class="h-full bg-secondary" style="width:${((distribution[star] || 0) / max) * 100}%"></div>
            </div>
        </div>
      </div>`).join("");
}

function renderSuggestions(items) {
  const list = document.getElementById("suggestions");
  if (!list || !items) return;
  list.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "flex gap-3 items-start p-3 bg-surface-container-lowest border-l-2 border-cyan-400 rounded-sm";
    li.innerHTML = `
        <span class="material-symbols-outlined text-xs text-cyan-400 mt-1">auto_awesome</span>
        <span class="text-xs text-on-surface-variant">${escapeHtml(item)}</span>
    `;
    list.appendChild(li);
  });
}

function renderPriorityInsights(items) {
  const list = document.getElementById("priorityInsights");
  if (!list || !items) return;
  list.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "p-3 bg-error-container/10 border-l-2 border-error rounded-sm";
    li.innerHTML = `
        <div class="text-[10px] font-bold uppercase mb-1 text-error">${escapeHtml(item.title)}</div>
        <div class="text-xs text-zinc-400">${escapeHtml(item.evidence)}</div>
    `;
    list.appendChild(li);
  });
}

async function exportExecutiveSummary() {
    if (!currentSid) return setStatus("No active session to export", "error");
    window.location.href = `/api/export-summary-pdf?sid=${currentSid}`;
}

async function exportSearch() {
  if (!currentSid) return setStatus("No active session! Start from Home.", "error");
  if (latestSearch.length === 0) return setStatus("Search for data first to export.", "error");
  
  try {
    const csvContent = "Feedback Text\n" + latestSearch.map(s => `"${escapeHtml(s).replaceAll('"', '""')}"`).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `search_export_${latestKeyword || "all"}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

// ---------------------------------------------------------
// Navigation Hook
// ---------------------------------------------------------
const navHandlers = {
    "navDashboard": () => window.location.href = currentSid ? `/dashboard?sid=${currentSid}` : "/dashboard",
    "navAnalytics": () => window.location.href = currentSid ? `/analytics?sid=${currentSid}` : "/analytics",
    "navReports": exportExecutiveSummary,
    "sideOverview": () => window.location.href = currentSid ? `/dashboard?sid=${currentSid}` : "/dashboard",
    "sideSentiment": () => window.location.href = currentSid ? `/analytics?sid=${currentSid}` : "/analytics",
    "sideRawData": () => window.location.href = currentSid ? `/raw_data?sid=${currentSid}` : "/raw_data",
    "sideExport": exportExecutiveSummary,
    "sideUploadBtn": () => window.location.href = "/"
};

Object.entries(navHandlers).forEach(([id, handler]) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", (e) => {
        e.preventDefault();
        handler();
    });
});

if (refreshBtn) refreshBtn.addEventListener("click", loadAnalysis);
if (compareBtn) compareBtn.addEventListener("click", compareFiles);
if (searchBtn) searchBtn.addEventListener("click", runSearch);
if (exportSummaryBtn) exportSummaryBtn.addEventListener("click", exportExecutiveSummary);
if (exportBtn) exportBtn.addEventListener("click", exportSearch);

// Enter key triggers search
if (keywordEl) keywordEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runSearch();
});

initTheme();

// ---------------------------------------------------------
// Auto-Load Active Session on any Page Load
// ---------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
    // 1. Resolve Active Nav Glow
    const path = window.location.pathname;
    const activeMap = {
        "/dashboard": "sideOverview",
        "/analytics": "sideSentiment",
        "/raw_data":  "sideRawData"
    };
    if (activeMap[path]) {
        const el = document.getElementById(activeMap[path]);
        if (el) {
            el.classList.remove("text-zinc-500", "hover:text-zinc-300", "hover:bg-zinc-800/50");
            el.classList.add("text-cyan-400", "bg-cyan-500/10", "border-l-2", "border-cyan-400", "shadow-[0_0_15px_rgba(0,219,231,0.3)]");
        }
    }

    const subPages = ["/dashboard", "/analytics", "/raw_data"];
    const zeroStateEl = document.getElementById("zero-state");
    const dataSectionsEl = document.getElementById("data-sections");

    // 2. Handle no-session zero-state
    if (subPages.includes(path) && !currentSid) {
        setStatus("NO ACTIVE UPLINK — Initialize a session from HQ.", "error");
        if (zeroStateEl) zeroStateEl.classList.remove("hidden");
        return;
    }

    // 3. Fetch Active Session and populate
    if (currentSid) {
        try {
            setLoading(true);
            const res = await fetch(`/api/data?sid=${currentSid}`);
            const body = await res.json();
            if (!res.ok) throw new Error(body.error?.message || "Invalid Session");
            latestAnalysis = body.data;
            if (dataSectionsEl) dataSectionsEl.classList.remove("hidden");
            if (zeroStateEl) zeroStateEl.classList.add("hidden");
            renderDashboard(latestAnalysis);
            // Update avg rating display if exists
            const avgEl = document.getElementById("avgRatingCurrent");
            if (avgEl && latestAnalysis.average_rating != null) avgEl.textContent = latestAnalysis.average_rating;
        } catch (e) {
            setStatus("Session error: " + e.message, "error");
            if (zeroStateEl) zeroStateEl.classList.remove("hidden");
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    // 4. Raw Data page: show prompt if no search has been run
    if (path === "/raw_data" && currentSid) {
        const list = document.getElementById("searchResults");
        if (list && list.children.length === 0) {
            list.innerHTML = '<li class="text-zinc-600 p-8 text-center font-headline uppercase tracking-[0.2em] text-[10px]">Enter a keyword to scan the DATAMATRIX ↑</li>';
        }
    }
});

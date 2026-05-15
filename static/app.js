/**
 * Pulse — Feedback Analyzer
 * Single JS file for all pages.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function escapeHtml(v) {
  if (!v) return "";
  return String(v)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;");
}

function prefersReducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function pluralize(value, singular, plural) {
  return `${value} ${value === 1 ? singular : (plural || `${singular}s`)}`;
}

function setHtml(id, value) {
  const el = $(id);
  if (el) el.innerHTML = value;
}

function animateMetric(id, target, options = {}) {
  const el = $(id);
  if (!el) return;

  const {
    prefix = "",
    suffix = "",
    decimals = 0,
    duration = 700,
  } = options;

  const endValue = Number(target);
  if (!Number.isFinite(endValue) || prefersReducedMotion()) {
    el.textContent = `${prefix}${endValue.toFixed(decimals)}${suffix}`;
    return;
  }

  const start = performance.now();
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);

  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    const current = endValue * easeOut(progress);
    el.textContent = `${prefix}${current.toFixed(decimals)}${suffix}`;
    if (progress < 1) requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

function confidenceBand(value) {
  if (value >= 75) return "High confidence";
  if (value >= 55) return "Stable confidence";
  if (value >= 40) return "Moderate confidence";
  return "Low confidence";
}

function highlightText(text, keyword, caseSensitive) {
  if (!keyword) return escapeHtml(text);
  const flags = caseSensitive ? "g" : "gi";
  const safe = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return escapeHtml(text).replace(new RegExp(safe, flags), (m) => `<mark>${m}</mark>`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────────────────────

let _toastTimer = null;

function showToast(message, type = "info") {
  const bar = $("status-bar");
  if (!bar) return;
  bar.innerHTML = `<div class="toast-title">${escapeHtml(message)}</div>`;
  bar.className = "visible" + (type === "ok" ? " ok" : type === "error" ? " error" : "");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { bar.className = ""; }, 3500);
}

function revealContentStages() {
  document.querySelectorAll('.content-stage').forEach((el) => {
    requestAnimationFrame(() => el.classList.add('is-visible'));
  });
}

function injectSearchSkeleton() {
  const listEl = $("searchResults");
  const metaEl = $("searchMeta");
  if (!listEl) return;
  if (metaEl) metaEl.textContent = "Searching feedback…";
  listEl.innerHTML = Array.from({ length: 3 }, () => `
    <div class="result-item" aria-hidden="true">
      <div class="result-item-header" style="margin-bottom:14px;display:flex;gap:10px;flex-wrap:wrap;">
        <div class="skeleton skel" style="width:24%;min-width:80px;"></div>
        <div class="skeleton skel" style="width:16%;min-width:64px;"></div>
      </div>
      <div class="result-text">
        <div class="skeleton skel" style="height:14px;margin-bottom:10px;width:100%;"></div>
        <div class="skeleton skel" style="height:14px;width:92%;"></div>
      </div>
    </div>`).join("");
}

function setupExplorerInteractions() {
  const results = $("searchResults");
  if (!results) return;

  results.addEventListener("click", (event) => {
    const button = event.target.closest(".result-expand-btn");
    if (!button) return;
    const card = button.closest(".result-item");
    if (!card) return;
    const full = card.querySelector(".result-text-full");
    const preview = card.querySelector(".result-text-preview");
    const expanded = card.classList.toggle("expanded");
    if (full) full.hidden = !expanded;
    if (preview) preview.style.display = expanded ? "none" : "block";
    button.textContent = expanded ? "Show less" : "Show full entry";
    button.setAttribute('aria-expanded', String(expanded));
  });

  results.addEventListener("keydown", (event) => {
    const button = event.target.closest(".result-expand-btn");
    if (button && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      button.click();
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading overlay — animated steps
// ─────────────────────────────────────────────────────────────────────────────

let _stepTimers = [];

function setLoading(flag, message) {
  const overlay = $("loading-overlay");
  if (!overlay) return;
  if (flag) {
    overlay.classList.add("visible");
    _stepTimers.forEach(clearTimeout); _stepTimers = [];
    document.querySelectorAll(".loading-step").forEach((el) => {
      el.classList.remove("done","active");
      const ic = el.querySelector(".step-icon");
      if (ic) ic.textContent = "○";
    });
    const title = $("loading-title");
    if (title && message) title.textContent = message;
    _animateSteps();
  } else {
    _stepTimers.forEach(clearTimeout); _stepTimers = [];
    document.querySelectorAll(".loading-step").forEach((el) => {
      el.classList.add("done"); el.classList.remove("active");
      const ic = el.querySelector(".step-icon");
      if (ic) ic.textContent = "✓";
    });
    const t = setTimeout(() => { overlay.classList.remove("visible"); }, 280);
    _stepTimers.push(t);
  }
}

function _animateSteps() {
  const steps = document.querySelectorAll(".loading-step");
  if (!steps.length) return;
  [0, 550, 1200, 1950, 2800].forEach((delay, i) => {
    const t = setTimeout(() => {
      const ov = $("loading-overlay");
      if (!ov || !ov.classList.contains("visible")) return;
      if (i > 0) {
        const prev = steps[i-1];
        if (prev) { prev.classList.remove("active"); prev.classList.add("done"); const ic = prev.querySelector(".step-icon"); if (ic) ic.textContent = "✓"; }
      }
      const cur = steps[i];
      if (cur) { cur.classList.add("active"); const ic = cur.querySelector(".step-icon"); if (ic) ic.textContent = "●"; }
    }, delay);
    _stepTimers.push(t);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Session state
// ─────────────────────────────────────────────────────────────────────────────

const urlParams = new URLSearchParams(window.location.search);
const currentSid = urlParams.get("sid");

let latestAnalysis = null;
let latestSearch = [];
let latestKeyword = "";
// Store detailed_analysis for enriched explorer cards
let _detailedMap = {};  // feedback text → {label, confidence}

// ─────────────────────────────────────────────────────────────────────────────
// Sidebar workspace info
// ─────────────────────────────────────────────────────────────────────────────

function updateWorkspaceInfo(data) {
  const box = $("workspace-info");
  if (!box) return;
  box.style.display = "block";
  const fnEl = $("ws-filename");
  const countEl = $("ws-count");
  const timeEl = $("ws-time");
  if (fnEl && data.file) fnEl.textContent = data.file.name || "—";
  if (countEl && data.stats) countEl.textContent = (data.stats.total || 0) + " records";
  if (timeEl) timeEl.textContent = "Analyzed " + new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
}

// ─────────────────────────────────────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────────────────────────────────────

function navTo(path) {
  const sidebar = $("sidebar");
  const backdrop = $("sidebarBackdrop");
  const toggle = $("menuToggle");
  if (window.innerWidth < 1024 && sidebar) {
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("visible");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("sidebar-open");
  }
  window.location.href = currentSid ? `${path}?sid=${currentSid}` : path;
}

function setupNav() {
  const path = window.location.pathname;
  const activeMap = {
    "/":"/sideUploadBtn", "/dashboard":"sideOverview", "/analytics":"sideInsights",
    "/raw_data":"sideFeedback", "/compare":"sideCompare", "/reports":"sideReports",
  };
  Object.values(activeMap).forEach((id) => {
    const el = $(id); if (el) { el.classList.remove("active"); el.removeAttribute("aria-current"); }
  });
  const activeId = activeMap[path];
  if (activeId) { const el = $(activeId); if (el) { el.classList.add("active"); el.setAttribute("aria-current","page"); } }

  const handlers = {
    sideOverview:  () => navTo("/dashboard"),
    sideFeedback:  () => navTo("/raw_data"),
    sideInsights:  () => navTo("/analytics"),
    sideReports:   () => navTo("/reports"),
    sideCompare:   () => navTo("/compare"),
    sideUploadBtn: () => { window.location.href = "/"; },
  };
  Object.entries(handlers).forEach(([id, fn]) => {
    const el = $(id); if (el) el.addEventListener("click", (e) => { e.preventDefault(); fn(); });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Upload & Analyze
// ─────────────────────────────────────────────────────────────────────────────

async function loadAnalysis() {
  const fileEl = $("feedbackFile");
  const file = fileEl && fileEl.files && fileEl.files.length ? fileEl.files[0] : null;
  if (!file) { showToast("Please select a .txt or .csv file first.", "error"); return; }
  const fd = new FormData();
  fd.append("feedback_file", file);
  try {
    setLoading(true, `Analyzing ${file.name}…`);
    const res = await fetch("/api/analyze", { method:"POST", body:fd });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Analysis failed");
    window.location.href = `/dashboard?sid=${body.data.session_id}`;
  } catch (err) { showToast(err.message, "error"); setLoading(false); }
}

async function compareFiles() {
  const fileA = $("compareFileBaseline");
  const fileB = $("compareFile");
  const f1 = fileA && fileA.files && fileA.files.length ? fileA.files[0] : null;
  const f2 = fileB && fileB.files && fileB.files.length ? fileB.files[0] : null;
  if (!f1 || !f2) { showToast("Please select both a baseline and a candidate file.", "error"); return; }
  const fd = new FormData();
  fd.append("feedback_file", f1);
  fd.append("feedback_file_compare", f2);
  try {
    setLoading(true, "Comparing datasets…");
    const res = await fetch("/api/compare", { method:"POST", body:fd });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Comparison failed");
    const data = body.data;
    if (window.location.pathname === "/compare" && typeof window._onCompareSuccess === "function") {
      setLoading(false);
      window._onCompareSuccess(data, f1.name, f2.name);
      showToast("Comparison complete", "ok");
      if (typeof window._logActivity === "function")
        window._logActivity("success", "Datasets compared — " + f1.name + " vs " + f2.name, "Compare");
    } else {
      window.location.href = `/dashboard?sid=${data.session_id}`;
    }
  } catch (err) { showToast(err.message, "error"); setLoading(false); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Search — enriched result cards
// ─────────────────────────────────────────────────────────────────────────────

async function runSearch() {
  if (!currentSid) { showToast("No active session. Upload a file first.", "error"); return; }
  const keyword = ($("keyword") || {}).value?.trim() || "";
  const fd = new FormData();
  fd.append("sid", currentSid);
  fd.append("keyword", keyword);
  fd.append("case_sensitive", String(($("caseSensitive") || {}).checked || false));
  fd.append("match_mode", ($("matchMode") || {}).value || "partial");
  fd.append("sentiment_filter", ($("sentimentFilter") || {}).value || "all");
  const minRating = ($("minRating") || {}).value;
  if (minRating) fd.append("min_rating", minRating);

  const metaEl = $("searchMeta");
  const listEl = $("searchResults");
  if (listEl) injectSearchSkeleton();

  try {
    const res = await fetch("/api/search", { method:"POST", body:fd });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Search failed");
    const data = body.data;
    latestSearch = data.matches || [];
    latestKeyword = data.keyword || "";

    if (metaEl) {
      metaEl.textContent = data.count === 0
        ? "No results found"
        : `${data.count} result${data.count !== 1 ? "s" : ""} for "${escapeHtml(data.keyword)}"`;
    }

    if (listEl) {
      if (latestSearch.length === 0) {
        listEl.innerHTML = `<div class="empty-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <div class="empty-search-title">No results found</div>
          <div>Try broader keywords or remove filters to surface more feedback.</div>
        </div>`;
      } else {
        listEl.innerHTML = latestSearch.map((text) => {
          const detail = _detailedMap[text];
          const label = detail ? detail.label : null;
          const conf  = detail ? detail.confidence : null;
          const badgeCls = label ? {
            Positive:"badge-positive", Negative:"badge-negative",
            Neutral:"badge-neutral", Mixed:"badge-mixed"
          }[label] || "badge-neutral" : "";
          const confBar = conf != null
            ? `<div class="conf-bar-wrap">
                <div class="conf-bar-track"><div class="conf-bar-fill" style="width:${conf}%;"></div></div>
                <span>${conf}%</span>
               </div>`
            : "";
          const badge = label
            ? `<span class="badge ${badgeCls}">${escapeHtml(label)}</span>`
            : "";
          const previewText = text.length > 220 ? text.slice(0, 220) + "…" : text;
          const longText = text.length > 220 ? text : "";
          return `<div class="result-item" role="listitem">
            ${badge || conf != null ? `<div class="result-item-header">${badge}${confBar}</div>` : ""}
            <div class="result-text">
              <div class="result-text-preview">${highlightText(previewText, data.keyword, data.options?.case_sensitive)}</div>
              ${longText ? `<div class="result-text-full" hidden>${highlightText(longText, data.keyword, data.options?.case_sensitive)}</div>` : ""}
            </div>
            ${longText ? `<button type="button" class="result-expand-btn" aria-expanded="false">Show full entry</button>` : ""}
          </div>`;
        }).join("");
      }
    }
    showToast(`${data.count} result${data.count !== 1 ? "s" : ""} found`, data.count > 0 ? "ok" : "info");
  } catch (err) { showToast(err.message, "error"); }
  finally { revealContentStages(); }
}


// ─────────────────────────────────────────────────────────────────────────────
// Exports
// ─────────────────────────────────────────────────────────────────────────────

function exportExecutiveSummary() {
  if (!currentSid) { showToast("No active session to export.", "error"); return; }
  if (typeof window._logActivity === "function") window._logActivity("info","PDF report exported","PDF");
  window.location.href = `/api/export-summary-pdf?sid=${currentSid}`;
}

function exportDetailedCsv() {
  if (!currentSid) { showToast("No active session to export.", "error"); return; }
  if (typeof window._logActivity === "function") window._logActivity("info","Detailed CSV exported","CSV");
  window.location.href = `/api/export-detailed-csv?sid=${currentSid}`;
}

function exportSearch() {
  if (!currentSid) { showToast("No active session.", "error"); return; }
  if (latestSearch.length === 0) { showToast("Run a search first.", "error"); return; }
  const csv = "Feedback\n" + latestSearch.map((s) => `"${s.replace(/"/g,'""')}"`).join("\n");
  const blob = new Blob([csv], { type:"text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `search_${latestKeyword || "results"}.csv`;
  a.click(); URL.revokeObjectURL(url);
}

// ─────────────────────────────────────────────────────────────────────────────
// Render: Dashboard
// ─────────────────────────────────────────────────────────────────────────────

function renderDashboard(data) {
  const total = data.stats?.total || 0;
  const positivePct = Number(data.sentiment_percent?.Positive || 0);
  const rating = data.average_rating;
  const confidence = Number(data.overall_confidence || 0);

  animateMetric("statTotal", total, { decimals: 0, duration: 640 });
  animateMetric("statPositive", positivePct, { decimals: 1, suffix: "%", duration: 760 });
  if (rating != null) animateMetric("statRating", Number(rating), { decimals: 2, suffix: " / 5", duration: 760 });
  else setText("statRating", "N/A");
  animateMetric("statConfidence", confidence, { decimals: 1, suffix: "%", duration: 760 });

  renderDashboardStories(data);
  renderDashboardNarrative(data);
  renderConfidenceSummary(data);

  if (data.sentiment_percent && typeof window._buildSentimentChart === "function")
    window._buildSentimentChart(data);

  if (data.categories && typeof window._buildCategoryChart === "function")
    window._buildCategoryChart(data);

  if (typeof window._buildConfidenceChart === "function")
    window._buildConfidenceChart(data);

  const ratingSection = $("ratingSection");
  if (data.rating_distribution) {
    if (ratingSection) ratingSection.style.display = "block";
    if (typeof window._buildRatingChart === "function")
      window._buildRatingChart(data);
  } else if (ratingSection) {
    ratingSection.style.display = "none";
  }

  // Business insights
  renderStrengths(data.business_insights?.top_strengths);
  renderComplaints(data.business_insights?.top_complaints);
  renderSuggestions(data.suggestions);

  // Comparison
  if (data.comparison) renderComparison(data.comparison);

  // Success banner
  const banner = $("successBanner");
  const bannerText = $("successBannerText");
  if (banner && bannerText && data.stats?.total) {
    bannerText.textContent = `Analysis complete — ${data.stats.total} feedback entries processed`;
    banner.style.display = "flex";
    setTimeout(() => { if (banner) banner.style.display = "none"; }, 5000);
  }

  updateWorkspaceInfo(data);
}

function renderDashboardStories(data) {
  const total = data.stats?.total || 0;
  const sentimentPercent = data.sentiment_percent || {};
  const sentimentEntries = Object.entries(sentimentPercent).sort((a, b) => b[1] - a[1]);
  const [topSentiment, topSentimentValue] = sentimentEntries[0] || ["Positive", 0];
  const categories = Object.entries(data.categories || {}).sort((a, b) => b[1] - a[1]);
  const [topCategory, topCategoryCount] = categories[0] || ["Uncategorized", 0];
  const rating = data.average_rating;

  const cards = [
    {
      eyebrow: "Sentiment lead",
      title: `${topSentiment} sentiment leads at ${Number(topSentimentValue || 0).toFixed(1)}%`,
      copy: `${pluralize(data.sentiment?.[topSentiment] || 0, "entry")} currently land in the strongest segment.`,
    },
    {
      eyebrow: "Category focus",
      title: `${topCategory} generates the highest feedback volume`,
      copy: `${pluralize(topCategoryCount, "entry")} from ${pluralize(total, "record")} sit in this category.`,
    },
    {
      eyebrow: "Quality signal",
      title: rating != null ? `Average rating holds at ${rating}/5` : `Confidence sits at ${data.overall_confidence || 0}%`,
      copy: rating != null
        ? `${confidenceBand(Number(data.overall_confidence || 0))} supports the current rating signal.`
        : `Use the confidence meter to judge how decisive the sentiment labels are.`,
    },
  ];

  setHtml("dashboardStories", cards.map((card) => `
    <div class="story-card">
      <div class="story-eyebrow">${escapeHtml(card.eyebrow)}</div>
      <div class="story-title">${escapeHtml(card.title)}</div>
      <div class="story-copy">${escapeHtml(card.copy)}</div>
    </div>
  `).join(""));
}

function renderDashboardNarrative(data) {
  const total = data.stats?.total || 0;
  const sentimentPercent = data.sentiment_percent || {};
  const categories = Object.entries(data.categories || {}).sort((a, b) => b[1] - a[1]);
  const [topCategory, topCategoryCount] = categories[0] || ["Uncategorized", 0];
  const ratingDistribution = data.rating_distribution || {};
  const ratingTop = Object.entries(ratingDistribution).sort((a, b) => Number(b[1]) - Number(a[1]))[0];

  setText("sentimentTotal", pluralize(total, "entry"));
  setText("categoryKicker", categories.length ? `${categories.length} categories` : "Live split");
  setText("ratingKicker", ratingTop ? `${ratingTop[0]}* leads` : "Histogram");

  setText(
    "sentimentStory",
    `Positive, negative, neutral, and mixed feedback are shown in one responsive stack so proportions stay easy to compare at a glance.`
  );
  setText(
    "categoryStory",
    categories.length
      ? `${topCategory} contributes ${topCategoryCount} ${topCategoryCount === 1 ? "entry" : "entries"}, making it the largest source of feedback volume.`
      : "Category distribution will appear here after analysis."
  );

  if (data.rating_distribution) {
    const count = ratingTop ? Number(ratingTop[1]) : 0;
    const pct = total ? ((count / total) * 100).toFixed(1) : "0.0";
    setText(
      "ratingStory",
      ratingTop
        ? `${ratingTop[0]}* reviews are the most common band with ${count} entries, representing ${pct}% of rated feedback.`
        : "Rating distribution will appear here after analysis."
    );
  }
}

function renderConfidenceSummary(data) {
  const confidence = Number(data.overall_confidence || 0);
  const scale = [
    { label: "Low", active: confidence < 40 },
    { label: "Moderate", active: confidence >= 40 && confidence < 55 },
    { label: "Stable", active: confidence >= 55 && confidence < 75 },
    { label: "High", active: confidence >= 75 },
  ];

  animateMetric("confidenceMetricValue", confidence, { decimals: 1, suffix: "%", duration: 760 });
  setText(
    "confidenceMetricCopy",
    confidence >= 75
      ? "The sentiment model is reading feedback with strong separation between positive and negative language."
      : confidence >= 55
        ? "Signals are consistent enough to trust directional changes while still watching mixed and neutral feedback."
        : confidence >= 40
          ? "Interpret this dataset with some caution because the language mix is less decisive."
          : "Confidence is soft here, so this analysis is best used as a directional starting point."
  );
  setText("confidenceStory", `${confidenceBand(confidence)} across the full dataset.`);
  setHtml(
    "confidenceScale",
    scale.map((item) => `<span class="confidence-chip${item.active ? " is-active" : ""}">${escapeHtml(item.label)}</span>`).join("")
  );
}

function setText(id, value) {
  const el = $(id); if (el) el.textContent = value;
}

function renderStrengths(items) {
  const el = $("topStrengths"); if (!el) return;
  if (!items || items.length === 0) { el.innerHTML = `<div style="font-size:13px;color:var(--muted);">No strengths detected.</div>`; return; }
  el.innerHTML = items.map((s) => `
    <div class="insight-item">
      <span class="insight-item-icon" style="color:var(--success);">✓</span>
      <span>${escapeHtml(s)}</span>
    </div>`).join("");
}

function renderComplaints(items) {
  const el = $("topComplaints"); if (!el) return;
  if (!items || items.length === 0) { el.innerHTML = `<div style="font-size:13px;color:var(--muted);">No major complaints detected.</div>`; return; }
  el.innerHTML = items.map((c) => `
    <div class="insight-item">
      <span class="insight-item-icon" style="color:var(--error);">⚠</span>
      <span>${escapeHtml(c)}</span>
    </div>`).join("");
}

function renderSuggestions(items) {
  const el = $("suggestions"); if (!el) return;
  if (!items || items.length === 0) { el.innerHTML = `<div style="font-size:13px;color:var(--muted);">No recommendations available.</div>`; return; }
  el.innerHTML = items.map((s) => `
    <div class="insight-item">
      <span class="insight-item-icon" style="color:var(--primary);">💡</span>
      <span>${escapeHtml(s)}</span>
    </div>`).join("");
}

function renderComparison(comparison) {
  const panel = $("comparePanel"); if (!panel) return;
  panel.style.display = "block";
  const delta = comparison.delta;
  const candidate = comparison.candidate;
  const deltas = [
    { label:"Volume change",      value:delta.total_feedback_delta, suffix:" records", positive:delta.total_feedback_delta > 0 },
    { label:"Positive sentiment", value:delta.positive_pct_delta,   suffix:"%",        positive:delta.positive_pct_delta > 0 },
    { label:"Negative sentiment", value:delta.negative_pct_delta,   suffix:"%",        positive:delta.negative_pct_delta < 0 },
    { label:"Avg rating",         value:delta.avg_rating_delta,     suffix:"",         positive:(delta.avg_rating_delta||0) > 0 },
  ];
  const container = $("compareDeltas"); if (!container) return;
  container.className = "compare-deltas-grid";
  container.innerHTML = deltas.map((d) => {
    const val = d.value;
    const isNull = val === null || val === undefined;
    const sign = !isNull && val > 0 ? "+" : "";
    const neutral = !isNull && val === 0;
    const cls = isNull || neutral ? "delta-neutral" : d.positive ? "delta-up" : "delta-down";
    const arrow = isNull ? "" : val > 0 ? "↑" : val < 0 ? "↓" : "→";
    const note = d.label === "Positive sentiment"
      ? (val > 0 ? "Candidate gained positive share" : val < 0 ? "Positive share softened" : "Positive share held steady")
      : d.label === "Negative sentiment"
        ? (val < 0 ? "Complaint share improved" : val > 0 ? "Complaint share increased" : "Complaint share held steady")
        : d.label === "Avg rating"
          ? (val > 0 ? "Customer scoring improved" : val < 0 ? "Customer scoring declined" : "Rating held steady")
          : (val > 0 ? "Candidate volume increased" : val < 0 ? "Candidate volume decreased" : "Volume matched baseline");
    return `<div style="text-align:center;">
      <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;color:var(--muted);margin-bottom:8px;">${escapeHtml(d.label)}</div>
      <div class="compare-delta ${cls}">${arrow} ${isNull ? "N/A" : sign + val + d.suffix}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:6px;line-height:1.45;">${escapeHtml(note)}</div>
      ${candidate.average_rating != null && d.label === "Avg rating"
        ? `<div style="font-size:11px;color:var(--muted);margin-top:4px;">Candidate: ${candidate.average_rating}</div>` : ""}
    </div>`;
  }).join("");
}

// ─────────────────────────────────────────────────────────────────────────────
// Render: Analytics
// ─────────────────────────────────────────────────────────────────────────────

function renderAnalytics(data) {
  renderInsightsSummary(data);
  renderTopWords(data.top_words);
  renderNegativeWords(data.negative_top_words);
  renderPositiveWords(data.positive_top_words);
  renderPriorityInsights(data.priority_insights);
  updateWorkspaceInfo(data);
}

function renderInsightsSummary(data) {
  const priorities = data.priority_insights || [];
  const strongestPositive = data.positive_top_words?.[0];
  const strongestNegative = data.negative_top_words?.[0];

  const cards = [
    {
      label: "Priority queue",
      title: priorities.length ? `${priorities.length} action${priorities.length === 1 ? "" : "s"} need attention` : "No urgent actions surfaced",
      copy: priorities.length
        ? `${escapeHtml(priorities[0].title)} is currently the highest-impact recommendation.`
        : "This dataset is not surfacing critical follow-up actions right now.",
    },
    {
      label: "Positive lead",
      title: strongestPositive ? `"${strongestPositive.word}" is the strongest positive signal` : "No strong positive pattern detected",
      copy: strongestPositive
        ? `${pluralize(strongestPositive.count, "mention")} reinforce this strength in the current dataset.`
        : "Positive signal density is limited in this file.",
    },
    {
      label: "Risk cue",
      title: strongestNegative ? `"${strongestNegative.word}" is the loudest complaint cue` : "Negative language remains limited",
      copy: strongestNegative
        ? `${pluralize(strongestNegative.count, "mention")} point to a recurring issue worth monitoring.`
        : "Negative signal density is currently subdued.",
    },
  ];

  setHtml("insightsSummary", cards.map((card) => `
    <div class="summary-card">
      <div class="summary-label">${card.label}</div>
      <div class="summary-title">${card.title}</div>
      <div class="summary-copy">${card.copy}</div>
    </div>
  `).join(""));
}

function renderTopWords(words) {
  const el = $("topWords"); if (!el || !words) return;
  const topWord = words[0];
  if ($("topWordsChip")) $("topWordsChip").textContent = topWord ? `${topWord.word} leads` : "Top terms";
  el.innerHTML = words.map(({ word, count }) => `
    <div class="word-tag" role="listitem" title="${escapeHtml(word)} appears ${count} times">
      <span class="word-tag-label">${escapeHtml(word)}</span>
      <span class="word-tag-count">${count}</span>
    </div>`).join("");
}

function renderNegativeWords(words) {
  const el = $("negativeWords"); if (!el || !words) return;
  if (words.length === 0) { el.innerHTML = `<div style="font-size:13px;color:var(--muted);">No negative signals detected.</div>`; return; }
  const max = Math.max(...words.map((w) => w.count), 1);
  if ($("negWordsChip")) $("negWordsChip").textContent = `${words.length} tracked`;
  el.innerHTML = words.map(({ word, count }, index) => `
    <div class="signal-row" role="listitem">
      <div class="signal-rank">${index + 1}</div>
      <div class="signal-word">
        <div class="signal-word-label" style="color:var(--error);">${escapeHtml(word)}</div>
        <div class="signal-track" aria-hidden="true">
          <div class="signal-fill" style="width:${(count/max)*100}%;background:linear-gradient(90deg, rgba(200,91,91,0.5), rgba(200,91,91,0.95));"></div>
        </div>
      </div>
      <div class="signal-meta">${count}</div>
    </div>`).join("");
}

function renderPositiveWords(words) {
  const el = $("positiveWords"); if (!el || !words) return;
  if (words.length === 0) { el.innerHTML = `<div style="font-size:13px;color:var(--muted);">No positive signals detected.</div>`; return; }
  const max = Math.max(...words.map((w) => w.count), 1);
  if ($("posWordsChip")) $("posWordsChip").textContent = `${words.length} tracked`;
  el.innerHTML = words.map(({ word, count }, index) => `
    <div class="signal-row" role="listitem">
      <div class="signal-rank">${index + 1}</div>
      <div class="signal-word">
        <div class="signal-word-label" style="color:var(--success);">${escapeHtml(word)}</div>
        <div class="signal-track" aria-hidden="true">
          <div class="signal-fill" style="width:${(count/max)*100}%;background:linear-gradient(90deg, rgba(82,165,107,0.5), rgba(82,165,107,0.95));"></div>
        </div>
      </div>
      <div class="signal-meta">${count}</div>
    </div>`).join("");
}

function renderPriorityInsights(items) {
  const el = $("priorityInsights"); if (!el || !items) return;
  if (items.length === 0) { el.innerHTML = `<div style="font-size:13px;color:var(--muted);">No priority actions identified.</div>`; return; }
  el.innerHTML = items.map((item, i) => `
    <div class="priority-item" role="listitem">
      <div class="priority-num" aria-hidden="true">${i+1}</div>
      <div class="priority-body">
        <div class="priority-title">${escapeHtml(item.title)}</div>
        <div class="priority-evidence">${escapeHtml(item.evidence)}</div>
        <div class="priority-action">→ ${escapeHtml(item.action)}</div>
      </div>
      <div class="priority-score" aria-label="Impact score ${item.score}">Impact ${item.score}</div>
    </div>`).join("");
}

// ─────────────────────────────────────────────────────────────────────────────
// Session loader
// ─────────────────────────────────────────────────────────────────────────────

async function loadSession() {
  const path = window.location.pathname;
  const subPages = ["/dashboard","/analytics","/raw_data","/reports","/compare"];
  if (!subPages.includes(path)) return;

  const zeroEl = $("zero-state");
  const dataEl = $("data-sections");
  const explorerEl = $("explorerSection");

  if (path === "/compare" || path === "/reports") {
    if (currentSid) {
      try {
        const res = await fetch(`/api/data?sid=${currentSid}`);
        const body = await res.json();
        if (res.ok) { latestAnalysis = body.data; updateWorkspaceInfo(latestAnalysis); }
      } catch (_) {}
    }
    return;
  }

  if (!currentSid) { if (zeroEl) zeroEl.style.display = "block"; return; }

  if (dataEl) {
    dataEl.style.display = "block";
  }
  if (window.location.pathname === "/raw_data" && explorerEl) {
    explorerEl.style.display = "block";
  }

  try {
    if (dataEl) {
      dataEl.classList.add('page-loading');
    }
    setLoading(true, "Loading analysis…");
    const res = await fetch(`/api/data?sid=${currentSid}`);
    const body = await res.json();
    if (!res.ok) throw new Error(body.error?.message || "Session expired");
    latestAnalysis = body.data;

    // Build detailed map for enriched explorer cards
    if (latestAnalysis.detailed_analysis) {
      _detailedMap = {};
      latestAnalysis.detailed_analysis.forEach((d) => {
        _detailedMap[d.feedback] = { label: d.label, confidence: d.confidence };
      });
    }

    if (zeroEl) zeroEl.style.display = "none";

    if (path === "/dashboard") {
      if (dataEl) dataEl.style.display = "block";
      renderDashboard(latestAnalysis);
    } else if (path === "/analytics") {
      if (dataEl) dataEl.style.display = "block";
      renderAnalytics(latestAnalysis);
    } else if (path === "/raw_data") {
      if (explorerEl) explorerEl.style.display = "block";
      updateWorkspaceInfo(latestAnalysis);
    }

    showToast("Analysis loaded", "ok");
  } catch (err) {
    if (zeroEl) zeroEl.style.display = "block";
    showToast(err.message, "error");
  } finally {
    setLoading(false);
    if (dataEl) {
      dataEl.classList.remove('page-loading');
    }
    revealContentStages();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Wire buttons
// ─────────────────────────────────────────────────────────────────────────────

function wireButtons() {
  const map = {
    refreshBtn: loadAnalysis, compareBtn: compareFiles,
    searchBtn: runSearch, exportBtn: exportSearch,
    exportSummaryBtn: exportExecutiveSummary,
    downloadPdfBtn: exportExecutiveSummary,
    downloadCsvBtn: exportDetailedCsv,
  };
  Object.entries(map).forEach(([id, fn]) => {
    const el = $(id); if (el) el.addEventListener("click", fn);
  });
  const kw = $("keyword");
  if (kw) kw.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
}

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  setupNav();
  wireButtons();
  setupExplorerInteractions();
  loadSession();
});

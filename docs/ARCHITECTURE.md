# Architecture

## Overview

Pulse is a single-server Flask application. All analysis runs synchronously in the request cycle — no background workers, no external AI APIs, no database.

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser                                │
│                                                                 │
│  home.html ──► /api/analyze ──► dashboard.html                  │
│  compare.html ─► /api/compare ──► compare results (inline)      │
│  raw_data.html ─► /api/search ──► results list                  │
│  reports.html ──► /api/export-summary-pdf                       │
│                ──► /api/export-detailed-csv                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────────┐
│                        Flask (app.py)                           │
│                                                                 │
│  Routes          Middleware          Error handlers             │
│  ─────────       ──────────          ────────────────           │
│  GET  /          Rate limiter        AnalysisError → 400        │
│  GET  /dashboard Session cleanup     RequestEntityTooLarge→413  │
│  GET  /analytics Security headers    ValidationError → 500      │
│  GET  /raw_data  ProxyFix (opt.)     HTTPException → varies     │
│  GET  /compare                                                  │
│  GET  /reports                                                  │
│  POST /api/analyze                                              │
│  POST /api/compare                                              │
│  GET  /api/data                                                 │
│  POST /api/search                                               │
│  GET  /api/export-summary-pdf                                   │
│  GET  /api/export-detailed-csv                                  │
│  GET  /api/health                                               │
└──────┬──────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                   analysis_service.py                           │
│                                                                 │
│  parse_uploaded_feedback()   ← decodes file, validates headers  │
│  build_analysis_payload()    ← orchestrates all analysis        │
│  search_feedback()           ← keyword + filter matching        │
│  generate_detailed_csv()     ← per-entry CSV builder            │
└──────┬──────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                   feedback_analyzer.py                          │
│                                                                 │
│  analyze_sentiment()    weighted vocab + negation + multilingual│
│  detect_categories()    keyword pattern matching (5 categories) │
│  word_frequency()       top-N words, stop-word filtered         │
│  get_statistics()       total, avg_length, shortest, longest    │
│  rating_distribution()  1–5 star counts from CSV rows           │
│  normalize_text()       mojibake repair, encoding normalization │
└─────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                      pdf_export.py                              │
│                                                                 │
│  build_executive_summary_pdf()  ReportLab PDF, 2 pages          │
│  _sentiment_pie()               Pie chart with legend           │
│  _bar_chart_with_labels()       Bar chart with value labels     │
│  _generate_executive_summary()  Data-driven prose paragraph     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Session Storage

Sessions are stored in a module-level dict (`SERVER_SESSIONS`) protected by a `threading.Lock`.

```python
SERVER_SESSIONS[sid] = {
    "parsed":       ParsedFeedback,   # raw rows + feedback list
    "analysis":     dict,             # full analysis payload
    "comparison":   dict | None,      # present only for /api/compare
    "created_at":   float,            # unix timestamp
    "last_accessed": float,           # updated on every access
}
```

**Limitations:**
- Not shared across multiple worker processes (use Redis for multi-worker)
- Lost on server restart
- Max 1000 sessions by default (configurable via `MAX_SESSIONS`)

---

## Sentiment Engine

The sentiment engine in `feedback_analyzer.py` uses a rule-based approach:

```
Input text
    │
    ▼
normalize_text()          ← repair mojibake, preserve emojis
preprocess_text()         ← strip junk symbols, collapse spaces
    │
    ▼
Context patterns          ← "high quality" → +2, "long wait" → -2
    │
    ▼
Weighted vocabulary       ← "excellent" → +3, "bad" → -2
  + negation check        ← "not good" flips polarity
    │
    ▼
Multilingual mapping      ← "excelente" → "excellent" → +3
    │
    ▼
Classification
  pos_score > neg_score   → Positive
  neg_score > pos_score   → Negative
  both present, balanced  → Mixed  (balance ≥ 0.35)
  neither                 → Neutral
    │
    ▼
Confidence scoring
  Mixed:    strength×0.7 + balance×0.3
  One-sided: strength×0.6 + dominance×0.4
  Density cap for short texts (≤2 words: ×0.6, ≤4 words: ×0.8)
```

**Vocabulary sizes:**
- English positive: ~50 words (weights 1–3)
- English negative: ~55 words (weights 1–3)
- Domain-specific: ~20 additional terms
- Multilingual: ~22 Spanish + French terms
- Context patterns: 12 multi-word phrases

---

## Frontend Architecture

Single-page-per-route with shared JS (`static/app.js`).

```
base.html          ← layout: sidebar, topbar, loading overlay, FAB, toast
    │
    ├── home.html       ← upload + compare upload
    ├── dashboard.html  ← stats, sentiment, categories, insights
    ├── analytics.html  ← word signals, priority actions
    ├── raw_data.html   ← search explorer
    ├── compare.html    ← dataset comparison with inline results
    └── reports.html    ← export actions + activity feed

app.js
    ├── setLoading()         progress overlay with animated steps
    ├── showToast()          bottom toast notification
    ├── setupNav()           active state + aria-current + click handlers
    ├── loadAnalysis()       POST /api/analyze → redirect to dashboard
    ├── compareFiles()       POST /api/compare → inline results or redirect
    ├── runSearch()          POST /api/search → render results
    ├── exportExecutiveSummary()  GET /api/export-summary-pdf
    ├── exportDetailedCsv()       GET /api/export-detailed-csv
    ├── exportSearch()            client-side CSV from search results
    ├── loadSession()        GET /api/data → render appropriate page
    ├── renderDashboard()    stats + sentiment + categories + insights
    └── renderAnalytics()    word lists + priority actions
```

Session ID (`sid`) is passed as a URL query parameter and preserved across all navigation.

---

## Security

| Mechanism | Implementation |
|---|---|
| Rate limiting | In-memory per-IP, 60 req/min default |
| File validation | Extension whitelist, size limit, empty check |
| Filename sanitization | `werkzeug.utils.secure_filename` |
| Input escaping | `escapeHtml()` in JS, `saxutils.escape()` in PDF |
| Security headers | CSP, X-Frame-Options, HSTS, Referrer-Policy |
| Session isolation | UUID v4 session IDs, server-side storage |
| Cache prevention | `Cache-Control: no-store` on all API responses |

---

## Deployment

**Render (recommended):**
```yaml
# render.yaml already configured
services:
  - type: web
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
```

**Docker:**
```bash
docker build -t pulse-analyzer .
docker run -p 8000:8000 \
  -e MAX_UPLOAD_MB=10 \
  -e SESSION_TTL_MINUTES=60 \
  pulse-analyzer
```

**Environment variables:** See `.env.example` for full list.

# API Reference

All API endpoints return JSON with the envelope:

```json
{ "ok": true,  "data": { ... } }
{ "ok": false, "error": { "code": "...", "message": "..." } }
```

---

## POST /api/analyze

Upload a feedback file for analysis.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `feedback_file` | File | Yes | `.txt` or `.csv` file, max 5 MB |

**Response `data`:**

```json
{ "session_id": "uuid-string" }
```

**Errors:**

| Code | Status | Meaning |
|---|---|---|
| `bad_request` | 400 | Missing file, wrong extension, empty file |
| `file_too_large` | 413 | File exceeds `MAX_UPLOAD_MB` |
| `capacity_exceeded` | 503 | Server session limit reached |

---

## POST /api/compare

Upload two files and get side-by-side delta analysis.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `feedback_file` | File | Yes | Baseline dataset |
| `feedback_file_compare` | File | Yes | Candidate dataset |

**Response `data`:**

```json
{
  "session_id": "uuid",
  "baseline":  { /* full analysis payload */ },
  "candidate": { /* full analysis payload */ },
  "delta": {
    "total_feedback_delta": 5,
    "positive_pct_delta": 12.3,
    "negative_pct_delta": -8.1,
    "avg_rating_delta": 0.4
  }
}
```

---

## GET /api/data?sid=

Retrieve the full analysis payload for an active session.

**Query params:**

| Param | Required | Description |
|---|---|---|
| `sid` | Yes | Session ID from `/api/analyze` or `/api/compare` |

**Response `data` (analysis payload):**

```json
{
  "source": "uploaded_csv",
  "file": { "name": "feedback.csv", "extension": ".csv", "size_bytes": 4096 },
  "stats": { "total": 50, "avg_length": 82.4, "shortest": "...", "longest": "..." },
  "sentiment": { "Positive": 30, "Negative": 10, "Neutral": 5, "Mixed": 5 },
  "sentiment_percent": { "Positive": 60.0, "Negative": 20.0, "Neutral": 10.0, "Mixed": 10.0 },
  "sentiment_series": [ { "label": "Positive", "count": 30 }, ... ],
  "top_words": [ { "word": "delivery", "count": 12 }, ... ],
  "negative_top_words": [ { "word": "slow", "count": 5 }, ... ],
  "positive_top_words": [ { "word": "great", "count": 8 }, ... ],
  "categories": { "Product": 18, "Delivery": 14, "Service": 10, "Price": 5, "Support": 3 },
  "rating_distribution": { "1": 2, "2": 4, "3": 8, "4": 20, "5": 16 },
  "average_rating": 3.88,
  "overall_confidence": 62.4,
  "suggestions": [ "Negative sentiment at 20% warrants monitoring..." ],
  "priority_insights": [
    {
      "title": "Reduce negative sentiment",
      "score": 36.0,
      "evidence": "Negative sentiment is 20%",
      "action": "Review and resolve top negative comments in the next cycle."
    }
  ],
  "business_insights": {
    "top_strengths": [ "Delivery performance (71% positive)" ],
    "top_complaints": [ "Service friction (40% negative)" ]
  },
  "detailed_analysis": [
    { "feedback": "Great product!", "label": "Positive", "confidence": 72.5 }
  ],
  "comparison": { /* present only when session was created via /api/compare */ }
}
```

---

## POST /api/search

Search feedback entries with filters.

**Request:** `application/x-www-form-urlencoded` or `multipart/form-data`

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `sid` | string | Yes | — | Active session ID |
| `keyword` | string | Yes | — | Search term |
| `case_sensitive` | bool | No | `false` | Case-sensitive matching |
| `match_mode` | string | No | `partial` | `partial` or `exact` |
| `sentiment_filter` | string | No | `all` | `all`, `positive`, `negative`, `neutral`, `mixed` |
| `min_rating` | int | No | — | Minimum rating 1–5 (CSV only) |

**Response `data`:**

```json
{
  "keyword": "delivery",
  "count": 14,
  "matches": [ "Fast delivery, arrived next day.", ... ],
  "options": {
    "case_sensitive": false,
    "match_mode": "partial",
    "sentiment_filter": "all",
    "min_rating": null
  }
}
```

Results are capped at 200 matches.

---

## GET /api/export-summary-pdf?sid=

Download a two-page PDF executive summary.

**Response:** `application/pdf` — file download

Filename: `executive_summary_{sid[:8]}.pdf`

Contents:
- Page 1: Snapshot table, sentiment pie chart, rating bar chart, category bar chart
- Page 2: Business insights, top priorities, category breakdown, recommended actions

---

## GET /api/export-detailed-csv?sid=

Download a CSV with per-entry sentiment labels.

**Response:** `text/csv` — file download

Filename: `detailed_analysis_{sid[:8]}.csv`

**Columns (TXT upload):** `Feedback`, `Sentiment`, `Confidence`

**Columns (CSV upload):** `Name`, `Rating`, `Category`, `Sentiment`, `Confidence`, `Feedback`

---

## GET /api/health

Health check endpoint.

**Response:**
```json
{ "ok": true, "data": { "status": "ok" } }
```

---

## Error Codes

| Code | HTTP Status | Description |
|---|---|---|
| `bad_request` | 400 | Invalid input (missing file, bad format, etc.) |
| `MISSING_SESSION` | 400 | Session ID missing or expired |
| `file_too_large` | 413 | File exceeds size limit |
| `rate_limited` | 429 | Too many requests from this IP |
| `capacity_exceeded` | 503 | Server at max session capacity |
| `internal_error` | 500 | Unexpected server error |
| `schema_error` | 500 | Response schema validation failure |

---

## Session Lifecycle

Sessions are stored in-memory on the server.

- Created by: `POST /api/analyze` or `POST /api/compare`
- TTL: configurable via `SESSION_TTL_MINUTES` (default: 30 minutes)
- TTL resets on each access to `/api/data`, `/api/search`, `/api/export-*`
- Cleanup: runs every 5 minutes, evicts sessions past TTL
- Max sessions: configurable via `MAX_SESSIONS` (default: 1000)

Sessions are **not** persisted across server restarts.

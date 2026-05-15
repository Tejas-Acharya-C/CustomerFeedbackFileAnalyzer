# Pulse — Customer Feedback Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

A production-quality web application for analyzing customer feedback files. Upload a `.txt` or `.csv` file and get sentiment analysis, category breakdown, business insights, and exportable reports — all in seconds.

---

## Overview

Pulse processes raw customer feedback and surfaces:

- **Sentiment distribution** — Positive, Negative, Neutral, Mixed with confidence scores
- **Category detection** — Product, Delivery, Service, Price, Support
- **Business insights** — Top strengths, complaints, and recommended actions
- **Dataset comparison** — Side-by-side delta analysis between two files
- **Exportable reports** — PDF executive summary and detailed CSV

The entire analysis runs server-side with no external AI APIs. The sentiment engine uses a weighted vocabulary dictionary with negation handling, multilingual support (Spanish, French), and context-aware patterns.

---

## Features

| Feature | Description |
|---|---|
| Upload TXT / CSV | Drag-and-drop or browse. Supports UTF-8, Latin-1 encoding |
| Sentiment Analysis | 4-class: Positive / Negative / Neutral / Mixed with per-entry confidence |
| Category Detection | 5 categories auto-detected from keyword patterns |
| Business Insights | Strengths, complaints, and action recommendations derived from data |
| Feedback Explorer | Search by keyword with sentiment filter, rating filter, match mode |
| Dataset Comparison | Upload two files, get volume/sentiment/rating deltas side by side |
| PDF Export | 2-page executive summary with charts (pie + bar) via ReportLab |
| CSV Export | Per-entry CSV with sentiment label, confidence, and original fields |
| Session Management | Server-side sessions with TTL, rate limiting, and capacity controls |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, Flask 3.x |
| Validation | Pydantic v2 |
| PDF Generation | ReportLab |
| Frontend | Vanilla JS, Tailwind CSS (CDN), Inter font |
| Testing | Pytest |
| Deployment | Docker, Render (via `render.yaml`) |

---

## Architecture

```
Browser
  │
  ├── GET /              → home.html      (upload page)
  ├── GET /dashboard     → dashboard.html (overview + stats)
  ├── GET /analytics     → analytics.html (word signals + priorities)
  ├── GET /raw_data      → raw_data.html  (feedback explorer + search)
  ├── GET /compare       → compare.html   (dataset comparison)
  └── GET /reports       → reports.html   (export actions + activity)

Flask API
  ├── POST /api/analyze          → parse file → build payload → return session_id
  ├── POST /api/compare          → parse 2 files → compute deltas → return session_id
  ├── GET  /api/data?sid=        → return full analysis payload for session
  ├── POST /api/search           → keyword + filters → return matching feedback
  ├── GET  /api/export-summary-pdf?sid=   → ReportLab PDF
  └── GET  /api/export-detailed-csv?sid=  → CSV with sentiment labels

Analysis Pipeline (analysis_service.py + feedback_analyzer.py)
  ├── parse_uploaded_feedback()  → decode, validate, extract rows
  ├── analyze_sentiment()        → weighted vocab + negation + multilingual
  ├── detect_categories()        → keyword pattern matching
  ├── word_frequency()           → top N words excluding stop words
  ├── _business_insights()       → strengths + complaints from category sentiment
  └── _priority_insights()       → ranked action items from metrics
```

---

## Installation

```bash
git clone <your-repo-url>
cd "Customer Feedback File Analyzer Project"
pip install -r requirements.txt
```

### Environment

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_MB` | `5` | Max file size in MB |
| `SESSION_TTL_MINUTES` | `30` | Session expiry time |
| `RATE_LIMIT_PER_MIN` | `60` | API requests per IP per minute |
| `MAX_SESSIONS` | `1000` | Max concurrent sessions |
| `FLASK_DEBUG` | `false` | Enable debug mode |
| `REPORT_BRAND_NAME` | `Customer Feedback Pulse` | PDF header brand name |

---

## Running

**Development:**
```bash
python app.py
```
Visit `http://127.0.0.1:5000`

**Production (Gunicorn):**
```bash
gunicorn wsgi:app
```

**Docker:**
```bash
docker build -t pulse-analyzer .
docker run -p 8000:8000 pulse-analyzer
```

---

## CSV Format

For structured analysis with ratings and categories, use this CSV format:

```csv
Name,Rating,Category,Feedback
Alice,5,Product,Excellent quality and fast delivery
Bob,2,Support,Support team never responded to my emails
Carol,4,Delivery,Arrived on time but packaging was damaged
```

Required columns: `Name`, `Rating` (1–5), `Category`, `Feedback`

TXT files: one feedback entry per line.

---

## Workflow

```
1. Upload a .txt or .csv file on the home page
2. Click "Analyze Feedback" → redirected to Dashboard
3. View sentiment distribution, category breakdown, business insights
4. Navigate to Insights for word signals and priority actions
5. Navigate to Feedback Explorer to search and filter individual entries
6. Navigate to Compare to upload a second file and see deltas
7. Navigate to Reports to export PDF or CSV
```

---

## API Routes

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/analyze` | Upload file, returns `session_id` |
| `POST` | `/api/compare` | Upload 2 files, returns `session_id` + deltas |
| `GET` | `/api/data?sid=` | Full analysis payload for session |
| `POST` | `/api/search` | Search feedback with filters |
| `GET` | `/api/export-summary-pdf?sid=` | Download PDF report |
| `GET` | `/api/export-detailed-csv?sid=` | Download detailed CSV |
| `GET` | `/api/health` | Health check |

---

## Testing

```bash
pytest
```

Run specific test files:
```bash
pytest tests/test_api.py -v
pytest tests/test_service.py -v
pytest tests/test_sentiment_accuracy.py -v
```

---

## Project Structure

```
├── app.py                  Flask application factory + routes
├── wsgi.py                 Production WSGI entry point
├── analysis_service.py     Business logic: parsing, payload building, CSV export
├── feedback_analyzer.py    Core NLP: sentiment, categories, word frequency
├── pdf_export.py           ReportLab PDF generation
├── api_schemas.py          Pydantic request/response schemas
├── requirements.txt        Production dependencies
├── requirements-dev.txt    Development + test dependencies
├── Dockerfile              Container definition
├── render.yaml             Render deployment config
├── .env.example            Environment variable template
├── static/
│   └── app.js              Single JS file for all pages
├── templates/
│   ├── base.html           Shared layout: sidebar, topbar, loading, toast
│   ├── home.html           Upload page
│   ├── dashboard.html      Overview: stats, sentiment, categories, insights
│   ├── analytics.html      Word signals, positive/negative keywords, priorities
│   ├── raw_data.html       Feedback explorer with search and filters
│   ├── compare.html        Dataset comparison with inline delta results
│   └── reports.html        Export actions and activity feed
├── tests/                  Pytest test suite
└── data/                   Sample feedback files
    ├── feedback.csv
    └── feedback.txt
```

---

## Future Improvements

- Persistent session storage (Redis) for multi-worker deployments
- Batch file upload for analyzing multiple datasets at once
- Trend visualization across multiple historical uploads
- Configurable sentiment vocabulary via admin interface
- Webhook support for automated report delivery

---

## License

MIT License — see [LICENSE](LICENSE) for details.

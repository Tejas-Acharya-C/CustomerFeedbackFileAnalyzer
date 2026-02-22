# Customer Feedback File Analyzer

Web + CLI project for analyzing customer feedback from uploaded `.txt`/`.csv` files.

## Highlights

- Mandatory upload workflow (no local fallback files in web app)
- Strict CSV validation (`Name`, `Rating`, `Category`, `Feedback`)
- Sentiment, top words, negative-signal words, categories, rating distribution
- Priority insights (top issues to fix first)
- Smart search with options:
  - Case-sensitive toggle
  - Partial or exact word matching
  - Sentiment filter and minimum rating filter
  - Result highlighting + export
- Executive summary export
  - PDF executive summary with organized layout
- Compare two uploaded datasets
- Inline UX status + loading states
- API rate limiting + upload size limit + centralized error responses
- Test suite for service + API

## Setup

```powershell
pip install -r requirements-dev.txt
```

## Run (Development)

```powershell
python app.py
```

Open: `http://127.0.0.1:5000`

## Run (Production)

Linux/macOS with gunicorn:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app --timeout 60
```

Windows with waitress:

```powershell
waitress-serve --listen=0.0.0.0:8000 wsgi:app
```

## Environment Variables

Copy `.env.example` values as needed:

- `MAX_UPLOAD_MB` (default: `5`)
- `RATE_LIMIT_PER_MIN` (default: `60`)
- `LOG_LEVEL` (default: `INFO`)
- `FLASK_DEBUG` (default: `1`)
- `TRUST_PROXY_HEADERS` (default: `0`; set `1` only behind a trusted proxy)
- `REPORT_BRAND_NAME` (default: `Customer Feedback Pulse`; used in PDF header)

## API

All API responses are consistent:

- Success: `{ "ok": true, "data": { ... } }`
- Error: `{ "ok": false, "error": { "code": "...", "message": "..." } }`

Endpoints:

- `POST /api/analyze` (`feedback_file`)
- `POST /api/search` (`feedback_file`, `keyword`, optional `case_sensitive`, `match_mode`, `sentiment_filter`, `min_rating`)
- `POST /api/compare` (`feedback_file`, `feedback_file_compare`)
- `GET /api/health`
- `POST /api/export-summary-pdf` (`analysis` JSON payload from latest analysis response)

## Tests

```powershell
pytest -q
```

## Docker

```bash
docker build -t feedback-analyzer .
docker run -p 8000:8000 feedback-analyzer
```

## Deploy Online (GitHub + Render)

- This repository includes `render.yaml` for one-click Render deployment.
- Follow `DEPLOY_GITHUB_RENDER.md` for full steps.

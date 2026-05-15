# Development Guide

## Setup

```bash
git clone <repo-url>
cd "Customer Feedback File Analyzer Project"

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
```

## Running locally

```bash
python app.py
# → http://127.0.0.1:5000
```

For auto-reload during development:
```bash
FLASK_DEBUG=true python app.py
```

## Running tests

```bash
# Full suite
pytest

# Verbose with coverage
pytest -v --tb=short

# Specific test file
pytest tests/test_api.py -v
pytest tests/test_sentiment_accuracy.py -v

# Single test
pytest tests/test_e2e.py::TestUploadFlow::test_upload_txt_returns_session -v
```

## Test structure

| File | What it tests |
|---|---|
| `test_api.py` | HTTP routes, request validation, error responses |
| `test_e2e.py` | Full upload → analyze → export flows |
| `test_service.py` | `analysis_service.py` parsing and payload building |
| `test_sentiment_accuracy.py` | Sentiment classification correctness |
| `test_accuracy_calibration.py` | Confidence scoring, mojibake repair |
| `test_vocabulary_accuracy.py` | Weighted vocabulary behavior |
| `test_pdf_refinements.py` | PDF generation with real data |
| `test_audit_hardening.py` | Security, concurrency, session expiry |
| `test_final_portfolio.py` | Integration: CSV export, PDF charts |
| `benchmark.py` | Performance benchmarks (not in pytest suite) |

## Sample data

Two sample files are in `data/`:

- `data/feedback.txt` — plain text, one entry per line
- `data/feedback.csv` — structured with Name, Rating, Category, Feedback columns

Use these to test the upload flow manually.

## CSV format

```csv
Name,Rating,Category,Feedback
Alice,5,Product,Excellent quality and fast delivery
Bob,2,Support,Support team never responded to my emails
Carol,4,Delivery,Arrived on time but packaging was damaged
```

Required columns: `Name`, `Rating` (1–5 integer), `Category`, `Feedback`

## Adding new sentiment vocabulary

Edit `feedback_analyzer.py`:

```python
# Add to POSITIVE_WEIGHTED with weight 1 (weak), 2 (medium), or 3 (strong)
POSITIVE_WEIGHTED["phenomenal"] = 3

# Add to NEGATIVE_WEIGHTED
NEGATIVE_WEIGHTED["unreliable"] = 2

# Add domain-specific terms (won't override existing)
DOMAIN_POSITIVE["speedy"] = 2
```

After adding words, run `pytest tests/test_vocabulary_accuracy.py` to verify no regressions.

## Adding new categories

Edit `CATEGORY_KEYWORDS` in `feedback_analyzer.py`:

```python
CATEGORY_KEYWORDS = {
    "Product":  [...],
    "Delivery": [...],
    "Service":  [...],
    "Price":    [...],
    "Support":  [...],
    "Returns":  ["return", "refund", "exchange", "warranty"],  # new category
}
```

The `PRECOMPILED_CATEGORIES` dict is built at module load time from `CATEGORY_KEYWORDS`, so no other changes are needed.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_MB` | `5` | Max file upload size in MB |
| `SESSION_TTL_MINUTES` | `30` | Session expiry in minutes |
| `RATE_LIMIT_PER_MIN` | `60` | API requests per IP per minute |
| `MAX_SESSIONS` | `1000` | Max concurrent in-memory sessions |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `TRUST_PROXY_HEADERS` | `false` | Trust X-Forwarded-For (set true behind a proxy) |
| `REPORT_BRAND_NAME` | `Customer Feedback Pulse` | Brand name in PDF header |

## Code style

- Python: follow PEP 8, type hints on all public functions
- JS: vanilla ES2020+, no frameworks, null-safe element access throughout
- HTML: semantic elements, ARIA labels on interactive components, `aria-hidden` on decorative SVGs
- CSS: CSS custom properties for all colors, no inline styles for layout (use classes)

## Linting

```bash
# Python
flake8 app.py analysis_service.py feedback_analyzer.py pdf_export.py

# Or with ruff (faster)
ruff check .
```

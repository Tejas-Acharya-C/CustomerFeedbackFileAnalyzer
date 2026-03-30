# 📊 Customer Feedback File Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

A powerful, high-performance toolkit for analyzing customer sentiment, keyword frequency, and priority insights from raw feedback data. Features both a **modern Web Interface** and a **streamlined CLI tool**.

---

## 🔥 Key Features

### 💻 Modern Web Dashboard
- **Universal Upload**: Seamlessly process `.txt` and `.csv` feedback files.
- **Deep Analytics**: Automatic sentiment scoring, category detection, and rating distribution.
- **Priority Insights**: Identify "Red Flag" issues and critical feedback needing immediate attention.
- **Smart Search**: Advanced filtering by sentiment, rating, and match precision.
- **Data Comparison**: Compare two datasets (e.g., Q1 vs Q2) to track performance trends over time.
- **PDF Export**: Generate professional executive summaries in one click.

### 🛠️ Developer-First CLI
- Fast, menu-driven interface for local analysis.
- Instant statistics and word frequency reports.
- Lightweight and portable.

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install dependencies:
```powershell
git clone <your-repo-url>
cd "Customer Feedback File Analyzer Project"
pip install -r requirements.txt
```

### 2. Configure Environment
Copy the example environment file:
```powershell
cp .env.example .env
```

### 3. Run the Application
**Web Interface:**
```powershell
python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

**CLI Tool:**
```powershell
python main.py
```

---

## 🧪 Testing & Quality
Ensure everything is running smoothly with the automated test suite:
```powershell
pytest
```

---

## 🐳 Docker Deployment
Build and run with Docker for consistent production environments:
```bash
docker build -t feedback-analyzer .
docker run -p 8000:8000 feedback-analyzer
```

---

## 📂 Project Structure
```text
├── app.py                # Flask Web Entry Point
├── main.py               # CLI Tool Entry Point
├── analysis_service.py   # High-level business logic
├── feedback_analyzer.py  # Core NLP & processing
├── pdf_export.py         # PDF generation engine
├── api_schemas.py        # Data validation schemas
├── wsgi.py               # Production server entry
├── static/               # CSS, JS, and Images
├── templates/            # HTML Dashboards
├── tests/                # Unit & Integration Tests
└── data/                 # Sample datasets
```

---

## 📄 License
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

**Developed with ❤️ for Customer Excellence.**

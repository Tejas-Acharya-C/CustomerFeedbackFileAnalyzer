from __future__ import annotations

import io
import time
import threading
import pytest
import feedback_analyzer as fa
from analysis_service import parse_uploaded_feedback, search_feedback
from pdf_export import build_executive_summary_pdf
from flask import Flask
from app import create_app, SERVER_SESSIONS, SESSION_LOCK

def test_sentiment_boundary_words():
    # TEST: 'whenever' contains 'never', but shouldn't be negative.
    # Currently it will fail because it uses substring match 'word in sentence'
    feedback = ["It is whenever convenient for you."]
    results = fa.analyze_sentiment(feedback)
    assert len(results["Negative"]) == 0, "Sentiment analysis should use word boundaries, not substrings ('whenever' != 'never')"

def test_category_boundary_words():
    # TEST: 'apple' contains 'app', but shouldn't match 'Support' category keywords
    feedback = ["I bought an apple."]
    results = fa.detect_categories(feedback)
    assert len(results["Support"]) == 0, "Category detection should use word boundaries ('apple' != 'app')"

def test_pdf_injection_safety():
    # TEST: Malicious filename/text shouldn't crash PDF generation
    analysis = {
        "file": {"name": "test<b>inject</b>.csv", "extension": ".csv", "size_bytes": 100},
        "stats": {"total": 1, "avg_length": 10},
        "sentiment_percent": {"Positive": 100, "Negative": 0, "Neutral": 0},
        "priority_insights": [{"title": "<b>Broken</b>", "evidence": "<i>It is bad</i> & more", "action": "Fix it"}],
        "suggestions": ["<br/>Do something"]
    }
    try:
        pdf_bytes = build_executive_summary_pdf(analysis)
        assert len(pdf_bytes) > 0
    except Exception as e:
        pytest.fail(f"PDF generation crashed due to unescaped characters: {e}")

def test_search_logic_performance():
    # Performance check: Mocking large results (if possible)
    # This is more of a logic check to ensure search uses precomputed data if we fix it
    pass

def test_session_last_accessed_updated():
    """Active session usage should update last_accessed timestamp."""
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        data = {"feedback_file": (io.BytesIO(b"Great support\nBad delivery"), "test.txt")}
        res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
        sid = res.get_json()["data"]["session_id"]

        with SESSION_LOCK:
            initial_accessed = SERVER_SESSIONS[sid]["last_accessed"]

        time.sleep(0.05)  # small delay
        client.get(f"/api/data?sid={sid}")

        with SESSION_LOCK:
            updated_accessed = SERVER_SESSIONS[sid]["last_accessed"]

        assert updated_accessed > initial_accessed, "last_accessed should be updated on session use"


def test_session_expiry_uses_last_accessed(monkeypatch):
    """Expired sessions should be evicted based on last_accessed, not created_at."""
    monkeypatch.setenv("SESSION_TTL_MINUTES", "1")  # 1 minute = 60 seconds
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        data = {"feedback_file": (io.BytesIO(b"Great support"), "test.txt")}
        res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
        sid = res.get_json()["data"]["session_id"]

        # Manually expire by backdating last_accessed
        with SESSION_LOCK:
            SERVER_SESSIONS[sid]["last_accessed"] = time.time() - 120

        res = client.get(f"/api/data?sid={sid}")
        assert res.status_code == 400
        body = res.get_json()
        assert body["error"]["code"] == "MISSING_SESSION"


def test_concurrent_session_access():
    """Multiple threads accessing sessions simultaneously should not crash."""
    app = create_app()
    app.config.update(TESTING=True)
    errors = []

    with app.test_client() as client:
        data = {"feedback_file": (io.BytesIO(b"Great support\nBad delivery"), "test.txt")}
        res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
        sid = res.get_json()["data"]["session_id"]

        def fetch_data():
            try:
                with app.test_client() as tc:
                    r = tc.get(f"/api/data?sid={sid}")
                    assert r.status_code == 200
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=fetch_data) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(errors) == 0, f"Thread-safety errors: {errors}"


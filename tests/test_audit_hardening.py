from __future__ import annotations

import io
import pytest
import feedback_analyzer as fa
from analysis_service import parse_uploaded_feedback, search_feedback
from pdf_export import build_executive_summary_pdf
from flask import Flask

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

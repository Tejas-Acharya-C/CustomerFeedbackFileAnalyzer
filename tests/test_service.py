from __future__ import annotations

import io

import pytest
from werkzeug.datastructures import FileStorage

from analysis_service import AnalysisError, build_analysis_payload, parse_uploaded_feedback, search_feedback
from app import create_app


def _upload(name: str, content: str) -> FileStorage:
    return FileStorage(stream=io.BytesIO(content.encode("utf-8")), filename=name)


def test_parse_txt_upload_success():
    parsed = parse_uploaded_feedback(_upload("feedback.txt", "Great service\nBad delivery\n"))
    assert parsed.extension == ".txt"
    assert parsed.feedback_list == ["Great service", "Bad delivery"]
    assert parsed.csv_rows == []


def test_parse_csv_requires_headers():
    with pytest.raises(AnalysisError) as exc:
        parse_uploaded_feedback(_upload("feedback.csv", "a,b,c\n1,2,3"))
    assert "missing required headers" in str(exc.value).lower()


def test_build_analysis_payload_has_suggestions():
    content = "Name,Rating,Category,Feedback\nA,2,Delivery,Very slow and bad service\nB,5,Service,Great support"
    parsed = parse_uploaded_feedback(_upload("feedback.csv", content))
    data = build_analysis_payload(parsed)
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert "priority_insights" in data
    assert 1 <= len(data["priority_insights"]) <= 3


def test_search_feedback_partial_case_insensitive():
    rows = ["Delivery was Late", "Support was great"]
    matches = search_feedback(rows, "late", case_sensitive=False, match_mode="partial")
    assert len(matches) == 1
    assert matches[0] == "Delivery was Late"


def test_search_feedback_exact():
    rows = ["delivery delay", "delayed package", "delivery"]
    matches = search_feedback(rows, "delivery", case_sensitive=False, match_mode="exact")
    assert matches == ["delivery delay", "delivery"]


def test_search_feedback_with_sentiment_and_min_rating_filters():
    content = (
        "Name,Rating,Category,Feedback\n"
        "A,2,Delivery,Bad and slow service\n"
        "B,5,Service,Great support and smooth process\n"
        "C,4,Delivery,Fast delivery and good packaging"
    )
    parsed = parse_uploaded_feedback(_upload("feedback.csv", content))
    matches = search_feedback(
        parsed.feedback_list,
        "service",
        sentiment_filter="negative",
        min_rating=2,
        csv_rows=parsed.csv_rows,
    )
    assert matches == ["Bad and slow service"]


def test_create_app_uses_defaults_for_invalid_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "abc")
    monkeypatch.setenv("MAX_UPLOAD_MB", "-5")
    app = create_app()
    assert app.config["MAX_CONTENT_LENGTH"] == 5 * 1024 * 1024

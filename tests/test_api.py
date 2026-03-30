from __future__ import annotations

import io

import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

def get_session(client, csv_bytes: bytes, filename: str = "feedback.csv") -> str:
    data = {"feedback_file": (io.BytesIO(csv_bytes), filename)}
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    return res.get_json()["data"]["session_id"]

def test_analyze_requires_upload(client):
    res = client.post("/api/analyze", data={})
    assert res.status_code == 400
    body = res.get_json()
    assert body["ok"] is False


def test_analyze_success(client):
    data = {
        "feedback_file": (io.BytesIO(b"Great support\nBad delivery"), "feedback.txt"),
    }
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    assert "session_id" in body["data"]


def test_search_with_options(client):
    csv = b"Name,Rating,Category,Feedback\nA,4,Delivery,Package Late\nB,5,Service,Great support"
    sid = get_session(client, csv)
    data = {
        "sid": sid,
        "keyword": "Late",
        "case_sensitive": "true",
        "match_mode": "exact",
    }
    res = client.post("/api/search", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    assert body["data"]["count"] == 1


def test_search_with_sentiment_and_rating_filters(client):
    csv = (
        b"Name,Rating,Category,Feedback\n"
        b"A,2,Delivery,Bad delivery and slow support\n"
        b"B,5,Service,Great support and fast delivery\n"
        b"C,4,Delivery,Good packaging and quick delivery"
    )
    sid = get_session(client, csv)
    data = {
        "sid": sid,
        "keyword": "delivery",
        "case_sensitive": "false",
        "match_mode": "partial",
        "sentiment_filter": "negative",
        "min_rating": "2",
    }
    res = client.post("/api/search", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    assert body["data"]["count"] == 1
    assert body["data"]["matches"][0] == "Bad delivery and slow support"


def test_search_invalid_min_rating_returns_400(client):
    csv = b"Name,Rating,Category,Feedback\nA,4,Delivery,Package Late"
    sid = get_session(client, csv)
    data = {
        "sid": sid,
        "keyword": "late",
        "min_rating": "abc",
    }
    res = client.post("/api/search", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    body = res.get_json()
    assert body["ok"] is False


def test_export_summary_pdf_success(client):
    sid = get_session(client, b"Good feedback")
    res = client.get(f"/api/export-summary-pdf?sid={sid}")
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF")


def test_compare_requires_second_file(client):
    data = {
        "feedback_file": (io.BytesIO(b"Good"), "a.txt"),
    }
    res = client.post("/api/compare", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    body = res.get_json()
    assert body["ok"] is False


def test_api_unknown_route_returns_404_json(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    body = res.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "http_error"


def test_filename_is_sanitized(client):
    data = {
        "feedback_file": (io.BytesIO(b"Great support"), "<img src=x onerror=alert(1)>.txt"),
    }
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True

    # Validate that we can extract the analysis dataset and verify the sanitized name
    sid = body["data"]["session_id"]
    data_res = client.get(f"/api/data?sid={sid}")
    assert "<" not in data_res.get_json()["data"]["file"]["name"]

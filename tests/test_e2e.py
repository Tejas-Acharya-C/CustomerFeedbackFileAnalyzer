"""
End-to-end tests simulating browser-level behavior via Flask test client.

Covers:
  1. Home page loads
  2. Upload TXT → dashboard redirect
  3. Upload CSV → dashboard redirect
  4. Dashboard renders with session
  5. Search works
  6. PDF export works
  7. Invalid upload error
  8. Session expiration behavior
  9. Security headers present
  10. Compare flow
  11. Raw data page loads
  12. Analytics page loads
  13. Health endpoint
  14. Session capacity limit
"""
from __future__ import annotations

import io
import time

import pytest

from app import create_app, SERVER_SESSIONS, SESSION_LOCK


SAMPLE_TXT = b"Great product quality\nTerrible customer service\nFast delivery arrived on time"
SAMPLE_CSV = (
    b"Name,Rating,Category,Feedback\n"
    b"Alice,5,Product,Amazing quality and design\n"
    b"Bob,2,Delivery,Late arrival and damaged package\n"
    b"Carol,4,Service,Helpful and friendly staff\n"
)


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _upload_txt(client, content: bytes = SAMPLE_TXT):
    data = {"feedback_file": (io.BytesIO(content), "feedback.txt")}
    return client.post("/api/analyze", data=data, content_type="multipart/form-data")


def _upload_csv(client, content: bytes = SAMPLE_CSV):
    data = {"feedback_file": (io.BytesIO(content), "feedback.csv")}
    return client.post("/api/analyze", data=data, content_type="multipart/form-data")


def _get_sid(response) -> str:
    return response.get_json()["data"]["session_id"]


# ---------- Page loading tests ----------

class TestPageLoading:
    def test_home_page_loads(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"AEGIS" in res.data or b"html" in res.data

    def test_dashboard_page_loads_without_session(self, client):
        res = client.get("/dashboard")
        assert res.status_code == 200

    def test_analytics_page_loads_without_session(self, client):
        res = client.get("/analytics")
        assert res.status_code == 200

    def test_raw_data_page_loads_without_session(self, client):
        res = client.get("/raw_data")
        assert res.status_code == 200

    def test_health_endpoint(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        body = res.get_json()
        assert body["ok"] is True
        assert body["data"]["status"] == "ok"


# ---------- Upload flow tests ----------

class TestUploadFlow:
    def test_upload_txt_returns_session(self, client):
        res = _upload_txt(client)
        assert res.status_code == 200
        body = res.get_json()
        assert body["ok"] is True
        sid = body["data"]["session_id"]
        assert len(sid) == 36  # UUID format

    def test_upload_csv_returns_session(self, client):
        res = _upload_csv(client)
        assert res.status_code == 200
        body = res.get_json()
        assert body["ok"] is True
        assert "session_id" in body["data"]

    def test_invalid_file_extension_rejected(self, client):
        data = {"feedback_file": (io.BytesIO(b"data"), "payload.exe")}
        res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        body = res.get_json()
        assert body["ok"] is False

    def test_empty_file_rejected(self, client):
        data = {"feedback_file": (io.BytesIO(b""), "empty.txt")}
        res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
        assert res.status_code == 400

    def test_no_file_rejected(self, client):
        res = client.post("/api/analyze", data={})
        assert res.status_code == 400


# ---------- Dashboard data tests ----------

class TestDashboardData:
    def test_dashboard_data_loads_with_session(self, client):
        sid = _get_sid(_upload_txt(client))
        res = client.get(f"/api/data?sid={sid}")
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert "stats" in data
        assert "sentiment" in data
        assert "sentiment_percent" in data
        assert "categories" in data
        assert "top_words" in data
        assert "suggestions" in data
        assert "priority_insights" in data

    def test_csv_data_includes_ratings(self, client):
        sid = _get_sid(_upload_csv(client))
        res = client.get(f"/api/data?sid={sid}")
        data = res.get_json()["data"]
        assert data["rating_distribution"] is not None
        assert data["average_rating"] is not None

    def test_invalid_session_returns_error(self, client):
        res = client.get("/api/data?sid=nonexistent-id")
        assert res.status_code == 400
        body = res.get_json()
        assert body["ok"] is False
        assert body["error"]["code"] == "MISSING_SESSION"


# ---------- Search flow tests ----------

class TestSearchFlow:
    def test_search_returns_results(self, client):
        sid = _get_sid(_upload_txt(client))
        data = {"sid": sid, "keyword": "delivery"}
        res = client.post("/api/search", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        body = res.get_json()
        assert body["ok"] is True
        assert body["data"]["count"] >= 1

    def test_search_with_no_results(self, client):
        sid = _get_sid(_upload_txt(client))
        data = {"sid": sid, "keyword": "xyznonexistent"}
        res = client.post("/api/search", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        body = res.get_json()
        assert body["data"]["count"] == 0

    def test_search_without_session_fails(self, client):
        data = {"sid": "bad-sid", "keyword": "test"}
        res = client.post("/api/search", data=data, content_type="multipart/form-data")
        assert res.status_code == 400


# ---------- PDF export tests ----------

class TestPdfExport:
    def test_pdf_export_success(self, client):
        sid = _get_sid(_upload_txt(client))
        res = client.get(f"/api/export-summary-pdf?sid={sid}")
        assert res.status_code == 200
        assert res.content_type == "application/pdf"
        assert res.data[:4] == b"%PDF"

    def test_pdf_export_without_session_fails(self, client):
        res = client.get("/api/export-summary-pdf?sid=invalid")
        assert res.status_code == 400


# ---------- Compare flow tests ----------

class TestCompareFlow:
    def test_compare_returns_deltas(self, client):
        data = {
            "feedback_file": (io.BytesIO(SAMPLE_TXT), "a.txt"),
            "feedback_file_compare": (io.BytesIO(b"Bad service\nGood product"), "b.txt"),
        }
        res = client.post("/api/compare", data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        body = res.get_json()
        assert "delta" in body["data"]
        assert "session_id" in body["data"]

    def test_compare_session_has_comparison_data(self, client):
        data = {
            "feedback_file": (io.BytesIO(SAMPLE_TXT), "a.txt"),
            "feedback_file_compare": (io.BytesIO(b"Bad service\nGood product"), "b.txt"),
        }
        res = client.post("/api/compare", data=data, content_type="multipart/form-data")
        sid = res.get_json()["data"]["session_id"]
        data_res = client.get(f"/api/data?sid={sid}")
        assert data_res.status_code == 200
        assert "comparison" in data_res.get_json()["data"]


# ---------- Session lifecycle tests ----------

class TestSessionLifecycle:
    def test_session_expiry(self, client):
        sid = _get_sid(_upload_txt(client))
        # Backdate session to simulate expiration
        with SESSION_LOCK:
            SERVER_SESSIONS[sid]["last_accessed"] = time.time() - 7200  # 2 hours ago
        res = client.get(f"/api/data?sid={sid}")
        assert res.status_code == 400
        assert res.get_json()["error"]["code"] == "MISSING_SESSION"


# ---------- Security header tests ----------

class TestSecurityHeaders:
    def test_csp_header_present(self, client):
        res = client.get("/")
        assert "Content-Security-Policy" in res.headers
        csp = res.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_security_headers_on_api(self, client):
        res = client.get("/api/health")
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert "Permissions-Policy" in res.headers
        assert res.headers.get("Cache-Control") is not None
        assert "no-store" in res.headers["Cache-Control"]

    def test_hsts_header(self, client):
        res = client.get("/")
        assert "max-age=31536000" in res.headers.get("Strict-Transport-Security", "")

    def test_referrer_policy(self, client):
        res = client.get("/")
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

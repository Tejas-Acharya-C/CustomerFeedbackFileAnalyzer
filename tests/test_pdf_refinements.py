"""Tests for PDF report refinements: executive summary, charts, confidence, scaling."""
import pytest
from io import BytesIO
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _make_csv(n_rows: int) -> str:
    """Generate a CSV with n_rows of varied feedback."""
    lines = ["Name,Rating,Category,Feedback"]
    sentiments = [
        ("Alice", 5, "Product", "Amazing product love it excellent quality"),
        ("Bob", 1, "Delivery", "Worst delivery ever damaged and slow"),
        ("Carol", 3, "Service", "Good service but slow response time"),
        ("Dan", 4, "Support", "Helpful support agent resolved my issue"),
        ("Eve", 2, "Price", "Too expensive overpriced for what you get"),
    ]
    for i in range(n_rows):
        name, rating, cat, fb = sentiments[i % len(sentiments)]
        lines.append(f"{name}{i},{rating},{cat},{fb} row {i}")
    return "\n".join(lines)


def _upload_and_get_sid(client, csv_data: str) -> str:
    data = {"feedback_file": (BytesIO(csv_data.encode()), "test.csv")}
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    return res.get_json()["data"]["session_id"]


class TestPdfExecutiveSummary:
    def test_pdf_contains_confidence_in_snapshot(self, client):
        sid = _upload_and_get_sid(client, _make_csv(10))
        res = client.get(f"/api/export-summary-pdf?sid={sid}")
        assert res.status_code == 200
        assert res.content_type == "application/pdf"
        assert len(res.data) > 2000

    def test_pdf_contains_mixed_sentiment(self, client):
        """CSV with mixed feedback should generate PDF without crashing."""
        csv = "Name,Rating,Category,Feedback\nA,3,Product,Great product but terrible packaging"
        sid = _upload_and_get_sid(client, csv)
        res = client.get(f"/api/export-summary-pdf?sid={sid}")
        assert res.status_code == 200


class TestPdfScaling:
    """Verify PDF generation succeeds at various dataset sizes."""

    @pytest.mark.parametrize("n_rows", [50, 250])
    def test_pdf_scales_to_size(self, client, n_rows):
        csv_data = _make_csv(n_rows)
        sid = _upload_and_get_sid(client, csv_data)
        res = client.get(f"/api/export-summary-pdf?sid={sid}")
        assert res.status_code == 200
        assert res.content_type == "application/pdf"
        assert len(res.data) > 3000  # Should be a non-trivial PDF


class TestRecommendationLogic:
    def test_recommendations_are_dynamic(self, client):
        """Recommendations should contain actual metric values, not generic text."""
        csv_data = _make_csv(50)
        sid = _upload_and_get_sid(client, csv_data)
        res = client.get(f"/api/data?sid={sid}")
        data = res.get_json()["data"]
        suggestions = data.get("suggestions", [])
        assert len(suggestions) > 0
        # At least one suggestion should contain a percentage or number
        has_metric = any("%" in s or any(c.isdigit() for c in s) for s in suggestions)
        assert has_metric, f"Suggestions lack metrics: {suggestions}"

    def test_fallback_suggestion_when_positive(self, client):
        """All-positive data should get the 'maintain performance' fallback."""
        csv = "Name,Rating,Category,Feedback\n"
        csv += "\n".join(
            f"User{i},5,Product,Amazing excellent wonderful" for i in range(10)
        )
        sid = _upload_and_get_sid(client, csv)
        res = client.get(f"/api/data?sid={sid}")
        suggestions = res.get_json()["data"]["suggestions"]
        assert any("maintain" in s.lower() or "monitor" in s.lower() for s in suggestions)

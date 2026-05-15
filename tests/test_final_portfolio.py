import pytest
from io import BytesIO
import csv
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_confidence_logic():
    from feedback_analyzer import analyze_sentiment
    # High confidence: lots of sentiment words
    fb1 = ["amazing excellent great perfect wonderful"]
    res1 = analyze_sentiment(fb1)
    assert res1["detailed"][0]["confidence"] > 50
    
    # Low confidence: mostly stop words/neutral
    fb2 = ["the and is it was here"]
    res2 = analyze_sentiment(fb2)
    assert res2["detailed"][0]["confidence"] == 0
    
    # Mixed: both positive and negative signals present
    fb3 = ["great but terrible"]
    res3 = analyze_sentiment(fb3)
    assert res3["detailed"][0]["label"] == "Mixed"
    assert res3["detailed"][0]["confidence"] > 0

def test_business_insights_generation():
    from analysis_service import _business_insights
    categories_raw = {
        "Product": ["Great quality", "Excellent build", "Love the design"], # 100% pos
        "Delivery": ["Slow shipping", "Late delivery", "Damaged box"],     # 100% neg
        "Support": ["Helpful agent"]                                        # 100% pos
    }
    insights = _business_insights({}, categories_raw, 4.0)
    assert any("Product performance" in s for s in insights["top_strengths"])
    assert any("Delivery friction" in c for c in insights["top_complaints"])

def test_detailed_csv_export(client):
    # 1. Upload a CSV
    csv_data = "Name,Rating,Category,Feedback\nAlice,5,Product,Amazing product love it\nBob,1,Delivery,Worst delivery ever"
    data = {"feedback_file": (BytesIO(csv_data.encode()), "test.csv")}
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    sid = res.get_json()["data"]["session_id"]
    
    # 2. Export detailed CSV
    res_csv = client.get(f"/api/export-detailed-csv?sid={sid}")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.content_type
    
    content = res_csv.data.decode()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    
    assert len(rows) == 2
    assert rows[0]["Sentiment"] == "Positive"
    assert rows[1]["Sentiment"] == "Negative"
    assert "Confidence" in rows[0]
    assert rows[0]["Name"] == "Alice"

def test_pdf_export_with_charts(client):
    # Just verify the endpoint doesn't crash with the new ReportLab logic
    csv_data = "Name,Rating,Category,Feedback\nAlice,5,Product,Amazing product\nBob,1,Delivery,Worst delivery"
    data = {"feedback_file": (BytesIO(csv_data.encode()), "test.csv")}
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    sid = res.get_json()["data"]["session_id"]
    
    res_pdf = client.get(f"/api/export-summary-pdf?sid={sid}")
    assert res_pdf.status_code == 200
    assert res_pdf.content_type == "application/pdf"
    assert len(res_pdf.data) > 1000 # Basic size check

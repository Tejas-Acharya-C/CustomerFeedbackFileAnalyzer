import pytest
from feedback_analyzer import analyze_sentiment

class TestVocabularyAccuracy:
    def test_strong_vs_weak_words(self):
        """A. Strong vs weak words: amazing score > good score."""
        res_strong = analyze_sentiment(["amazing"])
        res_weak = analyze_sentiment(["good"])
        # Both are positive, but strong word should yield higher confidence
        assert res_strong["detailed"][0]["confidence"] > res_weak["detailed"][0]["confidence"]

    def test_domain_specific_words(self):
        """B. Domain-specific words."""
        res_pos = analyze_sentiment(["Delivery arrived early"])
        res_neg = analyze_sentiment(["Support ghosted me"])
        assert res_pos["detailed"][0]["label"] == "Positive"
        assert res_neg["detailed"][0]["label"] == "Negative"

    def test_ambiguous_words(self):
        """C. Ambiguous words with context."""
        res_pos = analyze_sentiment(["long battery life"])
        res_neg = analyze_sentiment(["long waiting time"])
        assert res_pos["detailed"][0]["label"] == "Positive"
        assert res_neg["detailed"][0]["label"] == "Negative"

    def test_mixed_sentiment(self):
        """D. Mixed sentiment."""
        res = analyze_sentiment(["Great product but terrible delivery"])
        assert res["detailed"][0]["label"] == "Mixed"

    def test_negation(self):
        """E. Negation handling."""
        res_neg = analyze_sentiment(["not good"])
        res_pos = analyze_sentiment(["not bad"])
        assert res_neg["detailed"][0]["label"] == "Negative"
        assert res_pos["detailed"][0]["label"] == "Positive"

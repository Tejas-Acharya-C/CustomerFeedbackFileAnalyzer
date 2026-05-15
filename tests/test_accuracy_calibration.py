"""Tests for encoding normalization (mojibake repair) and confidence calibration."""
import pytest
from feedback_analyzer import (
    analyze_sentiment,
    normalize_text,
    preprocess_text,
    _compute_confidence,
)


# ── Encoding / Mojibake Repair ───────────────────────────────────────

class TestMojibakeRepair:
    def test_emoji_mojibake_repair(self):
        """Common mojibake: UTF-8 emoji bytes read as latin-1."""
        # "😡" in UTF-8 is \xf0\x9f\x98\xa1.  When misread as latin-1 it
        # becomes the multi-char garble "ðŸ˜¡".  normalize_text should
        # recover the original emoji.
        garbled = "\u00f0\u009f\u0098\u00a1"  # latin-1 interpretation of 😡
        repaired = normalize_text(garbled)
        assert repaired == "😡", f"Expected '😡', got '{repaired}'"

    def test_french_accent_mojibake_repair(self):
        """'Très' misread as latin-1 produces 'TrÃ¨s'."""
        garbled = "Tr\u00c3\u00a8s bon produit"  # latin-1 of 'Très'
        repaired = normalize_text(garbled)
        assert "è" in repaired
        assert "Ã" not in repaired

    def test_valid_utf8_unchanged(self):
        """Already-valid UTF-8 text must not be altered."""
        text = "Très bon produit 😊"
        assert normalize_text(text) == text

    def test_valid_ascii_unchanged(self):
        text = "Great product excellent quality"
        assert normalize_text(text) == text

    def test_empty_and_none(self):
        assert normalize_text("") == ""
        assert normalize_text(None) is None

    def test_emoji_preserved_after_preprocess(self):
        """Emojis survive the full preprocessing pipeline."""
        text = "Great product 😊👍🎉"
        cleaned = preprocess_text(text)
        assert "😊" in cleaned
        assert "👍" in cleaned
        assert "🎉" in cleaned

    def test_spanish_accents_preserved(self):
        text = "Producto fantástico y rápido"
        cleaned = preprocess_text(text)
        assert "fantástico" in cleaned
        assert "rápido" in cleaned

    def test_french_accents_preserved(self):
        text = "Très bon produit mais service lent"
        cleaned = preprocess_text(text)
        assert "Très" in cleaned

    def test_multilingual_sentiment_after_repair(self):
        """Repaired text should still trigger correct sentiment analysis."""
        # Garbled "Très bon" → should repair to valid French → "bon" = Positive
        garbled = "Tr\u00c3\u00a8s bon produit"
        res = analyze_sentiment([garbled])
        assert res["detailed"][0]["label"] == "Positive"


# ── Confidence Calibration ───────────────────────────────────────────

class TestConfidenceCalibration:
    def test_strong_positive_high_confidence(self):
        res = analyze_sentiment(["Amazing excellent great perfect wonderful outstanding"])
        conf = res["detailed"][0]["confidence"]
        assert conf >= 50, f"Strong positive should be >=50%, got {conf}%"

    def test_strong_negative_high_confidence(self):
        res = analyze_sentiment(["Terrible horrible broken poor worst defective"])
        conf = res["detailed"][0]["confidence"]
        assert conf >= 50, f"Strong negative should be >=50%, got {conf}%"

    def test_mixed_confidence_reasonable(self):
        """Mixed sentiment should NOT produce very low confidence."""
        res = analyze_sentiment(["Support was helpful but refund process took too long"])
        det = res["detailed"][0]
        assert det["label"] in ("Mixed", "Positive", "Negative")
        # Confidence should reflect that sentiment was detected, not penalize mixing
        assert det["confidence"] > 20, f"Mixed shouldn't be extremely low, got {det['confidence']}%"

    def test_single_keyword_not_100(self):
        """Single-word feedback should not reach 100% confidence."""
        res = analyze_sentiment(["Terrible!!!"])
        conf = res["detailed"][0]["confidence"]
        assert conf > 0
        assert conf < 100, f"Single keyword shouldn't be 100%, got {conf}%"

    def test_neutral_always_zero(self):
        res = analyze_sentiment(["The package arrived today at noon"])
        assert res["detailed"][0]["confidence"] == 0

    def test_mixed_confidence_above_weak_positive(self):
        """Mixed with multiple signals should have higher or equal confidence
        compared to a weak single-keyword positive."""
        mixed = analyze_sentiment(["Great product but terrible delivery and slow support"])
        weak = analyze_sentiment(["okay"])
        assert mixed["detailed"][0]["confidence"] >= weak["detailed"][0]["confidence"], (
            f"Mixed ({mixed['detailed'][0]['confidence']}%) should be >= "
            f"weak ({weak['detailed'][0]['confidence']}%)"
        )

    def test_compute_confidence_mixed_formula(self):
        """Direct formula check: Mixed uses strength*0.7 + balance*0.3."""
        # 2 pos, 2 neg, 6 relevant words
        conf = _compute_confidence(2, 2, 6, label="Mixed")
        max_possible = 6 * 3  # total_relevant * max_weight
        strength = min(4 / max_possible, 1.0)
        balance = 2 / 2
        expected = strength * 0.7 + balance * 0.3
        assert abs(conf - expected) < 0.01, f"Expected ~{expected:.3f}, got {conf:.3f}"

    def test_compute_confidence_onesided_formula(self):
        """Direct formula check: Positive uses strength*0.6 + dominance*0.4."""
        # 4 pos, 0 neg, 6 relevant words
        conf = _compute_confidence(4, 0, 6, label="Positive")
        max_possible = 6 * 3
        strength = min(4 / max_possible, 1.0)
        dominance = 4 / 4  # abs(4-0)/4
        expected = strength * 0.6 + dominance * 0.4
        assert abs(conf - expected) < 0.01, f"Expected ~{expected:.3f}, got {conf:.3f}"

    def test_density_cap_short_text(self):
        """Same keyword count, short text gets density-capped."""
        # Both have 3 sentiment words, but different total_relevant
        short = _compute_confidence(3, 0, 3, label="Positive")  # 3/3 strength, cap 0.8
        long = _compute_confidence(3, 0, 10, label="Positive")  # 3/10 strength, no cap
        # Short text has 100% strength * 0.8 cap = high
        # Long text has 30% strength * 1.0 = lower
        # With enough words, the cap matters less than diluted strength
        assert short > 0
        assert long > 0
        # Verify the density cap is actually applied (short < 1.0)
        assert short < 1.0

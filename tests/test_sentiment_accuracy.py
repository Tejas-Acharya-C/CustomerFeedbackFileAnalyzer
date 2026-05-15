"""Tests for sentiment accuracy improvements: negation, Mixed, multilingual, emoji, encoding, confidence."""
import pytest
from feedback_analyzer import (
    analyze_sentiment,
    preprocess_text,
    _check_negation,
    _compute_confidence,
)


# ── Mixed Sentiment ──────────────────────────────────────────────────

class TestMixedSentiment:
    def test_mixed_when_both_positive_and_negative(self):
        res = analyze_sentiment(["Great product but terrible delivery"])
        assert res["detailed"][0]["label"] == "Mixed"
        assert len(res["Mixed"]) == 1
        assert len(res["Positive"]) == 0
        assert len(res["Negative"]) == 0

    def test_mixed_with_multiple_signals(self):
        res = analyze_sentiment(["Amazing quality but slow shipping and damaged box"])
        assert res["detailed"][0]["label"] == "Mixed"

    def test_pure_positive_not_mixed(self):
        res = analyze_sentiment(["Amazing excellent wonderful product"])
        assert res["detailed"][0]["label"] == "Positive"

    def test_pure_negative_not_mixed(self):
        res = analyze_sentiment(["Terrible horrible broken product"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_neutral_when_no_signals(self):
        res = analyze_sentiment(["The package arrived on time"])
        assert res["detailed"][0]["label"] == "Neutral"


# ── Negation Handling ────────────────────────────────────────────────

class TestNegation:
    def test_not_good_is_negative(self):
        res = analyze_sentiment(["The product was not good"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_never_arrived_is_negative(self):
        """'never' is already in NEGATIVE_WORDS, but 'arrived' is not a sentiment word.
        This should be Negative from the 'never' keyword."""
        res = analyze_sentiment(["The package never arrived"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_wasnt_fast_is_negative(self):
        res = analyze_sentiment(["The delivery wasn't fast at all"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_isnt_helpful_is_negative(self):
        res = analyze_sentiment(["Support isn't helpful"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_not_bad_is_positive(self):
        res = analyze_sentiment(["The product is not bad"])
        assert res["detailed"][0]["label"] == "Positive"

    def test_double_negation_preserves_original(self):
        """'not terrible' should flip terrible from neg→pos."""
        res = analyze_sentiment(["The experience was not terrible"])
        assert res["detailed"][0]["label"] == "Positive"

    def test_negation_check_helper(self):
        assert _check_negation("this is not good at all", "good") is True
        assert _check_negation("this is really good", "good") is False
        assert _check_negation("wasn't fast enough", "fast") is True


# ── Multilingual Sentiment ───────────────────────────────────────────

class TestMultilingual:
    def test_spanish_positive(self):
        res = analyze_sentiment(["El producto es bueno y excelente"])
        assert res["detailed"][0]["label"] == "Positive"

    def test_spanish_negative(self):
        res = analyze_sentiment(["La entrega fue lenta y mala"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_french_positive(self):
        res = analyze_sentiment(["Le produit est bon et parfait"])
        assert res["detailed"][0]["label"] == "Positive"

    def test_french_negative(self):
        res = analyze_sentiment(["Le service est lent et mauvais"])
        assert res["detailed"][0]["label"] == "Negative"

    def test_mixed_language(self):
        """English positive + Spanish negative → Mixed."""
        res = analyze_sentiment(["Amazing product pero lenta entrega"])
        assert res["detailed"][0]["label"] == "Mixed"


# ── Emoji Preservation ───────────────────────────────────────────────

class TestEmojiPreservation:
    def test_emoji_not_stripped(self):
        text = "Great product 😊👍"
        cleaned = preprocess_text(text)
        assert "😊" in cleaned
        assert "👍" in cleaned

    def test_symbols_stripped_emoji_kept(self):
        text = "Good price <100% off> = amazing!! 🎉"
        cleaned = preprocess_text(text)
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "%" not in cleaned
        assert "=" not in cleaned
        assert "🎉" in cleaned

    def test_sentiment_works_with_emojis(self):
        res = analyze_sentiment(["Amazing product 😊 love it 👍"])
        assert res["detailed"][0]["label"] == "Positive"


# ── Encoding ─────────────────────────────────────────────────────────

class TestEncoding:
    def test_utf8_text_works(self):
        res = analyze_sentiment(["Très bon produit"])  # French accented
        assert res["detailed"][0]["label"] == "Positive"  # 'bon' is multilingual positive

    def test_accented_characters_preserved(self):
        text = "El café es excelente"
        cleaned = preprocess_text(text)
        assert "café" in cleaned

    def test_unicode_emoji_doesnt_crash(self):
        res = analyze_sentiment(["Product is great 🚀✨💯"])
        assert res["detailed"][0]["label"] == "Positive"


# ── Confidence Realism ───────────────────────────────────────────────

class TestConfidenceRealism:
    def test_single_keyword_short_text_capped(self):
        """A single 'good' in a 1-word text should NOT be 100% confidence."""
        res = analyze_sentiment(["good"])
        conf = res["detailed"][0]["confidence"]
        assert conf > 0
        assert conf < 100  # density_cap prevents 100%

    def test_many_keywords_high_confidence(self):
        """Dense sentiment text should have high confidence."""
        res = analyze_sentiment(["amazing excellent great perfect wonderful outstanding incredible"])
        conf = res["detailed"][0]["confidence"]
        assert conf >= 60

    def test_neutral_zero_confidence(self):
        """No sentiment words → 0% confidence."""
        res = analyze_sentiment(["The package arrived today"])
        assert res["detailed"][0]["confidence"] == 0

    def test_mixed_has_lower_balance(self):
        """Mixed signals should reduce confidence via balance factor."""
        pure = analyze_sentiment(["amazing excellent wonderful"])
        mixed = analyze_sentiment(["amazing excellent but terrible"])
        # Pure positive should have higher confidence than mixed
        assert pure["detailed"][0]["confidence"] >= mixed["detailed"][0]["confidence"]

    def test_compute_confidence_edge_cases(self):
        assert _compute_confidence(0, 0, 0) == 0.0
        assert _compute_confidence(0, 0, 10) == 0.0
        # Single positive word in short text — density cap dampens
        conf = _compute_confidence(1, 0, 1, label="Positive")
        assert conf > 0
        assert conf < 100  # density_cap kicks in

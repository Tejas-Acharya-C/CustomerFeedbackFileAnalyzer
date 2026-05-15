import re

# ══════════════════════════════════════════════════════════════════════
# WEIGHTED SENTIMENT DICTIONARIES
# Weight 3 = strong, 2 = medium, 1 = weak
# ══════════════════════════════════════════════════════════════════════

POSITIVE_WEIGHTED = {
    # --- Strong (3) ---
    "excellent": 3, "fantastic": 3, "amazing": 3, "outstanding": 3,
    "perfect": 3, "wonderful": 3, "brilliant": 3, "awesome": 3,
    "superb": 3, "exceptional": 3, "incredible": 3, "flawless": 3,
    "impeccable": 3, "unbeatable": 3, "stunning": 3, "love": 3,
    "loved": 3, "best": 3, "exceeded": 3, "perfectly": 3,
    # --- Medium (2) ---
    "good": 2, "great": 2, "nice": 2, "smooth": 2, "helpful": 2,
    "responsive": 2, "reliable": 2, "clean": 2, "easy": 2,
    "intuitive": 2, "happy": 2, "satisfied": 2, "recommended": 2,
    "polite": 2, "impressed": 2, "premium": 2, "durable": 2,
    "beautiful": 2, "seamless": 2, "comfortable": 2, "professional": 2,
    "friendly": 2, "worth": 2, "courteous": 2, "efficient": 2,
    # --- Weak (1) ---
    "okay": 1, "fine": 1, "acceptable": 1, "satisfactory": 1,
    "decent": 1, "adequate": 1, "fair": 1,
}

NEGATIVE_WEIGHTED = {
    # --- Strong (3) ---
    "terrible": 3, "horrible": 3, "awful": 3, "worst": 3,
    "broken": 3, "unusable": 3, "disaster": 3, "pathetic": 3,
    "nightmare": 3, "hate": 3, "ruined": 3, "unacceptable": 3,
    "hazard": 3, "ripoff": 3, "waste": 3,
    # --- Medium (2) ---
    "bad": 2, "slow": 2, "late": 2, "poor": 2, "annoying": 2,
    "damaged": 2, "confusing": 2, "expensive": 2, "disappointed": 2,
    "frustrating": 2, "defective": 2, "rude": 2, "unhelpful": 2,
    "overpriced": 2, "dismissive": 2, "complained": 2, "refund": 2,
    "return": 2, "fake": 2, "misleading": 2, "crashed": 2,
    "crushed": 2, "flimsy": 2, "cheap": 2, "dishonest": 2,
    "inaccurate": 2, "untrained": 2, "unresponsive": 2, "complicated": 2,
    "lost": 2, "wrong": 2, "missing": 2, "delayed": 2, "careless": 2,
    "never": 2,
    # --- Weak (1) ---
    "average": 1, "minor": 1, "slightly": 1, "inconsistent": 1,
    "tearing": 1,
}

# ── Domain-specific vocabulary (merged into weighted dicts) ──────────

DOMAIN_POSITIVE = {
    # Delivery
    "fast": 2, "early": 2, "quick": 2, "prompt": 2,
    "on-time": 2, "timely": 2,
    # Support
    "resolved": 2,
    # Product
    "quality": 2,
    # Website/App
    "user-friendly": 2,
    # Payment
    "secure": 2, "seamless": 2,
    # Price
    "reasonable": 2, "affordable": 2, "value": 2,
}

DOMAIN_NEGATIVE = {
    # Support
    "ignored": 2, "ghosted": 2, "useless": 2,
    # Product
    "fragile": 2, "defective": 2,
    # Website/App
    "laggy": 2, "clunky": 2,
    # Payment
    "failed": 2, "declined": 2, "stuck": 2,
    # Price
    "costly": 2,
}

# Merge domain vocabulary into main weighted dicts (domain doesn't override existing)
for _w, _s in DOMAIN_POSITIVE.items():
    POSITIVE_WEIGHTED.setdefault(_w, _s)
for _w, _s in DOMAIN_NEGATIVE.items():
    NEGATIVE_WEIGHTED.setdefault(_w, _s)

# Legacy flat lists derived from weighted dicts (for backward compatibility)
POSITIVE_WORDS = list(POSITIVE_WEIGHTED.keys())
NEGATIVE_WORDS = list(NEGATIVE_WEIGHTED.keys())


# ── Context-aware patterns for ambiguous words ───────────────────────
# These are multi-word phrases where a normally neutral word gains sentiment.

CONTEXT_POSITIVE_PATTERNS = [
    (re.compile(r"\bhigh\s+quality\b", re.I), 2),
    (re.compile(r"\blong\s+(?:battery|lasting|life)\b", re.I), 2),
    (re.compile(r"\bbig\s+(?:improvement|upgrade|selection)\b", re.I), 2),
    (re.compile(r"\blow\s+price[sd]?\b", re.I), 2),
    (re.compile(r"\bshort\s+(?:wait|delivery)\b", re.I), 2),
    (re.compile(r"\bsmall\s+(?:footprint|size)\b", re.I), 1),
]

CONTEXT_NEGATIVE_PATTERNS = [
    (re.compile(r"\bhigh\s+price[sd]?\b", re.I), 2),
    (re.compile(r"\blong\s+(?:delay|wait(?:ing)?|time|shipping|queue)\b", re.I), 2),
    (re.compile(r"\bbig\s+(?:problem|issue|disappointment|mistake)\b", re.I), 2),
    (re.compile(r"\blow\s+quality\b", re.I), 2),
    (re.compile(r"\bshort\s+(?:battery|life(?:span)?)\b", re.I), 2),
    (re.compile(r"\bsmall\s+(?:portion|screen)\b", re.I), 1),
]


# ── Multilingual sentiment word mappings ─────────────────────────────

MULTILINGUAL_POSITIVE = {
    # Spanish
    "bueno": "good", "excelente": "excellent", "increíble": "incredible",
    "perfecto": "perfect", "maravilloso": "wonderful", "genial": "great",
    "fantástico": "fantastic", "encantado": "happy", "satisfecho": "satisfied",
    "rápido": "fast", "amable": "friendly",
    # French  ("excellent" omitted — already in English dict)
    "bon": "good", "incroyable": "incredible",
    "parfait": "perfect", "merveilleux": "wonderful", "génial": "great",
    "fantastique": "fantastic", "satisfait": "satisfied", "rapide": "fast",
    "formidable": "great",
}

MULTILINGUAL_NEGATIVE = {
    # Spanish  ("terrible"/"horrible" omitted — already in English dict)
    "malo": "bad", "lenta": "slow", "lento": "slow",
    "roto": "broken", "decepcionado": "disappointed",
    "caro": "overpriced", "defectuoso": "defective", "confuso": "confusing",
    "dañado": "damaged", "falso": "fake",
    # French  ("horrible" omitted — already in English dict)
    "mauvais": "bad", "lent": "slow", "lente": "slow", "cassé": "broken",
    "déçu": "disappointed", "cher": "overpriced",
    "défectueux": "defective", "confus": "confusing", "endommagé": "damaged",
}

STOP_WORDS = [
    "the", "a", "an", "and", "is", "it", "in", "to", "of", "for",
    "was", "with", "my", "i", "that", "this", "but", "not", "very",
    "be", "on", "are", "at", "have", "has", "had", "from", "or",
    "as", "by", "do", "so", "if", "their", "our", "we", "you",
    "me", "they", "them", "what", "all", "would", "will", "just",
    "been", "no", "its", "am", "did", "get", "got", "here", "too",
    "after", "over", "such", "out", "way", "up", "about", "any",
    "even", "like", "could", "than", "also", "more", "much", "can",
    "when", "how", "where", "which", "while", "who", "whom", "then",
    "there", "were", "being", "does", "done", "going", "went", "come"
]

CATEGORY_KEYWORDS = {
    "Product":  ["product", "quality", "item", "features", "broke",
                 "defective", "works", "looks", "description", "material",
                 "design", "build", "durable", "craftsmanship", "battery"],
    "Delivery": ["delivery", "shipping", "arrived", "package",
                 "packaging", "fast", "late", "damaged", "packed",
                 "transit", "courier", "tracking", "shipped", "bubble wrap"],
    "Service":  ["service", "experience", "staff", "shopping",
                 "navigate", "website", "process", "ordering",
                 "checkout", "app", "interface", "browsing"],
    "Price":    ["price", "value", "money", "expensive", "cheap",
                 "pricing", "cost", "overpriced", "fair", "deal",
                 "discount", "rupee", "worth", "budget", "sale"],
    "Support":  ["support", "customer support", "responded", "emails",
                 "resolved", "help", "replied", "messages", "team",
                 "customer care", "warranty", "replacement", "agent"]
}

# Negation patterns: phrases where a negator flips sentiment
NEGATION_PATTERNS = re.compile(
    r"\b(?:not|never|no|n't|wasn't|weren't|isn't|aren't|don't|doesn't|didn't|"
    r"wouldn't|couldn't|shouldn't|can't|cannot|hardly|barely|scarcely)\b",
    re.IGNORECASE
)

# Pre-compiled regex patterns for sentiment analysis (compiled once at module load)
PRECOMPILED_POSITIVE = [(word, re.compile(rf"\b{re.escape(word)}\b")) for word in POSITIVE_WEIGHTED]
PRECOMPILED_NEGATIVE = [(word, re.compile(rf"\b{re.escape(word)}\b")) for word in NEGATIVE_WEIGHTED]
PRECOMPILED_MULTILINGUAL_POS = [(word, re.compile(rf"\b{re.escape(word)}\b")) for word in MULTILINGUAL_POSITIVE]
PRECOMPILED_MULTILINGUAL_NEG = [(word, re.compile(rf"\b{re.escape(word)}\b")) for word in MULTILINGUAL_NEGATIVE]
PRECOMPILED_CATEGORIES = {
    cat: [(kw, re.compile(rf"\b{re.escape(kw)}\b")) for kw in keywords]
    for cat, keywords in CATEGORY_KEYWORDS.items()
}

# Symbols to strip during preprocessing (preserve emojis and alphanumerics)
_STRIP_SYMBOLS = re.compile(r"[<>=%;@#\^\*\{\}\[\]\\|~`]")


def normalize_text(text):
    """Repair mojibake and normalize encoding.

    Handles the common case where UTF-8 bytes were misread as latin-1,
    producing garbled sequences like ``Ã¨`` instead of ``è``.
    Preserves emojis, accented characters, and already-valid text.
    """
    if not text:
        return text
    try:
        # If the string contains mojibake (UTF-8 bytes decoded as latin-1),
        # re-encoding to latin-1 recovers the original bytes, then we
        # decode them properly as UTF-8.
        repaired = text.encode("latin-1").decode("utf-8")
        return repaired
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Text is already valid or uses characters outside latin-1 range
        # (e.g. emojis, CJK).  Return as-is.
        return text


def preprocess_text(text):
    """Normalize encoding, strip junk symbols, preserve emojis and words."""
    text = normalize_text(text)
    cleaned = _STRIP_SYMBOLS.sub(" ", text)
    # Collapse multiple spaces
    cleaned = re.sub(r"  +", " ", cleaned).strip()
    return cleaned


def _check_negation(text, word):
    """Check if a sentiment word is preceded by a negation within a 3-word window."""
    # Find the position of the word in text
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return False
    # Extract up to 4 words before the match
    prefix = text[:match.start()]
    prefix_words = prefix.split()[-4:]
    prefix_chunk = " ".join(prefix_words)
    return bool(NEGATION_PATTERNS.search(prefix_chunk))


def _compute_confidence(pos_score, neg_score, total_relevant, label=None):
    """
    Calibrated confidence score using weighted sentiment scores.

    For Mixed:    confidence = strength * 0.7 + balance * 0.3
    For one-sided: confidence = strength * 0.6 + dominance * 0.4

    A density cap prevents single-keyword inflation on very short texts.
    Returns a float 0.0–1.0.
    """
    total_sentiment = pos_score + neg_score
    if total_relevant == 0 or total_sentiment == 0:
        return 0.0

    # Strength now uses weighted scores divided by (relevant words * max weight)
    # This normalizes so a single strong word doesn't auto-max confidence
    max_possible = total_relevant * 3  # theoretical max if every word was weight-3
    strength = min(total_sentiment / max(1, max_possible), 1.0)
    balance = min(pos_score, neg_score) / max(pos_score, neg_score)

    if label == "Mixed":
        raw = strength * 0.7 + balance * 0.3
    else:
        dominance = abs(pos_score - neg_score) / total_sentiment
        raw = strength * 0.6 + dominance * 0.4

    # Density cap: dampen confidence when very few total words
    if total_relevant <= 2:
        raw *= 0.6
    elif total_relevant <= 4:
        raw *= 0.8

    return min(1.0, max(0.0, raw))


def analyze_sentiment(feedback_list):
    """
    Analyzes sentiment with:
    - Weighted vocabulary (strong=3, medium=2, weak=1)
    - Context-aware patterns for ambiguous words
    - Mixed classification (both pos & neg signals present)
    - Negation handling (flips polarity when negator precedes sentiment word)
    - Multilingual word support (Spanish, French)
    - Label-aware confidence scoring
    """
    results = {"Positive": [], "Negative": [], "Neutral": [], "Mixed": [], "detailed": []}

    for feedback in feedback_list:
        preprocessed = preprocess_text(feedback)
        lower = preprocessed.lower()
        pos_score = 0
        neg_score = 0

        # --- Context-aware patterns (checked first, higher priority) ----
        for pattern, weight in CONTEXT_POSITIVE_PATTERNS:
            if pattern.search(lower):
                pos_score += weight
        for pattern, weight in CONTEXT_NEGATIVE_PATTERNS:
            if pattern.search(lower):
                neg_score += weight

        # --- Core English weighted sentiment matching with negation ---
        for word, pattern in PRECOMPILED_POSITIVE:
            if pattern.search(lower):
                weight = POSITIVE_WEIGHTED[word]
                if _check_negation(lower, word):
                    neg_score += weight  # "not good" → negative
                else:
                    pos_score += weight
        for word, pattern in PRECOMPILED_NEGATIVE:
            if pattern.search(lower):
                weight = NEGATIVE_WEIGHTED[word]
                if _check_negation(lower, word):
                    pos_score += weight  # "not bad" → positive
                else:
                    neg_score += weight

        # --- Multilingual matching (use weight of English equivalent) ---
        for word, pattern in PRECOMPILED_MULTILINGUAL_POS:
            if pattern.search(lower):
                eng = MULTILINGUAL_POSITIVE[word]
                weight = POSITIVE_WEIGHTED.get(eng, 2)
                if _check_negation(lower, word):
                    neg_score += weight
                else:
                    pos_score += weight
        for word, pattern in PRECOMPILED_MULTILINGUAL_NEG:
            if pattern.search(lower):
                eng = MULTILINGUAL_NEGATIVE[word]
                weight = NEGATIVE_WEIGHTED.get(eng, 2)
                if _check_negation(lower, word):
                    pos_score += weight
                else:
                    neg_score += weight

        # --- Count relevant words for density ---
        cleaned_for_count = re.sub(r"[^a-z\s\u00C0-\u024F]", " ", lower)  # Keep accented chars
        words = [w for w in cleaned_for_count.split() if w not in STOP_WORDS and len(w) > 1]
        total_relevant = len(words)

        # --- Classification (must precede confidence so label is available) ---
        if pos_score > 0 and neg_score > 0:
            smaller = min(pos_score, neg_score)
            larger = max(pos_score, neg_score)
            sentiment_balance = smaller / larger

            # Classify as Mixed only when both signals are meaningful
            if sentiment_balance >= 0.35:
                label = "Mixed"
            elif pos_score > neg_score:
                label = "Positive"
            else:
                label = "Negative"
        elif pos_score > neg_score:
            label = "Positive"
        elif neg_score > pos_score:
            label = "Negative"
        else:
            label = "Neutral"

        # --- Confidence calculation (label-aware) ---
        if label == "Neutral":
            confidence = 0.0
        else:
            confidence = _compute_confidence(pos_score, neg_score, total_relevant, label=label)

        results[label].append(feedback)

        results["detailed"].append({
            "feedback": feedback,
            "label": label,
            "confidence": round(confidence * 100, 1)
        })

    return results


def word_frequency(feedback_list, top_n=10):
    freq = {}

    for feedback in feedback_list:
        preprocessed = preprocess_text(feedback)
        cleaned = ""
        for ch in preprocessed:
            if ch.isalnum() or ch == " ":
                cleaned += ch.lower()
            else:
                cleaned += " "

        words = cleaned.split()
        for word in words:
            if word not in STOP_WORDS and len(word) > 1:
                if word in freq:
                    freq[word] += 1
                else:
                    freq[word] = 1

    sorted_freq = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return sorted_freq[:top_n]


def get_statistics(feedback_list):
    if not feedback_list:
        return {"total": 0, "avg_length": 0, "shortest": "", "longest": ""}

    total = len(feedback_list)
    lengths = [len(fb) for fb in feedback_list]

    avg_length = sum(lengths) / total

    shortest = min(feedback_list, key=len)
    longest = max(feedback_list, key=len)

    return {
        "total": total,
        "avg_length": round(avg_length, 1),
        "shortest": shortest,
        "longest": longest
    }


def detect_categories(feedback_list):
    categorized = {}
    for cat in CATEGORY_KEYWORDS:
        categorized[cat] = []

    for feedback in feedback_list:
        lower = preprocess_text(feedback).lower()
        for cat, compiled_keywords in PRECOMPILED_CATEGORIES.items():
            for _kw, pattern in compiled_keywords:
                if pattern.search(lower):
                    categorized[cat].append(feedback)
                    break

    return categorized


def rating_distribution(csv_data):
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for record in csv_data:
        rating = record.get("rating", 0)
        if rating in distribution:
            distribution[rating] += 1
    return distribution

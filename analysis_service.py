from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Any

import feedback_analyzer as fa
from werkzeug.utils import secure_filename

REQUIRED_CSV_HEADERS = {"Name", "Rating", "Category", "Feedback"}
ALLOWED_EXTENSIONS = {".txt", ".csv"}


class AnalysisError(Exception):
    def __init__(self, message: str, code: str = "bad_request", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass
class ParsedFeedback:
    filename: str
    extension: str
    feedback_list: list[str]
    csv_rows: list[dict[str, Any]]
    total_bytes: int


def _safe_lower_words(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in cleaned.split() if len(w) > 1]


def parse_uploaded_feedback(uploaded_file) -> ParsedFeedback:
    if not uploaded_file or not uploaded_file.filename:
        raise AnalysisError("Please upload a .txt or .csv file")

    raw_filename = uploaded_file.filename.strip()
    extension = f".{raw_filename.rsplit('.', 1)[-1].lower()}" if "." in raw_filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise AnalysisError("Only .txt or .csv files are supported")
    filename = secure_filename(raw_filename)
    if not filename:
        filename = f"uploaded{extension}"

    raw = uploaded_file.read()
    total_bytes = len(raw)
    if total_bytes == 0:
        raise AnalysisError("Uploaded file is empty")

    content = raw.decode("utf-8-sig", errors="replace")
    if extension == ".txt":
        feedback = [line.strip() for line in content.splitlines() if line.strip()]
        if not feedback:
            raise AnalysisError("No valid feedback entries found in the selected file")
        return ParsedFeedback(
            filename=filename,
            extension=extension,
            feedback_list=feedback,
            csv_rows=[],
            total_bytes=total_bytes,
        )

    reader = csv.DictReader(io.StringIO(content))
    headers = set(reader.fieldnames or [])
    if not REQUIRED_CSV_HEADERS.issubset(headers):
        missing = ", ".join(sorted(REQUIRED_CSV_HEADERS - headers))
        raise AnalysisError(f"CSV is missing required headers: {missing}")

    rows: list[dict[str, Any]] = []
    for record in reader:
        rating_raw = (record.get("Rating") or "").strip()
        feedback_text = (record.get("Feedback") or "").strip()
        if not feedback_text:
            continue
        try:
            rating = int(rating_raw)
        except ValueError:
            continue
        if rating < 1 or rating > 5:
            continue
        rows.append(
            {
                "name": (record.get("Name") or "").strip(),
                "rating": rating,
                "category": (record.get("Category") or "").strip(),
                "feedback": feedback_text,
            }
        )

    feedback = [row["feedback"] for row in rows]
    if not feedback:
        raise AnalysisError("No valid feedback entries found in the selected CSV file")

    return ParsedFeedback(
        filename=filename,
        extension=extension,
        feedback_list=feedback,
        csv_rows=rows,
        total_bytes=total_bytes,
    )


def _top_negative_words(feedback_list: list[str], top_n: int = 8) -> list[dict[str, Any]]:
    negatives = fa.analyze_sentiment(feedback_list)["Negative"]
    if not negatives:
        return []
    words = fa.word_frequency(negatives, top_n=top_n)
    return [{"word": word, "count": count} for word, count in words]


def _action_suggestions(
    sentiment_percent: dict[str, float],
    categories: dict[str, int],
    avg_rating: float | None,
) -> list[str]:
    suggestions: list[str] = []

    if sentiment_percent.get("Negative", 0) >= 35:
        suggestions.append("Prioritize root-cause review for top negative comments this week.")
    if categories.get("Delivery", 0) > categories.get("Service", 0):
        suggestions.append("Audit shipping SLAs and packaging quality for delivery-heavy complaints.")
    if categories.get("Support", 0) >= 5:
        suggestions.append("Add support response-time KPI tracking for faster customer recovery.")
    if avg_rating is not None and avg_rating < 3.5:
        suggestions.append("Trigger product quality checks for low-rated SKUs and suppliers.")
    if not suggestions:
        suggestions.append("Maintain current performance and monitor weekly sentiment trend.")

    return suggestions


def _sentiment_label(feedback: str) -> str:
    sentiment = fa.analyze_sentiment([feedback])
    if sentiment["Positive"]:
        return "Positive"
    if sentiment["Negative"]:
        return "Negative"
    return "Neutral"


def _priority_insights(
    sentiment_percent: dict[str, float],
    categories: dict[str, int],
    negative_top_words: list[dict[str, Any]],
    avg_rating: float | None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    negative_pct = sentiment_percent.get("Negative", 0.0)
    if negative_pct >= 20:
        candidates.append(
            {
                "title": "Reduce negative sentiment",
                "score": round(negative_pct * 1.8, 1),
                "evidence": f"Negative sentiment is {negative_pct}%",
                "action": "Review and resolve top negative comments in the next cycle.",
            }
        )

    for category, count in sorted(categories.items(), key=lambda item: item[1], reverse=True)[:2]:
        if count > 0:
            candidates.append(
                {
                    "title": f"Address {category.lower()} issues",
                    "score": round(count * 3.0, 1),
                    "evidence": f"{count} feedback item(s) mapped to {category}",
                    "action": f"Prioritize corrective actions for {category.lower()} pain points.",
                }
            )

    if avg_rating is not None and avg_rating < 4:
        candidates.append(
            {
                "title": "Improve average rating",
                "score": round((4.0 - avg_rating) * 18, 1),
                "evidence": f"Average rating is {avg_rating}/5",
                "action": "Investigate low-rated experiences and close recurring gaps.",
            }
        )

    for word_entry in negative_top_words[:2]:
        word = word_entry.get("word", "")
        count = int(word_entry.get("count", 0))
        if word and count > 1:
            candidates.append(
                {
                    "title": f"Resolve '{word}' complaints",
                    "score": round(count * 4.0, 1),
                    "evidence": f"Keyword '{word}' appears {count} times in negative feedback",
                    "action": f"Create a short-term fix plan for '{word}' related complaints.",
                }
            )

    if not candidates:
        candidates.append(
            {
                "title": "Maintain current performance",
                "score": 1.0,
                "evidence": "No critical issue spike detected",
                "action": "Continue weekly monitoring for early warning signals.",
            }
        )

    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:3]


def build_analysis_payload(parsed: ParsedFeedback) -> dict[str, Any]:
    feedback_list = parsed.feedback_list
    stats = fa.get_statistics(feedback_list)
    sentiment = fa.analyze_sentiment(feedback_list)
    categories_raw = fa.detect_categories(feedback_list)
    categories = {name: len(items) for name, items in categories_raw.items()}
    top_words = fa.word_frequency(feedback_list, top_n=12)

    total = stats["total"]
    sentiment_counts = {key: len(value) for key, value in sentiment.items()}
    sentiment_percent = {
        key: round((count / total) * 100, 1) if total else 0
        for key, count in sentiment_counts.items()
    }

    if parsed.csv_rows:
        avg_rating = round(sum(r["rating"] for r in parsed.csv_rows) / len(parsed.csv_rows), 2)
        rating_dist = fa.rating_distribution(parsed.csv_rows)
    else:
        avg_rating = None
        rating_dist = None

    negative_top_words = _top_negative_words(feedback_list)
    priority_insights = _priority_insights(sentiment_percent, categories, negative_top_words, avg_rating)

    return {
        "source": "uploaded_csv" if parsed.extension == ".csv" else "uploaded_txt",
        "file": {
            "name": parsed.filename,
            "extension": parsed.extension,
            "size_bytes": parsed.total_bytes,
        },
        "stats": stats,
        "sentiment": sentiment_counts,
        "sentiment_percent": sentiment_percent,
        "sentiment_series": [
            {"label": "Positive", "count": sentiment_counts["Positive"]},
            {"label": "Negative", "count": sentiment_counts["Negative"]},
            {"label": "Neutral", "count": sentiment_counts["Neutral"]},
        ],
        "top_words": [{"word": word, "count": count} for word, count in top_words],
        "negative_top_words": negative_top_words,
        "categories": categories,
        "rating_distribution": rating_dist,
        "average_rating": avg_rating,
        "samples": {key: value[:3] for key, value in sentiment.items()},
        "suggestions": _action_suggestions(sentiment_percent, categories, avg_rating),
        "priority_insights": priority_insights,
    }


def search_feedback(
    feedback_list: list[str],
    keyword: str,
    case_sensitive: bool = False,
    match_mode: str = "partial",
    sentiment_filter: str = "all",
    min_rating: int | None = None,
    csv_rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    keyword = keyword.strip()
    if not keyword:
        raise AnalysisError("keyword is required")
    if match_mode not in {"partial", "exact"}:
        raise AnalysisError("match_mode must be 'partial' or 'exact'")
    sentiment_filter = sentiment_filter.strip().lower()
    if sentiment_filter not in {"all", "positive", "negative", "neutral"}:
        raise AnalysisError("sentiment_filter must be one of: all, positive, negative, neutral")
    if min_rating is not None and (min_rating < 1 or min_rating > 5):
        raise AnalysisError("min_rating must be between 1 and 5")

    if not case_sensitive:
        keyword_cmp = keyword.lower()
    else:
        keyword_cmp = keyword

    matches = []
    # Optimization: Pre-calculate sentiment if filtering
    sentiment_map = {}
    if sentiment_filter != "all":
        # Group analyze instead of one-by-one to save overhead
        full_sentiment = fa.analyze_sentiment(feedback_list)
        for label, items in full_sentiment.items():
            label_lower = label.lower()
            for item in items:
                # Note: this assumes feedback strings are unique identifiers which is
                # usually true for short feedback or sufficient for this app.
                sentiment_map[item] = label_lower

    for idx, feedback in enumerate(feedback_list):
        if min_rating is not None:
            if not csv_rows or idx >= len(csv_rows):
                continue
            rating = csv_rows[idx].get("rating")
            if not isinstance(rating, int) or rating < min_rating:
                continue

        if sentiment_filter != "all":
            label = sentiment_map.get(feedback)
            if label != sentiment_filter:
                continue

        source = feedback if case_sensitive else feedback.lower()
        if match_mode == "exact":
            # Optimization: Use fixed regex for exact match
            pattern = rf"\b{re.escape(keyword_cmp)}\b"
            if re.search(pattern, source if case_sensitive else source):
                matches.append(feedback)
        elif keyword_cmp in source:
            matches.append(feedback)

    return matches

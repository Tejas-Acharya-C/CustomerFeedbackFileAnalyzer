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

    # UTF-8 detection with fallback chain
    content = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            content = raw.decode(encoding)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    if content is None:
        content = raw.decode("utf-8", errors="replace")
    if extension == ".txt":
        feedback = [fa.normalize_text(line.strip()) for line in content.splitlines() if line.strip()]
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
        feedback_text = fa.normalize_text((record.get("Feedback") or "").strip())
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


def _top_sentiment_words(sentiment: dict[str, list[str]], label: str, top_n: int = 8) -> list[dict[str, Any]]:
    items = sentiment.get(label, [])
    if not items:
        return []
    words = fa.word_frequency(items, top_n=top_n)
    return [{"word": word, "count": count} for word, count in words]


def _top_negative_words(sentiment: dict[str, list[str]], top_n: int = 8) -> list[dict[str, Any]]:
    return _top_sentiment_words(sentiment, "Negative", top_n)


def _top_positive_words(sentiment: dict[str, list[str]], top_n: int = 8) -> list[dict[str, Any]]:
    return _top_sentiment_words(sentiment, "Positive", top_n)


def _action_suggestions(
    sentiment_percent: dict[str, float],
    categories: dict[str, int],
    avg_rating: float | None,
) -> list[str]:
    suggestions: list[str] = []
    total_categorized = sum(categories.values())

    neg_pct = sentiment_percent.get("Negative", 0)
    mixed_pct = sentiment_percent.get("Mixed", 0)

    if neg_pct >= 35:
        suggestions.append(
            f"Negative sentiment is critically high at {neg_pct}%. "
            "Prioritize root-cause review for top negative comments this week."
        )
    elif neg_pct >= 20:
        suggestions.append(
            f"Negative sentiment at {neg_pct}% warrants monitoring. "
            "Schedule a bi-weekly review of emerging complaint patterns."
        )

    if mixed_pct >= 15:
        suggestions.append(
            f"Mixed sentiment accounts for {mixed_pct}% of feedback. "
            "Investigate experiences with both positive and negative aspects to isolate fixable gaps."
        )

    # Dynamic category-driven recommendations (top 2 dominant categories)
    sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    for cat_name, count in sorted_cats[:2]:
        if count > 0 and total_categorized > 0:
            pct = round((count / total_categorized) * 100, 1)
            if pct >= 30:
                suggestions.append(
                    f"{cat_name} dominates at {pct}% of categorized mentions ({count} items). "
                    f"Conduct a focused {cat_name.lower()} quality review this cycle."
                )

    if avg_rating is not None and avg_rating < 3.0:
        suggestions.append(
            f"Average rating is critically low at {avg_rating}/5. "
            "Trigger immediate product quality checks for lowest-rated items."
        )
    elif avg_rating is not None and avg_rating < 3.5:
        suggestions.append(
            f"Average rating of {avg_rating}/5 is below target. "
            "Investigate low-rated experiences and close recurring gaps."
        )

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


def _business_insights(
    sentiment_percent: dict[str, float],
    categories_raw: dict[str, list[str]],
    avg_rating: float | None,
) -> dict[str, Any]:
    strengths = []
    complaints = []
    
    # Calculate category performance
    cat_stats = {}
    for cat, items in categories_raw.items():
        if not items:
            continue
        s = fa.analyze_sentiment(items)
        pos_pct = (len(s["Positive"]) / len(items)) * 100
        neg_pct = (len(s["Negative"]) / len(items)) * 100
        cat_stats[cat] = {"pos": pos_pct, "neg": neg_pct, "count": len(items)}

    # Top Strengths
    sorted_pos = sorted(cat_stats.items(), key=lambda x: x[1]["pos"], reverse=True)
    for cat, stats in sorted_pos:
        if stats["pos"] >= 50 and stats["count"] >= 1:
            strengths.append(f"{cat} performance ({round(stats['pos'])}% positive)")
    
    # Top Complaints
    sorted_neg = sorted(cat_stats.items(), key=lambda x: x[1]["neg"], reverse=True)
    for cat, stats in sorted_neg:
        if stats["neg"] >= 30 and stats["count"] >= 1:
            complaints.append(f"{cat} friction ({round(stats['neg'])}% negative)")

    # Fallbacks
    if not strengths: strengths = ["Overall sentiment stability"]
    if not complaints: complaints = ["No major frictional clusters detected"]

    return {
        "top_strengths": strengths[:3],
        "top_complaints": complaints[:3],
    }


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
    sentiment_data = fa.analyze_sentiment(feedback_list)
    
    categories_raw = fa.detect_categories(feedback_list)
    categories = {name: len(items) for name, items in categories_raw.items()}
    top_words = fa.word_frequency(feedback_list, top_n=12)

    total = stats["total"]
    sentiment_counts = {key: len(value) for key, value in sentiment_data.items() if key != "detailed"}
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

    negative_top_words = _top_negative_words(sentiment_data)
    positive_top_words = _top_positive_words(sentiment_data)
    
    priority_insights = _priority_insights(sentiment_percent, categories, negative_top_words, avg_rating)
    insights = _business_insights(sentiment_percent, categories_raw, avg_rating)

    # Calculate overall confidence
    detailed = sentiment_data.get("detailed", [])
    avg_confidence = round(sum(d["confidence"] for d in detailed) / len(detailed), 1) if detailed else 0

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
            {"label": "Positive", "count": sentiment_counts.get("Positive", 0)},
            {"label": "Negative", "count": sentiment_counts.get("Negative", 0)},
            {"label": "Neutral", "count": sentiment_counts.get("Neutral", 0)},
            {"label": "Mixed", "count": sentiment_counts.get("Mixed", 0)},
        ],
        "top_words": [{"word": word, "count": count} for word, count in top_words],
        "negative_top_words": negative_top_words,
        "positive_top_words": positive_top_words,
        "categories": categories,
        "rating_distribution": rating_dist,
        "average_rating": avg_rating,
        "overall_confidence": avg_confidence,
        "samples": {key: value[:3] for key, value in sentiment_data.items() if key != "detailed"},
        "suggestions": _action_suggestions(sentiment_percent, categories, avg_rating),
        "priority_insights": priority_insights,
        "business_insights": insights,
        "detailed_analysis": detailed,
    }


def generate_detailed_csv(payload: dict[str, Any], csv_rows: list[dict[str, Any]]) -> str:
    """Generates a detailed CSV with original data + sentiment + category + confidence."""
    output = io.StringIO()
    # Find all original headers if CSV, otherwise just 'Feedback'
    if csv_rows:
        headers = ["Name", "Rating", "Category", "Sentiment", "Confidence", "Feedback"]
    else:
        headers = ["Feedback", "Sentiment", "Confidence"]
    
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    
    detailed = payload.get("detailed_analysis", [])
    
    for idx, d in enumerate(detailed):
        row = {
            "Feedback": d["feedback"],
            "Sentiment": d["label"],
            "Confidence": f"{d['confidence']}%"
        }
        if csv_rows and idx < len(csv_rows):
            orig = csv_rows[idx]
            row["Name"] = orig.get("name", "N/A")
            row["Rating"] = orig.get("rating", 0)
            row["Category"] = orig.get("category", "Uncategorized")
            
        writer.writerow(row)
        
    return output.getvalue()


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
    if sentiment_filter not in {"all", "positive", "negative", "neutral", "mixed"}:
        raise AnalysisError("sentiment_filter must be one of: all, positive, negative, neutral, mixed")
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
            if label == "detailed":
                continue
            label_lower = label.lower()
            for item in items:
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

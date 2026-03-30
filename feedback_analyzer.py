import re
import csv

POSITIVE_WORDS = [
    "amazing", "love", "excellent", "great", "fantastic", "happy",
    "satisfied", "best", "outstanding", "perfect", "wonderful",
    "recommended", "good", "smooth", "helpful", "polite",
    "exceeded", "fast", "quick", "perfectly", "impressed",
    "premium", "durable", "stunning", "beautiful", "flawless",
    "seamless", "reliable", "comfortable", "intuitive", "incredible",
    "impeccable", "exceptional", "professional", "friendly", "worth",
    "responsive", "courteous", "efficient", "unbeatable", "loved"
]

NEGATIVE_WORDS = [
    "terrible", "worst", "broken", "poor", "horrible", "disappointed",
    "frustrating", "defective", "damaged", "rude", "unhelpful",
    "slow", "confusing", "overpriced", "bad", "never", "hate",
    "unacceptable", "dismissive", "complained", "refund", "return",
    "waste", "fake", "misleading", "nightmare", "crashed", "ruined",
    "crushed", "tearing", "flimsy", "cheap", "dishonest", "inaccurate",
    "ripoff", "untrained", "unresponsive", "complicated", "hazard",
    "lost", "wrong", "missing", "delayed", "careless"
]

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


def load_txt(filepath):
    feedback_list = []
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    feedback_list.append(stripped)
    except Exception:
        pass
    return feedback_list


def load_csv(filepath):
    csv_data = []
    try:
        with open(filepath, "r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                feedback = (row.get("Feedback") or "").strip()
                if not feedback:
                    continue
                try:
                    rating = int((row.get("Rating") or "").strip())
                except ValueError:
                    continue
                record = {
                    "name": (row.get("Name") or "").strip(),
                    "rating": rating,
                    "category": (row.get("Category") or "").strip(),
                    "feedback": feedback
                }
                csv_data.append(record)
    except Exception:
        pass
    return csv_data


def analyze_sentiment(feedback_list):
    results = {"Positive": [], "Negative": [], "Neutral": []}

    for feedback in feedback_list:
        lower = feedback.lower()
        pos_count = 0
        neg_count = 0

        for word in POSITIVE_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                pos_count += 1
        for word in NEGATIVE_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                neg_count += 1

        if pos_count > neg_count:
            results["Positive"].append(feedback)
        elif neg_count > pos_count:
            results["Negative"].append(feedback)
        else:
            results["Neutral"].append(feedback)

    return results


def word_frequency(feedback_list, top_n=10):
    freq = {}

    for feedback in feedback_list:
        cleaned = ""
        for ch in feedback:
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


def search_feedback(feedback_list, keyword):
    keyword_lower = keyword.lower()
    matches = []

    for feedback in feedback_list:
        if keyword_lower in feedback.lower():
            matches.append(feedback)

    return matches


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
        lower = feedback.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", lower):
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


def generate_report(feedback_list, csv_data=None):
    lines = []
    lines.append("=" * 56)
    lines.append("       CUSTOMER FEEDBACK ANALYSIS REPORT")
    lines.append("=" * 56)

    stats = get_statistics(feedback_list)
    lines.append("\n-- STATISTICS ------------------------------")
    lines.append(f"  Total Feedback Entries : {stats['total']}")
    lines.append(f"  Average Length (chars) : {stats['avg_length']}")
    lines.append(f"  Shortest Feedback      : \"{stats['shortest'][:60]}...\"")
    lines.append(f"  Longest Feedback       : \"{stats['longest'][:60]}...\"")

    sentiment = analyze_sentiment(feedback_list)
    lines.append("\n-- SENTIMENT ANALYSIS ----------------------")
    lines.append(f"  Positive : {len(sentiment['Positive']):>3}  "
                 f"({_percent(len(sentiment['Positive']), stats['total'])}%)")
    lines.append(f"  Negative : {len(sentiment['Negative']):>3}  "
                 f"({_percent(len(sentiment['Negative']), stats['total'])}%)")
    lines.append(f"  Neutral  : {len(sentiment['Neutral']):>3}  "
                 f"({_percent(len(sentiment['Neutral']), stats['total'])}%)")

    top_words = word_frequency(feedback_list, 10)
    lines.append("\n-- TOP 10 WORDS ----------------------------")
    for rank, (word, count) in enumerate(top_words, 1):
        bar = "#" * count
        lines.append(f"  {rank:>2}. {word:<15} {count:>3}  {bar}")

    categories = detect_categories(feedback_list)
    lines.append("\n-- CATEGORY BREAKDOWN ----------------------")
    for cat, items in categories.items():
        lines.append(f"  {cat:<12} : {len(items)} feedback(s)")

    if csv_data:
        dist = rating_distribution(csv_data)
        lines.append("\n-- STAR RATING DISTRIBUTION ----------------")
        for star in range(5, 0, -1):
            count = dist[star]
            bar = "*" * count
            lines.append(f"  {star} *  | {bar}  ({count})")

    lines.append("\n" + "=" * 56)
    lines.append("            END OF REPORT")
    lines.append("=" * 56)
    return "\n".join(lines)


def export_report(report, filepath):
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(report)
    except Exception:
        pass


def _percent(part, total):
    if total == 0:
        return "0.0"
    return str(round(part / total * 100, 1))

import os

import feedback_analyzer as fa

txt_feedback = []
csv_data = []
active_feedback = []


def display_menu():
    print("\n" + "=" * 48)
    print("     CUSTOMER FEEDBACK FILE ANALYZER")
    print("=" * 48)
    print("  1.  Load Feedback from Text File (.txt)")
    print("  2.  Load Feedback from CSV  File (.csv)")
    print("  3.  Show Sentiment Analysis")
    print("  4.  Show Word Frequency (Top 10)")
    print("  5.  Search Feedback by Keyword")
    print("  6.  Show Feedback Statistics")
    print("  7.  Show Category Analysis")
    print("  8.  Show Rating Distribution (CSV only)")
    print("  9.  Generate & Export Full Report")
    print("  0.  Exit")
    print("=" * 48)


def ensure_loaded():
    if not active_feedback:
        print("\n  [WARN] No feedback data loaded!")
        print("     Please load a file first (option 1 or 2).")
        return False
    return True


def handle_load_txt():
    global txt_feedback, active_feedback
    filepath = input("\n  Enter path to .txt file (or press Enter for default): ").strip()
    if not filepath:
        filepath = os.path.join(os.path.dirname(__file__), "data", "feedback.txt")
    txt_feedback = fa.load_txt(filepath)
    active_feedback = txt_feedback


def handle_load_csv():
    global csv_data, active_feedback
    filepath = input("\n  Enter path to .csv file (or press Enter for default): ").strip()
    if not filepath:
        filepath = os.path.join(os.path.dirname(__file__), "data", "feedback.csv")
    csv_data = fa.load_csv(filepath)
    active_feedback = [record["feedback"] for record in csv_data]


def handle_sentiment():
    if not ensure_loaded():
        return
    results = fa.analyze_sentiment(active_feedback)
    total = len(active_feedback)

    print("\n" + "-" * 48)
    print("  SENTIMENT ANALYSIS RESULTS")
    print("-" * 48)

    for sentiment in ["Positive", "Negative", "Neutral"]:
        items = results[sentiment]
        count = len(items)
        pct = round(count / total * 100, 1) if total else 0
        bar = "#" * int(pct / 2)
        print(f"\n  {sentiment.upper()} - {count} feedback(s) ({pct}%) {bar}")
        print("  " + "." * 40)
        show_limit = 5
        for i, fb in enumerate(items[:show_limit], 1):
            print(f"    {i}. {fb[:75]}{'...' if len(fb) > 75 else ''}")
        if count > show_limit:
            print(f"    ... and {count - show_limit} more {sentiment.lower()} feedback(s)")


def handle_word_frequency():
    if not ensure_loaded():
        return
    top_words = fa.word_frequency(active_feedback, 10)

    print("\n" + "-" * 48)
    print("  TOP 10 MOST FREQUENT WORDS")
    print("-" * 48)
    max_bar = 30
    max_count = top_words[0][1] if top_words else 1
    for rank, (word, count) in enumerate(top_words, 1):
        bar_len = int(count / max_count * max_bar)
        bar = "#" * bar_len
        print(f"  {rank:>2}. {word:<15} {count:>3}  {bar}")


def handle_search():
    if not ensure_loaded():
        return
    keyword = input("\n  Enter keyword to search: ").strip()
    if not keyword:
        print("  [WARN] No keyword entered.")
        return

    matches = fa.search_feedback(active_feedback, keyword)
    print(f"\n  Found {len(matches)} result(s) for \"{keyword}\":")
    print("  " + "." * 40)
    if matches:
        for i, fb in enumerate(matches, 1):
            print(f"    {i}. {fb}")
    else:
        print("    No matching feedback found.")


def handle_statistics():
    if not ensure_loaded():
        return
    stats = fa.get_statistics(active_feedback)

    print("\n" + "-" * 48)
    print("  FEEDBACK STATISTICS")
    print("-" * 48)
    print(f"  Total Entries          : {stats['total']}")
    print(f"  Average Length (chars) : {stats['avg_length']}")
    print(f"\n  Shortest Feedback:")
    print(f"    \"{stats['shortest']}\"")
    print(f"\n  Longest Feedback:")
    print(f"    \"{stats['longest']}\"")


def handle_categories():
    if not ensure_loaded():
        return
    categories = fa.detect_categories(active_feedback)

    print("\n" + "-" * 48)
    print("  CATEGORY ANALYSIS")
    print("-" * 48)
    for cat, items in categories.items():
        count = len(items)
        print(f"\n  [CAT] {cat.upper()} - {count} feedback(s)")
        print("  " + "." * 40)
        if items:
            show_limit = 5
            for i, fb in enumerate(items[:show_limit], 1):
                print(f"    {i}. {fb[:75]}{'...' if len(fb) > 75 else ''}")
            if count > show_limit:
                print(f"    ... and {count - show_limit} more in this category")
        else:
            print("    (no feedback in this category)")


def handle_ratings():
    if not csv_data:
        print("\n  [WARN] Rating distribution requires CSV data!")
        print("     Please load a CSV file first (option 2).")
        return

    dist = fa.rating_distribution(csv_data)
    total = len(csv_data)

    print("\n" + "-" * 48)
    print("  STAR RATING DISTRIBUTION")
    print("-" * 48)
    for star in range(5, 0, -1):
        count = dist[star]
        pct = round(count / total * 100, 1) if total else 0
        bar = "* " * count
        print(f"  {star} *  | {bar}({count} - {pct}%)")
    print("-" * 48)

    total_score = 0
    for record in csv_data:
        total_score += record["rating"]
    avg = round(total_score / total, 2) if total else 0
    print(f"  Average Rating: {avg} / 5.0")


def handle_export():
    if not ensure_loaded():
        return
    report = fa.generate_report(active_feedback, csv_data if csv_data else None)

    print("\n" + report)

    export_path = os.path.join(os.path.dirname(__file__), "analysis_report.txt")
    fa.export_report(report, export_path)


def main():
    print("\n" + "*" * 48)
    print("  Welcome to the Customer Feedback Analyzer!")
    print("  Built with Python - File Reading & Strings")
    print("*" * 48)

    while True:
        display_menu()
        choice = input("\n  Enter your choice (0-9): ").strip()

        if choice == "1":
            handle_load_txt()
        elif choice == "2":
            handle_load_csv()
        elif choice == "3":
            handle_sentiment()
        elif choice == "4":
            handle_word_frequency()
        elif choice == "5":
            handle_search()
        elif choice == "6":
            handle_statistics()
        elif choice == "7":
            handle_categories()
        elif choice == "8":
            handle_ratings()
        elif choice == "9":
            handle_export()
        elif choice == "0":
            print("\n  Thank you for using the Feedback Analyzer!")
            print("  Goodbye!\n")
            break
        else:
            print("\n  [WARN] Invalid choice. Please enter a number from 0 to 9.")


if __name__ == "__main__":
    main()

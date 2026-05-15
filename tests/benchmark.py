"""
Benchmark suite for Customer Feedback File Analyzer.

Outputs reproducible results including:
  - Python version and platform
  - Dataset size
  - Run count (iterations)
  - Average timing per operation
  - Environment information

Usage:
    python -m tests.benchmark
"""
from __future__ import annotations

import platform
import statistics
import sys
import time

# Ensure project root is importable
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import feedback_analyzer as fa


def _generate_dataset(n: int) -> list[str]:
    """Generate a synthetic feedback dataset of size n."""
    templates = [
        "Great product, love the quality and design!",
        "Terrible delivery experience, package was damaged.",
        "Customer support was helpful and resolved my issue.",
        "Overpriced for what you get, very disappointed.",
        "Fast shipping, excellent packaging and smooth checkout.",
        "The product broke after two days, worst purchase ever.",
        "Friendly staff, smooth and intuitive experience overall.",
        "Late arrival, wrong item shipped, need a refund immediately.",
        "Beautiful design, premium build quality, worth every penny.",
        "Misleading description, cheap materials, complete waste.",
    ]
    return [templates[i % len(templates)] for i in range(n)]


def _bench(fn, *, runs: int = 10, label: str = "") -> dict:
    """Run fn() multiple times and return timing statistics."""
    timings = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
    return {
        "label": label,
        "runs": runs,
        "avg_ms": round(statistics.mean(timings) * 1000, 3),
        "median_ms": round(statistics.median(timings) * 1000, 3),
        "stdev_ms": round(statistics.stdev(timings) * 1000, 3) if len(timings) > 1 else 0,
        "min_ms": round(min(timings) * 1000, 3),
        "max_ms": round(max(timings) * 1000, 3),
    }


def main():
    dataset_sizes = [100, 500, 1000]
    run_count = 10

    print("=" * 64)
    print("  CUSTOMER FEEDBACK ANALYZER — BENCHMARK REPORT")
    print("=" * 64)
    print()
    print("  Environment")
    print(f"    Python version : {sys.version}")
    print(f"    Platform       : {platform.platform()}")
    print(f"    Processor      : {platform.processor() or 'N/A'}")
    print(f"    Machine        : {platform.machine()}")
    print(f"    Runs per bench : {run_count}")
    print()

    for size in dataset_sizes:
        dataset = _generate_dataset(size)
        print(f"  Dataset size: {size} entries")
        print(f"  {'-' * 56}")

        results = [
            _bench(lambda: fa.analyze_sentiment(dataset), runs=run_count, label="analyze_sentiment"),
            _bench(lambda: fa.word_frequency(dataset, top_n=12), runs=run_count, label="word_frequency"),
            _bench(lambda: fa.get_statistics(dataset), runs=run_count, label="get_statistics"),
            _bench(lambda: fa.detect_categories(dataset), runs=run_count, label="detect_categories"),
            _bench(lambda: fa.rating_distribution([{"rating": (i % 5) + 1} for i in range(size)]),
                   runs=run_count, label="rating_distribution"),
        ]

        for r in results:
            print(f"    {r['label']:<25s}  avg={r['avg_ms']:>8.3f}ms  "
                  f"median={r['median_ms']:>8.3f}ms  stdev={r['stdev_ms']:>7.3f}ms  "
                  f"[min={r['min_ms']:.3f}, max={r['max_ms']:.3f}]")
        print()

    print("=" * 64)
    print("  END OF BENCHMARK")
    print("=" * 64)


if __name__ == "__main__":
    main()

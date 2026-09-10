"""V2.1 benchmark suite — smarter memory retrieval performance.

Compares V1.1, V2.0 (no scorer), and V2.1 (with scorer) on accuracy,
generalization, and regression scenarios.

Usage:
    python -m benchmarks.v2_1_benchmarks
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.learner.base import LearningInput  # noqa: E402
from core.learner.learner_v1 import SimilarityLearner  # noqa: E402
from core.learner.learner_v2 import HybridSimilarityLearner  # noqa: E402
from core.learner.retrieval_scorer import ScorerConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    name: str
    description: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    results: list[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult) -> None:
        self.results.append(result)

    def summary(self) -> str:
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("  V2.1 SMARTER MEMORY RETRIEVAL BENCHMARK RESULTS")
        lines.append("=" * 70)
        lines.append("")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.name}")
            if r.description:
                lines.append(f"         {r.description}")
            for key, val in r.details.items():
                lines.append(f"         {key}: {val}")
            lines.append("")

        lines.append("-" * 70)
        lines.append(f"  Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        lines.append("-" * 70)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test datasets
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE = [
    ("sort a list", "use sorted()"),
    ("reverse a string", "s[::-1]"),
    ("find maximum", "max()"),
    ("filter items", "[x for x in lst if cond]"),
    ("join strings", "sep.join(items)"),
    ("count occurrences", "lst.count(x)"),
    ("remove duplicates", "set(lst)"),
    ("check membership", "x in collection"),
    ("open file", "open(path, mode)"),
    ("read file", "f.read()"),
]

# Paraphrases — V2.1 should still match via lexical similarity
PARAPHRASE_QUERIES = [
    ("how to sort a list", "use sorted()"),
    ("reverse a string python", "s[::-1]"),
    ("find the biggest number", "max()"),
    ("filter a list", "[x for x in lst if cond]"),
    ("concatenate strings", "sep.join(items)"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def train_v1(pairs: list[tuple[str, str]]) -> SimilarityLearner:
    v1 = SimilarityLearner()
    for text, output in pairs:
        inp = LearningInput(observation={"input": text, "output": output})
        v1.learn(inp)
    return v1


def train_v2_no_scorer(pairs: list[tuple[str, str]]) -> HybridSimilarityLearner:
    v2 = HybridSimilarityLearner(k=3)
    for text, output in pairs:
        v2.learn(LearningInput(observation={"input": text, "output": output}))
    return v2


def train_v2_with_scorer(pairs: list[tuple[str, str]]) -> HybridSimilarityLearner:
    v21 = HybridSimilarityLearner(
        k=3,
        scorer_config=ScorerConfig(
            quality_weight=0.1,
            recency_weight=0.05,
            diversity_threshold=0.9,
        ),
    )
    for text, output in pairs:
        v21.learn(LearningInput(observation={"input": text, "output": output}))
    return v21


def measure_accuracy(
    learner: Any, test_pairs: list[tuple[str, str]]
) -> dict[str, Any]:
    correct = 0
    total = len(test_pairs)
    latencies: list[float] = []

    for text, expected in test_pairs:
        start = time.perf_counter()
        pred = learner.predict(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
        if pred.output == expected:
            correct += 1

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    return {
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
        "correct": correct,
        "total": total,
        "avg_latency_ms": round(avg_latency, 3),
    }


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


def run_benchmarks() -> BenchmarkSuite:
    suite = BenchmarkSuite()

    # --- V1.1 baseline ---
    t0 = time.perf_counter()
    v1 = train_v1(KNOWLEDGE_BASE)
    v1_train_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    v1_results = measure_accuracy(v1, PARAPHRASE_QUERIES)
    v1_bench_ms = (time.perf_counter() - t0) * 1000

    suite.add(BenchmarkResult(
        name="V1.1 TF-IDF Baseline",
        description="Traditional TF-IDF similarity learning",
        passed=v1_results["accuracy"] >= 60,
        details={
            "accuracy": f"{v1_results['accuracy']}%",
            "avg_latency_ms": v1_results["avg_latency_ms"],
            "train_ms": round(v1_train_ms, 1),
            "benchmark_ms": round(v1_bench_ms, 1),
        },
    ))

    # --- V2.0 no scorer ---
    t0 = time.perf_counter()
    v20 = train_v2_no_scorer(KNOWLEDGE_BASE)
    v20_train_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    v20_results = measure_accuracy(v20, PARAPHRASE_QUERIES)
    v20_bench_ms = (time.perf_counter() - t0) * 1000

    suite.add(BenchmarkResult(
        name="V2.0 No Scorer",
        description="Hybrid similarity without quality/recency scoring",
        passed=v20_results["accuracy"] >= 60,
        details={
            "accuracy": f"{v20_results['accuracy']}%",
            "avg_latency_ms": v20_results["avg_latency_ms"],
            "train_ms": round(v20_train_ms, 1),
            "benchmark_ms": round(v20_bench_ms, 1),
        },
    ))

    # --- V2.1 with scorer ---
    t0 = time.perf_counter()
    v21 = train_v2_with_scorer(KNOWLEDGE_BASE)
    v21_train_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    v21_results = measure_accuracy(v21, PARAPHRASE_QUERIES)
    v21_bench_ms = (time.perf_counter() - t0) * 1000

    suite.add(BenchmarkResult(
        name="V2.1 With Scorer",
        description="Hybrid similarity with quality/recency/diversity scoring",
        passed=v21_results["accuracy"] >= 60,
        details={
            "accuracy": f"{v21_results['accuracy']}%",
            "avg_latency_ms": v21_results["avg_latency_ms"],
            "train_ms": round(v21_train_ms, 1),
            "benchmark_ms": round(v21_bench_ms, 1),
        },
    ))

    # --- V2.1 must not regress vs V2.0 ---
    no_regression = v21_results["accuracy"] >= v20_results["accuracy"] - 5  # allow 5% tolerance
    suite.add(BenchmarkResult(
        name="V2.1 vs V2.0 No Regression",
        description="V2.1 must not lose more than 5% accuracy vs V2.0",
        passed=no_regression,
        details={
            "v20_accuracy": f"{v20_results['accuracy']}%",
            "v21_accuracy": f"{v21_results['accuracy']}%",
            "difference": f"{v21_results['accuracy'] - v20_results['accuracy']}%",
        },
    ))

    # --- V2.1 latency overhead acceptable ---
    latency_overhead = (
        (v21_results["avg_latency_ms"] / v20_results["avg_latency_ms"] - 1.0) * 100
        if v20_results["avg_latency_ms"] > 0 else 0
    )
    latency_ok = v21_results["avg_latency_ms"] < 1.0  # under 1ms is fine
    suite.add(BenchmarkResult(
        name="V2.1 Latency Overhead",
        description="V2.1 scoring must stay under 1ms per prediction",
        passed=latency_ok,
        details={
            "v20_avg_ms": v20_results["avg_latency_ms"],
            "v21_avg_ms": v21_results["avg_latency_ms"],
            "overhead_pct": f"{round(latency_overhead, 1)}%",
        },
    ))

    # --- V2.1 usage tracking works ---
    v21.predict("sort a list")
    v21.predict("sort a list")
    v21.predict("reverse a string")

    stats = v21._memory.get_usage_stats(0)
    usage_tracked = stats is not None and stats["use_count"] > 0
    suite.add(BenchmarkResult(
        name="V2.1 Usage Tracking",
        description="Memory usage is tracked during predictions",
        passed=usage_tracked,
        details={
            "use_count": stats["use_count"] if stats else 0,
        },
    ))

    # --- V2.1 feedback records success/failure ---
    v21.feedback(text="sort a list", predicted="use sorted()", correct=True)
    v21.feedback(text="sort a list", predicted="use sorted()", correct=True)

    stats_after = v21._memory.get_usage_stats(0)
    feedback_tracked = stats_after is not None and stats_after["success_count"] >= 2
    suite.add(BenchmarkResult(
        name="V2.1 Feedback Tracking",
        description="Success/failure counts are recorded from feedback",
        passed=feedback_tracked,
        details={
            "success_count": stats_after["success_count"] if stats_after else 0,
        },
    ))

    # --- V2.1 save/load preserves scorer config ---
    with tempfile.TemporaryDirectory() as tmpdir:
        v21.save_state(tmpdir)
        loaded = HybridSimilarityLearner.load_state(
            tmpdir,
            scorer_config=ScorerConfig(
                quality_weight=0.1,
                recency_weight=0.05,
                diversity_threshold=0.9,
            ),
        )
        pred = loaded.predict("sort a list")
        load_ok = pred.output == "use sorted()"

    suite.add(BenchmarkResult(
        name="V2.1 Persistence",
        description="V2.1 state saves and loads correctly",
        passed=load_ok,
        details={
            "loaded_prediction": pred.output,
            "expected": "use sorted()",
        },
    ))

    # --- Regression: V1 vs V2.1 same predictions for exact matches ---
    v1_exact = measure_accuracy(v1, KNOWLEDGE_BASE)
    v21_exact = measure_accuracy(v21, KNOWLEDGE_BASE)
    exact_match_ok = v21_exact["accuracy"] >= v1_exact["accuracy"] - 5

    suite.add(BenchmarkResult(
        name="V2.1 vs V1.1 Regression",
        description="V2.1 must not lose more than 5% accuracy vs V1.1",
        passed=exact_match_ok,
        details={
            "v1_accuracy": f"{v1_exact['accuracy']}%",
            "v21_accuracy": f"{v21_exact['accuracy']}%",
        },
    ))

    return suite


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import tempfile

    results_dir = _project_root / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    suite = run_benchmarks()
    print(suite.summary())

    # Save results
    result_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [
            {
                "name": r.name,
                "description": r.description,
                "passed": r.passed,
                "details": r.details,
            }
            for r in suite.results
        ],
    }
    out_path = results_dir / "v2_1_benchmark.json"
    out_path.write_text(json.dumps(result_data, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")

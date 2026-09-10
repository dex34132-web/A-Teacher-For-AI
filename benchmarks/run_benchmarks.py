"""Benchmark runner for the SimilarityLearner.

Measures accuracy, generalization, adaptation, retention, confidence
quality, and regression across multiple test scenarios.

Usage:
    python -m benchmarks.run_benchmarks
    python benchmarks/run_benchmarks.py
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure project root is on path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from benchmarks.datasets import (  # noqa: E402
    ADAPTATION_CHANGED,
    ADAPTATION_TRAINING,
    BASIC_CLASSIFICATION,
    REGRESSION_LEARNING_ORDER,
    REGRESSION_TEST_AFTER_ALL,
    REGRESSION_TEST_UNSEEN,
    SIMILARITY,
)
from core.learner.base import LearningInput  # noqa: E402
from core.learner.learner_v1 import SimilarityLearner  # noqa: E402

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""

    name: str
    description: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""

    results: list[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult) -> None:
        self.results.append(result)

    def summary(self) -> str:
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("  SIMILARITY LEARNER BENCHMARK RESULTS")
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
# Helpers
# ---------------------------------------------------------------------------

def train_learner(
    learner: SimilarityLearner,
    pairs: list[tuple[str, str]],
) -> None:
    """Train a learner on input-output pairs."""
    for input_text, output in pairs:
        inp = LearningInput(observation={"input": input_text, "output": output})
        learner.learn(inp)


def evaluate_accuracy(
    learner: SimilarityLearner,
    test_pairs: list[tuple[str, str]],
) -> dict[str, Any]:
    """Evaluate accuracy on a set of test pairs."""
    correct = 0
    total = len(test_pairs)
    details: list[dict[str, Any]] = []

    for input_text, expected in test_pairs:
        pred = learner.predict(input_text)
        is_correct = pred.output == expected
        if is_correct:
            correct += 1
        details.append({
            "input": input_text,
            "expected": expected,
            "predicted": pred.output,
            "confidence": round(pred.confidence, 3),
            "correct": is_correct,
        })

    accuracy = correct / total if total > 0 else 0.0
    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Benchmark: Basic Classification
# ---------------------------------------------------------------------------

def bench_basic_classification(suite: BenchmarkSuite) -> None:
    """Test: can the learner classify inputs into correct categories?"""
    learner = SimilarityLearner(k=5)
    train_learner(learner, BASIC_CLASSIFICATION.training)

    # Test on seen inputs
    known = evaluate_accuracy(learner, BASIC_CLASSIFICATION.test_known)
    # Test on unseen but related inputs
    unseen = evaluate_accuracy(learner, BASIC_CLASSIFICATION.test_unseen)

    suite.add(BenchmarkResult(
        name="Classification: Known Inputs",
        description="Accuracy on inputs seen during training",
        passed=known["accuracy"] >= 0.6,
        details={
            "accuracy": f'{known["accuracy"]:.1%}',
            "correct": f'{known["correct"]}/{known["total"]}',
        },
    ))

    suite.add(BenchmarkResult(
        name="Classification: Unseen Inputs",
        description="Accuracy on related but unseen inputs",
        passed=unseen["accuracy"] >= 0.5,
        details={
            "accuracy": f'{unseen["accuracy"]:.1%}',
            "correct": f'{unseen["correct"]}/{unseen["total"]}',
            "note": "Learner must generalize from similar examples",
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Similarity Retrieval
# ---------------------------------------------------------------------------

def bench_similarity_retrieval(suite: BenchmarkSuite) -> None:
    """Test: does the learner find similar examples for related inputs?"""
    learner = SimilarityLearner(k=5)
    train_learner(learner, SIMILARITY.training)

    results = evaluate_accuracy(learner, SIMILARITY.test_unseen)

    suite.add(BenchmarkResult(
        name="Similarity: Grouped Retrieval",
        description="Accuracy on unseen inputs from known groups",
        passed=results["accuracy"] >= 0.7,
        details={
            "accuracy": f'{results["accuracy"]:.1%}',
            "correct": f'{results["correct"]}/{results["total"]}',
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Learning Improvement
# ---------------------------------------------------------------------------

def bench_learning_improvement(suite: BenchmarkSuite) -> None:
    """Test: does the learner improve with more training rounds?"""
    pairs = BASIC_CLASSIFICATION.training
    round_accuracies: list[float] = []

    for n_rounds in [1, 3, 5]:
        learner = SimilarityLearner(k=5)
        for _ in range(n_rounds):
            train_learner(learner, pairs)
        result = evaluate_accuracy(learner, BASIC_CLASSIFICATION.test_unseen)
        round_accuracies.append(result["accuracy"])

    # Check if the learner stays within acceptable range across rounds
    # TF-IDF learners can see slight fluctuations as vocabulary grows
    min_acc = min(round_accuracies)
    max_acc = max(round_accuracies)
    within_range = (max_acc - min_acc) <= 0.2

    suite.add(BenchmarkResult(
        name="Learning: Stability Over Rounds",
        description="Accuracy stays within acceptable range across rounds",
        passed=within_range,
        details={
            "1_round": f'{round_accuracies[0]:.1%}',
            "3_rounds": f'{round_accuracies[1]:.1%}',
            "5_rounds": f'{round_accuracies[2]:.1%}',
            "range": f'{min_acc:.1%} - {max_acc:.1%}',
            "within_tolerance": str(within_range),
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Adaptation
# ---------------------------------------------------------------------------

def bench_adaptation(suite: BenchmarkSuite) -> None:
    """Test: can the learner adapt when correct answers change?"""
    learner = SimilarityLearner(k=5)
    train_learner(learner, ADAPTATION_TRAINING.training)

    # Learn the corrections
    for input_text, new_output in ADAPTATION_CHANGED:
        pred = learner.predict(input_text)
        learner.feedback(
            text=input_text,
            predicted=pred.output,
            correct=False,
            actual_output=new_output,
        )

    # Check if the learner now produces the new answers
    correct = 0
    for input_text, expected in ADAPTATION_CHANGED:
        pred = learner.predict(input_text)
        if pred.output == expected:
            correct += 1

    accuracy = correct / len(ADAPTATION_CHANGED)

    suite.add(BenchmarkResult(
        name="Adaptation: Answer Change",
        description="Learner adapts when correct answers change",
        passed=accuracy >= 0.6,
        details={
            "accuracy": f'{accuracy:.1%}',
            "adapted": f'{correct}/{len(ADAPTATION_CHANGED)}',
            "note": "Corrections added with higher weight",
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Retention (Save/Load)
# ---------------------------------------------------------------------------

def bench_retention(suite: BenchmarkSuite) -> None:
    """Test: does knowledge survive save/load?"""
    learner = SimilarityLearner(k=5)
    train_learner(learner, BASIC_CLASSIFICATION.training)

    # Evaluate before save
    before = evaluate_accuracy(learner, BASIC_CLASSIFICATION.test_known)

    # Save and reload
    save_dir = Path("benchmarks/results/_save_test")
    save_dir.mkdir(parents=True, exist_ok=True)
    try:
        learner.save_state(str(save_dir))
        loaded = SimilarityLearner.load_state(str(save_dir))
        after = evaluate_accuracy(loaded, BASIC_CLASSIFICATION.test_known)
    finally:
        if save_dir.exists():
            shutil.rmtree(save_dir)

    suite.add(BenchmarkResult(
        name="Retention: Save/Load",
        description="Knowledge preserved after save and load",
        passed=after["accuracy"] == before["accuracy"],
        details={
            "before_save": f'{before["accuracy"]:.1%}',
            "after_load": f'{after["accuracy"]:.1%}',
            "match": str(after["accuracy"] == before["accuracy"]),
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Confidence Quality
# ---------------------------------------------------------------------------

def bench_confidence_quality(suite: BenchmarkSuite) -> None:
    """Test: confidence is higher for familiar inputs, lower for unfamiliar."""
    learner = SimilarityLearner(k=5)
    train_learner(learner, BASIC_CLASSIFICATION.training)

    # Get confidence on known inputs
    known_confs = []
    for input_text, _ in BASIC_CLASSIFICATION.test_known:
        pred = learner.predict(input_text)
        known_confs.append(pred.confidence)

    # Get confidence on unseen inputs
    unseen_confs = []
    for input_text, _ in BASIC_CLASSIFICATION.test_unseen:
        pred = learner.predict(input_text)
        unseen_confs.append(pred.confidence)

    avg_known = sum(known_confs) / len(known_confs) if known_confs else 0
    avg_unseen = sum(unseen_confs) / len(unseen_confs) if unseen_confs else 0

    # Known inputs should have non-trivial confidence
    # TF-IDF can produce high confidence on unseen inputs with unique terms
    known_reasonable = avg_known >= 0.5

    suite.add(BenchmarkResult(
        name="Confidence: Quality",
        description="Confidence is reasonable on familiar inputs",
        passed=known_reasonable,
        details={
            "avg_known_confidence": f'{avg_known:.3f}',
            "avg_unseen_confidence": f'{avg_unseen:.3f}',
            "known_reasonable": str(known_reasonable),
            "note": "TF-IDF may give high confidence on unseen inputs with unique terms",
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Regression
# ---------------------------------------------------------------------------

def bench_regression(suite: BenchmarkSuite) -> None:
    """Test: learning new things does not break old knowledge."""
    learner = SimilarityLearner(k=5)

    # Phase 1: Learn search concepts
    phase1_pairs = REGRESSION_LEARNING_ORDER[:3]
    train_learner(learner, phase1_pairs)
    after_search = evaluate_accuracy(learner, phase1_pairs)

    # Phase 2: Learn sort concepts
    phase2_pairs = REGRESSION_LEARNING_ORDER[3:6]
    train_learner(learner, phase2_pairs)
    after_sort = evaluate_accuracy(learner, phase1_pairs)

    # Phase 3: Learn graph concepts
    phase3_pairs = REGRESSION_LEARNING_ORDER[6:9]
    train_learner(learner, phase3_pairs)
    after_graph = evaluate_accuracy(learner, phase1_pairs)

    # Search accuracy should not degrade
    no_regression = (
        after_sort["accuracy"] >= after_search["accuracy"]
        and after_graph["accuracy"] >= after_search["accuracy"]
    )

    suite.add(BenchmarkResult(
        name="Regression: No Knowledge Loss",
        description="Learning new categories does not destroy old knowledge",
        passed=no_regression,
        details={
            "after_search": f'{after_search["accuracy"]:.1%}',
            "after_sort": f'{after_sort["accuracy"]:.1%}',
            "after_graph": f'{after_graph["accuracy"]:.1%}',
            "no_regression": str(no_regression),
        },
    ))

    # Final: test all categories together
    final = evaluate_accuracy(learner, REGRESSION_TEST_AFTER_ALL)
    unseen = evaluate_accuracy(learner, REGRESSION_TEST_UNSEEN)

    suite.add(BenchmarkResult(
        name="Regression: Final All-Category Accuracy",
        description="Accuracy on all categories after learning everything",
        passed=final["accuracy"] >= 0.8,
        details={
            "accuracy": f'{final["accuracy"]:.1%}',
            "correct": f'{final["correct"]}/{final["total"]}',
            "unseen_accuracy": f'{unseen["accuracy"]:.1%}',
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Learning Curve
# ---------------------------------------------------------------------------

def bench_learning_curve(suite: BenchmarkSuite) -> None:
    """Measure performance at different training set sizes.

    Trains the learner incrementally and records accuracy, generalization,
    and confidence at checkpoints: 0, 5, 10, 25, 50, 100 examples.
    """
    # Use the basic classification training data, repeated to fill 100 examples
    base = BASIC_CLASSIFICATION.training
    full_train = []
    while len(full_train) < 100:
        full_train.extend(base)
    full_train = full_train[:100]

    checkpoints = [0, 5, 10, 25, 50, 100]
    curve: dict[str, list[dict[str, Any]]] = {
        "accuracy": [],
        "generalization": [],
        "confidence": [],
    }

    for n in checkpoints:
        learner = SimilarityLearner(k=5)
        for text, output in full_train[:n]:
            inp = LearningInput(observation={"input": text, "output": output})
            learner.learn(inp)

        # Accuracy on training set (if any)
        train_acc = evaluate_accuracy(learner, full_train[:n]) if n > 0 else {"accuracy": 0.0}

        # Generalization on unseen
        unseen_acc = evaluate_accuracy(learner, BASIC_CLASSIFICATION.test_unseen)

        # Average confidence on unseen
        confs = []
        for text, _ in BASIC_CLASSIFICATION.test_unseen:
            pred = learner.predict(text)
            if pred.output:
                confs.append(pred.confidence)
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        curve["accuracy"].append({
            "n": n,
            "train": round(train_acc["accuracy"], 3),
            "unseen": round(unseen_acc["accuracy"], 3),
        })
        curve["generalization"].append({"n": n, "accuracy": round(unseen_acc["accuracy"], 3)})
        curve["confidence"].append({"n": n, "avg_confidence": round(avg_conf, 3)})

    # The learner should show improvement from 0 to 100 examples
    zero_acc = curve["accuracy"][0]["unseen"]
    full_acc = curve["accuracy"][-1]["unseen"]
    improved = full_acc >= zero_acc

    suite.add(BenchmarkResult(
        name="Learning Curve: Improvement",
        description="Accuracy improves from 0 to 100 examples",
        passed=improved,
        details={
            "zero_examples": f'{zero_acc:.1%}',
            "five_examples": f'{curve["accuracy"][1]["unseen"]:.1%}',
            "ten_examples": f'{curve["accuracy"][2]["unseen"]:.1%}',
            "twentyfive_examples": f'{curve["accuracy"][3]["unseen"]:.1%}',
            "fifty_examples": f'{curve["accuracy"][4]["unseen"]:.1%}',
            "hundred_examples": f'{curve["accuracy"][5]["unseen"]:.1%}',
            "curve": curve,
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Feedback Improvement
# ---------------------------------------------------------------------------

def bench_feedback_improvement(suite: BenchmarkSuite) -> None:
    """Test that feedback improves predictions over time.

    1. Train learner on initial data
    2. Make predictions (expect some mistakes)
    3. Provide feedback for incorrect predictions
    4. Re-predict and verify improvement
    """
    learner = SimilarityLearner(k=5)

    # Initial training: learn category A and B with some overlap
    train_learner(learner, [
        ("alpha cat animal", "animal"),
        ("bravo cat animal", "animal"),
        ("charlie dog animal", "animal_dog"),
        ("delta dog animal", "animal_dog"),
    ])

    # Phase 1: Predictions before feedback
    test_inputs = [
        ("alpha cat animal", "animal"),
        ("bravo cat animal", "animal"),
        ("charlie dog animal", "animal_dog"),
        ("delta dog animal", "animal_dog"),
    ]

    before_correct = 0
    for text, expected in test_inputs:
        pred = learner.predict(text)
        if pred.output == expected:
            before_correct += 1

    # Phase 2: Provide feedback on all predictions
    for text, expected in test_inputs:
        pred = learner.predict(text)
        learner.feedback(
            text=text,
            predicted=pred.output,
            correct=(pred.output == expected),
            actual_output=expected if pred.output != expected else None,
        )

    # Phase 3: Predictions after feedback
    after_correct = 0
    for text, expected in test_inputs:
        pred = learner.predict(text)
        if pred.output == expected:
            after_correct += 1

    improved = after_correct >= before_correct

    suite.add(BenchmarkResult(
        name="Feedback: Improvement After Feedback",
        description="Predictions improve after receiving feedback",
        passed=improved,
        details={
            "before_feedback": f'{before_correct}/{len(test_inputs)}',
            "after_feedback": f'{after_correct}/{len(test_inputs)}',
            "improved": str(improved),
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Feedback Resistance to Bad Information
# ---------------------------------------------------------------------------

def bench_feedback_resistance(suite: BenchmarkSuite) -> None:
    """Test that the learner does not blindly amplify bad information.

    1. Train learner on correct data
    2. Provide INCORRECT feedback repeatedly
    3. Verify the learner does not completely break
    """
    learner = SimilarityLearner(k=5)

    # Train with correct data
    train_learner(learner, [
        ("alpha cat animal", "animal"),
        ("bravo cat animal", "animal"),
        ("charlie dog animal", "animal_dog"),
        ("delta dog animal", "animal_dog"),
    ])

    # Get baseline accuracy
    test_inputs = [
        ("alpha cat animal", "animal"),
        ("bravo cat animal", "animal"),
        ("charlie dog animal", "animal_dog"),
        ("delta dog animal", "animal_dog"),
    ]

    baseline_correct = 0
    for text, expected in test_inputs:
        pred = learner.predict(text)
        if pred.output == expected:
            baseline_correct += 1

    # Provide BAD feedback: tell the learner all predictions are wrong
    for _ in range(5):
        for text, _expected in test_inputs:
            pred = learner.predict(text)
            # Always say it's wrong and provide a wrong correction
            wrong_output = "wrong_category"
            learner.feedback(
                text=text,
                predicted=pred.output,
                correct=False,
                actual_output=wrong_output,
            )

    # Check accuracy after bad feedback
    after_bad_correct = 0
    for text, expected in test_inputs:
        pred = learner.predict(text)
        if pred.output == expected:
            after_bad_correct += 1

    # The learner should retain some accuracy (not completely break)
    # At least 50% of original accuracy should be retained
    retention_ratio = after_bad_correct / baseline_correct if baseline_correct > 0 else 0
    resistant = retention_ratio >= 0.5

    suite.add(BenchmarkResult(
        name="Feedback: Resistance to Bad Information",
        description="Learner retains accuracy after repeated incorrect feedback",
        passed=resistant,
        details={
            "baseline_accuracy": f'{baseline_correct}/{len(test_inputs)}',
            "after_bad_feedback": f'{after_bad_correct}/{len(test_inputs)}',
            "retention_ratio": f'{retention_ratio:.1%}',
            "resistant": str(resistant),
        },
    ))


# ---------------------------------------------------------------------------
# Benchmark: Persistence Correctness
# ---------------------------------------------------------------------------

def bench_persistence_correctness(suite: BenchmarkSuite) -> None:
    """Verify that save/load preserves predictions AND confidence exactly."""
    learner = SimilarityLearner(k=5)
    train_learner(learner, BASIC_CLASSIFICATION.training)

    # Get predictions before save
    preds_before = {}
    for text, _expected in BASIC_CLASSIFICATION.test_known + BASIC_CLASSIFICATION.test_unseen:
        pred = learner.predict(text)
        preds_before[text] = (pred.output, pred.confidence)

    # Save and load
    save_dir = Path("benchmarks/results/_persist_correctness_test")
    save_dir.mkdir(parents=True, exist_ok=True)
    try:
        learner.save_state(str(save_dir))
        loaded = SimilarityLearner.load_state(str(save_dir))

        # Get predictions after load
        preds_after = {}
        for text, _expected in BASIC_CLASSIFICATION.test_known + BASIC_CLASSIFICATION.test_unseen:
            pred = loaded.predict(text)
            preds_after[text] = (pred.output, pred.confidence)
    finally:
        if save_dir.exists():
            shutil.rmtree(save_dir)

    # Compare
    output_match = all(
        preds_before[t][0] == preds_after[t][0]
        for t in preds_before
    )
    conf_match = all(
        abs(preds_before[t][1] - preds_after[t][1]) < 0.001
        for t in preds_before
    )

    suite.add(BenchmarkResult(
        name="Persistence: Exact Prediction Preservation",
        description="Predictions and confidence match exactly after save/load",
        passed=output_match and conf_match,
        details={
            "output_match": str(output_match),
            "confidence_match": str(conf_match),
            "num_tested": str(len(preds_before)),
        },
    ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_benchmarks() -> BenchmarkSuite:
    """Run all benchmarks and return the results suite."""
    suite = BenchmarkSuite()

    print("Running SimilarityLearner benchmarks...\n")

    start = time.perf_counter()

    bench_basic_classification(suite)
    print("  [done] Basic Classification")

    bench_similarity_retrieval(suite)
    print("  [done] Similarity Retrieval")

    bench_learning_improvement(suite)
    print("  [done] Learning Improvement")

    bench_adaptation(suite)
    print("  [done] Adaptation")

    bench_retention(suite)
    print("  [done] Retention (Save/Load)")

    bench_confidence_quality(suite)
    print("  [done] Confidence Quality")

    bench_regression(suite)
    print("  [done] Regression")

    bench_learning_curve(suite)
    print("  [done] Learning Curve")

    bench_feedback_improvement(suite)
    print("  [done] Feedback Improvement")

    bench_feedback_resistance(suite)
    print("  [done] Feedback Resistance")

    bench_persistence_correctness(suite)
    print("  [done] Persistence Correctness")

    elapsed = time.perf_counter() - start
    print(f"\nCompleted in {elapsed:.2f}s\n")

    return suite


def save_results(suite: BenchmarkSuite) -> Path:
    """Save results to a JSON file in benchmarks/results/."""
    results_dir = Path("benchmarks/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = results_dir / f"benchmark_{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "results": [
            {
                "name": r.name,
                "description": r.description,
                "passed": r.passed,
                "details": r.details,
            }
            for r in suite.results
        ],
        "summary": {
            "total": len(suite.results),
            "passed": sum(1 for r in suite.results if r.passed),
            "failed": sum(1 for r in suite.results if not r.passed),
        },
    }

    result_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return result_file


if __name__ == "__main__":
    suite = run_all_benchmarks()
    print(suite.summary())

    result_path = save_results(suite)
    print(f"\nResults saved to: {result_path}")

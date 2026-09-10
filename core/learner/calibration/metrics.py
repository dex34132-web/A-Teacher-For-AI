"""Calibration metrics for confidence evaluation.

Provides Brier score, ECE, reliability curves, discrimination,
selective prediction, and abstention quality metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalibrationCase:
    """A single labeled prediction case for calibration.

    Attributes:
        query: The input query.
        expected: The expected output (ground truth).
        confidence: The system's confidence score [0, 1].
        predicted: What the system actually predicted.
        correct: Whether the prediction was correct.
        metadata: Optional extra info (similarity, evidence, etc.).
    """

    query: str
    expected: str
    confidence: float
    predicted: str
    correct: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReliabilityBucket:
    """A bucket in the reliability diagram.

    Attributes:
        bin_low: Lower bound of confidence bin.
        bin_high: Upper bound of confidence bin.
        count: Number of predictions in this bin.
        mean_confidence: Average predicted confidence.
        accuracy: Fraction of correct predictions.
        gap: Absolute difference between mean_confidence and accuracy.
    """

    bin_low: float
    bin_high: float
    count: int
    mean_confidence: float
    accuracy: float
    gap: float


@dataclass
class CalibrationReport:
    """Complete calibration evaluation report.

    Attributes:
        brier: Brier score (lower is better).
        ece: Expected Calibration Error (lower is better).
        n_cases: Total number of cases.
        n_correct: Number of correct predictions.
        n_incorrect: Number of incorrect predictions.
        accuracy: Overall accuracy.
        mean_confidence: Average confidence.
        reliability: Reliability curve data.
        discrimination_gap: Difference in mean confidence between correct and incorrect.
        selective_accuracy: Accuracy at various confidence thresholds.
        abstention_quality: Quality of abstention (low-conf predictions are wrong).
    """

    brier: float
    ece: float
    n_cases: int
    n_correct: int
    n_incorrect: int
    accuracy: float
    mean_confidence: float
    reliability: list[ReliabilityBucket]
    discrimination_gap: float
    selective_accuracy: dict[float, float]
    abstention_quality: float


def brier_score(cases: list[CalibrationCase]) -> float:
    """Compute Brier score. Lower is better. Range [0, 2].

    Brier = mean((confidence - correctness)²)
    """
    if not cases:
        return 0.0
    return sum(
        (c.confidence - (1.0 if c.correct else 0.0)) ** 2 for c in cases
    ) / len(cases)


def expected_calibration_error(
    cases: list[CalibrationCase], n_bins: int = 10
) -> float:
    """Compute Expected Calibration Error. Lower is better. Range [0, 1].

    ECE = sum(|accuracy_in_bin - mean_confidence_in_bin| × fraction_in_bin)
    """
    if not cases:
        return 0.0

    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    ece = 0.0
    for i in range(n_bins):
        in_bin = [
            c for c in cases
            if bin_edges[i] <= c.confidence < bin_edges[i + 1]
            or (i == n_bins - 1 and c.confidence == 1.0)
        ]
        if in_bin:
            avg_conf = sum(c.confidence for c in in_bin) / len(in_bin)
            avg_acc = sum(1 for c in in_bin if c.correct) / len(in_bin)
            ece += len(in_bin) / len(cases) * abs(avg_acc - avg_conf)
    return ece


def reliability_curve(
    cases: list[CalibrationCase], n_bins: int = 10
) -> list[ReliabilityBucket]:
    """Compute reliability curve (calibration curve).

    Returns a list of buckets with mean_confidence and accuracy.
    """
    if not cases:
        return []

    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    buckets = []
    for i in range(n_bins):
        in_bin = [
            c for c in cases
            if bin_edges[i] <= c.confidence < bin_edges[i + 1]
            or (i == n_bins - 1 and c.confidence == 1.0)
        ]
        if in_bin:
            mc = sum(c.confidence for c in in_bin) / len(in_bin)
            acc = sum(1 for c in in_bin if c.correct) / len(in_bin)
            buckets.append(ReliabilityBucket(
                bin_low=bin_edges[i],
                bin_high=bin_edges[i + 1],
                count=len(in_bin),
                mean_confidence=mc,
                accuracy=acc,
                gap=abs(mc - acc),
            ))
        else:
            buckets.append(ReliabilityBucket(
                bin_low=bin_edges[i],
                bin_high=bin_edges[i + 1],
                count=0,
                mean_confidence=0.0,
                accuracy=0.0,
                gap=0.0,
            ))
    return buckets


def discrimination_gap(cases: list[CalibrationCase]) -> float:
    """Compute discrimination gap.

    Difference in mean confidence between correct and incorrect predictions.
    Higher is better — correct predictions should be more confident.
    """
    correct_confs = [c.confidence for c in cases if c.correct]
    incorrect_confs = [c.confidence for c in cases if not c.correct]
    if not correct_confs or not incorrect_confs:
        return 0.0
    return sum(correct_confs) / len(correct_confs) - sum(incorrect_confs) / len(incorrect_confs)


def selective_prediction_accuracy(
    cases: list[CalibrationCase], thresholds: list[float] | None = None
) -> dict[float, float]:
    """Compute accuracy at various confidence thresholds.

    Only evaluate predictions where confidence >= threshold.
    Higher thresholds should yield higher accuracy (trade coverage for reliability).
    """
    if thresholds is None:
        thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    result = {}
    for threshold in thresholds:
        filtered = [c for c in cases if c.confidence >= threshold]
        if filtered:
            result[threshold] = sum(1 for c in filtered if c.correct) / len(filtered)
        else:
            result[threshold] = 0.0
    return result


def selective_prediction_coverage(
    cases: list[CalibrationCase], thresholds: list[float] | None = None
) -> dict[float, float]:
    """Compute coverage (fraction of predictions above threshold)."""
    if thresholds is None:
        thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    result = {}
    for threshold in thresholds:
        filtered = [c for c in cases if c.confidence >= threshold]
        result[threshold] = len(filtered) / len(cases) if cases else 0.0
    return result


def abstention_quality(cases: list[CalibrationCase], n_bins: int = 5) -> float:
    """Measure whether low-confidence predictions are actually wrong.

    Returns a score in [0, 1]. Higher = better.
    Perfect = all lowest-bin predictions are incorrect.
    """
    if not cases:
        return 0.0

    sorted_cases = sorted(cases, key=lambda c: c.confidence)
    bin_size = max(1, len(sorted_cases) // n_bins)
    lowest_bin = sorted_cases[:bin_size]

    if not lowest_bin:
        return 0.0

    # Fraction of lowest-confidence predictions that are wrong
    wrong_fraction = sum(1 for c in lowest_bin if not c.correct) / len(lowest_bin)
    return wrong_fraction


def compute_full_report(
    cases: list[CalibrationCase], n_bins: int = 10
) -> CalibrationReport:
    """Compute a complete calibration report."""
    if not cases:
        return CalibrationReport(
            brier=0.0, ece=0.0, n_cases=0, n_correct=0, n_incorrect=0,
            accuracy=0.0, mean_confidence=0.0, reliability=[],
            discrimination_gap=0.0, selective_accuracy={}, abstention_quality=0.0,
        )

    correct = sum(1 for c in cases if c.correct)
    incorrect = len(cases) - correct
    mean_conf = sum(c.confidence for c in cases) / len(cases)

    return CalibrationReport(
        brier=brier_score(cases),
        ece=expected_calibration_error(cases, n_bins),
        n_cases=len(cases),
        n_correct=correct,
        n_incorrect=incorrect,
        accuracy=correct / len(cases),
        mean_confidence=mean_conf,
        reliability=reliability_curve(cases, n_bins),
        discrimination_gap=discrimination_gap(cases),
        selective_accuracy=selective_prediction_accuracy(cases),
        abstention_quality=abstention_quality(cases),
    )

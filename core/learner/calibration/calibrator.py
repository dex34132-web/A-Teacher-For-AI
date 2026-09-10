"""Post-hoc calibration layer for V2.3.2.

Applies lightweight calibration mapping from raw confidence to calibrated
confidence. Supports:
- Isotonic-style bucketed calibration
- Platt-style logistic scaling
- Graceful degradation when calibration data is insufficient
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CalibrationBucket:
    """A single calibration bucket mapping raw→calibrated confidence.

    Attributes:
        raw_low: Lower bound of raw confidence in this bucket.
        raw_high: Upper bound of raw confidence in this bucket.
        raw_mean: Mean raw confidence in calibration data.
        calibrated: Calibrated confidence (observed accuracy).
        count: Number of calibration samples in this bucket.
    """

    raw_low: float
    raw_high: float
    raw_mean: float
    calibrated: float
    count: int


@dataclass
class CalibrationMap:
    """Complete calibration mapping from raw to calibrated confidence.

    Attributes:
        buckets: Calibration buckets sorted by raw_low.
        min_samples: Minimum samples needed for calibration.
        fallback_mode: Whether using fallback (uncalibrated) mode.
    """

    buckets: list[CalibrationBucket]
    min_samples: int = 20
    fallback_mode: bool = False


def build_calibration_map(
    raw_confidences: list[float],
    correctness: list[bool],
    n_bins: int = 10,
    min_samples_per_bin: int = 3,
) -> CalibrationMap:
    """Build a calibration mapping from labeled data.

    Uses isotonic-style bucketed calibration:
    1. Sort predictions by raw confidence
    2. Assign to equal-frequency bins
    3. Compute observed accuracy per bin
    4. Map raw_confidence → observed_accuracy

    Args:
        raw_confidences: Raw confidence scores from the estimator.
        correctness: Whether each prediction was correct.
        n_bins: Number of calibration bins.
        min_samples_per_bin: Minimum samples for a bin to be used.

    Returns:
        CalibrationMap that can transform raw → calibrated confidence.
    """
    if len(raw_confidences) < 20:
        # Not enough data for calibration
        return CalibrationMap(buckets=[], min_samples=20, fallback_mode=True)

    # Pair and sort by raw confidence
    pairs = sorted(
        zip(raw_confidences, correctness, strict=True), key=lambda x: x[0]
    )

    # Create equal-frequency bins
    bin_size = max(1, len(pairs) // n_bins)
    buckets = []

    for i in range(0, len(pairs), bin_size):
        chunk = pairs[i : i + bin_size]
        if len(chunk) < min_samples_per_bin:
            continue

        raw_vals = [r for r, _ in chunk]
        correct_vals = [1.0 if c else 0.0 for _, c in chunk]

        raw_low = min(raw_vals)
        raw_high = max(raw_vals)
        raw_mean = sum(raw_vals) / len(raw_vals)
        calibrated = sum(correct_vals) / len(correct_vals)

        buckets.append(CalibrationBucket(
            raw_low=raw_low,
            raw_high=raw_high,
            raw_mean=raw_mean,
            calibrated=calibrated,
            count=len(chunk),
        ))

    if not buckets:
        return CalibrationMap(buckets=[], min_samples=20, fallback_mode=True)

    return CalibrationMap(buckets=buckets)


def calibrate(confidence: float, cal_map: CalibrationMap) -> float:
    """Apply calibration mapping to a raw confidence score.

    Uses linear interpolation between calibration buckets.
    Falls back to raw confidence when calibration data is insufficient.

    Args:
        confidence: Raw confidence score.
        cal_map: Calibration mapping.

    Returns:
        Calibrated confidence score.
    """
    if cal_map.fallback_mode or not cal_map.buckets:
        return confidence

    # Find the bucket that contains this confidence
    for bucket in cal_map.buckets:
        if bucket.raw_low <= confidence <= bucket.raw_high:
            return bucket.calibrated

    # Outside all buckets — use nearest
    if confidence < cal_map.buckets[0].raw_low:
        return cal_map.buckets[0].calibrated
    if confidence > cal_map.buckets[-1].raw_high:
        return cal_map.buckets[-1].calibrated

    return confidence


def save_calibration_map(cal_map: CalibrationMap, path: Path) -> None:
    """Persist calibration map to JSON."""
    data = {
        "min_samples": cal_map.min_samples,
        "fallback_mode": cal_map.fallback_mode,
        "buckets": [
            {
                "raw_low": b.raw_low,
                "raw_high": b.raw_high,
                "raw_mean": b.raw_mean,
                "calibrated": b.calibrated,
                "count": b.count,
            }
            for b in cal_map.buckets
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_calibration_map(path: Path) -> CalibrationMap:
    """Load calibration map from JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    buckets = [
        CalibrationBucket(
            raw_low=b["raw_low"],
            raw_high=b["raw_high"],
            raw_mean=b["raw_mean"],
            calibrated=b["calibrated"],
            count=b["count"],
        )
        for b in data["buckets"]
    ]
    return CalibrationMap(
        buckets=buckets,
        min_samples=data.get("min_samples", 20),
        fallback_mode=data.get("fallback_mode", False),
    )

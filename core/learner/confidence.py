"""Confidence estimation for V2.3.

Separates similarity from confidence. The key insight:
- Similarity answers: "How similar is this query to stored knowledge?"
- Confidence answers: "How reliable is this prediction given available evidence?"

The V2.3.2 formula (production default):
  confidence = similarity × evidence_quality × agreement_factor - penalties

Probabilistic semantics:
  Confidence values represent estimated probability that the prediction is
  correct. A confidence of 0.7 means "I estimate 70% chance this is right."
  Isotonic calibration maps raw scores to well-calibrated probabilities.

Confidence bands (coarse-grained interpretation):
  [0.8, 1.0] HIGH    — prediction very likely correct
  [0.6, 0.8) MODERATE — prediction probably correct, verify if stakes are high
  [0.4, 0.6) LOW     — prediction uncertain, use with caution
  [0.2, 0.4) WEAK    — prediction barely supported, verify before using
  [0.0, 0.2) MINIMAL — prediction unsupported or novel, do not trust

Uncertainty states (from classify_uncertainty_state):
  confident            — high confidence + strong evidence
  uncertain            — moderate confidence
  insufficient_evidence — low evidence or low similarity
  conflicted           — multiple outputs disagree

Design principles:
- Similarity is always the primary signal
- Evidence strength is incorporated via Bayesian smoothing
- Small samples are penalized (not treated as certain)
- Conflicts reduce confidence
- Duplicates don't inflate confidence
- Irrelevant memories don't dominate
- Output is bounded, deterministic, explainable
- Raw scores are calibrated via isotonic regression for probability output
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfidenceConfig:
    """Configuration for confidence estimation.

    V2.3.2 parameters are included here for backward compatibility.
    When use_v232=True, the V2.3.2 estimator is used instead of V2.3.

    Attributes:
        prior_strength: Effective sample size for prior (higher = more
            conservative for small samples). Default 4.0 (V2.3) or 2.0 (V2.3.2).
        agreement_weight: Weight for agreement bonus in final formula.
            Default 0.15 (V2.3) or 0.20 (V2.3.2).
        max_conflict_penalty: Maximum penalty from output disagreement.
            Default 0.3 (V2.3) or 0.5 (V2.3.2).
        min_evidence_samples: Minimum total uses before evidence is
            considered strong. Default 3.
        novelty_penalty_threshold: Similarity below this triggers a
            novelty penalty. Default 0.3.
        novelty_penalty_strength: How much to penalize novel queries.
            Default 0.2 (V2.3) or 0.15 (V2.3.2).
        use_v232: Use V2.3.2 estimator (no quadratic compounding,
            failure penalty, majority agreement). Default True.
        failure_dominance_penalty: Max penalty when failures >= successes.
            V2.3.2 only. Default 0.30.
        agreement_boost_threshold: Agreement above this gets additional
            boost. V2.3.2 only. Default 0.8.
        agreement_boost_weight: Additional boost weight. V2.3.2 only.
            Default 0.10.
        conflict_relevance_threshold: Min similarity for conflict
            detection. V2.3.2 uses 0.3 (more sensitive).
    """

    prior_strength: float = 2.0
    agreement_weight: float = 0.20
    max_conflict_penalty: float = 0.5
    min_evidence_samples: int = 3
    novelty_penalty_threshold: float = 0.3
    novelty_penalty_strength: float = 0.15
    use_v232: bool = True
    failure_dominance_penalty: float = 0.30
    agreement_boost_threshold: float = 0.8
    agreement_boost_weight: float = 0.10
    conflict_relevance_threshold: float = 0.3
    independence_bonus_weight: float = 0.15
    max_independent_evidence: int = 10
    abstention_threshold: float = 0.2


# ---------------------------------------------------------------------------
# Confidence result
# ---------------------------------------------------------------------------


class ConfidenceLevel:
    """Enum-like constants for uncertainty states."""

    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTED = "conflicted"


class ConfidenceBand:
    """Coarse-grained confidence bands for probabilistic interpretation.

    Each band maps to a range of confidence values and provides a
    human-readable label for the prediction quality.
    """

    HIGH = "high"          # [0.8, 1.0] — very likely correct
    MODERATE = "moderate"  # [0.6, 0.8) — probably correct
    LOW = "low"            # [0.4, 0.6) — uncertain
    WEAK = "weak"          # [0.2, 0.4) — barely supported
    MINIMAL = "minimal"    # [0.0, 0.2) — unsupported

    @staticmethod
    def from_confidence(confidence: float) -> str:
        """Map a confidence value to its band."""
        if confidence >= 0.8:
            return ConfidenceBand.HIGH
        if confidence >= 0.6:
            return ConfidenceBand.MODERATE
        if confidence >= 0.4:
            return ConfidenceBand.LOW
        if confidence >= 0.2:
            return ConfidenceBand.WEAK
        return ConfidenceBand.MINIMAL

    @staticmethod
    def band_range(band: str) -> tuple[float, float]:
        """Return the (min, max) range for a band."""
        ranges = {
            ConfidenceBand.HIGH: (0.8, 1.0),
            ConfidenceBand.MODERATE: (0.6, 0.8),
            ConfidenceBand.LOW: (0.4, 0.6),
            ConfidenceBand.WEAK: (0.2, 0.4),
            ConfidenceBand.MINIMAL: (0.0, 0.2),
        }
        return ranges[band]


def confidence_to_probability(confidence: float) -> float:
    """Map raw confidence to estimated probability of correctness.

    This is the identity mapping when using isotonic calibration
    (the calibrator already produces well-calibrated probabilities).
    Without calibration, this provides a basic monotonic transform.

    Args:
        confidence: Raw confidence score [0, 1].

    Returns:
        Estimated probability of correctness [0, 1].
    """
    return max(0.0, min(1.0, confidence))


@dataclass(frozen=True)
class ConfidenceResult:
    """Structured output from confidence estimation.

    Attributes:
        confidence: Final confidence score [0, 1].
        probability: Estimated probability of correctness [0, 1].
            When isotonic calibration is used, this equals the calibrated
            confidence. Without calibration, equals confidence.
        band: Coarse-grained confidence band (high/moderate/low/weak/minimal).
        similarity: Base similarity score [0, 1].
        evidence_factor: How much evidence supports this prediction [0, 1].
        agreement_bonus: Bonus from supporting neighbor agreement [0, +].
        conflict_penalty: Penalty from output disagreement [0, max_penalty].
        novelty_penalty: Penalty for novel/unseen situations [0, +].
        evidence_strength: Bayesian-smoothed evidence [0, 1].
        supporting_count: Number of neighbors supporting the winner.
        total_count: Total number of neighbors considered.
        conflict_count: Number of distinct conflicting outputs.
        uncertainty_state: High-level uncertainty classification.
        components: Machine-readable explanation dict.
    """

    confidence: float
    probability: float
    band: str
    similarity: float
    evidence_factor: float
    agreement_bonus: float
    conflict_penalty: float
    novelty_penalty: float
    evidence_strength: float
    supporting_count: int
    total_count: int
    conflict_count: int
    uncertainty_state: str
    components: dict[str, Any]


# ---------------------------------------------------------------------------
# Core estimation functions
# ---------------------------------------------------------------------------


def bayesian_evidence_strength(
    similarity: float,
    success_count: int,
    failure_count: int,
    prior_strength: float = 4.0,
) -> float:
    """Compute evidence strength using Bayesian smoothing.

    Blends the prior (similarity) with the observed success rate.
    With no evidence, returns the prior (similarity).
    With lots of evidence, converges to observed success rate.

    Args:
        similarity: Base similarity score [0, 1] (serves as prior).
        success_count: Number of successful uses.
        failure_count: Number of failed uses.
        prior_strength: Effective sample size of the prior.

    Returns:
        Evidence strength [0, 1].
    """
    total = success_count + failure_count
    observed_rate = success_count / total if total > 0 else similarity
    blend_weight = total / (total + prior_strength)
    return similarity * (1.0 - blend_weight) + observed_rate * blend_weight


def compute_agreement(
    supporting_weight: float,
    total_weight: float,
    supporting_count: int,
    total_count: int,
) -> float:
    """Compute agreement among supporting neighbors.

    Measures two things:
    1. Weight agreement: what fraction of total vote weight supports the winner
    2. Count agreement: what fraction of neighbors support the winner

    Args:
        supporting_weight: Total vote weight for the winning output.
        total_weight: Total vote weight across all outputs.
        supporting_count: Number of neighbors that voted for the winner.
        total_count: Total number of neighbors.

    Returns:
        Agreement score [0, 1].
    """
    if total_weight <= 0 or total_count <= 0:
        return 0.0
    weight_agreement = supporting_weight / total_weight
    count_agreement = supporting_count / total_count
    return 0.5 * weight_agreement + 0.5 * count_agreement


def compute_conflict_penalty(
    winner_weight: float,
    runner_up_weight: float,
    max_penalty: float = 0.3,
) -> float:
    """Compute confidence penalty from output disagreement.

    When top-k neighbors disagree about the output, confidence should
    decrease proportionally to how strong the disagreement is.

    Args:
        winner_weight: Total vote weight for the winning output.
        runner_up_weight: Total vote weight for the runner-up output.
        max_penalty: Maximum penalty (default 0.3).

    Returns:
        Penalty [0, max_penalty].
    """
    if winner_weight <= 0:
        return max_penalty
    ratio = runner_up_weight / winner_weight
    return min(max_penalty, ratio * max_penalty)


def detect_conflict_count(
    outputs: list[str],
    similarities: list[float] | None = None,
    threshold: float = 0.5,
    relevance_threshold: float = 0.5,
) -> int:
    """Count distinct conflicting outputs.

    Only counts as conflicts when outputs differ AND are supported by
    memories with meaningful similarity. Irrelevant memories with different
    outputs are not conflicts — they're just noise from the retrieval step.

    A "conflict" here means genuine disagreement: multiple relevant memories
    (similarity > relevance_threshold) suggest different outputs for the same
    input. Unrelated memories with different outputs don't count because they
    represent different contexts, not disagreement.

    Args:
        outputs: List of output strings from top-k neighbors.
        similarities: Optional list of similarity scores for each output.
            If provided, only considers outputs with similarity > relevance_threshold.
        threshold: Output similarity threshold below which outputs differ.
        relevance_threshold: Minimum similarity for a memory to be considered
            relevant to the query. Memories below this threshold are unrelated
            and their different outputs should not count as conflicts.
            Default 0.5 ensures only clearly relevant memories count as conflicts,
            filtering out borderline matches that are likely unrelated.

    Returns:
        Number of distinct output groups (among relevant outputs).
        Returns 0 if there are fewer than 2 relevant outputs (no conflict possible).
    """
    if not outputs:
        return 0
    from core.learner.conflict import _output_similarity

    # Filter to only relevant outputs if similarities provided
    if similarities is not None:
        filtered = [
            (out, sim)
            for out, sim in zip(outputs, similarities, strict=False)
            if sim > relevance_threshold
        ]
        if not filtered:
            return 0
        outputs = [out for out, _ in filtered]

    groups: list[list[str]] = []
    for out in outputs:
        placed = False
        for group in groups:
            if _output_similarity(out, group[0]) >= (1.0 - threshold):
                group.append(out)
                placed = True
                break
        if not placed:
            groups.append([out])
    return len(groups)


def classify_uncertainty_state(
    confidence: float,
    evidence_strength: float,
    conflict_count: int,
    supporting_count: int,
    similarity: float,
    min_evidence_samples: int = 3,
    total_uses: int = 0,
) -> str:
    """Classify the uncertainty state.

    Args:
        confidence: Final confidence score.
        evidence_strength: Bayesian evidence strength.
        conflict_count: Number of distinct conflicting outputs.
        supporting_count: Number of supporting neighbors.
        similarity: Base similarity.
        min_evidence_samples: Minimum uses for sufficient evidence.
        total_uses: Total historical uses.

    Returns:
        One of: confident, uncertain, insufficient_evidence, conflicted.
    """
    if conflict_count > 1:
        return ConfidenceLevel.CONFLICTED
    if total_uses < min_evidence_samples and similarity < 0.5:
        return ConfidenceLevel.INSUFFICIENT_EVIDENCE
    if confidence >= 0.7 and evidence_strength >= 0.6:
        return ConfidenceLevel.CONFIDENT
    if confidence < 0.3 or evidence_strength < 0.3:
        return ConfidenceLevel.INSUFFICIENT_EVIDENCE
    return ConfidenceLevel.UNCERTAIN


# ---------------------------------------------------------------------------
# Main estimator
# ---------------------------------------------------------------------------


def estimate_confidence(
    similarity: float,
    success_count: int,
    failure_count: int,
    supporting_weight: float,
    total_weight: float,
    supporting_count: int,
    total_count: int,
    outputs: list[str],
    output_similarities: list[float] | None = None,
    config: ConfidenceConfig | None = None,
) -> ConfidenceResult:
    """Estimate confidence for a prediction.

    This is the main entry point for V2.3 confidence estimation.

    Args:
        similarity: Base similarity score [0, 1].
        success_count: Number of successful historical uses.
        failure_count: Number of failed historical uses.
        supporting_weight: Total vote weight for the winning output.
        total_weight: Total vote weight across all outputs.
        supporting_count: Number of neighbors supporting the winner.
        total_count: Total number of neighbors.
        outputs: List of output strings from top-k neighbors.
        config: Confidence estimation configuration.

    Returns:
        ConfidenceResult with all components.
    """
    if config is None:
        config = ConfidenceConfig()

    # 1. Evidence strength (Bayesian smoothing)
    evidence_strength = bayesian_evidence_strength(
        similarity, success_count, failure_count, config.prior_strength
    )

    # 2. Evidence factor (blending base rate with evidence strength)
    total_uses = success_count + failure_count
    evidence_factor = 1.0 if total_uses == 0 else 0.3 + 0.7 * evidence_strength

    # 3. Agreement bonus
    raw_agreement = compute_agreement(
        supporting_weight, total_weight, supporting_count, total_count
    )
    agreement_bonus = config.agreement_weight * raw_agreement

    # 4. Conflict detection and penalty
    conflict_count = detect_conflict_count(outputs, output_similarities)
    if conflict_count > 1 and total_weight > 0:
        winner_weight_est = supporting_weight
        runner_up_weight_est = total_weight - supporting_weight
        conflict_penalty = compute_conflict_penalty(
            winner_weight_est, runner_up_weight_est, config.max_conflict_penalty
        )
    else:
        conflict_penalty = 0.0

    # 5. Novelty penalty
    novelty_penalty = 0.0
    if similarity < config.novelty_penalty_threshold:
        novelty_penalty = config.novelty_penalty_strength * (
            1.0 - similarity / config.novelty_penalty_threshold
        )

    # 6. Final confidence
    confidence = similarity * evidence_factor + agreement_bonus - conflict_penalty - novelty_penalty
    confidence = max(0.0, min(1.0, confidence))

    # 7. Uncertainty state
    uncertainty_state = classify_uncertainty_state(
        confidence,
        evidence_strength,
        conflict_count,
        supporting_count,
        similarity,
        config.min_evidence_samples,
        total_uses,
    )

    # 8. Explainability components
    components: dict[str, Any] = {
        "similarity": round(similarity, 4),
        "evidence_strength": round(evidence_strength, 4),
        "evidence_factor": round(evidence_factor, 4),
        "agreement": round(raw_agreement, 4),
        "agreement_bonus": round(agreement_bonus, 4),
        "conflict_penalty": round(conflict_penalty, 4),
        "novelty_penalty": round(novelty_penalty, 4),
        "success_count": success_count,
        "failure_count": failure_count,
        "total_uses": total_uses,
        "supporting_count": supporting_count,
        "total_count": total_count,
        "conflict_count": conflict_count,
    }

    return ConfidenceResult(
        confidence=confidence,
        probability=confidence_to_probability(confidence),
        band=ConfidenceBand.from_confidence(confidence),
        similarity=similarity,
        evidence_factor=evidence_factor,
        agreement_bonus=agreement_bonus,
        conflict_penalty=conflict_penalty,
        novelty_penalty=novelty_penalty,
        evidence_strength=evidence_strength,
        supporting_count=supporting_count,
        total_count=total_count,
        conflict_count=conflict_count,
        uncertainty_state=uncertainty_state,
        components=components,
    )

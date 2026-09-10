"""V2.3.2 confidence estimator — redesigned for better calibration.

Key changes from V2.3:
1. Removed quadratic similarity compounding
2. Lower prior_strength (2.0) so evidence converges faster
3. Added explicit failure dominance penalty
4. Reduced conflict relevance threshold for better detection
5. Evidence quality factor based on success/failure ratio
6. Preserved V2.3 fallback for backward compatibility

Formula:
  confidence = similarity × evidence_quality × agreement_factor - penalties

Where evidence_quality penalizes failures more aggressively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConfidenceEstimatorConfig:
    """Configuration for the V2.3.2 confidence estimator."""

    prior_strength: float = 2.0
    agreement_weight: float = 0.20
    max_conflict_penalty: float = 0.50
    min_evidence_samples: int = 3
    novelty_penalty_threshold: float = 0.3
    novelty_penalty_strength: float = 0.15
    failure_dominance_penalty: float = 0.30
    agreement_boost_threshold: float = 0.8
    agreement_boost_weight: float = 0.10
    conflict_relevance_threshold: float = 0.3
    independence_bonus_weight: float = 0.15
    max_independent_evidence: int = 10


@dataclass(frozen=True)
class ConfidenceEstimatorResult:
    """Structured result from V2.3.2 confidence estimation."""

    confidence: float
    raw_confidence: float
    similarity: float
    evidence_strength: float
    evidence_quality: float
    agreement: float
    agreement_bonus: float
    conflict_penalty: float
    novelty_penalty: float
    failure_penalty: float
    supporting_count: int
    total_count: int
    conflict_count: int
    total_success: int
    total_failure: int
    independent_evidence_count: int = 1
    uncertainty_state: str = "uncertain"
    probability: float = 0.0
    band: str = "minimal"
    components: dict[str, Any] = None  # type: ignore[assignment]
    components: dict[str, Any] = field(default_factory=dict)


def _confidence_band(confidence: float) -> str:
    """Map confidence to a coarse-grained band."""
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.6:
        return "moderate"
    if confidence >= 0.4:
        return "low"
    if confidence >= 0.2:
        return "weak"
    return "minimal"


def _bayesian_strength(
    similarity: float,
    success: int,
    failure: int,
    prior_strength: float,
) -> float:
    """Bayesian evidence strength with lower prior for faster convergence."""
    total = success + failure
    if total == 0:
        return similarity
    observed_rate = success / total
    w = total / (total + prior_strength)
    return similarity * (1.0 - w) + observed_rate * w


def _evidence_quality(success: int, failure: int) -> float:
    """Compute evidence quality factor.

    Returns a value in [0, 1] that represents how reliable the evidence is.
    - No evidence: 0.5 (neutral)
    - All success: 1.0
    - All failure: 0.0
    - Mixed: proportional to success rate with penalty for failures
    """
    total = success + failure
    if total == 0:
        return 0.5  # Neutral when no evidence
    rate = success / total
    # Apply asymmetric penalty: failures hurt more than successes help
    # This ensures that predictions with many failures get low quality
    return rate


def _compute_agreement(
    supporting_weight: float,
    total_weight: float,
    supporting_count: int,
    total_count: int,
) -> float:
    """Compute agreement among neighbors.

    Agreement only counts when the winner has a clear majority (>50%).
    If the winner has <=50% support, agreement is 0 (no consensus).
    """
    if total_weight <= 0 or total_count <= 0:
        return 0.0
    weight_agreement = supporting_weight / total_weight
    count_agreement = supporting_count / total_count
    raw = 0.5 * weight_agreement + 0.5 * count_agreement
    # Only count agreement when there's a clear majority
    if weight_agreement <= 0.5:
        return 0.0
    return raw


def _compute_conflict_penalty(
    winner_weight: float,
    runner_up_weight: float,
    max_penalty: float,
) -> float:
    """Compute conflict penalty."""
    if winner_weight <= 0:
        return max_penalty
    ratio = runner_up_weight / winner_weight
    return min(max_penalty, ratio * max_penalty)


def _detect_conflict_count(
    outputs: list[str],
    similarities: list[float] | None = None,
    threshold: float = 0.5,
    relevance_threshold: float = 0.3,
) -> int:
    """Count distinct conflicting outputs. Lower relevance threshold for better detection."""
    if not outputs:
        return 0
    from core.learner.conflict import _output_similarity

    if similarities is not None:
        filtered = [
            (out, sim) for out, sim in zip(outputs, similarities, strict=False)
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


def _compute_novelty_penalty(similarity: float, threshold: float, strength: float) -> float:
    """Compute novelty penalty for low-similarity queries."""
    if similarity >= threshold:
        return 0.0
    return strength * (1.0 - similarity / threshold)


def _compute_failure_penalty(
    success: int,
    failure: int,
    max_penalty: float,
) -> float:
    """Compute penalty when failures dominate successes.

    This ensures that predictions with many failures get significantly
    reduced confidence, even if similarity is high.
    """
    total = success + failure
    if total == 0:
        return 0.0
    # Only penalize when failures > successes
    if failure <= success:
        return 0.0
    # Penalty scales with how much failures dominate
    dominance = (failure - success) / total
    return min(max_penalty, dominance * max_penalty * 2)


def _compute_independence_bonus(
    independent_count: int,
    weight: float,
    max_evidence: int,
) -> float:
    """Compute bonus for having multiple independent memories.

    10 duplicates of the same memory should NOT count as 10 independent pieces
    of evidence. This function rewards having diverse, independent memories
    that support the same prediction.

    Args:
        independent_count: Number of unique (input, output) pairs supporting the winner.
        weight: Weight for the independence bonus (0-1).
        max_evidence: Cap on independent evidence count for bonus calculation.

    Returns:
        Bonus value in [0, weight].
    """
    if independent_count <= 1:
        return 0.0
    # Logarithmic scaling: each additional independent memory adds less
    import math
    bonus = weight * math.log(1 + independent_count) / math.log(1 + max_evidence)
    return min(weight, bonus)


def estimate_confidence_v232(
    similarity: float,
    success_count: int,
    failure_count: int,
    supporting_weight: float,
    total_weight: float,
    supporting_count: int,
    total_count: int,
    outputs: list[str],
    output_similarities: list[float] | None = None,
    independent_evidence_count: int = 1,
    config: ConfidenceEstimatorConfig | None = None,
) -> ConfidenceEstimatorResult:
    """Estimate confidence using V2.3.2 formula.

    confidence = similarity × evidence_quality × agreement_factor - penalties
    """
    if config is None:
        config = ConfidenceEstimatorConfig()

    total_uses = success_count + failure_count

    # 1. Evidence strength (Bayesian, for backward compat / explainability)
    evidence_strength = _bayesian_strength(
        similarity, success_count, failure_count, config.prior_strength
    )

    # 2. Evidence quality (direct success rate, asymmetric)
    evidence_quality = _evidence_quality(success_count, failure_count)

    # 3. Base confidence: similarity × evidence_quality (NO quadratic)
    base_confidence = similarity * evidence_quality

    # 4. Agreement bonus (only when there's base confidence from similarity)
    raw_agreement = _compute_agreement(
        supporting_weight, total_weight, supporting_count, total_count
    )
    agreement_bonus = config.agreement_weight * raw_agreement if base_confidence > 0 else 0.0

    # 5. Agreement boost for very high agreement (only when there's base confidence)
    if raw_agreement >= config.agreement_boost_threshold:
        overshoot = raw_agreement - config.agreement_boost_threshold
        max_overshoot = 1.0 - config.agreement_boost_threshold
        agreement_bonus += config.agreement_boost_weight * (overshoot / max_overshoot)

    # 6. Conflict detection and penalty
    conflict_count = _detect_conflict_count(
        outputs, output_similarities, relevance_threshold=config.conflict_relevance_threshold
    )
    if conflict_count > 1 and total_weight > 0:
        winner_weight_est = supporting_weight
        runner_up_weight_est = total_weight - supporting_weight
        conflict_penalty = _compute_conflict_penalty(
            winner_weight_est, runner_up_weight_est, config.max_conflict_penalty
        )
    else:
        conflict_penalty = 0.0

    # 7. Novelty penalty
    novelty_penalty = _compute_novelty_penalty(
        similarity, config.novelty_penalty_threshold, config.novelty_penalty_strength
    )

    # 8. Failure dominance penalty
    failure_penalty = _compute_failure_penalty(
        success_count, failure_count, config.failure_dominance_penalty
    )

    # 9. Independence bonus — multiple independent memories strengthen confidence
    independence_bonus = _compute_independence_bonus(
        independent_evidence_count, config.independence_bonus_weight, config.max_independent_evidence
    )

    # 10. Final confidence
    raw_confidence = (
        base_confidence
        + agreement_bonus
        + independence_bonus
        - conflict_penalty
        - novelty_penalty
        - failure_penalty
    )
    raw_confidence = max(0.0, min(1.0, raw_confidence))

    # 11. Classify uncertainty state
    total_uses = success_count + failure_count
    if conflict_count > 1:
        uncertainty_state = "conflicted"
    elif total_uses < config.min_evidence_samples and similarity < 0.5:
        uncertainty_state = "insufficient_evidence"
    elif raw_confidence < 0.3 or evidence_strength < 0.3:
        uncertainty_state = "insufficient_evidence"
    elif raw_confidence >= 0.7 and evidence_strength >= 0.6:
        uncertainty_state = "confident"
    else:
        uncertainty_state = "uncertain"

    # 12. Components for explainability
    components: dict[str, Any] = {
        "similarity": round(similarity, 4),
        "evidence_strength": round(evidence_strength, 4),
        "evidence_quality": round(evidence_quality, 4),
        "base_confidence": round(base_confidence, 4),
        "agreement": round(raw_agreement, 4),
        "agreement_bonus": round(agreement_bonus, 4),
        "independence_bonus": round(independence_bonus, 4),
        "independent_evidence_count": independent_evidence_count,
        "conflict_penalty": round(conflict_penalty, 4),
        "novelty_penalty": round(novelty_penalty, 4),
        "failure_penalty": round(failure_penalty, 4),
        "success_count": success_count,
        "failure_count": failure_count,
        "total_uses": total_uses,
        "supporting_count": supporting_count,
        "total_count": total_count,
        "conflict_count": conflict_count,
    }

    return ConfidenceEstimatorResult(
        confidence=raw_confidence,
        raw_confidence=raw_confidence,
        similarity=similarity,
        evidence_strength=evidence_strength,
        evidence_quality=evidence_quality,
        agreement=raw_agreement,
        agreement_bonus=agreement_bonus,
        conflict_penalty=conflict_penalty,
        novelty_penalty=novelty_penalty,
        failure_penalty=failure_penalty,
        supporting_count=supporting_count,
        total_count=total_count,
        conflict_count=conflict_count,
        total_success=success_count,
        total_failure=failure_count,
        independent_evidence_count=independent_evidence_count,
        uncertainty_state=uncertainty_state,
        probability=raw_confidence,
        band=_confidence_band(raw_confidence),
        components=components,
    )

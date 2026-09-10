"""Pluggable retrieval scoring for V2.1.

Combines raw similarity with quality and recency signals to produce
a final retrieval score. The scorer is optional — when not used,
V2.0 behavior (raw similarity × weight) is preserved.

Design principles:
- Similarity is ALWAYS the primary signal
- Quality and recency are small multiplicative bonuses
- Irrelevant memories (similarity ≈ 0) get score ≈ 0 regardless of quality
- All signals are bounded and stable
- No single signal can overpower relevance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.learner.hybrid_memory import HybridExample


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScorerConfig:
    """Configuration for retrieval scoring.

    Attributes:
        quality_weight: How much quality boosts retrieval score [0, 0.5].
            Default 0.1 means max 10% boost from perfect quality.
        recency_weight: How much recency boosts retrieval score [0, 0.2].
            Default 0.05 means max 5% boost from most recent.
        recency_half_life: Seconds until recency score drops to 0.5.
            Default 86400 (1 day). Set to 0 to disable recency.
        diversity_threshold: Cosine similarity above which two memories
            are considered near-duplicates [0.8, 1.0].
            Default 0.9. Set to 1.0 to disable diversity.
    """

    quality_weight: float = 0.1
    recency_weight: float = 0.05
    recency_half_life: float = 86400.0
    diversity_threshold: float = 0.9


# ---------------------------------------------------------------------------
# Quality calculation
# ---------------------------------------------------------------------------


def quality_score(example: HybridExample) -> float:
    """Compute bounded quality score for a memory.

    Quality blends success rate with feedback weight:
    - success_rate: fraction of successful uses (0.5 if untested)
    - weight_norm: normalized weight in [0, 1] from [0.3, 5.0]

    Returns a value in [0, 1].
    """
    total = example.success_count + example.failure_count
    success_rate = 0.5 if total == 0 else example.success_count / total

    # Normalize weight from [0.3, 5.0] to [0, 1]
    weight_norm = max(0.0, min(1.0, (example.weight - 0.3) / 4.7))

    # Blend: 60% success rate, 40% weight
    return 0.6 * success_rate + 0.4 * weight_norm


# ---------------------------------------------------------------------------
# Recency calculation
# ---------------------------------------------------------------------------


def recency_score(example: HybridExample, now: float, half_life: float) -> float:
    """Compute bounded recency score using exponential decay.

    Args:
        example: The memory to score.
        now: Current epoch timestamp.
        half_life: Seconds until score drops to 0.5.

    Returns a value in [0.1, 1.0]. Floor at 0.1 ensures old
    proven memories are never completely forgotten.
    """
    if half_life <= 0:
        return 1.0  # Recency disabled

    age = now - example.last_used_at
    if age <= 0:
        return 1.0

    # Exponential decay: score = 2^(-age/half_life)
    import math
    score = math.pow(2.0, -age / half_life)
    return max(0.1, score)


# ---------------------------------------------------------------------------
# Retrieval scoring
# ---------------------------------------------------------------------------


def retrieval_score(
    relevance: float,
    quality: float,
    recency: float,
    quality_weight: float = 0.1,
    recency_weight: float = 0.05,
) -> float:
    """Combine relevance with quality and recency bonuses.

    The formula is:
        score = relevance * (1 + quality_weight * quality + recency_weight * recency)

    This ensures:
    - If relevance = 0, score = 0 (irrelevant memories never rank high)
    - Quality and recency are small bonuses, not dominant signals
    - Maximum boost from perfect quality + recency is ~15%

    Args:
        relevance: Raw similarity score [0, 1].
        quality: Quality score [0, 1].
        recency: Recency score [0, 1].
        quality_weight: Max quality contribution [0, 0.5].
        recency_weight: Max recency contribution [0, 0.2].

    Returns:
        Final retrieval score >= 0.
    """
    bonus = quality_weight * quality + recency_weight * recency
    return relevance * (1.0 + bonus)


# ---------------------------------------------------------------------------
# Diversity
# ---------------------------------------------------------------------------


def diversify_top_k(
    scored: list[tuple[int, float, float]],
    k: int,
    similarity_threshold: float = 0.9,
) -> list[tuple[int, float]]:
    """Remove near-duplicates from top-k results.

    Args:
        scored: List of (example_id, retrieval_score, pairwise_similarity).
            pairwise_similarity is the max similarity to any already-selected
            memory. For the first item, this is 0.0.
        k: Maximum number of results to return.
        similarity_threshold: Above this, two memories are near-duplicates.

    Returns:
        List of (example_id, retrieval_score) with near-duplicates removed.
    """
    if similarity_threshold >= 1.0:
        # Diversity disabled — just take top-k
        return [(eid, score) for eid, score, _ in scored[:k]]

    selected: list[tuple[int, float]] = []
    for eid, score, max_sim in scored:
        if len(selected) >= k:
            break
        if max_sim < similarity_threshold:
            selected.append((eid, score))
    return selected

"""Knowledge lifecycle management for V2.4.

Manages the lifecycle of learned knowledge through states:
- ACTIVE: Knowledge currently considered useful and trustworthy
- UNCERTAIN: Knowledge retained but confidence/evidence insufficient
- SUPERSEDED: Newer/better-supported knowledge replaces practical role
- ARCHIVED: Retained for history/audit, excluded from normal retrieval

Design principles:
- NEVER blindly delete knowledge
- Every state transition is explainable and auditable
- Provenance is preserved across all mutations
- Strong evidence slows decay
- Independent evidence is preserved through consolidation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Lifecycle states
# ---------------------------------------------------------------------------


class MemoryState(Enum):
    """Lifecycle states for learned knowledge."""

    ACTIVE = "active"
    UNCERTAIN = "uncertain"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Lifecycle event (provenance)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleEvent:
    """Record of a lifecycle state transition.

    Attributes:
        previous_state: State before transition.
        new_state: State after transition.
        reason: Human-readable explanation.
        timestamp: When the transition occurred.
        evidence_summary: Key evidence at decision time.
        related_ids: IDs of related memories involved.
        confidence_at_transition: Confidence when decision was made.
    """

    previous_state: str
    new_state: str
    reason: str
    timestamp: float
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    related_ids: list[int] = field(default_factory=list)
    confidence_at_transition: float = 0.0


# ---------------------------------------------------------------------------
# Memory health signals
# ---------------------------------------------------------------------------


@dataclass
class HealthSignals:
    """Individual health signals for a memory.

    Each signal is documented with its purpose:
    - success_rate: Historical success/failure ratio [0, 1]
    - independent_evidence: Count of independent confirmations
    - confidence: Current confidence estimate [0, 1]
    - recency: How recently used (0=never, 1=just now) [0, 1]
    - usage_frequency: Normalized usage count [0, 1]
    - redundancy: How many similar memories exist (0=solo, 1=many duplicates)
    - contradiction_count: Number of contradicted memories
    """

    success_rate: float = 0.5
    independent_evidence: int = 0
    confidence: float = 0.5
    recency: float = 0.5
    usage_frequency: float = 0.0
    redundancy: float = 0.0
    contradiction_count: int = 0


# ---------------------------------------------------------------------------
# Lifecycle configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleConfig:
    """Configuration for lifecycle management.

    Attributes:
        decay_rate: Base rate of confidence decay per day [0.001, 0.1].
            Default 0.01 means ~1% confidence lost per day without use.
        decay_min: Minimum confidence before archival consideration [0.0, 0.2].
        reinforcement_strength: How much successful use reinforces confidence
            [0.01, 0.1]. Diminishing returns applied.
        independence_bonus: Bonus per independent confirmation [0.01, 0.05].
        supersession_threshold: Confidence difference needed for supersession
            [0.1, 0.5]. Higher = fewer false supersessions.
        merge_similarity: Minimum output similarity for merge candidates
            [0.7, 1.0]. Higher = fewer merges.
        archive_threshold: Confidence below which archival is considered
            [0.05, 0.2].
        uncertainty_threshold: Confidence below which state becomes UNCERTAIN
            [0.1, 0.3].
        max_redundancy: Maximum similar memories before consolidation [3, 10].
    """

    decay_rate: float = 0.01
    decay_min: float = 0.1
    reinforcement_strength: float = 0.03
    independence_bonus: float = 0.02
    supersession_threshold: float = 0.2
    merge_similarity: float = 0.8
    archive_threshold: float = 0.1
    uncertainty_threshold: float = 0.2
    max_redundancy: int = 5


# ---------------------------------------------------------------------------
# Health computation
# ---------------------------------------------------------------------------


def compute_health_score(signals: HealthSignals) -> float:
    """Compute overall health score from individual signals.

    Health = weighted combination of signals, with success_rate dominant.

    Score > 0.6: likely ACTIVE
    Score 0.3-0.6: likely UNCERTAIN
    Score < 0.3: candidate for SUPERSEDED/ARCHIVED

    Returns value in [0, 1].
    """
    # Base: success rate (most important signal)
    base = 0.40 * signals.success_rate

    # Evidence bonus: more independent confirmations = healthier
    evidence_bonus = 0.20 * min(1.0, signals.independent_evidence / 5.0)

    # Confidence contribution
    conf_bonus = 0.15 * signals.confidence

    # Recency: recently used knowledge is healthier
    recency_bonus = 0.10 * signals.recency

    # Usage: frequently used knowledge is valuable
    usage_bonus = 0.10 * signals.usage_frequency

    # Redundancy penalty: too many similar memories is noise
    redundancy_penalty = 0.05 * signals.redundancy

    # Contradiction penalty: contradicted knowledge is less trustworthy
    contradiction_penalty = 0.05 * min(1.0, signals.contradiction_count / 3.0)

    score = base + evidence_bonus + conf_bonus + recency_bonus + usage_bonus
    score -= redundancy_penalty + contradiction_penalty

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Decay computation
# ---------------------------------------------------------------------------


def compute_decay(
    confidence: float,
    days_since_use: float,
    success_rate: float,
    independent_evidence: int,
    config: LifecycleConfig,
) -> float:
    """Compute decayed confidence based on time and evidence quality.

    Key insight: strong evidence slows decay.

    - High success rate + many independent confirmations = slow decay
    - Low success rate + few confirmations = fast decay
    - Never use time alone to determine truth

    Args:
        confidence: Current confidence [0, 1].
        days_since_use: Days since last use.
        success_rate: Historical success rate [0, 1].
        independent_evidence: Number of independent confirmations.
        config: Lifecycle configuration.

    Returns:
        New confidence after decay [0, 1].
    """
    if days_since_use <= 0:
        return confidence

    # Evidence strength slows decay
    # Strong evidence: decay rate * 0.3 (70% slower)
    # Weak evidence: decay rate * 1.5 (50% faster)
    evidence_factor = 1.5 - 0.7 * success_rate
    evidence_factor *= 1.0 / (1.0 + 0.2 * independent_evidence)

    # Apply decay: exponential with evidence-adjusted rate
    effective_rate = config.decay_rate * evidence_factor
    decay = math.exp(-effective_rate * days_since_use)

    new_confidence = confidence * decay

    # Floor: don't decay below minimum
    new_confidence = max(config.decay_min, new_confidence)

    return new_confidence


# ---------------------------------------------------------------------------
# Reinforcement computation
# ---------------------------------------------------------------------------


def compute_reinforcement(
    confidence: float,
    success_count: int,
    independent_evidence: int,
    config: LifecycleConfig,
) -> float:
    """Compute reinforced confidence from successful use.

    Diminishing returns: each additional success adds less.

    Args:
        confidence: Current confidence [0, 1].
        success_count: Total successful uses.
        independent_evidence: Number of independent confirmations.
        config: Lifecycle configuration.

    Returns:
        New confidence after reinforcement [0, 1].
    """
    # Diminishing returns: log scale
    # 1 success: full strength
    # 2 successes: ~0.63 of full
    # 5 successes: ~0.43 of full
    # 10 successes: ~0.33 of full
    if success_count <= 0:
        return confidence

    reinforcement = config.reinforcement_strength * (
        math.log(1 + success_count) / math.log(2)
    )

    # Independence bonus: each independent source adds a small bonus
    independence = config.independence_bonus * min(
        independent_evidence, config.max_redundancy
    )

    new_confidence = confidence + reinforcement + independence

    return min(1.0, new_confidence)

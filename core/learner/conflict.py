"""Conflict detection and evidence-based resolution for V2.2.

Detects when retrieved memories disagree about the output for a query,
compares evidence, and either resolves or reports the conflict.

Design principles:
- Relevance is always the primary signal
- No single factor dominates automatically
- Conflicting knowledge is never blindly deleted
- Unresolved conflicts reduce confidence rather than forcing a choice
- All mechanisms are deterministic and explainable
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.learner.hybrid_memory import HybridExample


# ---------------------------------------------------------------------------
# Conflict state
# ---------------------------------------------------------------------------


class ConflictState(Enum):
    """Possible states for a detected conflict."""

    NONE = "none"
    POSSIBLE = "possible"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidence supporting a single memory in a conflict.

    Attributes:
        example_id: The memory's ID.
        output: The memory's predicted output.
        relevance: How relevant this memory is to the query [0, 1].
        success_rate: Fraction of successful uses (0.5 if untested).
        success_count: Raw number of successful uses.
        failure_count: Raw number of failed uses.
        weight: Feedback-adjusted weight from memory [0.3, 5.0].
        recency: How recently this memory was used [0.1, 1.0].
    """

    example_id: int
    output: str
    relevance: float
    success_rate: float
    success_count: int
    failure_count: int
    weight: float
    recency: float


# ---------------------------------------------------------------------------
# Conflict
# ---------------------------------------------------------------------------


@dataclass
class Conflict:
    """A detected conflict between memories.

    Attributes:
        involved_ids: IDs of all memories involved in the conflict.
        outputs: The distinct outputs being proposed.
        state: Current resolution state.
        strength: How strong the conflict is [0, 1]. 1 = exact same input,
            different output. Lower = more different contexts.
        evidence: Per-memory evidence for resolution.
        selected_output: The chosen output (if resolved).
        winner_id: The winning memory's ID (if resolved).
        confidence_penalty: How much confidence is reduced [0, 1].
    """

    involved_ids: list[int]
    outputs: list[str]
    state: ConflictState = ConflictState.NONE
    strength: float = 0.0
    evidence: list[Evidence] = field(default_factory=list)
    selected_output: str | None = None
    winner_id: int | None = None
    confidence_penalty: float = 0.0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConflictConfig:
    """Configuration for conflict detection and resolution.

    Attributes:
        input_similarity_threshold: Minimum input similarity for two
            memories to be considered potentially conflicting [0.7, 1.0].
            Higher = fewer false conflicts, may miss subtle conflicts.
        output_equality_threshold: Maximum output similarity below which
            two outputs are considered different [0.0, 1.0].
            0.0 = exact string match required.
        evidence_margin: Minimum evidence score difference to declare a
            winner. Below this, conflict is unresolved [0.0, 0.5].
        context_similarity_threshold: Input similarity above which context
            differences are ignored (memories are treated as same-context)
            [0.8, 1.0].
        min_evidence_samples: Minimum total uses before evidence is trusted.
            Below this, success rate is treated as neutral [0, 100].
    """

    input_similarity_threshold: float = 0.75
    output_equality_threshold: float = 0.0
    evidence_margin: float = 0.1
    context_similarity_threshold: float = 0.9
    min_evidence_samples: int = 3


# ---------------------------------------------------------------------------
# Output similarity
# ---------------------------------------------------------------------------


def _output_similarity(a: str, b: str) -> float:
    """Compute similarity between two output strings.

    Uses token-level Jaccard similarity for simple comparison.
    Returns value in [0, 1] where 1 = identical.

    This is intentionally simple — output comparison does not need
    the full semantic encoder. Token overlap is sufficient for
    detecting whether two outputs are "the same answer."
    """
    if a == b:
        return 1.0
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def detect_conflicts(
    candidates: list[tuple[int, float, str]],
    examples: dict[int, HybridExample],
    config: ConflictConfig | None = None,
) -> list[Conflict]:
    """Detect conflicts among retrieved candidates.

    A conflict exists when two candidates:
    1. Have high input similarity (same context) AND
    2. Have different outputs (disagree)

    Args:
        candidates: List of (example_id, relevance_score, output) for
            the top-k retrieved memories.
        examples: Dict mapping example_id to HybridExample for metadata.
        config: Conflict detection configuration.

    Returns:
        List of detected conflicts (may be empty if no conflicts).
    """
    if config is None:
        config = ConflictConfig()
    if len(candidates) < 2:
        return []

    # Group candidates by output
    output_groups: dict[str, list[tuple[int, float]]] = {}
    for example_id, relevance, output in candidates:
        output_groups.setdefault(output, []).append((example_id, relevance))

    if len(output_groups) < 2:
        return []

    # Compare each pair of output groups
    conflicts: list[Conflict] = []
    output_list = list(output_groups.keys())

    for i in range(len(output_list)):
        for j in range(i + 1, len(output_list)):
            out_a = output_list[i]
            out_b = output_list[j]

            # Check if outputs are actually different
            out_sim = _output_similarity(out_a, out_b)
            if out_sim >= (1.0 - config.output_equality_threshold):
                continue  # Outputs are effectively the same

            group_a = output_groups[out_a]
            group_b = output_groups[out_b]

            # Check input similarity between the strongest representatives
            best_a_id = max(group_a, key=lambda x: x[1])[0]
            best_b_id = max(group_b, key=lambda x: x[1])[0]

            ex_a = examples.get(best_a_id)
            ex_b = examples.get(best_b_id)
            if ex_a is None or ex_b is None:
                continue

            # Compute input similarity from lexical vectors
            from core.learner.similarity import cosine_similarity

            input_sim = cosine_similarity(
                ex_a.lexical_vector, ex_b.lexical_vector
            )

            # Determine conflict strength and state
            if input_sim >= config.context_similarity_threshold:
                # Same context, different output — strong conflict
                strength = input_sim
                state = ConflictState.CONFIRMED
            elif input_sim >= config.input_similarity_threshold:
                # Similar context, different output — possible conflict
                strength = input_sim
                state = ConflictState.POSSIBLE
            else:
                # Different contexts — may be context-dependent, not a conflict
                continue

            # Gather all involved IDs
            involved = [eid for eid, _ in group_a] + [eid for eid, _ in group_b]
            outputs = [out_a, out_b]

            conflict = Conflict(
                involved_ids=involved,
                outputs=outputs,
                state=state,
                strength=strength,
            )
            conflicts.append(conflict)

    return conflicts


# ---------------------------------------------------------------------------
# Evidence gathering
# ---------------------------------------------------------------------------


def gather_evidence(
    conflict: Conflict,
    examples: dict[int, HybridExample],
    query_relevance: dict[int, float],
    recency_scores: dict[int, float] | None = None,
) -> Conflict:
    """Gather evidence for each memory involved in a conflict.

    Enriches the conflict with per-memory evidence including relevance,
    success rate, success/failure counts, weight, and recency.

    Args:
        conflict: The conflict to enrich.
        examples: All examples by ID.
        query_relevance: Maps example_id -> relevance score for this query.
        recency_scores: Optional maps example_id -> recency score.

    Returns:
        The same conflict object, enriched with evidence.
    """
    evidence_list: list[Evidence] = []

    for eid in conflict.involved_ids:
        ex = examples.get(eid)
        if ex is None:
            continue

        total_uses = ex.success_count + ex.failure_count
        success_rate = 0.5 if total_uses == 0 else ex.success_count / total_uses

        recency = 0.5  # Default neutral
        if recency_scores and eid in recency_scores:
            recency = recency_scores[eid]

        ev = Evidence(
            example_id=eid,
            output=ex.output,
            relevance=query_relevance.get(eid, 0.0),
            success_rate=success_rate,
            success_count=ex.success_count,
            failure_count=ex.failure_count,
            weight=ex.weight,
            recency=recency,
        )
        evidence_list.append(ev)

    conflict.evidence = evidence_list
    return conflict


# ---------------------------------------------------------------------------
# Evidence comparison
# ---------------------------------------------------------------------------


def _evidence_score(ev: Evidence, min_samples: int = 3) -> float:
    """Compute a composite evidence score for one memory.

    The score blends multiple signals, with relevance always dominant:

    score = relevance * (0.60 + 0.15 * sr + 0.10 * log_b + 0.10 * rec + 0.05 * wn)

    Where sr=success_rate, log_b=log_bonus, rec=recency, wn=weight_norm.

    Where:
    - relevance: primary signal (60% base weight)
    - success_rate: historical success rate (15%)
    - log_bonus: diminishing returns on success count (10%)
    - recency: how recently used (10%)
    - weight_norm: feedback weight (5%)

    Returns value in [0, 1].
    """
    # Success rate bonus (bounded, neutral if insufficient samples)
    total = ev.success_count + ev.failure_count
    sr_bonus = 0.0 if total < min_samples else ev.success_rate

    # Log bonus: diminishing returns on raw success count
    # log(1 + count) / log(1 + 100) — saturates around 100 uses
    import math
    log_bonus = min(1.0, math.log(1.0 + ev.success_count) / math.log(101.0))

    # Weight normalization: [0.3, 5.0] -> [0, 1]
    weight_norm = max(0.0, min(1.0, (ev.weight - 0.3) / 4.7))

    # Composite score — relevance is always the primary factor
    score = ev.relevance * (
        0.60
        + 0.15 * sr_bonus
        + 0.10 * log_bonus
        + 0.10 * ev.recency
        + 0.05 * weight_norm
    )
    return max(0.0, min(1.0, score))


def compare_evidence(
    conflict: Conflict,
    config: ConflictConfig | None = None,
) -> Conflict:
    """Compare evidence and attempt to resolve a conflict.

    Resolution rules:
    1. Compute evidence score for each memory
    2. If one memory clearly dominates (score difference > margin): RESOLVED
    3. If scores are close: UNRESOLVED (confidence is reduced)
    4. Never automatically delete or weaken any memory

    Args:
        conflict: The conflict with gathered evidence.
        config: Resolution configuration.

    Returns:
        The same conflict object, with state updated to RESOLVED or UNRESOLVED.
    """
    if config is None:
        config = ConflictConfig()

    if len(conflict.evidence) < 2:
        conflict.state = ConflictState.UNRESOLVED
        conflict.confidence_penalty = 0.3
        return conflict

    # Compute evidence scores
    scores: list[tuple[int, str, float]] = []
    for ev in conflict.evidence:
        score = _evidence_score(ev, config.min_evidence_samples)
        scores.append((ev.example_id, ev.output, score))

    # Sort by score descending
    scores.sort(key=lambda x: x[2], reverse=True)

    winner_id, winner_output, winner_score = scores[0]
    _, _, runner_up_score = scores[1]

    margin = winner_score - runner_up_score

    if margin > config.evidence_margin:
        # Clear winner
        conflict.state = ConflictState.RESOLVED
        conflict.selected_output = winner_output
        conflict.winner_id = winner_id
        conflict.confidence_penalty = max(0.05, 0.3 - margin)
    else:
        # Too close to call
        conflict.state = ConflictState.UNRESOLVED
        conflict.selected_output = winner_output  # Still pick best, but...
        conflict.winner_id = winner_id
        # Confidence is significantly reduced
        conflict.confidence_penalty = max(0.3, 0.6 - margin)

    return conflict

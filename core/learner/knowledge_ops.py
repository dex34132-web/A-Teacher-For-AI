"""Knowledge supersession, merging, and redundancy for V2.4.2.

Supersession:
- When new knowledge conflicts with old, determine if new genuinely replaces old
- Never automatically choose "newer = better" or "older = more trusted"
- If evidence insufficient, retain both and mark uncertain

Merging:
- Detect memories representing the same underlying knowledge
- Preserve provenance (memory IDs of source memories)
- Never merge genuinely contradictory knowledge
- Require sufficient semantic similarity + compatible outputs
- Multi-signal analysis: input similarity, output similarity, evidence quality
- Token inverted index for O(N·K) candidate generation

Redundancy:
- Classify: exact duplicate, normalized duplicate, semantic duplicate,
  related but independent, genuinely distinct
- Preserve independent evidence through consolidation

V2.4.2 Changes:
- Improved merging with multi-signal analysis
- Added input similarity computation
- Added minimum evidence requirements for merging
- Improved redundancy detection with input similarity
- Token inverted index for scalable candidate generation
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

from core.learner.lifecycle import (
    HealthSignals,
    LifecycleConfig,
    LifecycleEvent,
    MemoryState,
    compute_health_score,
)

if TYPE_CHECKING:
    from core.learner.hybrid_memory import HybridExample


# ---------------------------------------------------------------------------
# Supersession
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupersessionResult:
    """Result of supersession analysis.

    Attributes:
        should_supersede: Whether old should be superseded by new.
        reason: Human-readable explanation.
        old_health: Health score of old memory.
        new_health: Health score of new memory.
        confidence_difference: new_health - old_health.
    """

    should_supersede: bool
    reason: str
    old_health: float
    new_health: float
    confidence_difference: float


def analyze_supersession(
    old: HybridExample,
    new: HybridExample,
    config: LifecycleConfig,
    clock: Callable[[], float] | None = None,
) -> SupersessionResult:
    """Analyze whether new knowledge supersedes old knowledge.

    Rules:
    1. Never automatically choose newer = better
    2. Never automatically choose older = more trusted
    3. Compare evidence quality, not just timestamps
    4. If evidence insufficient, retain both

    Args:
        old: Existing memory.
        new: Newer memory with similar input.
        config: Lifecycle configuration.
        clock: Optional clock function for deterministic testing.

    Returns:
        SupersessionResult with recommendation and explanation.
    """
    now = (clock or time.time)()

    # Compute health for both
    old_signals = HealthSignals(
        success_rate=old.success_rate,
        independent_evidence=old.success_count,
        confidence=old.weight,
        recency=min(1.0, max(0.0, 1.0 - (now - old.last_used_at) / 86400)),
        usage_frequency=min(1.0, old.use_count / 10.0),
    )
    new_signals = HealthSignals(
        success_rate=new.success_rate,
        independent_evidence=new.success_count,
        confidence=new.weight,
        recency=min(1.0, max(0.0, 1.0 - (now - new.last_used_at) / 86400)),
        usage_frequency=min(1.0, new.use_count / 10.0),
    )

    old_health = compute_health_score(old_signals)
    new_health = compute_health_score(new_signals)
    diff = new_health - old_health

    # Check if outputs are actually different
    outputs_differ = old.output != new.output

    if not outputs_differ:
        return SupersessionResult(
            should_supersede=False,
            reason="Same output — no supersession needed, consider merging",
            old_health=old_health,
            new_health=new_health,
            confidence_difference=diff,
        )

    # Need sufficient evidence difference for supersession
    if abs(diff) < config.supersession_threshold:
        return SupersessionResult(
            should_supersede=False,
            reason=(
                f"Insufficient evidence difference ({diff:.3f} < "
                f"{config.supersession_threshold}) — retain both"
            ),
            old_health=old_health,
            new_health=new_health,
            confidence_difference=diff,
        )

    if diff > 0:
        return SupersessionResult(
            should_supersede=True,
            reason=(
                f"New knowledge has stronger evidence ({new_health:.3f} vs "
                f"{old_health:.3f}, diff={diff:.3f})"
            ),
            old_health=old_health,
            new_health=new_health,
            confidence_difference=diff,
        )
    else:
        return SupersessionResult(
            should_supersede=False,
            reason=(
                f"Old knowledge has stronger evidence ({old_health:.3f} vs "
                f"{new_health:.3f}, diff={abs(diff):.3f}) — retain old"
            ),
            old_health=old_health,
            new_health=new_health,
            confidence_difference=diff,
        )


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeCandidate:
    """A pair of memories that may be merge candidates.

    Attributes:
        id_a: First memory ID.
        id_b: Second memory ID.
        output_similarity: How similar the outputs are [0, 1].
        input_similarity: How similar the inputs are [0, 1].
        combined_evidence: Total independent evidence if merged.
        semantic_similarity: Semantic similarity if available [0, 1], else None.
    """

    id_a: int
    id_b: int
    output_similarity: float
    input_similarity: float
    combined_evidence: int
    semantic_similarity: float | None = None


def _output_similarity(a: str, b: str) -> float:
    """Compute token-level Jaccard similarity between outputs."""
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


def _input_similarity(a: str, b: str) -> float:
    """Compute token-level Jaccard similarity between inputs."""
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
# Token inverted index for scalable candidate generation
# ---------------------------------------------------------------------------


class TokenInvertedIndex:
    """Inverted index for efficient candidate generation.

    Maps tokens to memory IDs, enabling O(N·K) candidate generation
    instead of O(N²) brute force.

    K is the average number of memories sharing a token with the query.
    For typical workloads, K << N, making this much faster.
    """

    def __init__(self) -> None:
        """Initialize empty index."""
        self._index: dict[str, set[int]] = defaultdict(set)
        self._token_count: dict[int, int] = {}

    def add(self, memory_id: int, text: str) -> None:
        """Add a memory to the index.

        Args:
            memory_id: The memory's ID.
            text: The text to index (input_text).
        """
        tokens = set(text.lower().split())
        self._token_count[memory_id] = len(tokens)
        for token in tokens:
            self._index[token].add(memory_id)

    def remove(self, memory_id: int, text: str) -> None:
        """Remove a memory from the index.

        Args:
            memory_id: The memory's ID.
            text: The text that was indexed.
        """
        tokens = set(text.lower().split())
        self._token_count.pop(memory_id, None)
        for token in tokens:
            if token in self._index:
                self._index[token].discard(memory_id)
                if not self._index[token]:
                    del self._index[token]

    def find_candidates(
        self,
        query_text: str,
        min_overlap: int = 2,
        exclude_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Find candidate memories that share tokens with query.

        Args:
            query_text: The text to find candidates for.
            min_overlap: Minimum number of shared tokens to consider a candidate.
            exclude_ids: IDs to exclude from results.

        Returns:
            List of (memory_id, overlap_ratio) tuples, sorted by overlap descending.
        """
        exclude = exclude_ids or set()
        query_tokens = set(query_text.lower().split())
        if not query_tokens:
            return []

        # Count overlapping tokens for each candidate
        candidate_counts: dict[int, int] = defaultdict(int)
        for token in query_tokens:
            if token in self._index:
                for mid in self._index[token]:
                    if mid not in exclude:
                        candidate_counts[mid] += 1

        # Filter by minimum overlap and compute ratio
        results = []
        for mid, count in candidate_counts.items():
            if count >= min_overlap:
                # Compute overlap ratio (Jaccard-like)
                mem_tokens = self._token_count.get(mid, 1)
                union_size = len(query_tokens) + mem_tokens - count
                ratio = count / union_size if union_size > 0 else 0.0
                results.append((mid, ratio))

        # Sort by overlap descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def clear(self) -> None:
        """Clear the index."""
        self._index.clear()
        self._token_count.clear()



def _build_merge_index(examples: list[HybridExample]) -> TokenInvertedIndex:
    """Build a fresh merge index from the given examples.

    Args:
        examples: All memories to index.

    Returns:
        A new TokenInvertedIndex populated with the examples.
    """
    index = TokenInvertedIndex()
    for ex in examples:
        index.add(ex.id, ex.input_text)
    return index


def find_merge_candidates(
    examples: list[HybridExample],
    config: LifecycleConfig,
    use_index: bool = True,
) -> list[MergeCandidate]:
    """Find pairs of memories that are candidates for merging.

    Uses token inverted index for O(N·K) candidate generation when use_index=True.
    Falls back to O(N²) brute force when use_index=False.

    Merge candidates must:
    1. Have high output similarity (same underlying knowledge)
    2. Have sufficient input similarity (related queries)
    3. Not be genuinely contradictory
    4. Have sufficient combined evidence
    5. Have compatible evidence quality

    Args:
        examples: All memories to consider.
        config: Lifecycle configuration.
        use_index: If True, use inverted index for faster generation.

    Returns:
        List of MergeCandidate pairs.
    """
    if not use_index or len(examples) < 50:
        return _find_merge_candidates_bruteforce(examples, config)

    return _find_merge_candidates_indexed(examples, config)


def _find_merge_candidates_bruteforce(
    examples: list[HybridExample],
    config: LifecycleConfig,
) -> list[MergeCandidate]:
    """O(N²) brute force candidate generation for small datasets."""
    candidates: list[MergeCandidate] = []
    id_to_example = {ex.id: ex for ex in examples}

    for i in range(len(examples)):
        for j in range(i + 1, len(examples)):
            a = examples[i]
            b = examples[j]

            # Check output similarity first (cheapest check)
            out_sim = _output_similarity(a.output, b.output)
            if out_sim < config.merge_similarity:
                continue

            # Check input similarity
            in_sim = _input_similarity(a.input_text, b.input_text)
            if in_sim < config.merge_input_similarity:
                continue

            # Compute combined evidence
            combined = a.success_count + b.success_count
            if combined < config.merge_min_evidence:
                continue

            # Don't merge if one has many failures and the other doesn't
            if (a.failure_count > 2 and b.failure_count == 0) or (
                b.failure_count > 2 and a.failure_count == 0
            ):
                continue

            # Compute semantic similarity if available
            sem_sim = compute_semantic_similarity(a, b)

            candidates.append(
                MergeCandidate(
                    id_a=a.id,
                    id_b=b.id,
                    output_similarity=out_sim,
                    input_similarity=in_sim,
                    combined_evidence=combined,
                    semantic_similarity=sem_sim,
                )
            )

    return candidates


def _find_merge_candidates_indexed(
    examples: list[HybridExample],
    config: LifecycleConfig,
) -> list[MergeCandidate]:
    """O(N·K) indexed candidate generation for larger datasets.

    Uses token inverted index to find candidates that share input tokens,
    then verifies output similarity for each pair.
    """
    # Build local index (no global state)
    id_to_example = {ex.id: ex for ex in examples}
    merge_index = _build_merge_index(examples)

    candidates: list[MergeCandidate] = []
    seen_pairs: set[tuple[int, int]] = set()

    for ex in examples:
        # Find candidates that share input tokens
        raw_candidates = merge_index.find_candidates(
            ex.input_text,
            min_overlap=2,
            exclude_ids={ex.id},
        )

        for other_id, overlap_ratio in raw_candidates:
            # Avoid duplicate pairs
            pair = (min(ex.id, other_id), max(ex.id, other_id))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            other = id_to_example.get(other_id)
            if other is None:
                continue

            # Check output similarity (main filter)
            out_sim = _output_similarity(ex.output, other.output)
            if out_sim < config.merge_similarity:
                continue

            # Compute input similarity
            in_sim = _input_similarity(ex.input_text, other.input_text)
            if in_sim < config.merge_input_similarity:
                continue

            # Compute combined evidence
            combined = ex.success_count + other.success_count
            if combined < config.merge_min_evidence:
                continue

            # Don't merge if one has many failures and the other doesn't
            if (ex.failure_count > 2 and other.failure_count == 0) or (
                other.failure_count > 2 and ex.failure_count == 0
            ):
                continue

            # Compute semantic similarity if available
            sem_sim = compute_semantic_similarity(ex, other)

            candidates.append(
                MergeCandidate(
                    id_a=ex.id,
                    id_b=other.id,
                    output_similarity=out_sim,
                    input_similarity=in_sim,
                    combined_evidence=combined,
                    semantic_similarity=sem_sim,
                )
            )

    return candidates


# ---------------------------------------------------------------------------
# Semantic similarity for merging
# ---------------------------------------------------------------------------


def compute_semantic_similarity(
    a: HybridExample,
    b: HybridExample,
) -> float | None:
    """Compute semantic similarity between two memories.

    Uses semantic vectors if available, otherwise returns None.

    Args:
        a: First memory.
        b: Second memory.

    Returns:
        Semantic similarity [0, 1] if both have semantic vectors, else None.
    """
    if a.semantic_vector is None or b.semantic_vector is None:
        return None

    if len(a.semantic_vector) != len(b.semantic_vector):
        return None

    # Compute cosine similarity
    dot = sum(x * y for x, y in zip(a.semantic_vector, b.semantic_vector, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a.semantic_vector))
    norm_b = math.sqrt(sum(x * x for x in b.semantic_vector))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return max(0.0, dot / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Redundancy detection
# ---------------------------------------------------------------------------


class RedundancyType(Enum):
    """Classification of redundancy between memories."""

    EXACT_DUPLICATE = "exact_duplicate"
    NORMALIZED_DUPLICATE = "normalized_duplicate"
    SEMANTIC_DUPLICATE = "semantic_duplicate"
    RELATED_BUT_INDEPENDENT = "related_but_independent"
    GENUINELY_DISTINCT = "genuinely_distinct"


@dataclass(frozen=True)
class RedundancyResult:
    """Result of redundancy analysis between two memories.

    Attributes:
        type: Classification of redundancy.
        should_consolidate: Whether to consolidate.
        reason: Human-readable explanation.
        combined_evidence: Total independent evidence if consolidated.
        semantic_similarity: Semantic similarity if available [0, 1], else None.
    """

    type: RedundancyType
    should_consolidate: bool
    reason: str
    combined_evidence: int
    semantic_similarity: float | None = None


def analyze_redundancy(
    a: HybridExample,
    b: HybridExample,
    config: LifecycleConfig,
) -> RedundancyResult:
    """Analyze redundancy between two memories.

    Classifies the relationship and determines if consolidation is safe.

    Args:
        a: First memory.
        b: Second memory.
        config: Lifecycle configuration.

    Returns:
        RedundancyResult with classification and recommendation.
    """
    # Compute semantic similarity if available
    sem_sim = compute_semantic_similarity(a, b)

    # Exact duplicate
    if a.input_text == b.input_text and a.output == b.output:
        combined = a.success_count + b.success_count
        return RedundancyResult(
            type=RedundancyType.EXACT_DUPLICATE,
            should_consolidate=True,
            reason="Exact duplicate — safe to consolidate",
            combined_evidence=combined,
            semantic_similarity=sem_sim,
        )

    # Normalized duplicate (same meaning, different wording)
    out_sim = _output_similarity(a.output, b.output)
    if out_sim >= 0.9:
        combined = a.success_count + b.success_count
        return RedundancyResult(
            type=RedundancyType.NORMALIZED_DUPLICATE,
            should_consolidate=True,
            reason=f"Normalized duplicate (output sim={out_sim:.2f}) — safe to consolidate",
            combined_evidence=combined,
            semantic_similarity=sem_sim,
        )

    # Semantic duplicate (same output, different phrasing)
    if a.output == b.output:
        combined = a.success_count + b.success_count
        return RedundancyResult(
            type=RedundancyType.SEMANTIC_DUPLICATE,
            should_consolidate=True,
            reason="Same output — consolidate to preserve evidence count",
            combined_evidence=combined,
            semantic_similarity=sem_sim,
        )

    # Related but independent
    if out_sim >= 0.5:
        return RedundancyResult(
            type=RedundancyType.RELATED_BUT_INDEPENDENT,
            should_consolidate=False,
            reason=f"Related but different outputs (sim={out_sim:.2f}) — retain separately",
            combined_evidence=a.success_count + b.success_count,
            semantic_similarity=sem_sim,
        )

    # Genuinely distinct
    return RedundancyResult(
        type=RedundancyType.GENUINELY_DISTINCT,
        should_consolidate=False,
        reason="Genuinely distinct knowledge — no consolidation needed",
        combined_evidence=a.success_count + b.success_count,
        semantic_similarity=sem_sim,
    )


# ---------------------------------------------------------------------------
# Archiving
# ---------------------------------------------------------------------------


def is_eligible_for_archive(
    example: HybridExample,
    health_score: float,
    config: LifecycleConfig,
) -> tuple[bool, str]:
    """Determine if a memory is eligible for archival.

    Archival rules:
    - NEVER archive solely because it is old
    - Archive if health is very low AND evidence is weak
    - Archive if superseded by stronger knowledge
    - Archive if explicitly requested

    Args:
        example: The memory to evaluate.
        health_score: Current health score [0, 1].
        config: Lifecycle configuration.

    Returns:
        Tuple of (eligible, reason).
    """
    # Very low health + weak evidence
    if health_score < config.archive_threshold:
        total_uses = example.success_count + example.failure_count
        if total_uses < 3:
            return True, (
                f"Very low health ({health_score:.3f}) with insufficient "
                f"evidence ({total_uses} uses)"
            )

    # Low confidence after many failures
    if example.failure_count > example.success_count and example.failure_count >= 3:
        return True, (
            f"More failures ({example.failure_count}) than successes "
            f"({example.success_count})"
        )

    return False, "Not eligible for archival"


def archive_memory(
    example: HybridExample,
    reason: str,
    current_state: MemoryState,
    clock: Callable[[], float] | None = None,
) -> tuple[MemoryState, LifecycleEvent]:
    """Transition a memory to ARCHIVED state.

    Args:
        example: The memory to archive.
        reason: Reason for archival.
        current_state: Current lifecycle state.
        clock: Optional clock function for deterministic testing.

    Returns:
        Tuple of (new_state, event) — always ARCHIVED.
    """
    now = (clock or time.time)()
    event = LifecycleEvent(
        previous_state=current_state.value,
        new_state=MemoryState.ARCHIVED.value,
        reason=reason,
        timestamp=now,
        evidence_summary={
            "success_count": example.success_count,
            "failure_count": example.failure_count,
            "weight": example.weight,
        },
        related_ids=[example.id],
        confidence_at_transition=example.weight,
    )
    return MemoryState.ARCHIVED, event

# EVO V2.4 — Knowledge Lifecycle

**Date:** 2026-09-10
**Status:** COMPLETED

## Overview

V2.4 adds a robust knowledge lifecycle system to EVO. Knowledge can now evolve over time through principled state transitions, health evaluation, reinforcement, decay, supersession, merging, redundancy detection, and archival.

**Key principle: NEVER blindly delete knowledge.**

## Lifecycle States

| State | Description |
|-------|-------------|
| `ACTIVE` | Knowledge currently considered useful and trustworthy |
| `UNCERTAIN` | Knowledge retained but confidence/evidence insufficient |
| `SUPERSEDED` | Newer/better-supported knowledge replaces practical role |
| `ARCHIVED` | Retained for history/audit, excluded from normal retrieval |

State transitions are always auditable with provenance tracking.

## Memory Health Model

Health is computed from individual signals, each with a documented purpose:

| Signal | Weight | Purpose |
|--------|--------|---------|
| Success rate | 40% | Historical success/failure ratio |
| Independent evidence | 20% | Number of independent confirmations |
| Confidence | 15% | Current confidence estimate |
| Recency | 10% | How recently used |
| Usage frequency | 10% | How often accessed |
| Redundancy | -5% | Penalty for too many similar memories |
| Contradictions | -5% | Penalty for contradicted knowledge |

Health score > 0.6: likely ACTIVE
Health score 0.3-0.6: likely UNCERTAIN
Health score < 0.3: candidate for SUPERSEDED/ARCHIVED

## Knowledge Reinforcement

Successful use reinforces knowledge with diminishing returns:
- 1 success: full strength
- 2 successes: ~63% of full
- 5 successes: ~43% of full
- 10 successes: ~33% of full

Independence bonus: each independent source adds a small bonus.

## Knowledge Decay

Decay is controlled and principled:
- **Strong evidence slows decay** (70% slower with high success rate)
- **Weak evidence accelerates decay** (50% faster with low success rate)
- **Never use time alone to determine truth**
- Decay has a configurable floor (default 0.1)

Formula: `new_confidence = confidence * exp(-rate * evidence_factor * days)`

## Supersession

When new knowledge conflicts with old:
1. Never automatically choose "newer = better"
2. Never automatically choose "older = more trusted"
3. Compare evidence quality, not timestamps
4. If evidence insufficient, retain both

Supersession requires a configurable evidence difference threshold (default 0.2).

## Knowledge Merging

Safe consolidation:
1. Detect memories with same underlying knowledge
2. Require high output similarity (>0.8)
3. Never merge genuinely contradictory knowledge
4. Preserve provenance (memory IDs of source memories)

## Redundancy Detection

Classification:
- `EXACT_DUPLICATE`: Same input and output
- `NORMALIZED_DUPLICATE`: Same meaning, different wording
- `SEMANTIC_DUPLICATE`: Same output, different phrasing
- `RELATED_BUT_INDEPENDENT`: Similar but different outputs
- `GENUINELY_DISTINCT`: Completely different

Consolidation preserves independent evidence counts.

## Archiving

Archived memories:
- Remain persisted
- Remain inspectable
- Preserve provenance
- Are excluded from normal retrieval
- Are recoverable if needed

Archival rules:
- NEVER archive solely because it is old
- Archive if health is very low AND evidence is weak
- Archive if more failures than successes

## Provenance

Every lifecycle mutation is tracked:
- Previous state
- New state
- Reason
- Timestamp
- Evidence summary
- Related memory IDs
- Confidence at decision time

## Persistence

Lifecycle state survives:
- Save/load
- Restart
- Migration

Backward compatible with V1/V2/V2.3.x stored memories.

## Safety Guarantees

1. **No accidental deletion** — only archival
2. **No false merging** — requires high output similarity
3. **No false supersession** — requires evidence difference
4. **No lifecycle oscillation** — diminishing returns prevent rapid state changes
5. **No evidence inflation** — duplicates are consolidated, not counted separately
6. **No recency bias** — strong evidence slows decay regardless of age

## Configuration

```python
from core.learner.lifecycle import LifecycleConfig

config = LifecycleConfig(
    decay_rate=0.01,           # Base decay rate per day
    decay_min=0.1,             # Minimum confidence floor
    reinforcement_strength=0.03,  # How much success reinforces
    independence_bonus=0.02,   # Bonus per independent source
    supersession_threshold=0.2,  # Evidence diff for supersession
    merge_similarity=0.8,      # Output similarity for merging
    archive_threshold=0.1,     # Health below which archival considered
    uncertainty_threshold=0.2,  # Confidence below which UNCERTAIN
    max_redundancy=5,          # Max similar memories before consolidation
)
```

## Usage

```python
from core.learner.learner_v2 import HybridSimilarityLearner
from core.learner.lifecycle import LifecycleConfig

# Create learner with lifecycle management
learner = HybridSimilarityLearner(
    k=5,
    lifecycle_config=LifecycleConfig(),
)

# Learn and provide feedback as usual
learner.learn({"input": "sort list", "output": "sorted(x)"})
learner.feedback("sort list", "sorted(x)", correct=True)

# Lifecycle is managed automatically
# Access lifecycle manager for manual operations
if learner._lifecycle:
    manager = learner._lifecycle
    # Process all memories (apply decay, check archival)
    results = manager.process_all(learner.memory)
    # Archive specific memory
    example = learner.memory.get_hybrid(1)
    manager.archive(example, "No longer relevant")
    # Restore archived memory
    manager.restore(1, "Relevant again")
```

## Benchmarks

- 570 tests passing (45 new lifecycle tests)
- 13 adversarial tests passing
- Backward compatible with V2.3.4

## Known Limitations

- Lifecycle processing is not automatic (must be called manually or via batch)
- Semantic similarity for merging uses token-level Jaccard (not full semantic)
- No automatic supersession detection (requires explicit comparison)

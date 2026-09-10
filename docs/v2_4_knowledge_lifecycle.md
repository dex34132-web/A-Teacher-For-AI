# EVO V2.4.2 — Knowledge Lifecycle Hardening

**Date:** 2026-09-10
**Status:** COMPLETED
**Previous:** V2.4.0

## Overview

V2.4.2 hardens the knowledge lifecycle system from V2.4.0 with:
- Automatic maintenance with configurable interval
- Multi-signal merging (input similarity, output similarity, evidence quality)
- Deterministic behavior for reproducibility
- Backward compatibility with V2.4.0 persistence
- 22 new adversarial tests

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

Safe consolidation with multi-signal analysis:
1. Detect memories with same underlying knowledge
2. Require high output similarity (default >0.8)
3. Require input similarity (default >0.6)
4. Require minimum combined evidence (default ≥2)
5. Never merge if one has many failures and other doesn't
6. Preserve provenance (memory IDs of source memories)

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
    maintenance_interval_hours=24.0,  # Hours between maintenance cycles
    merge_input_similarity=0.6,  # Input similarity for merging
    merge_min_evidence=2,      # Minimum combined evidence for merging
)
```

## Automatic Maintenance

V2.4.2 adds automatic lifecycle maintenance:

```python
from core.learner.lifecycle_manager import LifecycleManager

manager = LifecycleManager(config)

# Check if maintenance is due
if manager.needs_maintenance:
    record = manager.run_maintenance(memory)
    print(f"Processed {record.memories_processed} memories")

# Force maintenance (ignore interval)
record = manager.run_maintenance(memory, force=True)

# Manual trigger
results = manager.process_all(memory)  # Legacy API
```

Maintenance is idempotent - running multiple times with no new evidence
should not repeatedly damage the same memory.

## Deterministic Behavior

V2.4.2 supports deterministic testing with a custom clock:

```python
clock_value = 1000000.0
clock = lambda: clock_value

manager = LifecycleManager(config, clock=clock)
# All operations use the provided clock for reproducibility
```

## Backward Compatibility

V2.4.2 is backward compatible with:
- V2.4.0 persisted state (missing fields get defaults)
- V2.3.4 confidence system (preserved)
- V1/V2 basic functionality

New persistence fields:
- `maintenance_interval_hours` (default: 24.0)
- `merge_input_similarity` (default: 0.6)
- `merge_min_evidence` (default: 2)
- `last_reinforced` (per memory)
- `last_decayed` (per memory)
- `lifecycle_metadata.json` (version tracking)

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

- 592 tests passing (22 new V2.4.2 adversarial tests)
- 13 original adversarial tests passing
- Backward compatible with V2.3.4 and V2.4.0
- Tested with 100, 500, and 1000+ memory populations

### Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Lifecycle core | 32 | ✓ |
| V2.4 adversarial | 13 | ✓ |
| V2.4.2 adversarial | 22 | ✓ |
| Maintenance | 4 | ✓ |
| Persistence | 3 | ✓ |
| Deterministic | 2 | ✓ |
| Provenance | 2 | ✓ |

## Known Limitations

- Semantic similarity for merging uses token-level Jaccard (not full semantic)
- No automatic supersession detection (requires explicit comparison)
- Maintenance interval is time-based, not event-based
- Large memory sets (1000+) may have O(N²) merge candidate detection

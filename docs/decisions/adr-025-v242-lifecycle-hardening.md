# ADR-025: V2.4.2 Knowledge Lifecycle Hardening

**Date:** 2026-09-10
**Status:** Accepted
**Deciders:** Lerev Team

## Context

V2.4 introduced a knowledge lifecycle system with states (ACTIVE, UNCERTAIN, SUPERSEDED, ARCHIVED), health computation, reinforcement, decay, supersession, merging, redundancy detection, and archival. While functional, the implementation had several gaps:

1. **No automatic maintenance** — Lifecycle processing required manual calls
2. **Simplistic merging** — Only used output similarity, ignored input similarity and evidence quality
3. **Non-deterministic behavior** — Used `time.time()` everywhere, making tests non-reproducible
4. **Missing persistence metadata** — No version tracking for backward compatibility
5. **Insufficient test coverage** — Only 13 adversarial tests

## Decision

Upgrade V2.4 to V2.4.2 with the following improvements:

### 1. Automatic Maintenance

- Added `maintenance_interval_hours` configuration (default: 24 hours)
- Added `run_maintenance()` method with `force` parameter
- Added `needs_maintenance` property for checking if maintenance is due
- Maintenance is idempotent — running multiple times doesn't damage memories
- Added `MaintenanceRecord` for tracking maintenance history

### 2. Multi-Signal Merging

- Added `merge_input_similarity` configuration (default: 0.6)
- Added `merge_min_evidence` configuration (default: 2)
- Merging now requires:
  - High output similarity (existing)
  - Sufficient input similarity (new)
  - Minimum combined evidence (new)
  - Compatible failure history (new)

### 3. Deterministic Behavior

- Added optional `clock` parameter to `LifecycleManager`
- All time-dependent operations use the clock function
- Default to `time.time` for production use
- Enables reproducible testing with fixed clock values

### 4. Persistence Improvements

- Added `lifecycle_metadata.json` with version tracking
- Added `last_reinforced` and `last_decayed` fields per memory
- Backward compatible with V2.4.0 (missing fields get defaults)
- Version string: "2.4.2"

### 5. Enhanced Test Coverage

- Added 22 new adversarial tests covering:
  - Duplicate memory floods
  - Repeated success/failure floods
  - Stale high-quality vs recent low-quality memories
  - Contradictory memories
  - Semantic near-duplicates
  - Related-but-distinct memories
  - Poisoned feedback
  - Conflicting feedback
  - Archive/recovery cycles
  - Repeated maintenance (idempotency)
  - Persistence corruption/backward compatibility
  - Large memory populations (100, 500)
  - Mixed-quality populations
  - Deterministic behavior
  - Maintenance intervals
  - Provenance tracking

## Consequences

### Positive

- **Reproducibility** — Deterministic testing with custom clocks
- **Safety** — Multi-signal merging reduces false merges
- **Automation** — Automatic maintenance reduces manual overhead
- **Compatibility** — Backward compatible with V2.4.0
- **Confidence** — 22 new adversarial tests improve reliability

### Negative

- **Complexity** — More configuration options to understand
- **Performance** — Input similarity computation adds O(N²) cost for merging
- **Memory** — Additional metadata per memory (last_reinforced, last_decayed)

### Risks

- **Maintenance overhead** — Automatic maintenance may run when not needed
- **Merge aggressiveness** — Multi-signal requirements may miss valid merges
- **Clock dependence** — Custom clocks may behave differently in production

## Alternatives Considered

1. **Event-based maintenance** — Triggered by specific events instead of time
   - Rejected: More complex, harder to predict, may miss important cycles

2. **Semantic similarity for merging** — Use dense embeddings instead of token Jaccard
   - Rejected: Requires semantic encoder, adds dependency, token Jaccard sufficient for V2.4.2

3. **Background maintenance threads** — Run maintenance in background
   - Rejected: Adds complexity, may interfere with main operations, premature optimization

## Validation

- All 592 tests passing
- 22 new adversarial tests covering edge cases
- Backward compatibility verified with V2.4.0 persistence
- Deterministic behavior verified with custom clocks
- Large memory populations tested (100, 500, 1000+)
- No V2.3.4 confidence regression

## References

- V2.4 Knowledge Lifecycle: `docs/v2_4_knowledge_lifecycle.md`
- ADR-024: V2.4 Knowledge Lifecycle (original)
- ADR-022: V2.3.3 Confidence Validation
- ADR-021: V2.3.2 Confidence System Overhaul

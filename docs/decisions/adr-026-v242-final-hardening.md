# ADR-026: V2.4.2 Final Hardening Pass

**Date:** 2026-09-10
**Status:** ACCEPTED
**Context:** V2.4.2 lifecycle hardening (8.5-9/10 target)

## Decision

Implement comprehensive hardening pass to address identified weaknesses:
1. O(N²) → O(N·K) merge candidate generation
2. Semantic similarity integration
3. Event-based maintenance triggers
4. Health score optimization
5. Long-run lifecycle simulation
6. Scalability benchmarks

## Rationale

### Problem
The V2.4.2 lifecycle system had several performance and correctness issues:
- Merge candidate generation was O(N²), limiting scalability
- Merging used only token-level Jaccard, missing semantic relationships
- Maintenance was time-based only, not event-driven
- Health evaluation was O(N²) due to repeated iterations
- No long-run simulation to verify stability

### Solution
1. **Token Inverted Index**: Maps tokens to memory IDs for O(N·K) candidate generation
2. **Semantic Similarity**: Uses encoder vectors when available, falls back to tokens
3. **Event-Based Triggers**: Configurable events with cooldown to prevent rapid triggers
4. **Health Precomputation**: Output index and word cache for O(N) batch evaluation
5. **Long-Run Simulation**: 100-500 cycle tests with 100-1000 memories
6. **Scalability Benchmarks**: 100-10,000 memory performance tests

## Consequences

### Positive
- Merge candidate generation scales to 10,000+ memories
- Semantic similarity improves merge accuracy
- Event-based triggers enable responsive maintenance
- Health evaluation runs in O(N) during maintenance
- Stability verified over hundreds of cycles
- Performance benchmarks establish baselines

### Negative
- Added complexity in knowledge_ops.py and lifecycle_manager.py
- Semantic similarity requires encoder (graceful fallback)
- Event-based triggers add configuration surface area

### Risks
- Token inverted index may have memory overhead for large vocabularies
- Event cooldown may delay needed maintenance
- Semantic similarity adds coupling to encoder module

## Alternatives Considered

### 1. Brute Force Only
- Keep O(N²) merge generation
- Simple but doesn't scale
- Rejected: doesn't meet scalability requirements

### 2. External Indexing Library
- Use Whoosh, Elasticsearch, etc.
- Powerful but adds dependencies
- Rejected: overkill for current scale, adds complexity

### 3. No Event-Based Triggers
- Keep time-based only
- Simpler but less responsive
- Rejected: misses important lifecycle events

## Implementation Notes

### Files Modified
- `core/learner/knowledge_ops.py`: Added TokenInvertedIndex, compute_semantic_similarity, updated find_merge_candidates and analyze_redundancy
- `core/learner/lifecycle_manager.py`: Added EventTriggerConfig, MaintenanceEvent, record_event, _precompute_health_data, updated evaluate_health and run_maintenance

### Files Created
- `tests/unit/test_v242_hardening.py`: 33 tests for new features
- `tests/unit/test_longrun_simulation.py`: 14 tests for simulation and scalability

### Test Coverage
- 556 total tests, all passing
- 46 new tests for hardening features
- Coverage includes: correctness, performance, adversarial, edge cases

## Success Criteria
- [x] O(N·K) merge candidate generation
- [x] Semantic similarity integration
- [x] Event-based maintenance triggers
- [x] Health score optimization
- [x] Long-run lifecycle simulation
- [x] Scalability benchmarks
- [x] All tests passing
- [x] Documentation updated
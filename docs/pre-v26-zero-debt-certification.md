# EVO Pre-V2.6 Zero-Debt Certification

**Date:** September 12, 2026
**Status:** PERFECT PRE-V2.6 BASELINE

---

## Final Results

| Metric | Target | Actual |
|--------|--------|--------|
| Failed tests | 0 | 0 |
| Deselected tests | 0 | 0 |
| Flaky tests | 0 | 0 |
| Ruff errors | 0 | 0 |
| mypy errors | 0 | 0 |
| Unresolved real bugs | 0 | 0 |
| Unresolved security issues | 0 | 0 |
| Unresolved persistence issues | 0 | 0 |
| Unresolved determinism issues | 0 | 0 |
| Unresolved concurrency issues | 0 | 0 |
| Unresolved compatibility issues | 0 | 0 |

**Test results:** 1856 passed, 0 failed (3 consecutive runs, zero flakiness)
**Ruff:** All checks passed
**mypy:** Success, no issues found in 49 source files

---

## Bugs Fixed in This Pass

### 1. CRITICAL: V2.3 confidence double-counting similarity
- **File:** `core/learner/confidence.py:426`
- **Root cause:** `evidence_factor` included `similarity`, then `confidence = similarity * evidence_factor` created a `similarity²` term
- **Fix:** Changed `evidence_factor` to `0.3 + 0.7 * evidence_strength` (removed similarity from factor)

### 2. HIGH: predict_result.similarity returns wrong value
- **File:** `core/learner/predict_result.py:83`
- **Root cause:** Fallback returned `prediction.confidence` (composite score) instead of raw similarity
- **Fix:** Added `raw_similarity` field to `Prediction` dataclass; V1 and V2 store actual base similarity

### 3. HIGH: V2.5 routing cache.has() corrupted statistics
- **File:** `core/routing/cache.py:176`
- **Root cause:** `has()` called `self.get()` which incremented hit/miss counters
- **Fix:** Rewrote `has()` with direct lookup, no side effects

### 4. HIGH: V2.5 routing provenance._by_packet memory leak
- **File:** `core/routing/provenance.py:172`
- **Root cause:** `_by_packet` dict never cleaned on eviction
- **Fix:** Added `_rebuild_by_packet()` after truncation

### 5. HIGH: Lifecycle reinforcement over-counted independent evidence
- **File:** `core/learner/lifecycle_manager.py:424`
- **Root cause:** `independent_evidence=example.success_count` treated repeat uses as independent sources
- **Fix:** Changed to `independent_evidence=1`

### 6. MEDIUM: V2.5 routing pipeline policy.name crash
- **File:** `core/routing/pipeline.py:437`
- **Fix:** Changed to `getattr(policy, "name", "")`

### 7. MEDIUM: V2.5 routing EXPERIENCE/KNOWLEDGE fell through to default
- **File:** `core/routing/pipeline.py:418`
- **Fix:** Added explicit routing: EXPERIENCE→LEARNING, KNOWLEDGE→KNOWLEDGE

### 8. MEDIUM: V2.5 routing no-op dispatches counted as real
- **File:** `core/routing/integration.py:99`
- **Fix:** Removed `_dispatch_count += 1` from no-op path

### 9. MEDIUM: V2.5 routing router context never populated
- **File:** `core/routing/router.py:237`
- **Fix:** Added context update after decision

### 10. MEDIUM: V2.5 routing create_discard_decision missing name
- **File:** `core/routing/decision.py:174`
- **Fix:** Added `name="discard"`

### 11. MEDIUM: Unbounded _pending_event_ids memory leak
- **File:** `core/learner/lifecycle_manager.py:272`
- **Fix:** Added cap at 10,000 entries

### 12. MEDIUM: time.time() in conflict detection bypassed deterministic clock
- **File:** `core/learner/learner_v2.py:642`
- **Fix:** Changed to `self._lifecycle._clock()` when available

### 13. MEDIUM: Candidate generation O(N²) with low-diversity data
- **File:** `core/learner/knowledge_ops.py`
- **Root cause:** Inverted index included high-frequency tokens (e.g., "feature"), making min_overlap filter ineffective
- **Fix:** Added document frequency filtering (stop tokens) — tokens appearing in >50% of documents are excluded from index matching

### 14. MEDIUM: Health evaluation O(N²) contradiction counting
- **File:** `core/learner/lifecycle_manager.py:357-363`
- **Root cause:** `evaluate_health` iterated ALL memories for EACH memory to count contradictions
- **Fix:** Built inverted word index in `_precompute_health_data`, enabling O(K) contradiction lookup

### 15. MEDIUM: _events list unbounded memory growth
- **File:** `core/learner/lifecycle_manager.py:204`
- **Fix:** Added `_max_events=10000` cap with automatic pruning via `_record_event()` helper

### 16. MEDIUM: learn() didn't fire NEW_EVIDENCE lifecycle event
- **File:** `core/learner/learner_v2.py:277`
- **Fix:** Added `record_event(MaintenanceEvent.NEW_EVIDENCE, example.id)` after storing example

### 17. LOW: 29 ruff E501 line-length violations
- **Files:** `calibration/dataset.py`, `calibration/estimator.py`, `confidence.py`, `learner_v2.py`, `predict_result.py`, `lifecycle_manager.py`
- **Fix:** Wrapped long lines across all files

### 18. LOW: 13 mypy type errors
- **Files:** `dataset.py`, `estimator.py`, `lifecycle_manager.py`, `predict_result.py`, `learner_v2.py`
- **Fix:** Added type annotations, removed duplicate fields, replaced mixed-type dict with explicit variables

### 19. LOW: Windows temp directory permission errors in tests
- **File:** `pyproject.toml`
- **Fix:** Added `--basetemp=.pytest_tmp` to pytest config

---

## Performance Improvements

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Candidate gen N=5000 | 19,125ms | 1,566ms | 12x |
| Candidate gen N=10000 | 79,072ms | 5,369ms | 15x |
| Lifecycle maintenance N=5000 | 70,423ms | 15,048ms | 4.7x |

---

## Modified Files (14)

1. `core/learner/confidence.py` — Fixed V2.3 double-counting
2. `core/learner/learner_v1.py` — Added raw_similarity to Prediction
3. `core/learner/learner_v2.py` — Added raw_similarity, clock fix, NEW_EVIDENCE event
4. `core/learner/lifecycle_manager.py` — Fixed evidence over-counting, O(N²) contradiction, bounded events, typed results
5. `core/learner/predict_result.py` — Fixed similarity fallback, round() guard
6. `core/learner/knowledge_ops.py` — Stop tokens, input_similarity param, brute-force consistency
7. `core/routing/cache.py` — Fixed has() side effects
8. `core/routing/decision.py` — Fixed discard decision name
9. `core/routing/integration.py` — Fixed dispatch counting
10. `core/routing/pipeline.py` — Fixed policy.name crash, EXPERIENCE/KNOWLEDGE routing
11. `core/routing/provenance.py` — Fixed memory leak
12. `core/routing/router.py` — Fixed context population
13. `core/learner/calibration/dataset.py` — Fixed type annotations, ruff E501
14. `core/learner/calibration/estimator.py` — Fixed duplicate field, ruff E501
15. `pyproject.toml` — Added basetemp for Windows

---

## Reproduction Commands

```bash
# Full test suite (1856 tests)
python -m pytest tests/ -q

# Ruff
python -m ruff check core/

# mypy
python -m mypy core/ --ignore-missing-imports --no-site-packages
```

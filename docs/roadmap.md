# Roadmap

## Phase 0 — Infrastructure ✓
- [x] Project structure
- [x] Core interfaces (ABCs)
- [x] Adapter stubs
- [x] Documentation framework
- [x] Git setup

## Phase 1 — Basic Learning Prototype ✓
- [x] Implement minimal Learner (SimilarityLearner)
- [x] Implement in-memory ExampleMemory
- [x] FeatureExtractor with TF-IDF
- [x] Cosine similarity + weighted voting prediction
- [x] Feedback-driven weight updates
- [x] Save/load persistence
- [x] Unit tests for core learner
- [x] Benchmark suite (9 tests, all passing)

## Phase 1.1 — Audit & Scientific Validation ✓
- [x] Smoothed IDF formula: `log(1 + N/(df+1))`
- [x] Dynamic IDF application (TF-only storage, IDF at comparison time)
- [x] Conservative feedback weights (+0.05/-0.1, floor 0.3)
- [x] No duplicate correction examples
- [x] Multi-factor confidence (vote share + margin + support + avg similarity)
- [x] Benchmark suite expanded to 13 tests, all passing
- [x] All documentation updated with honest audit findings
- [x] V1 is now **scientifically validated** — all claims backed by reproducible benchmarks

### V1.1 Benchmark Results

| Benchmark | Result |
|-----------|--------|
| Classification: Known | 100% (3/3) |
| Classification: Unseen | 100% (10/10) |
| Similarity: Grouped Retrieval | 100% (4/4) |
| Learning: Stability | 90-100% (within 20% tolerance) |
| Adaptation: Answer Change | 100% (5/5) |
| Retention: Save/Load | Exact match |
| Confidence: Quality | 0.807 known, 0.803 unseen |
| Regression: No Loss | 100% maintained |
| Regression: Final Accuracy | 100% (6/6) |
| Learning Curve | 0→20→40→100→90→90% |
| Feedback: Improvement | 4/4 before and after |
| Feedback: Resistance | 100% retention after 5 bad rounds |
| Persistence: Exact Preservation | Output + confidence match |

## Phase 2 — Semantic Learning ✓
- [x] SemanticEncoder pluggable interface (ABC)
- [x] FastEmbedEncoder implementation (BAAI/bge-small-en-v1.5, 384-dim)
- [x] HybridMemory extending ExampleMemory with semantic vector storage
- [x] HybridSimilarityLearner (V2) combining lexical + semantic similarity
- [x] Configurable lexical/semantic weight ratio
- [x] Graceful fallback to V1 when no semantic encoder available
- [x] Semantic benchmark datasets (4 datasets: paraphrase, synonym, technical, mixed)
- [x] V1 vs V2 comparative benchmarks
- [x] V2 feedback, persistence, regression tests
- [x] V2 save/load with semantic vectors
- [x] All 254 tests passing, ruff clean, mypy clean
- [x] Research documented (FastEmbed decision, ADR-016)

### V2 Architecture

```
SimilarityLearner (V1)          HybridSimilarityLearner (V2)
├── FeatureExtractor (TF-IDF)   ├── FeatureExtractor (TF-IDF) [same]
├── ExampleMemory               ├── HybridMemory [extended]
├── cosine_similarity           ├── cosine_similarity [same]
└── weighted_similarity         ├── dense_cosine_similarity [new]
                                ├── SemanticEncoder (pluggable)
                                │   └── FastEmbedEncoder (default)
                                └── RetrievalScorer (optional, V2.1)
                                    ├── quality_score()
                                    ├── recency_score()
                                    └── diversify_top_k()
```

### V2 Benchmark Results

| Metric | V1 | V2 | Notes |
|--------|----|----|-------|
| Memorization | 100% | 100% | V2 matches V1 |
| Paraphrase recognition | Low | High | Semantic similarity captures meaning |
| Synonym recognition | Low | High | Dense vectors capture synonyms |
| Feedback handling | ✓ | ✓ | Same conservative weights |
| Persistence | ✓ | ✓ | Saves semantic vectors |
| Graceful degradation | N/A | ✓ | Falls back to V1 without encoder |

## Phase 2.1 — Smarter Memory Retrieval ✓
- [x] HybridExample metadata: created_at, last_used_at, use_count, success_count, failure_count
- [x] HybridMemory usage tracking: record_use, record_success, record_failure, get_usage_stats
- [x] RetrievalScorer: quality_score, recency_score, retrieval_score, diversify_top_k
- [x] ScorerConfig with sensible defaults (q=0.1, r=0.05, diversity=0.9)
- [x] Integration into HybridSimilarityLearner (optional, backward compatible)
- [x] Usage tracking in predict (record_use) and feedback (record_success/record_failure)
- [x] V2.1 persistence: scorer config saved/loaded, metadata backward compatible with V1/V2
- [x] Unit tests (43 tests): metadata, usage tracking, scorer functions, diversity
- [x] Adversarial safety tests (13 tests): quality cannot override relevance
- [x] Integration tests (13 tests): end-to-end V2.1 pipeline
- [x] V2.1 benchmarks: V1 vs V2.0 vs V2.1 comparison
- [x] ADR-017 documented
- [ ] Pattern extraction from interactions
- [ ] Context-aware suggestions
- [ ] Expand benchmark suite to cover more scenarios
- [ ] TF-IDF vocabulary pruning (min_df, max_df)
- [ ] Feature vector normalization strategy

## Phase 2.2 — Conflict & Contradiction Handling ✓
- [x] ConflictState enum (NONE/POSSIBLE/CONFIRMED/RESOLVED/UNRESOLVED)
- [x] Evidence dataclass (relevance, success_rate, recency, weight)
- [x] Conflict dataclass (involved_ids, outputs, strength, evidence, selected_output)
- [x] ConflictConfig (input_similarity_threshold, output_equality_threshold, evidence_margin, context_similarity_threshold, min_evidence_samples)
- [x] detect_conflicts() — input similarity + output disagreement detection
- [x] gather_evidence() — build Evidence list from memory metadata
- [x] compare_evidence() — evidence scoring and resolution
- [x] PredictResult wrapper with conflict info (has_conflict, is_resolved, is_unresolved, conflicting_outputs, summary())
- [x] predict() returns PredictResult; predict_legacy() returns raw Prediction
- [x] Integration into HybridSimilarityLearner (optional, backward compatible)
- [x] Zero-relevance candidates excluded from conflict detection
- [x] Persistence: conflict config saved/loaded, backward compatible
- [x] Unit tests (29 tests): conflict detection, evidence, PredictResult
- [x] Adversarial safety tests (11 tests): false conflicts, alternating feedback, edge cases
- [x] Integration tests (16 tests): end-to-end V2.2 pipeline
- [x] V2.2 benchmarks: V2.0 vs V2.1 vs V2.2 comparison (10/10 pass)
- [x] ADR-018 documented
- [ ] Multi-hop conflict detection
- [ ] Temporal conflict resolution
- [ ] Confidence calibration across conflict states

## Phase 2.3 — Confidence & Uncertainty ✓
- [x] ConfidenceConfig (prior_strength, agreement_weight, max_conflict_penalty, min_evidence_samples, novelty_penalty_threshold, novelty_penalty_strength)
- [x] bayesian_evidence_strength() — smoothed success rate with prior
- [x] compute_agreement() — weight + count agreement among neighbors
- [x] compute_conflict_penalty() — penalty from output disagreement
- [x] detect_conflict_count() — relevance-aware conflict detection
- [x] classify_uncertainty_state() — confident/uncertain/insufficient_evidence/conflicted
- [x] estimate_confidence() — main entry point with all components
- [x] ConfidenceResult dataclass with explainable components
- [x] PredictResult updated with confidence_result, uncertainty_state, similarity, confidence_components
- [x] Integration into HybridSimilarityLearner (optional, backward compatible)
- [x] Persistence: confidence config saved/loaded, backward compatible
- [x] Unit tests (42 tests): Bayesian evidence, agreement, conflict penalty, uncertainty states
- [x] Adversarial safety tests (15 tests): duplicates, irrelevant memories, alternating feedback
- [x] Integration tests (15 tests): end-to-end V2.3 pipeline, backward compatibility
- [x] V2.3 benchmarks: V2.0 vs V2.1 vs V2.2 vs V2.3 comparison (13/14 pass)
- [x] ADR-019 documented

## Phase 2.3.1 — Confidence Calibration Audit ✓
- [x] Formula verification: mathematical correctness, monotonicity verified
- [x] Root cause analysis: lexical_weight cap, conflict over-triggering, small benchmark
- [x] Fix detect_conflict_count relevance_threshold (0.1 → 0.5)
- [x] Re-run diagnostics: Brier 0.54→0.38, conflicts 72%→5%
- [x] ADR-020 documented
- [x] Verdict: V2.3 formula is correctly calibrated, no rewrite needed

## Phase 2.3.2 — Confidence System Overhaul ✓
- [x] Phase 1: Full audit — identified quadratic compounding, evidence_strength prior, single-memory evidence as bottlenecks
- [x] Phase 2: Fix output_similarities bug — learner_v2.py now passes actual blended similarities for conflict detection
- [x] Phase 3: New estimator formula — `confidence = similarity × evidence_quality × agreement_factor - penalties`
- [x] Phase 4: Removed quadratic compounding (0.3 × sim² → direct sim × ev_quality)
- [x] Phase 5: Aggregated evidence across ALL supporting memories (not just best)
- [x] Phase 6: Added failure_dominance_penalty (0.30)
- [x] Phase 7: Lowered prior_strength (4.0 → 2.0) for faster evidence convergence
- [x] Phase 8: Stronger conflict penalty (max 0.40 → 0.50)
- [x] Phase 9: Agreement only counts with >50% majority (no agreement on 50/50 splits)
- [x] Calibration infrastructure: estimator.py, calibrator.py, metrics.py, dataset.py
- [x] Adversarial robustness: 7/7 tests pass (was 3/7 before)
- [x] Unit tests: 34 new estimator tests, all passing
- [x] Adversarial regression tests: 7 tests in test suite
- [x] Large benchmark: 134 training, 144 test cases
- [x] Selective prediction: 99.1% accuracy at conf≥0.4 (80.6% coverage)
- [x] All 506 tests passing, ruff clean
- [x] ADR-021 documented

## Phase 2.3.3 — Confidence Validation and Integration ✓
- [x] Phase 1: Full audit — traced V2.3.2 integration, identified dead code, calibration bug, agreement bug
- [x] Phase 2: Integrated V2.3.2 into learner (use_v232 flag, default True)
- [x] Phase 3: Fixed calibrator interpolation bug
- [x] Phase 4: Fixed agreement bonus gating (no bonus when similarity=0)
- [x] Phase 5: Added uncertainty_state to ConfidenceEstimatorResult
- [x] Phase 6: Expanded ConfidenceConfig with V2.3.2 parameters
- [x] Phase 7: Fixed PredictResult.summary() evidence_factor → evidence_quality
- [x] Phase 8: Fixed persistence bug (load_state is classmethod)
- [x] Phase 9: Comprehensive evaluation framework (12 dataset categories A-L)
- [x] Phase 10: Version comparison V2.0-V2.3.2 on Dataset A
- [x] Phase 11: Selective prediction metrics at 0.5/0.7/0.9 thresholds
- [x] Phase 12: ADR-022 documented
- [x] All 506 tests passing, ruff clean
- [x] Evaluation: V2.3.2 Brier=0.000, ECE=0.002 on normal data (best version)

## Phase 3 — Feedback and Evaluation
- [ ] Feedback collection interface
- [ ] Evaluation metrics implementation
- [ ] Regression detection
- [ ] Learning rate measurement

## Phase 4 — Persistent Memory
- [ ] File-based storage backend
- [ ] SQLite storage backend
- [ ] Memory lifecycle management
- [ ] Cross-session persistence

## Phase 5 — Web Knowledge Acquisition
- [ ] Search provider abstraction
- [ ] Content fetcher with safety checks
- [ ] Source quality evaluation
- [ ] Documentation resolver

## Phase 6 — Advanced Learning Algorithms
- [ ] Multi-factor learning
- [ ] Confidence scoring improvements
- [ ] Knowledge graph construction
- [ ] Experimental algorithms (in experiments/)

## Phase 7 — OpenCode Plugin
- [ ] OpenCode adapter implementation
- [ ] Plugin packaging
- [ ] Integration tests
- [ ] Documentation

## Phase 8 — Claude Code Adapter
- [ ] Claude Code adapter implementation
- [ ] Adaptation for Claude-specific features
- [ ] Integration tests

## Phase 9 — Codex Adapter
- [ ] Codex adapter implementation
- [ ] Adaptation for Codex-specific features
- [ ] Integration tests

## Phase 10 — Other Harnesses
- [ ] Generic adapter improvements
- [ ] Community adapter guidelines
- [ ] Adapter SDK documentation

## Success Criteria

- [x] Core learner implemented and passing benchmarks
- [x] V1.1 audit completed — all claims scientifically validated
- [x] All core interfaces have implementations
- [ ] All adapters pass integration tests
- [ ] Benchmarks show measurable improvement
- [ ] Documentation is complete
- [ ] Security model is validated

---

## V2.3.4 — Probabilistic Confidence System

**Date:** 2026-09-10
**Status:** COMPLETED

### What was done

1. **Probabilistic semantics** — Confidence values now represent estimated probability of correctness
   - `ConfidenceBand` enum: HIGH (≥0.8), MODERATE (≥0.6), LOW (≥0.4), WEAK (≥0.2), MINIMAL (<0.2)
   - `confidence_to_probability()` function
   - Both result types include `probability` and `band` fields

2. **Semantic matching enabled** — Default weights changed to lexical=0.4, semantic=0.6
   - Uses fastembed for 384-dimensional embeddings
   - Handles paraphrases better (at cost of exact-match accuracy)

3. **Improved abstention** — Multi-signal abstention with 3 rules:
   - Low confidence (< threshold)
   - Insufficient evidence with low similarity (< 0.3)
   - Conflicted predictions

4. **500+ case benchmark** — `benchmarks/v2_3_4_benchmark.py`
   - 14 categories (A-N), 500+ cases
   - 4-way split: CAL (148) / VAL (148) / HELD-OUT (204)
   - No overlap between splits
   - Isotonic calibration trained on CAL, evaluated on HELD-OUT

### Results

- Isotonic Brier: 0.0049 (excellent)
- Isotonic ECE: 0.0049 (excellent)
- 525 tests passing, ruff clean

### Next steps

- V2.5: Vector memory for 1000+ memories
- V3.1: Neural confidence head (PyTorch)
- More training data to improve accuracy

---

## V2.4 — Knowledge Lifecycle

**Date:** 2026-09-10
**Status:** COMPLETED

### What was done

1. **Lifecycle states** — ACTIVE, UNCERTAIN, SUPERSEDED, ARCHIVED
2. **Memory health model** — 7 signals with documented purposes
3. **Knowledge reinforcement** — Diminishing returns, independence bonus
4. **Knowledge decay** — Evidence-adjusted rate, configurable floor
5. **Knowledge supersession** — Evidence comparison, not timestamp comparison
6. **Knowledge merging** — Safe consolidation with provenance preservation
7. **Redundancy detection** — 5-level classification
8. **Archiving** — Never delete, always recoverable
9. **Provenance** — Every state transition tracked
10. **Persistence** — Lifecycle state survives save/load

### Results

- 570 tests passing (45 new lifecycle tests)
- 13 adversarial tests passing
- Backward compatible with V2.3.4
- No V2.3.4 confidence regression

### Next steps

- V2.4.2: Lifecycle hardening (completed)
- V2.5: Vector memory for 1000+ memories
- V3.1: Neural confidence head (PyTorch)

---

## V2.4.2 — Knowledge Lifecycle Hardening

**Date:** 2026-09-10
**Status:** COMPLETED

### What was done

1. **Automatic maintenance** — Configurable interval, idempotent execution
2. **Multi-signal merging** — Input similarity, output similarity, evidence quality
3. **Deterministic behavior** — Custom clock for reproducible tests
4. **Backward compatibility** — V2.4.0 persistence loads with defaults
5. **Provenance tracking** — All mutations traceable with timestamps
6. **Redundancy detection** — Improved with input similarity
7. **Adversarial testing** — 22 new tests covering edge cases
8. **Large-scale testing** — 100, 500, 1000+ memory populations

### Results

- 592 tests passing (22 new V2.4.2 tests)
- All V2.3.4 confidence tests pass
- All V2.4 lifecycle tests pass
- Backward compatible with V2.4.0

### Next steps

- V2.5: Vector memory for 1000+ memories
- V3.1: Neural confidence head (PyTorch)
- Event-based maintenance triggers

# V2.3.3 Independent Calibration Audit

**Date:** 2026-09-10
**Auditor:** Independent verification (V2.3.3 audit)
**Status:** COMPLETE

---

## 1. Verdict

**VERIFIED WITH CAVEATS**

The V2.3.3 confidence system is mathematically correct and the production algorithm is sound. However, the previously reported metrics (Brier=0.000, ECE=0.002) were **invalid** due to a benchmark design flaw: 100% train/test overlap in Dataset A. With proper independent evaluation, the real metrics are significantly worse but still reasonable for a lexical-only system.

---

## 2. Metric Verification

### Independent vs Production Metrics

| Metric | Independent | Production | Match |
|--------|-------------|------------|-------|
| Brier | 0.085000 | 0.085000 | YES |
| ECE | 0.170000 | 0.170000 | YES |

The production metric implementations are mathematically correct and match independent reference implementations exactly.

### Real Metrics (Independent Audit)

| Metric | Value |
|--------|-------|
| Brier (raw) | 0.3971 |
| Brier (calibrated) | 0.3827 |
| ECE (raw) | 0.4437 |
| ECE (calibrated) | 0.4155 |
| Accuracy | 0.6000 |
| Coverage | 0.9000 |
| Abstention rate | 0.1000 |

### Updated Existing Benchmark (Fixed Overlap)

| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| Dataset A Brier | 0.000 | 0.129 |
| Dataset A ECE | 0.000 | 0.184 |
| Aggregate Brier | 0.095 | 0.139 |
| Aggregate ECE | 0.107 | 0.170 |

---

## 3. Leakage Analysis

### Train/Test Leakage: **FOUND AND FIXED**

The original Dataset A used the **exact same queries** for training and testing:

```python
# Original (BUGGY):
train.extend([{"input": q, "output": output} for q in queries])
test.extend([(q, output) for q in queries])  # SAME queries!

# Fixed:
test.extend([(q, output) for q in test_paraphrases[cat]])  # PARAPHRASED queries
```

This meant every test query found a perfect match in memory, producing trivially perfect predictions.

### Calibration/Test Leakage: **FOUND (minor)**

When calibration is fitted on evaluation data vs independent data:
- ECE difference: 0.088 (significant)
- Brier difference: 0.010 (small)

This demonstrates that calibration leakage could explain artificially good metrics.

### Label Leakage: **NOT FOUND**

No ground-truth labels were used during prediction.

### Duplicate Contamination: **NOT FOUND**

No test examples appeared in training data after the fix.

### Benchmark Contamination: **NOT FOUND**

No production code conditionals on benchmark data.

### Threshold Tuning Contamination: **NOT FOUND**

Abstention threshold (0.2) was not tuned against the evaluation set.

### Abstention-Induced Metric Distortion: **MINOR**

Abstention removes 10% of predictions (the hardest cases). This slightly improves apparent accuracy but does not explain the 0.000 Brier.

---

## 4. The 0.000 Brier Investigation

### Root Cause

**100% train/test overlap in Dataset A.**

```
Train/test INPUT overlap: 13 / 13 (100%)
```

Every test query was an exact duplicate of a training query. The learner found perfect matches with similarity=1.0 and 100% success rate, producing confidence=1.0 for all predictions. Since all predictions were correct:

```
Brier = mean((1.0 - 1.0)²) = 0.000
```

### Proof

The investigation showed:
- 13 test queries, all exact duplicates of training queries
- All predictions correct with confidence=1.0
- No abstentions occurred (confidence > 0.2 threshold)
- Brier = 0.000 is mathematically correct for this (degenerate) case

### Conclusion

The 0.000 Brier was **not** a production algorithm bug. It was a **benchmark design flaw** — the test set was trivially easy because it consisted entirely of memorized queries.

---

## 5. Independent vs Existing Benchmark

| Metric | Existing (Fixed) | Independent Audit |
|--------|------------------|-------------------|
| Brier | 0.139 | 0.397 |
| ECE | 0.170 | 0.444 |
| Accuracy | 0.569 | 0.600 |

The independent audit shows **worse** calibration because:
1. Test queries are more diverse (novel categories, distribution shift)
2. No calibration tuning on the evaluation set
3. Stricter data separation

The existing benchmark (after fix) shows better metrics because:
1. Test queries are closer paraphrases of training (higher similarity)
2. Calibration is fitted on similar data
3. Fewer novel/out-of-distribution cases

---

## 6. Statistical Confidence

| Dataset | Samples | Assessment |
|---------|---------|------------|
| Independent audit | 30 | **Too small** for reliable statistics |
| Existing benchmark | 65 | **Marginal** — needs 100+ |
| Abstention test | 30 | **Too small** — needs 100+ |

**Warning:** All sample sizes are too small for statistical certainty. The reported metrics should be treated as indicative, not definitive. A proper evaluation needs 500+ samples across diverse categories.

---

## 7. Code Bugs Found

### High Severity

1. **`predict_result.py:59`** — Abstained predictions reported meaningful confidence instead of 0.0. **FIXED.**

2. **`predict_result.py:196`** — `evidence_quality=0.0` silently fell back to wrong value due to `or` operator. **FIXED.**

3. **`estimator.py:91`** — `_evidence_quality` docstring promised asymmetric penalty, code was plain success rate. **Documentation mismatch (not fixed — cosmetic).**

### Medium Severity

4. **`metrics.py:153`** — Empty reliability buckets reported 0.0 accuracy instead of being omitted.

5. **`estimator.py:62`** — Duplicate field definition (dead code).

6. **`predict_result.py:54`** — Empty string `""` for abstention is ambiguous (should use `None`).

### Low Severity

7. **`estimator.py:217`** — Dead variable `normalized` in `_compute_independence_bonus`.

8. **`metrics.py:87`** — Brier score range documented as [0,2], actual is [0,1].

---

## 8. Independence-Aware Evidence

### Duplicates Do NOT Inflate Confidence

| Scenario | Confidence | Independent Evidence |
|----------|------------|---------------------|
| 1 memory | 1.0000 | 1 |
| 3 duplicates | 1.0000 | 1 |
| 10 duplicates | 1.0000 | 1 |
| 30 duplicates | 1.0000 | 1 |

Duplicates are correctly counted as 1 independent piece of evidence.

### Genuine Independent Evidence Is Counted

| Scenario | Confidence | Independent Evidence |
|----------|------------|---------------------|
| 1 independent | 1.0000 | 1 |
| 3 independent | 1.0000 | 3 |
| 5 independent | 1.0000 | 5 |
| 10 independent | 1.0000 | 5 (capped at k=5) |

The independence bonus works correctly.

---

## 9. Abstention Behavior

| Threshold | Coverage | Accuracy | Brier |
|-----------|----------|----------|-------|
| 0.0 | 1.000 | 0.667 | 0.445 |
| 0.1 | 0.967 | 0.667 | 0.445 |
| 0.2 | 0.900 | 0.600 | 0.397 |
| 0.3 | 0.800 | 0.567 | 0.378 |
| 0.5 | 0.700 | 0.467 | 0.361 |
| 0.7 | 0.567 | 0.333 | 0.395 |
| 0.9 | 0.567 | 0.333 | 0.395 |

Abstention does NOT dramatically improve Brier — it primarily reduces coverage. The system is not "gaming" metrics by abstaining from hard cases.

---

## 10. Randomization Stability

All seeds produce identical results (Brier=0.3971, ECE=0.4437). The system is deterministic for lexical-only mode.

---

## 11. Overall Quality Rating

**4/10**

Reasoning:
- The production algorithm is mathematically correct (+2)
- Independence-aware evidence works (+1)
- Abstention mechanism works (+1)
- But: Benchmark was fundamentally flawed (was showing 0.000 Brier) (-2)
- But: Real metrics are mediocre (Brier=0.397, ECE=0.444) (-2)
- But: Sample sizes too small for reliable conclusions (-1)
- But: Multiple code bugs found in audit (-1)

The system works correctly but is not well-calibrated on independent data. The previously reported "perfect" metrics were an artifact of benchmark design, not production quality.

---

## 12. Recommendation

**NEEDS BENCHMARK REPAIR**

The production code is sound but the evaluation infrastructure was compromised. Before proceeding to V2.4:

1. **Expand evaluation to 500+ samples** across diverse categories
2. **Fix remaining code bugs** (empty bucket reporting, abstention sentinel)
3. **Retune calibration** on the fixed benchmark
4. **Re-evaluate all versions** on the fixed benchmark to establish honest baselines

The system is safe to use but the evaluation needs to be rebuilt from scratch with proper data separation.

---

## Appendix: Terminal Summary

```
VERDICT:              VERIFIED WITH CAVEATS
INDEPENDENT BRIER:    0.3971 (raw) / 0.3827 (calibrated)
INDEPENDENT ECE:      0.4437 (raw) / 0.4155 (calibrated)
ACCURACY:             0.6000
COVERAGE:             0.9000
ABSTENTION RATE:      0.1000
LEAKAGE FOUND:        YES — 100% train/test overlap in Dataset A (FIXED)
0.000 BRIER EXPLANATION: Benchmark design flaw — test queries were exact duplicates of training queries
OVERALL RATING:       4/10
RECOMMENDATION:       NEEDS BENCHMARK REPAIR
```

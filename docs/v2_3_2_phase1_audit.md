# V2.3.2 Phase 1 — Full Confidence Audit

## 1. Complete Input Trace

The prediction → confidence pipeline has these inputs:

### From retrieval (learner_v2.py):
- `best_similarity` — blended lexical+semantic similarity of best supporting memory
- `winner_weight` — total vote weight for winning output
- `total_weight` — total vote weight across all outputs  
- `n_support` — number of top-k neighbors voting for winner
- `total_count` — total neighbors (k)
- `outputs` — list of output strings from top-k neighbors
- `output_similarities` — weighted scores from top-k

### From memory (hybrid_memory.py):
- `success_count` — best supporting memory's success count
- `failure_count` — best supporting memory's failure count
- `weight` — example weight (0.3–5.0, adjusted by feedback)

### From feedback loop (learner_v2.py):
- `record_feedback` adjusts weight: +0.05 correct, -0.1 incorrect
- `record_success/failure` updates success_count/failure_count

## 2. Formula Analysis

```
confidence = similarity × evidence_factor + agreement_bonus - conflict_penalty - novelty_penalty
```

### 2a. Evidence factor (THE BOTTLENECK)

```python
evidence_factor = similarity if total_uses == 0 else 0.3 * similarity + 0.7 * evidence_strength
```

This creates: `confidence = similarity × (0.3 × similarity + 0.7 × evidence_strength) + ...`

**Problem**: This is `0.3 × similarity² + 0.7 × similarity × evidence_strength`. The quadratic similarity term means confidence is ALWAYS substantially below similarity × evidence_strength.

Example: similarity=0.8, evidence_strength=1.0
- evidence_factor = 0.3×0.8 + 0.7×1.0 = 0.94
- base = 0.8 × 0.94 = 0.752

Example: similarity=0.9, evidence_strength=1.0  
- evidence_factor = 0.3×0.9 + 0.7×1.0 = 0.97
- base = 0.9 × 0.97 = 0.873

The quadratic term is the primary structural bottleneck. Even with perfect evidence, confidence is capped at `similarity × (0.3 × similarity + 0.7)`.

### 2b. Evidence strength (Bayesian smoothing)

```python
evidence_strength = similarity * (1-w) + observed_rate * w
where w = total / (total + prior_strength=4)
```

With 0 uses: evidence_strength = similarity (prior dominates)
With 4 uses: w = 0.5, evidence_strength = 0.5×sim + 0.5×observed
With 20 uses: w = 0.83, evidence_strength converges to observed_rate

**Issue**: The prior IS the similarity, which means evidence_strength can never be higher than max(similarity, observed_rate). If similarity is 0.4 and observed_rate is 1.0, evidence_strength ≈ 0.83 after 20 uses. This is correct behavior but means low-similarity memories can never fully "prove themselves".

### 2c. Agreement bonus

```python
agreement_bonus = 0.15 × (0.5 × weight_agreement + 0.5 × count_agreement)
```

Max agreement_bonus ≈ 0.15 when all neighbors agree. Small but additive.

### 2d. Conflict penalty

```python
conflict_penalty = min(0.3, runner_up_weight / winner_weight × 0.3)
```

Max penalty 0.3. Only applied when detect_conflict_count > 1.

### 2e. Novelty penalty

```python
novelty_penalty = 0.2 × (1 - similarity / 0.3) when similarity < 0.3
```

Max penalty 0.2 when similarity = 0.

## 3. Identified Bottlenecks

### Bottleneck 1: Quadratic similarity compounding
The `similarity × evidence_factor` formula creates `0.3 × sim² + 0.7 × sim × ev_str`. This caps confidence below what the evidence supports.

### Bottleneck 2: Evidence strength uses similarity as prior
The Bayesian prior IS the similarity, so evidence can never "overcome" low similarity. This is theoretically sound but practically limiting.

### Bottleneck 3: Only best memory's evidence used
`best_success_count` and `best_failure_count` come from the single best supporting memory, not from ALL supporting memories. If the best match has weak evidence but others have strong evidence, this is ignored.

### Bottleneck 4: lexical_weight cap (without semantic encoder)
Blended similarity = 0.4 × lex_sim when no semantic encoder. This caps maximum similarity at 0.4, capping confidence at ~0.45.

### Bottleneck 5: Agreement bonus is too small
Max 0.15 from agreement. With strong agreement (5/5 neighbors), this barely moves the needle.

## 4. Sources of Overconfidence

- None identified in the formula itself. The formula is structurally conservative.

## 5. Sources of Underconfidence

- Bottleneck 1 (quadratic compounding) — primary
- Bottleneck 3 (single-memory evidence) — secondary
- Bottleneck 5 (small agreement bonus) — tertiary

## 6. Interaction Analysis

- **similarity × evidence**: Quadratic interaction suppresses confidence
- **evidence × agreement**: Independent signals, no interaction
- **conflict × agreement**: Conflict penalty can override agreement bonus
- **novelty × similarity**: Novelty penalty applies when similarity < 0.3, further reducing confidence for novel queries

## 7. Theoretical Coherence

The formula is theoretically coherent — it asks the right questions:
1. How similar is this to known knowledge? (similarity)
2. How reliable is the evidence? (evidence_strength)
3. Do neighbors agree? (agreement)
4. Are there credible conflicts? (conflict)
5. Is this a novel situation? (novelty)

The issue is the WEIGHTING, not the CONCEPTS. The quadratic compounding and single-memory evidence are the main structural problems.

## 8. Recommendation

The formula needs restructuring, not just parameter tuning. The key changes needed:

1. **Remove quadratic compounding**: Use `similarity × evidence_strength` directly (not `similarity × (0.3×similarity + 0.7×evidence_strength)`)
2. **Aggregate evidence across ALL supporting memories**: Sum success/failure across all neighbors voting for winner
3. **Increase agreement weight**: Make agreement a stronger signal when evidence is strong
4. **Add a calibration layer**: Post-hoc mapping from raw scores to calibrated probabilities

The V2.3.1 baseline formula should be preserved as a fallback option, but the primary path should use the improved formula.

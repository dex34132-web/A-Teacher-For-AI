# Learning System Design

## Overview

The learning system enables AI coding agents to improve over time by:
1. Learning from feedback and corrections
2. Detecting patterns in interactions
3. Acquiring knowledge from external sources
4. Adapting behavior based on what works

## V1 Implementation: SimilarityLearner

The first implemented learner uses a **TF-IDF + cosine similarity + weighted voting** algorithm. This is not a neural network and does not use gradient descent. It is an online, incremental, nearest-neighbor classifier with feedback-driven weight adjustments.

### What "Learning" Means in This Project

In V1, "learning" means:

1. **Storing input-output pairs** as sparse TF (term frequency) feature vectors
2. **Finding similar past examples** when presented with new input
3. **Voting** among similar examples to produce a prediction
4. **Adjusting weights** based on feedback (correct/incorrect)

The system improves because:
- More examples = broader coverage of the input space
- Feedback weights = reliable examples are trusted more
- TF-IDF = meaningful features that capture term importance (IDF applied dynamically at comparison time)

This is fundamentally different from neural network learning. There is no backpropagation, no gradient descent, no learned weight matrices. It is closer to a memory-based learner (like k-nearest neighbors) than a parametric model.

### Algorithm Step by Step

#### Step 1: Feature Extraction (TF only, IDF applied dynamically)

Raw text is converted to a sparse feature vector:

```
Input: "create a list of numbers"
Tokens: ["create", "list", "numbers"]  (after stop word removal, unigrams + bigrams)
```

For each term, **term frequency** is computed at storage time:

```
tf(t, d) = count(t in d) / len(d)           (term frequency)
```

IDF is **NOT** applied at storage time. Stored vectors contain only raw TF values. IDF weighting is applied lazily during similarity comparison.

#### Step 1b: IDF Formula (Smoothed)

The IDF formula used is the smoothed variant:

```
idf(t) = log(1 + N / (df + 1))
```

Where:
- `N` = total documents seen so far
- `df(t)` = number of documents containing term `t`

Properties:
- **brand-new term** (df=0): `log(1 + N)` — high weight
- **single-document term** (df=1): `log(1 + N/2)` — moderate weight
- **corpus-wide term** (df=N): `log(2) ≈ 0.69` — low weight (not zero)

The `+1` smoothing in the denominator prevents division-by-zero and ensures corpus-wide terms get a low but non-zero weight. The `+1` inside the logarithm prevents negative IDF values. A weight threshold in the similarity function filters out corpus-wide terms.

#### Step 2: Memory Storage

The feature vector (raw TF only) is stored alongside:
- The original input text
- The expected output/label
- An initial weight (default 1.0)
- Feedback counters (feedback_count, correct_count)

#### Step 3: Prediction (Nearest Neighbor + Weighted Voting)

When predicting for new input:

1. Extract TF features for the query (without updating vocabulary)
2. Compute cosine similarity between query and all stored examples, **applying IDF dynamically** at comparison time
3. Multiply similarity by example weight (from feedback)
4. Sort by weighted score, take top-k (default k=5)
5. Each neighbor votes for its output label, weighted by its score
6. Winner is the label with highest total vote weight
7. Confidence is computed from multiple factors (see below)

```
cosine_sim(a, b) = sum(a[t] * idf(t) * b[t] * idf(t)) / (||a_weighted|| * ||b_weighted||)
weighted_score(example) = cosine_sim(query, example.vector) * example.weight
```

#### Step 4: Multi-Factor Confidence

Confidence is not simply vote share. It combines four factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Vote share | 0.40 | Fraction of total weight going to the winner |
| Margin | 0.25 | Relative difference between winner and runner-up |
| Support ratio | 0.20 | Fraction of top-k neighbors that voted for the winner |
| Avg similarity | 0.15 | Average cosine similarity of supporting examples |

```
confidence = vote_share * 0.4 + margin * 0.25 + support_ratio * 0.2 + avg_sim * 0.15
```

This produces more calibrated confidence than vote share alone. A prediction supported by many similar neighbors scores higher than one from a single outlier.

#### Step 5: Feedback-Driven Weight Updates (Conservative)

When feedback is received, example weights are adjusted **conservatively**:

- **Correct prediction**: +0.05 (capped at 5.0)
- **Incorrect prediction**: -0.1 (floored at 0.3)

The minimum weight of 0.3 ensures no example is ever completely silenced by a few rounds of bad feedback. The asymmetric deltas (+0.05 vs -0.1) mean incorrect feedback has twice the impact of correct feedback, but the floor prevents runaway suppression.

#### Step 6: No Duplicate Correction Examples

When incorrect feedback includes the correct output, the system checks whether a correction example already exists for that exact input-output pair before adding a new one. This prevents vocabulary bloat from repeated corrections on the same input.

```python
existing = [ex for ex in memory if ex.input_text == text and ex.output == actual_output]
if not existing:
    memory.add(text, actual_output, ...)
```

### Mathematical Intuition

The system works because:

1. **TF-IDF creates meaningful feature spaces**: Similar texts end up with similar vectors. "create a list" and "make a list" share terms, so their vectors are close.

2. **Cosine similarity measures direction, not magnitude**: Two texts about the same topic point in similar directions in feature space, regardless of length.

3. **Dynamic IDF keeps comparisons consistent**: By applying IDF at comparison time rather than storage time, all vectors in the same comparison use the same IDF weights, even if the vocabulary has grown since they were stored.

4. **Weighted voting reduces noise**: By weighting neighbors by similarity * example confidence, the system trusts its best examples more.

5. **Conservative feedback prevents catastrophic forgetting**: Small weight adjustments (+0.05/-0.1) with a floor of 0.3 mean the system adapts slowly but never completely forgets.

### Known Limitations of V1

1. **No semantic understanding**: "happy" and "joyful" are completely different features. The system only sees surface-level term overlap.

2. **Vocabulary bloat is a real concern**: New terms are added to the vocabulary but old terms are never removed. Vocabulary grows with each new document. There is no feature selection or dimensionality reduction.

3. **Stored vectors are TF-only (stale IDF)**: Because IDF is applied dynamically at comparison time, stored vectors do not carry their original IDF context. This is a deliberate tradeoff to keep comparisons consistent, but it means the system cannot reconstruct the original TF-IDF representation of stored examples.

4. **No feature pruning**: Rare terms (appearing in only 1 document) can have very high IDF, making them disproportionately influential. The smoothed formula mitigates but does not eliminate this.

5. **Linear scaling**: Prediction requires comparing against all stored examples. With N examples, prediction is O(N * d) where d is the feature dimension.

6. **No sequence awareness**: The order of input tokens is mostly lost (only bigrams partially preserve local order).

7. **Confidence can still be miscalibrated for very small corpora**: The multi-factor confidence is better than vote share alone, but with fewer than ~5 examples, the confidence estimates are not well-grounded.

8. **Learning curve plateaus quickly**: The system reaches near-peak accuracy with 25 examples and shows diminishing returns beyond that. More examples add coverage but not necessarily better predictions on the existing input space.

9. **Fixed k**: The number of neighbors is a hyperparameter, not learned from data.

10. **No feature selection or dimensionality reduction**: All terms (unigrams + bigrams) are retained regardless of informativeness.

### How It Compares to Neural Approaches

| Aspect | SimilarityLearner V1 | Neural Network |
|---|---|---|
| Learning mechanism | Instance storage + weight adjustment | Gradient descent + weight matrices |
| Feature extraction | TF-IDF (hand-crafted) | Learned embeddings |
| Generalization | Similarity-based retrieval | Compositional generalization |
| Training data needed | Very few examples | Hundreds+ for good results |
| Explainability | Direct (shows similar examples) | Black box |
| Computational cost | Low | High (GPU recommended) |
| Semantic understanding | None | Approximate |

The V1 approach is a reasonable starting point. It works well for classification tasks with clear lexical overlap, requires minimal setup, and is fully explainable. It will be superseded by more sophisticated approaches as the project matures.

## Learning Modes

### Supervised Learning
- Agent receives explicit feedback (correct/incorrect)
- System updates models based on labeled examples
- Used for: code style preferences, error patterns

### Unsupervised Learning
- Agent discovers patterns without explicit labels
- System clusters similar interactions
- Used for: project conventions, common workflows

### Reinforcement Learning
- Agent learns from outcomes of actions
- System rewards successful strategies
- Used for: tool selection, approach optimization

## Memory Types

### Episodic Memory
- Specific interactions and their outcomes
- Stored as: {context, action, result, feedback}
- Used for: recalling what worked before

### Semantic Memory
- General knowledge and patterns
- Stored as: {concept, relationships, confidence}
- Used for: understanding project conventions

### Procedural Memory
- Learned procedures and workflows
- Stored as: {trigger, steps, conditions}
- Used for: automating common tasks

## Learning Pipeline

```
Input → Preprocessing → Feature Extraction → Model Update → Output
  ↓                                                      ↓
Feedback ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←← Evaluation
```

### Stage 1: Input Processing
- Receive interaction data from adapter
- Normalize and structure the data
- Extract relevant features

### Stage 2: Pattern Detection
- Compare with existing memories
- Identify similarities and differences
- Detect new patterns

### Stage 3: Knowledge Update
- Update memory store
- Adjust confidence scores
- Prune outdated information

### Stage 4: Output Generation
- Generate insights or suggestions
- Update adaptation rules
- Provide explainability

## Evaluation Metrics

### Learning Rate
- How quickly the system improves
- Measured as: improvement per interaction

### Retention
- How well knowledge persists
- Measured as: accuracy over time

### Generalization
- How well learning applies to new situations
- Measured as: performance on unseen cases

### Prediction Accuracy
- How often suggestions are correct
- Measured as: correct / total suggestions

## Safety Considerations

- Learning never overrides safety rules
- All adaptations are reversible
- Human can override any learned behavior
- Sensitive data is not retained without explicit consent

## V2 Implementation: HybridSimilarityLearner

Phase 2 adds a **semantic embedding layer** on top of V1's TF-IDF similarity. The V2 learner combines lexical (TF-IDF) and semantic (dense vector) similarity to recognize paraphrases and synonyms that TF-IDF alone misses.

### Why V2

V1's TF-IDF is purely lexical. Two texts about the same concept using different words get low similarity:

- "How do I add an item to a list?" vs "How can I append an element?" → low TF-IDF similarity
- "The cat sat on the mat" vs "A feline rested on the rug" → near-zero overlap

V2 adds semantic embeddings that capture meaning, not just spelling.

### Algorithm

V2 computes a **blended similarity** score:

```
blended_sim = w_lex * tfidf_sim + w_sem * semantic_sim
```

Where:
- `w_lex` = lexical weight (default: 0.4)
- `w_sem` = semantic weight (default: 0.6)
- `tfidf_sim` = TF-IDF cosine similarity (same as V1)
- `semantic_sim` = dense vector cosine similarity (from semantic encoder)

All other components (memory, feedback, confidence, persistence) are identical to V1.

### Semantic Encoder Interface

V2 defines a pluggable `SemanticEncoder` ABC:

```python
class SemanticEncoder(ABC):
    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]: ...
    @abstractmethod
    def encode_single(self, text: str) -> list[float]: ...
    @property
    @abstractmethod
    def dimension(self) -> int: ...
```

The default implementation is `FastEmbedEncoder` using BAAI/bge-small-en-v1.5 (384-dim, ONNX Runtime, ~33MB model).

### Graceful Degradation

When no semantic encoder is provided, V2 behaves identically to V1 (pure TF-IDF). This allows:
- Running V2 without fastembed installed
- A/B testing between V1 and V2
- Configurable lexical/semantic weight ratios

### Memory Extension

`HybridMemory` extends `ExampleMemory` by storing both TF-IDF and semantic vectors per example. Semantic vectors are optional — examples without them work fine (V1 behavior).

### Persistence

V2 save/load preserves:
- TF-IDF vocabulary and IDF statistics (same as V1)
- Semantic vectors per example
- All configuration (k, weights, etc.)
- V1-format files can be loaded by V2 (semantic vectors default to None)

## V2.1 Implementation: Smarter Memory Retrieval

V2.1 adds optional quality/recency scoring on top of V2 hybrid retrieval. When enabled via `ScorerConfig`, it applies small multiplicative bonuses to the retrieval score based on memory usage history.

### Quality Signal

Each memory tracks success/failure counts. Quality blends:
- **Success rate**: fraction of successful uses (0.5 if untested)
- **Weight normalization**: feedback weight normalized from [0.3, 5.0] to [0, 1]

Formula: `quality = 0.6 × success_rate + 0.4 × weight_norm`

### Recency Signal

Last-use timestamps with exponential decay:
- `recency = max(0.1, 2^(-age/half_life))`
- Half-life default: 86400 seconds (1 day)
- Floor at 0.1 ensures old proven memories are never completely forgotten

### Retrieval Scoring Formula

```
retrieval_score = relevance × (1 + q_weight × quality + r_weight × recency)
```

Key properties:
- If relevance = 0, score = 0 (irrelevant memories never rank high)
- Quality and recency are small bonuses (~10% and ~5% max by default)
- Maximum boost from perfect quality + recency is ~15%

### Diversity Mechanism

After scoring, near-duplicate results are removed:
- Pairwise lexical similarity computed between selected memories
- Memories with similarity above threshold (default 0.9) are removed as duplicates
- Only affects top-k results, not scoring itself

### Usage Tracking

V2.1 automatically tracks:
- `use_count`: incremented on each prediction that retrieves the memory
- `success_count`: incremented on correct feedback
- `failure_count`: incremented on incorrect feedback
- `last_used_at`: updated on each retrieval

### Backward Compatibility

- V2.1 is entirely optional — `ScorerConfig` defaults to `None`
- Without scorer, behavior is identical to V2.0
- V1 format files load with neutral metadata defaults

## V2.2 Implementation: Conflict & Contradiction Handling

V2.2 adds optional conflict detection to handle cases where the same input has multiple correct outputs (e.g., "sort a list" → both `sorted()` and `list.sort()`). When enabled via `ConflictConfig`, it detects conflicts, gathers evidence, and either resolves or reports them.

### Conflict Detection

When a prediction is made, the system:
1. Retrieves top-k candidates
2. Groups candidates by output
3. Compares input similarity between groups using cosine similarity of lexical vectors
4. Classifies conflicts as:
   - **CONFIRMED**: same context (similarity ≥ 0.9), different outputs
   - **POSSIBLE**: similar context (similarity ≥ 0.75), different outputs
   - **NONE**: different contexts (not a conflict)

Zero-relevance candidates are excluded from conflict detection to prevent false conflicts.

### Evidence Gathering

For each side of a conflict, the system gathers evidence from memory metadata:
- **Relevance**: how relevant the memory is to the query (0-1)
- **Success rate**: fraction of successful uses (0.5 if untested, < min_evidence_samples)
- **Log bonus**: diminishing returns on use count: `min(1.0, log(1 + success_count) / log(101))`
- **Recency**: time since last use (exponential decay)
- **Weight**: normalized feedback weight

### Evidence Scoring

```
score = relevance × (0.60 + 0.15 × sr + 0.10 × log_b + 0.10 × rec + 0.05 × wn)
```

Key properties:
- Relevance is always the dominant factor (multiplied outside)
- No single factor can dominate — weights are bounded and small
- Insufficient evidence (fewer than min_evidence_samples uses) is penalized
- Conflicting memories are never auto-deleted

### Resolution

- **Clear winner**: if the margin between top candidates exceeds `evidence_margin` (0.1), the conflict is RESOLVED
- **Close scores**: if scores are within the margin, the conflict is UNRESOLVED with a confidence penalty
- **Confidence penalty**: proportional to the margin reduction — `penalty = max(0, margin_ratio × 0.8)`
- Unresolved conflicts reduce overall prediction confidence rather than forcing a choice

### PredictResult

`predict()` now returns a `PredictResult` wrapper:
- `.output` / `.confidence` — backward-compatible properties
- `.base_confidence` — original confidence before conflict adjustment
- `.has_conflict` — whether any conflict was detected
- `.is_resolved` / `.is_unresolved` — conflict resolution status
- `.conflicting_outputs` / `.conflicting_ids` — conflict details
- `.summary()` — structured dict with all conflict info
- `.to_legacy()` — returns raw `Prediction` for backward compat

### Backward Compatibility

- V2.2 is entirely optional — `ConflictConfig` defaults to `None`
- Without conflict_config, behavior is identical to V2.1
- `predict_legacy()` returns raw `Prediction` (no conflict wrapper)
- V1 format files load with backward-compatible defaults
- All 254+ existing tests pass without modification

## V2.3 Implementation: Confidence & Uncertainty

V2.3 adds principled confidence estimation that separates similarity from confidence. The key insight: similarity answers "how similar is this query to stored knowledge?" while confidence answers "how reliable is this prediction given available evidence?"

### Why Confidence ≠ Similarity

The V1/V2 confidence formula (vote_share×0.4 + margin×0.25 + support_ratio×0.2 + avg_sim×0.15) is a fixed-weight linear combination that doesn't account for:
- How much evidence supports the prediction
- Whether the memory has been validated through feedback
- Whether multiple memories agree
- Whether the situation is novel/unseen

A brand-new memory with high similarity should have lower confidence than a well-validated memory with the same similarity.

### Bayesian Evidence Strength

Evidence strength uses Bayesian smoothing to blend the prior (similarity) with the observed success rate:

```
evidence_strength = prior × (1 - blend_weight) + observed_rate × blend_weight
blend_weight = total_uses / (total_uses + prior_strength)
```

With no evidence, confidence equals the prior (similarity). With lots of evidence, it converges to the observed success rate. The `prior_strength` parameter (default 4.0) controls how conservative the system is for small samples.

### Evidence Factor

The evidence factor blends similarity with evidence strength:

```
evidence_factor = 0.3 × similarity + 0.7 × evidence_strength
```

For new memories (no evidence), `evidence_factor = similarity`. For validated memories, it shifts toward the observed success rate.

### Agreement Bonus

When multiple supporting neighbors agree on the same output, confidence increases:

```
agreement = 0.5 × weight_agreement + 0.5 × count_agreement
agreement_bonus = agreement_weight × agreement
```

Where `weight_agreement = supporting_weight / total_weight` and `count_agreement = supporting_count / total_count`.

### Conflict Penalty

When top-k neighbors disagree about the output, confidence decreases:

```
conflict_penalty = max_penalty × (runner_up_weight / winner_weight)
```

Capped at `max_conflict_penalty` (default 0.3). Only triggers when `detect_conflict_count()` finds multiple relevant conflicting outputs.

### Novelty Penalty

Queries with low similarity trigger a novelty penalty:

```
if similarity < novelty_threshold:
    penalty = novelty_strength × (1 - similarity / threshold)
```

This ensures that completely unseen situations get appropriately low confidence.

### Final Formula

```
confidence = similarity × evidence_factor + agreement_bonus - conflict_penalty - novelty_penalty
```

All components are bounded. Maximum possible confidence is approximately 0.965 with default parameters.

### Uncertainty States

V2.3 classifies predictions into uncertainty states:
- **confident**: high confidence (≥0.7) with strong evidence (≥0.6)
- **uncertain**: moderate confidence, between confident and insufficient
- **insufficient_evidence**: low confidence (<0.3) or weak evidence (<0.3)
- **conflicted**: multiple conflicting outputs detected

### Explainability

Every prediction exposes structured components:
- `similarity`: base similarity score
- `evidence_strength`: Bayesian-smoothed evidence
- `evidence_factor`: blended similarity + evidence
- `agreement_bonus`: bonus from neighbor agreement
- `conflict_penalty`: penalty from output disagreement
- `novelty_penalty`: penalty for unseen situations
- `success_count` / `failure_count`: historical evidence
- `supporting_count` / `total_count`: neighbor statistics
- `conflict_count`: number of conflicting outputs

### PredictResult Updates

`predict()` now returns a `PredictResult` with additional V2.3 fields:
- `.confidence_result`: structured `ConfidenceResult` (or None if V2.3 disabled)
- `.uncertainty_state`: high-level classification
- `.similarity`: base similarity score
- `.confidence_components`: machine-readable explanation dict

### Backward Compatibility

- V2.3 is entirely optional — `ConfidenceConfig` defaults to `None`
- Without confidence_config, behavior is identical to V2.2 (V1 multi-factor formula)
- `predict_legacy()` returns raw `Prediction` (no confidence result)
- V1/V2/V2.1/V2.2 format files load with backward-compatible defaults

# Research Notes

## V1 Implementation Research

### Why TF-IDF Was Chosen

TF-IDF (Term Frequency - Inverse Document Frequency) was chosen for V1 because:

1. **Zero dependencies**: Implemented from scratch using only Python stdlib (`math`, `re`)
2. **Incremental updates**: Vocabulary and IDF statistics can be updated one document at a time
3. **Works with small data**: Performs reasonably with 10-50 examples (unlike neural networks)
4. **Interpretable**: Feature weights correspond to specific terms
5. **Fast**: O(d) per document where d is vocabulary size
6. **Proven**: Decades of use in information retrieval and text classification

The implementation uses:
- Standard TF: `count(t,d) / len(d)`
- Smoothed IDF: `log(1 + N / (df + 1))` (V1.1 audit fix)
- Optional sublinear TF: `1 + log(count)` (disabled by default)
- Unigrams + bigrams (ngram_range=(1,2))
- Minimal English stop word list

### Why Standard TF-IDF Breaks in Online Learning

Standard TF-IDF was designed for batch processing, where the entire corpus is available at once. In an online/incremental setting, it has two critical failure modes:

1. **Division by zero**: When a new term appears that hasn't been seen before, `df(t) = 0`, making `log(N / 0)` undefined. The standard formula requires either a special case or a minimum df floor.

2. **IDF drift**: As new documents are added, IDF values change for all existing terms. This means the TF-IDF vector for a document computed at time T is different from what it would be at time T+100. In a batch system this doesn't matter (you recompute everything). In an online system, stored vectors become inconsistent with the current vocabulary.

3. **Rare term dominance**: Terms appearing in exactly 1 document get `log(N / 1) = log(N)`. As N grows, these terms get arbitrarily high IDF, making single-document terms dominate similarity calculations.

### Why Smoothed IDF Is Necessary

The smoothed formula `log(1 + N / (df + 1))` addresses all three problems:

- **No division by zero**: `df + 1` is always >= 1
- **No infinite IDF**: `log(1 + ...)` is always finite
- **Bounded rare term weight**: A term in 1 document gets `log(1 + N/2)`, which grows logarithmically rather than linearly with N
- **Corpus-wide terms get low but non-zero weight**: `log(2) ≈ 0.69` instead of 0, preventing complete information loss for common terms

The tradeoff is slightly less discriminative power for rare terms compared to standard IDF. This is acceptable because the alternative (extremely high IDF for rare terms) causes more problems than it solves.

### Why Stored Vectors Should Be TF-Only

The V1.1 audit revealed that storing full TF-IDF vectors creates an inconsistency: the IDF component of stored vectors reflects the vocabulary at storage time, not the current vocabulary. When a new document adds a term that changes IDF for existing terms, all stored vectors become slightly wrong.

The solution is to store only TF and apply IDF dynamically at comparison time:

```
At storage time:  vector = {term: tf(term, doc)}                    (TF only)
At comparison time: similarity = Σ(tf_a * idf_current * tf_b * idf_current) / (||a|| * ||b||)
```

Benefits:
- Stored vectors are stable — they never change after creation
- All vectors in a comparison use the same IDF weights (the current vocabulary)
- Predictions are numerically reproducible after save/load
- The cost is one extra IDF lookup per shared term at comparison time, which is negligible

### Why Feedback Must Be Conservative

Online learners are vulnerable to feedback loops. If feedback has large weight deltas:

1. **Adversarial feedback**: A single incorrect feedback round can significantly suppress correct examples
2. **Noise amplification**: Ambiguous inputs with mixed feedback cause weight oscillation
3. **Catastrophic forgetting**: Aggressive negative feedback on correct examples can permanently silence them

The V1.1 audit found that the original deltas (+0.1/-0.2 with floor 0.1) were too aggressive. The conservative values (+0.05/-0.1 with floor 0.3) were chosen because:

- **Asymmetric but bounded**: Incorrect feedback (-0.1) has 2x the impact of correct (+0.05), reflecting that incorrect predictions are a stronger signal. But the floor of 0.3 prevents runaway suppression.
- **Verified empirically**: The learner retains 100% accuracy after 5 rounds of completely incorrect feedback (benchmark #12).
- **Slow but reliable adaptation**: When the correct answer genuinely changes, it takes multiple feedback rounds to shift predictions. This is a feature, not a bug — it prevents thrashing.

### Why Correction Examples Must Be Deduplicated

In V1, every incorrect feedback with a correct output added a new example. If the same input was predicted incorrectly 3 times (e.g., due to vocabulary drift between predictions), 3 identical correction examples would be stored. This causes:

1. **Vocabulary bloat**: Each duplicate adds terms to the vocabulary, increasing memory and computation
2. **Vote skewing**: Multiple identical examples for the same (input, output) pair dominate the top-k neighbors, crowding out other potentially useful examples
3. **IDF distortion**: Duplicate documents inflate document frequencies, reducing IDF for terms that appear in the duplicates

The fix is simple: before adding a correction, check if an example already exists for the exact (input_text, output) pair. If it does, skip the addition.

## V1.1 Audit Findings

The V1.1 audit was a systematic review of the V1 implementation, benchmarking all claims against actual performance. Key findings:

1. **All core claims validated**: Classification, generalization, adaptation, retention, and regression benchmarks all pass with the updated implementation.
2. **Confidence is better calibrated**: Multi-factor confidence (0.807 known, 0.803 unseen) is more stable than vote share alone.
3. **Feedback resistance is strong**: 100% retention after 5 rounds of bad feedback confirms conservative weights work.
4. **Learning curve plateaus**: Peak accuracy is reached at ~25 examples; more examples add coverage but not better predictions on existing inputs.
5. **Persistence is exact**: Save/load preserves predictions and confidence numerically, confirming TF-only storage works.

## Similarity-Based Learning Approaches

Several approaches were considered:

| Approach | Pros | Cons | Chosen? |
|---|---|---|---|
| TF-IDF + cosine similarity | Simple, explainable, no deps | Lexical only | Yes (V1) |
| BM25 | Better term weighting | More complex, still lexical | No |
| Word2Vec/GloVe | Semantic similarity | Requires pre-trained vectors, heavy | No |
| Sentence embeddings | Semantic, cross-lingual | Requires transformers library | No |
| LLM-based RAG | Strongest semantic understanding | API dependency, non-deterministic | No |

The plan is to evolve toward semantic embeddings (sentence-transformers) in Phase 2+.

### Why Not Neural Networks Yet

Neural networks require:
- **Hundreds of examples minimum** for decent performance
- **Batch processing** or careful online learning setup
- **Gradient computation** and optimization
- **Significant dependencies** (PyTorch, TensorFlow)
- **GPU** for reasonable training times

For V1, the goal was:
- Work with 10-50 examples
- No external dependencies
- Fully explainable
- Instant feedback response

Neural approaches are planned for Phase 6 (Advanced Learning Algorithms).

### Why Not LLM-Based Learning

LLMs (using prompting or RAG) were considered but rejected for V1 because:
- Requires API calls (cost, latency, availability dependency)
- Non-deterministic outputs
- Hard to control what the model "learns"
- Not self-contained (external service required)
- Difficult to benchmark reliably

LLM integration may be explored as an augmentation layer in later phases.

### Why Online/Incremental

The system must learn from examples arriving one at a time:
- Real-world usage: feedback arrives sporadically
- Cannot retrain on entire corpus for each new example
- Feedback must take effect immediately
- Memory grows monotonically

TF-IDF supports this naturally: `fit()` updates vocabulary and computes TF for a single document without touching existing vectors. This is a key advantage over batch-oriented approaches.

## Known Limitations of V1

1. **No semantic understanding**: "happy" and "joyful" are unrelated features. The system only sees surface-level term overlap. This is the most fundamental limitation and will require embeddings (Phase 2) to address.

2. **Vocabulary bloat is a real concern**: Vocabulary grows with each new document and is never pruned. Deduplication of correction examples helps, but the underlying problem remains. Feature selection (min_df, max_df) is planned for Phase 2.

3. **Confidence can still be miscalibrated for very small corpora**: With fewer than ~5 examples, the multi-factor confidence is not well-grounded. The support ratio and margin factors are meaningless with 1-2 neighbors.

4. **Learning curve plateaus quickly**: The system reaches near-peak accuracy with ~25 examples on the current benchmark datasets. Beyond that, more examples add coverage of new input patterns but do not improve predictions on the existing input space.

5. **No feature selection or dimensionality reduction**: All terms (unigrams + bigrams) are retained regardless of informativeness. Rare bigrams can have very high IDF and dominate similarity calculations.

6. **IDF drift is reduced but not eliminated**: Dynamic IDF application keeps comparisons consistent, but the underlying IDF values still shift as the vocabulary grows. This means the system's behavior changes subtly over time even without feedback.

7. **Linear scan**: Prediction compares against all stored examples. This is O(N * d) where N is the number of examples and d is the feature dimension. Fine for 50 examples, problematic for 10,000+.

8. **Fixed k**: The number of neighbors is a hyperparameter, not learned from data. Different tasks may benefit from different k values.

9. **No sequence modeling**: Only bigrams capture local word order. Long-range dependencies (e.g., subject-verb agreement across clauses) are invisible.

## Active Research Areas

### 1. Prompt Learning
- Learning from prompt-response pairs
- Identifying effective prompting patterns
- Adapting prompts based on success rate

### 2. Code Pattern Recognition
- Detecting coding style preferences
- Identifying project-specific conventions
- Learning error-prone patterns

### 3. Knowledge Graphs
- Building project knowledge graphs
- Relationship extraction from code
- Context-aware knowledge retrieval

### 4. Feedback Mechanisms
- Explicit feedback (thumbs up/down)
- Implicit feedback (acceptance/rejection)
- Outcome-based feedback (did it work?)

## Key Papers to Read

- [ ] "Learning to Prompt for Vision-Language Models" (CoOp)
- [ ] "Pattern Recognition and Machine Learning" (Bishop)
- [ ] "An Introduction to Statistical Learning" (ISLR)

## Libraries to Evaluate

### Memory
- SQLite (simple, embedded)
- ChromaDB (vector search)
- Qdrant (vector search, more features)

### ML
- scikit-learn (traditional ML)
- sentence-transformers (embeddings)
- numpy (numerical computing)

### Web
- httpx (async HTTP)
- beautifulsoup4 (HTML parsing)
- trafilatura (article extraction)

## Open Questions

1. What is the optimal memory retention strategy?
2. How to balance learning speed with stability?
3. When should the system stop learning?
4. How to detect and prevent negative learning?

## Experiments Planned

- [ ] E001: Memory retention strategies
- [ ] E002: Feedback weighting methods
- [ ] E003: Pattern detection algorithms
- [ ] E004: Knowledge graph construction
- [x] E005: TF-IDF vs BM25 vs embeddings comparison
- [ ] E006: Vocabulary pruning strategies

## Phase 2: Semantic Embedding Research

### Why Semantic Embeddings

V1 relies on lexical overlap (TF-IDF + cosine similarity). Two texts about the same concept
but using different words get low similarity scores. Example:

- "How do I add an item to a list?" vs "How can I append an element?" → low TF-IDF similarity
- "The cat sat on the mat" vs "A feline rested on the rug" → near-zero overlap

Semantic embeddings map texts to vectors where meaning, not spelling, determines distance.

### Approaches Evaluated

| Approach | Model | Dependencies | Size | Offline | Quality |
|----------|-------|-------------|------|---------|---------|
| **FastEmbed** | BAAI/bge-small-en-v1.5 | onnxruntime, numpy, tokenizers | ~150MB installed, ~33MB model | Yes (after download) | High (beats Ada-002) |
| **sentence-transformers** | all-MiniLM-L6-v2 | torch, transformers, sentence-transformers | ~2GB installed, ~90MB model | Yes | Highest |
| **tiny-embed** | GloVe + custom | Zero deps | ~15MB model | Yes | Low (static embeddings) |
| **FastText** | crawl-300d-2M | gensim | ~2.2GB | Yes | Medium |
| **Word2Vec** | GoogleNews | gensim | ~1.6GB | Yes | Medium |
| **API (OpenAI)** | text-embedding-3-small | openai, httpx | ~1MB | No | High |

### Decision: FastEmbed (BAAI/bge-small-en-v1.5)

**Chosen approach**: FastEmbed with BAAI/bge-small-en-v1.5

**Why**:
1. **Lightweight**: No PyTorch (~2GB). Uses ONNX Runtime (~50MB).
2. **High quality**: bge-small-en-v1.5 outperforms OpenAI Ada-002 on MTEB benchmarks.
3. **Offline**: Model downloads once to `~/.cache/huggingface/`, then works fully offline.
4. **Fast**: ~1000 docs/sec on CPU with ONNX optimization.
5. **Model size**: 33MB quantized ONNX model.
6. **Configurable**: Supports multiple models via `TextEmbedding.list_supported_models()`.
7. **Maintained**: By Qdrant team, active development, Apache 2.0 license.
8. **Python 3.14 compatible**: Verified install and runtime on our platform.

**Dependencies added**: `fastembed>=0.8.0` (brings: onnxruntime, numpy, tokenizers, huggingface-hub)

**Verified**:
```
>>> model = TextEmbedding(model_name='BAAI/bge-small-en-v1.5')
>>> Model loaded in 10.44s (first load, downloads model)
>>> Encoded 3 texts in 0.168s
>>> Embedding dimension: 384

>>> "How do I add an item to a Python list?" vs "How can I append an element to an array?"
>>> Cosine similarity: 0.7852 (high — correct semantic match)

>>> Both vs "What is the capital of France?"
>>> Cosine similarity: ~0.29 (low — correct semantic mismatch)
```

**Interface design**: `SemanticEncoder` ABC with `encode(texts) -> list[list[float]]`.
This allows swapping FastEmbed for any other provider (sentence-transformers, API, custom)
without touching the learner or memory code.

## References

- Anthropic's research on AI safety
- OpenAI's work on alignment
- Academic papers on lifelong learning
- FastEmbed docs: https://qdrant.github.io/fastembed/
- BGE-small-en-v1.5: https://huggingface.co/BAAI/bge-small-en-v1.5

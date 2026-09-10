# Architecture

## Overview

The AI Learning Engine follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Harness Adapters                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ OpenCode │  │  Claude  │  │  Codex   │  │  Generic ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
│       └──────────────┴──────────────┴──────────────┘     │
│                           │                              │
│                    ┌──────┴──────┐                       │
│                    │   Adapter   │                       │
│                    │   Registry  │                       │
│                    └──────┬──────┘                       │
├───────────────────────────┼─────────────────────────────┤
│                    Core Interfaces                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ Learner  │  │  Memory  │  │Evaluator │  │Adaptation││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
│       └──────────────┴──────────────┴──────────────┘     │
│                           │                              │
│                    ┌──────┴──────┐                       │
│                    │  Knowledge  │                       │
│                    │    Base     │                       │
│                    └──────┬──────┘                       │
├───────────────────────────┼─────────────────────────────┤
│                    Infrastructure                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │  Web     │  │ Storage  │  │ Security │  │  Utils   ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
└─────────────────────────────────────────────────────────┘
```

## Core Components

### Learner
The learning engine that processes feedback and updates knowledge.

**Responsibilities:**
- Process learning inputs (feedback, corrections, patterns)
- Update internal models
- Generate learning outputs (insights, predictions)

**Interface:** `core.learner.base.Learner`

**Implementation:** `core.learner.learner_v1.SimilarityLearner`

### Memory
Persistent storage for learned knowledge and context.

**Responsibilities:**
- Store and retrieve memories
- Manage memory lifecycle (creation, update, expiry)
- Support similarity-based retrieval

**Interface:** `core.memory.base.MemoryStore[T]`

### Evaluator
Measures learning effectiveness and system performance.

**Responsibilities:**
- Collect metrics on learning performance
- Generate evaluation reports
- Detect regressions

**Interface:** `core.evaluator.base.Evaluator`

### Adaptation
Modifies agent behavior based on learning.

**Responsibilities:**
- Detect adaptation signals
- Generate adaptation actions
- Apply behavior changes

**Interface:** `core.adaptation.base.AdaptationEngine`

### Knowledge
Acquires and manages external knowledge.

**Responsibilities:**
- Search and fetch web content
- Evaluate source quality
- Integrate knowledge into memory

**Interface:** `core.knowledge.base.KnowledgeBase`

## V1 Implementation Details

### SimilarityLearner (`core/learner/learner_v1.py`)

The first concrete learner implementation. Inherits from `Learner` ABC.

**Constructor parameters:**
- `k: int = 5` - Number of nearest neighbors
- `min_confidence: float = 0.1` - Minimum confidence threshold
- `feedback_weight_delta: float = 0.2` - Weight adjustment magnitude
- `use_sublinear_tf: bool = False` - Use log-scaled term frequency
- `ngram_range: tuple[int, int] = (1, 2)` - Unigrams + bigrams

**Key methods:**
- `learn(inp)` - Store input-output pair as TF-IDF vector
- `predict(text)` - Find k-nearest neighbors, weighted voting
- `feedback(text, predicted, correct, actual_output)` - Adjust weights
- `save_state(path)` / `load_state(path)` - Persistence

**State tracked:**
- `_total_predictions` - Count of predictions made
- `_correct_predictions` - Count of correct predictions
- `_total_feedback` - Count of feedback events

### FeatureExtractor (`core/learner/feature_extractor.py`)

Converts raw text to sparse TF-IDF feature vectors.

**Processing pipeline:**
1. Lowercase and tokenize (regex: `[a-z0-9]+`)
2. Remove stop words (minimal English set)
3. Generate n-grams (unigrams + bigrams by default)
4. Compute term frequency (TF)
5. Compute inverse document frequency (IDF)
6. Return sparse FeatureVector

**Key methods:**
- `fit(text)` - Extract features AND update vocabulary/IDF
- `transform(text)` - Extract features WITHOUT updating vocabulary

**State:**
- `_df: dict[str, int]` - Document frequency per term
- `_num_docs: int` - Total documents seen

### ExampleMemory (`core/learner/memory.py`)

In-memory store for learned input-output pairs.

**Stored per example:**
- `id` - Unique integer ID
- `input_text` - Original text
- `output` - Label/output
- `vector: FeatureVector` - Sparse TF-IDF vector
- `weight: float` - Confidence weight (updated by feedback)
- `feedback_count` - Times feedback was received
- `correct_count` - Times confirmed correct
- `metadata` - Arbitrary metadata

**Weight update rules:**
- Correct feedback: `weight = min(5.0, weight + 0.1)`
- Incorrect feedback: `weight = max(0.1, weight - 0.2)`
- New correction example: starts at `weight = 1.5`

**Persistence:**
- `save(path)` - JSON serialization
- `load(path)` - JSON deserialization

### Similarity Functions (`core/learner/similarity.py`)

- `cosine_similarity(a, b)` - Dot product / (norm_a * norm_b) for sparse vectors
- `weighted_similarity(query, candidates)` - Similarity * weight, sorted descending

## Component Connections

```
SimilarityLearner
  ├── FeatureExtractor
  │     ├── tokenize()
  │     ├── remove_stop_words()
  │     ├── ngrams()
  │     ├── fit() / transform()
  │     └── _df, _num_docs (vocabulary state)
  │
  └── ExampleMemory
        └── list[LearnedExample]
              └── LearnedExample
                    ├── id, input_text, output
                    ├── vector: FeatureVector
                    ├── weight, feedback_count, correct_count
                    └── metadata
```

## Data Flow

### Learning

```
LearningInput
  → SimilarityLearner.learn()
    → FeatureExtractor.fit(text)
      → tokenize → remove_stop_words → ngrams → TF-IDF
      → FeatureVector
    → ExampleMemory.add(input, output, vector)
    → LearningOutput (status, delta)
```

### Prediction

```
text
  → SimilarityLearner.predict()
    → FeatureExtractor.transform(text)
      → FeatureVector (no vocabulary update)
    → ExampleMemory.get_all()
    → weighted_similarity(query, candidates)
      → cosine_similarity for each candidate
      → multiply by example weight
      → sort descending
    → Take top-k
    → Weighted voting among neighbors
    → Prediction(output, confidence, similarities)
```

### Feedback

```
text, predicted, correct, actual_output
  → SimilarityLearner.feedback()
    → FeatureExtractor.transform(text)
    → Find similar examples (same as prediction)
    → For each top-k neighbor matching predicted label:
        → ExampleMemory.record_feedback(id, correct)
    → If incorrect and actual_output provided:
        → FeatureExtractor.fit(text)
        → ExampleMemory.add(text, actual_output, vector, weight=1.5)
    → Return changes dict
```

## Key Design Decisions

1. **Generic Memory Store**: `MemoryStore[T]` is generic to support different memory types
2. **Interface-First**: All components defined as ABCs before implementation
3. **Adapter Pattern**: Each harness gets its own adapter implementing `HarnessAdapter`
4. **Pluggable Everything**: Web providers, storage backends, learning algorithms are all swappable

## Security Model

- Web content is never executed directly
- All external data is sanitized before storage
- Permission boundaries are enforced at adapter level
- No blind execution of instructions from external sources

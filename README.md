# AI Learning Engine

A cross-harness AI learning and adaptation engine for coding agents.

## What This Is

The AI Learning Engine is a modular system that enables AI coding agents to learn, adapt, and improve over time. It provides persistent memory, feedback learning, knowledge acquisition, and pattern detection across multiple coding harnesses.

## What Problem It Solves

AI coding agents today are stateless - they don't learn from past interactions, don't retain knowledge across sessions, and can't adapt to individual developer preferences or project patterns. This engine adds a learning layer that makes agents more effective over time.

## Architecture Philosophy

- **Harness-agnostic core**: The learning engine works identically across OpenCode, Claude Code, Codex, and future platforms
- **Modular design**: Every component is replaceable and independently testable
- **Stable interfaces**: Adapters communicate with core through well-defined contracts
- **No premature complexity**: Start simple, add complexity only when needed
- **Measurable learning**: Every improvement can be benchmarked

## Platform Priorities

1. **OpenCode** - First-class support (primary development platform)
2. **Claude Code** - Second priority
3. **Codex** - Third priority
4. **Other harnesses** - Future adapters

## Current Development Stage

**Phase 1 - Basic Learning Prototype** (Complete)

- SimilarityLearner implemented (TF-IDF + cosine similarity + weighted voting)
- ExampleMemory with feedback-driven weight updates
- FeatureExtractor with incremental vocabulary
- Save/load persistence
- Benchmark suite passing (9/9 tests)

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd ai-learning-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run type checks
mypy core/

# Run linter
ruff check .
```

## Project Structure

```
ai-learning-engine/
├── core/           # Harness-agnostic learning engine
│   ├── learner/    # Learning algorithms
│   ├── memory/     # Memory storage and retrieval
│   ├── evaluator/  # Performance measurement
│   ├── adaptation/ # Behavior modification
│   └── knowledge/  # Knowledge acquisition
├── web/            # Web access abstractions
├── adapters/       # Harness-specific integrations
├── storage/        # Persistence backends
├── experiments/    # Experimental algorithms
├── benchmarks/     # Performance benchmarks
├── tests/          # Test suite
├── docs/           # Documentation
└── scripts/        # Development utilities
```

## Design Principles

1. Modular architecture
2. Core engine must not depend on any specific harness
3. Harness adapters communicate with core through stable interfaces
4. Web access must be an abstraction, not hardcoded to one provider
5. Memory must be replaceable
6. Learning algorithms must be replaceable
7. Every important component must be testable independently
8. Experimental algorithms must not destabilize the main implementation
9. All learning behavior should be measurable
10. Avoid premature complexity

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

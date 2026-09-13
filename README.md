# Lerev

Universal AI-agent learning and long-term memory system.

Lerev makes AI coding agents remember, learn, and improve across sessions. Install once, use everywhere.

## What Lerev Does

AI coding agents are stateless — they forget everything between sessions. Lerev gives them persistent, project-scoped memory that survives restarts.

- **Long-term memory**: Agents remember past decisions, patterns, and outcomes
- **Project isolation**: Each project's memories are completely separate
- **Session awareness**: Memories are tagged with session and agent context
- **Security**: Injection detection and instruction/data boundary enforcement
- **Universal**: Works with OpenCode, Claude Code, Codex, and future agents

## Quick Start

```bash
pip install lerev
lerev install
```

Then start OpenCode in any project — Lerev connects automatically.

## Installation

### pip (all platforms)

```bash
pip install lerev
lerev install
```

### Development

```bash
git clone https://github.com/dkshs/lerev.git
cd lerev
pip install -e .
lerev install
```

### Other methods

See [docs/installation.md](docs/installation.md) for Windows installer, Chocolatey, Homebrew, and Linux shell installer.

## CLI Commands

```bash
lerev --help        # Show available commands
lerev version       # Print version
lerev status        # Show installation status
lerev doctor        # Run diagnostics
lerev install       # Register OpenCode plugin
lerev uninstall     # Remove OpenCode plugin
```

## How It Works

```
OpenCode / Claude Code / Codex
        │
        ▼
TypeScript Lerev plugin (auto-discovered)
        │
        │ JSON over stdin/stdout
        ▼
Python bridge
        │
        ▼
Lerev V2.6 memory engine
        │
        ├── MemoryManager
        ├── Security (injection detection, scope validation)
        ├── Persistence (project-scoped JSON storage)
        ├── Experience (episodic/semantic memory)
        └── MemoryStore (retrieval and ranking)
```

Memory is stored per-project in `.lerev/memory/` and is never shared between projects.

## Architecture

```
V2.4.2 → Knowledge + lifecycle
V2.5   → Universal Agent Routing & Intelligence Layer
V2.6   → Long-Term Memory + Deep Agent Connection
```

### Project Structure

```
lerev/              # Python package (CLI, bridge, plugin source)
core/               # V2.5 routing + V2.6 memory engine
adapters/           # Agent-specific integrations
storage/            # Persistence backends
web/                # Web access abstractions
packaging/          # Windows, Chocolatey, Homebrew, Linux
docs/               # Documentation
tests/              # Test suite (2145+ tests)
```

## Development

```bash
pip install -e ".[dev]"
pytest                          # Run all tests
ruff check .                    # Lint
mypy core/                      # Type check
python -m lerev doctor          # Verify installation
```

## License

MIT — see [LICENSE](LICENSE).

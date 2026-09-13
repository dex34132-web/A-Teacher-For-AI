# Lerev

Universal AI-agent learning and long-term memory system.

Lerev gives coding agents persistent, project-scoped memory that survives restarts.

## Install

```bash
pip install lerev
lerev install
```

Then start your coding agent in any project — Lerev connects automatically.

## What Lerev Does

- Long-term memory across sessions
- Project isolation (memories never leak between projects)
- Session and agent awareness
- Injection detection and security boundaries
- Works with OpenCode, Claude Code, Codex, and others

## How It Works

```
Your coding agent
    │
    ▼
Lerev plugin (auto-discovered)
    │
    ▼
Python bridge (JSON over stdin/stdout)
    │
    ▼
Lerev V2.6 memory engine
    ├── MemoryManager
    ├── Security
    ├── Persistence (project-scoped)
    └── MemoryStore
```

Memory is stored in `.lerev/memory/` per project.

## CLI

```bash
lerev --help        # Show commands
lerev version       # Print version
lerev status        # Show installation status
lerev doctor        # Run diagnostics
lerev install       # Register agent plugin
lerev uninstall     # Remove agent plugin
```

## Other Install Methods

- **Windows installer**: Download `Lerev-Setup.exe` from [releases](https://github.com/dex34132-web/lerev/releases)
- **Chocolatey**: `choco install lerev`
- **Homebrew**: `brew install lerev`
- **Linux**: `curl -fsSL https://lerev.dev/install.sh | sh`
- **Development**: `git clone https://github.com/dex34132-web/lerev.git && pip install -e .`

See [docs/installation.md](docs/installation.md) for details.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy core/
```

## License

MIT — see [LICENSE](LICENSE).

# Lerev

Universal AI-agent learning and long-term memory system.

Lerev gives coding agents persistent, project-scoped memory that survives restarts.

## Install

### Python
```bash
pip install lerev
```

### npm / bun
```bash
npm install -g @dksh/lerev
# or
bun install -g @dksh/lerev
```

### Windows
Download `Lerev-Setup.exe` from [releases](https://github.com/dkshs/lerev/releases)

### Chocolatey
```bash
choco install lerev
```

### Homebrew (macOS)
```bash
brew install lerev
```

### Linux
```bash
curl -fsSL https://raw.githubusercontent.com/dkshs/lerev/main/packaging/linux/install.sh | sh
```

### From source
```bash
git clone https://github.com/dkshs/lerev.git
pip install -e .
```

Plugin auto-installs on first use. Restart OpenCode after install.

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
lerev install       # Reinstall plugin
lerev uninstall     # Remove plugin
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy core/
```

## License

MIT — see [LICENSE](LICENSE).

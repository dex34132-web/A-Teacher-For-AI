# Teacher

Universal AI-agent learning and long-term memory system.

Teacher gives coding agents persistent, project-scoped memory that survives restarts.

## Install

### Python
```bash
pip install teacher
```

### npm / bun
```bash
npm install -g @dksh/teacher
# or
bun install -g @dksh/teacher
```

### Windows
Download `Teacher-Setup.exe` from [releases](https://github.com/dex34132-web/lerev/releases)

### Chocolatey
```bash
choco install teacher
```

### Homebrew (macOS)
```bash
brew install teacher
```

### Linux
```bash
curl -fsSL https://raw.githubusercontent.com/dex34132-web/lerev/main/packaging/linux/install.sh | sh
```

### From source
```bash
git clone https://github.com/dex34132-web/lerev.git
pip install -e .
```

Plugin auto-installs on first use. Restart OpenCode after install.

## What Teacher Does

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
Teacher plugin (auto-discovered)
    │
    ▼
Python bridge (JSON over stdin/stdout)
    │
    ▼
Teacher V2.6 memory engine
    ├── MemoryManager
    ├── Security
    ├── Persistence (project-scoped)
    └── MemoryStore
```

Memory is stored in `.teacher/memory/` per project.

## CLI

```bash
teacher --help        # Show commands
teacher version       # Print version
teacher status        # Show installation status
teacher doctor        # Run diagnostics
teacher install       # Reinstall plugin
teacher uninstall     # Remove plugin
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy core/
```

## Migration from LEREV

This project was formerly named **LEREV**. The canonical identity is now
**Teacher**. Legacy aliases are kept so existing installs keep working:

- `lerev` console script → runs the Teacher CLI (legacy alias)
- `import lerev` / `python -m lerev.bridge` → shim over `teacher`
- `LEREV_HOME` / `EVO_HOME` env vars → honoured as fallbacks after `TEACHER_HOME`
- `lerev-bridge` on PATH → honoured as fallback after `teacher-bridge`
- `.lerev/memory/` (and older `.evo/memory/`) → copied non-destructively to
  `.teacher/memory/` on first use; the original data is never deleted
- stale `plugins/lerev.ts` / `node_modules/lerev` → removed on `teacher install`

New usage should always say **Teacher** / `teacher` / `teacher_*`.

## License

MIT — see [LICENSE](LICENSE).

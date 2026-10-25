# Toolio — Global Cross-Platform Installation & Distribution

> **Historical document.** Written under the project's former name, *LEREV* (now *Toolio*), and preserved as-is for the record; names below may not match the current codebase.


**Date:** 2026-09-13
**Status:** Design
**Product Name:** Toolio (renamed from Toolio)

---

## 1. Overview

Toolio is ONE product, ONE system, ONE user-facing name: **Toolio**.

After installation, OpenCode must be able to use Toolio from **any project directory**. The Toolio repository must NOT need to be the OpenCode working directory. The user must NOT manually copy plugins into every project.

### Naming

| Context | Name |
|---------|------|
| Product | Toolio |
| PyPI | `toolio` |
| npm | `toolio` |
| CLI | `toolio` |
| Memory dir | `.toolio/memory/` |
| Env var | `LEREV_HOME` |

### Backward Compatibility

- `.toolio/memory/` directories remain readable during transition
- `LEREV_HOME` env var still supported (fallback)
- Internal Python modules (`core/`, `core/routing/v26/`) keep existing names

---

## 2. Architecture

```
┌─────────────────────────────────────────────┐
│           Distribution Layer                │
│  PyPI (toolio) | npm (toolio)                │
│  Chocolatey | Homebrew | Windows Installer  │
│  Linux shell installer                      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│              CLI Layer                       │
│  toolio install | toolio doctor | toolio status │
│  toolio version | toolio uninstall            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           Discovery Layer                   │
│  Bridge discovery (LEREV_HOME → PATH →      │
│  installed module → dev fallback)           │
│  OpenCode global config registration        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         Existing Toolio Core (unchanged)     │
│  V2.6 Memory | V2.5 Routing | Bridge        │
└─────────────────────────────────────────────┘
```

### Python Package Structure

```
toolio/
├── __init__.py          # version, public API
├── __main__.py          # python -m toolio
├── cli.py               # argparse CLI
├── config.py            # LEREV_HOME, paths, OpenCode config discovery
├── discovery.py         # Bridge discovery (4-tier cascade)
├── bridge.py            # Bridge protocol (extracted from scripts/toolio_bridge.py)
└── plugin_source.py     # TypeScript plugin source (bundled as string)
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | MODIFY | Rename to `toolio`, add CLI entry point, include `toolio/` package |
| `toolio/__init__.py` | CREATE | Package init with version |
| `toolio/__main__.py` | CREATE | `python -m toolio` entry |
| `toolio/cli.py` | CREATE | CLI commands |
| `toolio/config.py` | CREATE | Path/config discovery |
| `toolio/discovery.py` | CREATE | Bridge discovery cascade |
| `toolio/bridge.py` | CREATE | Bridge protocol (importable) |
| `toolio/plugin_source.py` | CREATE | Bundled TypeScript plugin |
| `scripts/toolio_bridge.py` | MODIFY | Thin wrapper importing from `toolio.bridge` |
| `.opencode/plugins/evo.ts` | MODIFY | Add discovery cascade |
| `packaging/windows/` | CREATE | NSIS installer script |
| `packaging/chocolatey/` | CREATE | Chocolatey nuspec |
| `packaging/homebrew/` | CREATE | Homebrew formula |
| `packaging/linux/install.sh` | CREATE | Shell installer |
| `tests/unit/test_cli.py` | CREATE | CLI tests |
| `tests/unit/test_discovery.py` | CREATE | Discovery tests |
| `tests/unit/test_config.py` | CREATE | Config tests |
| `tests/unit/test_install.py` | CREATE | Install tests |
| `docs/installation.md` | CREATE | Installation guide |
| `docs/troubleshooting.md` | CREATE | Troubleshooting guide |

---

## 3. Bridge Discovery

### 4-Tier Cascade

```
1. LEREV_HOME env var → {LEREV_HOME}/toolio/bridge.py
2. `toolio-bridge` on PATH → execute directly
3. Installed module → python -m toolio.bridge
4. Dev fallback → {worktree}/scripts/toolio_bridge.py
```

### TypeScript Plugin Changes

The plugin will implement the cascade:

```typescript
async function discoverBridge(worktree: string): Promise<{python: string, bridgePath: string} | null> {
  // Tier 1: LEREV_HOME
  const toolioHome = process.env.LEREV_HOME || process.env.LEREV_HOME
  if (toolioHome) {
    const bridgePath = resolve(toolioHome, "toolio", "bridge.py")
    if (await fileExists(bridgePath)) return { python: await findPython(), bridgePath }
  }

  // Tier 2: toolio-bridge on PATH
  const bridgeCmd = await which("toolio-bridge").catch(() => null)
  if (bridgeCmd) return { python: "", bridgePath: bridgeCmd }

  // Tier 3: python -m toolio.bridge
  const python = await findPython()
  if (python) {
    const available = await testModule(python, "toolio.bridge")
    if (available) return { python, bridgePath: "-m toolio.bridge" }
  }

  // Tier 4: Dev fallback
  const devBridge = resolve(worktree, "scripts", "toolio_bridge.py")
  if (await fileExists(devBridge)) return { python: python ?? "python3", bridgePath: devBridge }

  return null
}
```

### Bridge Protocol (preserved)

```
TypeScript plugin
       ↓
JSON stdin
       ↓
Python bridge
       ↓
V2.6 Memory
       ↓
JSON stdout
       ↓
TypeScript plugin
```

No HTTP daemon. No network communication. No memory in CLI arguments.

---

## 4. CLI Commands

### `toolio install`

**Steps:**
1. Detect OS
2. Detect Python >=3.11
3. Detect OpenCode installation
4. Find OpenCode global config (`~/.config/opencode/opencode.jsonc`)
5. Check for existing Toolio registration
6. If not registered:
   - Copy `toolio.ts` plugin to `~/.config/opencode/node_modules/toolio/`
   - Add plugin entry to config `plugin` array
7. Verify bridge works
8. Report changes

**Idempotent:** Running multiple times produces identical state.

### `toolio doctor`

**Checks:**
```
Toolio runtime          PASS/FAIL
Python/runtime         PASS/FAIL
Bridge                 PASS/FAIL
JSON protocol          PASS/FAIL
OpenCode               PASS/FAIL
Plugin registration    PASS/FAIL
Plugin resolution      PASS/FAIL
Memory storage         PASS/FAIL
Round trip             PASS/FAIL

Result: READY / NOT READY
```

Provides actionable diagnostics for each failure.

### `toolio status`

```
Toolio
────────────────
Version: 2.6.x
Plugin: installed
OpenCode: detected
Bridge: healthy
Memory: available
```

### `toolio version`

```
toolio 2.6.x
```

### `toolio uninstall`

Removes only Toolio-owned components:
- Removes Toolio entry from OpenCode plugin array
- Removes `~/.config/opencode/node_modules/toolio/`
- Does NOT remove `.toolio/memory/`
- Does NOT remove unrelated plugins or config

---

## 5. Distribution Methods

### 1. Python / PyPI

```bash
pip install toolio
```

Package name: `toolio`
CLI entry point: `toolio`

### 2. npm

```bash
npm install -g toolio
```

Provides TypeScript plugin for OpenCode.

### 3. Chocolatey (Windows)

```powershell
choco install toolio
```

Wraps pip install + `toolio install`.

### 4. Windows Installer

Built with NSIS. Steps:
1. Welcome screen
2. License agreement
3. Install location (default: `%LOCALAPPDATA%\Toolio`)
4. Detect/bundle Python
5. Install Python package
6. Register OpenCode plugin
7. Verify installation
8. Finish

### 5. Homebrew (macOS)

```bash
brew install toolio
```

### 6. Linux shell installer

```bash
curl -fsSL https://toolio.dev/install.sh | sh
```

---

## 6. Global OpenCode Registration

### Mechanism

OpenCode discovers plugins via `~/.config/opencode/opencode.jsonc` with the global `plugin` array. Plugins are resolved from `~/.config/opencode/node_modules/`.

### Registration

```
~/.config/opencode/
├── opencode.jsonc          # plugin array includes toolio
└── node_modules/
    └── toolio/
        ├── toolio.ts        # TypeScript plugin
        └── package.json    # @opencode-ai/plugin dependency
```

### Config Format

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "~/.config/opencode/node_modules/superpowers",
    "@upstash/context7-opencode",
    "~/.config/opencode/node_modules/toolio"
  ]
}
```

---

## 7. Memory Isolation

Global installation does NOT mean global memory.

```
Agent
  ↓
Project
  ↓
Session
```

Memory stored in `{project}/.toolio/memory/` — per-project, not global.

Cross-project isolation:
- Project A memories cannot leak into Project B
- Each project has its own `.toolio/memory/` directory
- Session scope within project

---

## 8. Testing

### New Tests (29 categories)

1. CLI parsing
2. install
3. install idempotency
4. uninstall
5. uninstall safety
6. doctor
7. status
8. version
9. Python discovery
10. invalid Python discovery
11. LEREV_HOME
12. PATH bridge discovery
13. installed-package discovery
14. development fallback
15. global OpenCode configuration discovery
16. plugin registration
17. duplicate plugin prevention
18. malformed OpenCode config
19. unrelated plugin preservation
20. missing OpenCode
21. missing Python
22. permission errors
23. Windows paths
24. macOS paths
25. Linux paths
26. paths containing spaces
27. Unicode paths where practical
28. cross-project isolation
29. restart persistence

### Existing Tests

All 2056 existing tests must continue to pass.

### Validation

```
Existing 2056 tests: PASS
New tests: PASS
Total: PASS
Failures: 0
Skipped: 9

Global Toolio installation: PASS
OpenCode outside Toolio repo: PASS
Cross-project isolation: PASS
Restart persistence: PASS
```

---

## 9. Distribution Status Tracking

For each method, report:

```
IMPLEMENTED
TESTED
READY TO PUBLISH
PUBLISHED
```

Do NOT mark as published unless actually published.

---

## 10. Architectural Rules

Do NOT:
- Split Toolio into multiple products
- Create separate memory/core products
- Redesign V2.6
- Modify V2.5 routing semantics
- Modify V2.4.2 lifecycle semantics
- Duplicate security logic
- Duplicate retrieval logic
- Create an HTTP daemon
- Pass memory through CLI arguments
- Require Toolio repository as OpenCode working directory
- Copy the plugin into every project
- Merge project memory globally
- Delete unrelated OpenCode configuration
- Delete user memory during uninstall

---

## 11. Real OpenCode Test (Mandatory)

After implementation:

1. Install Toolio globally
2. Run `toolio doctor`
3. Start OpenCode from a directory that is NOT the Toolio repository
4. Verify Toolio loads
5. Use `toolio_status`
6. Store a memory
7. Recall it
8. Close OpenCode
9. Start OpenCode again
10. Recall the memory
11. Start OpenCode from another project
12. Verify memory isolation

This is the actual proof of global installation.

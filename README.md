<div align="center">

# Toolio

**Universal agent learning and memory system**

[![Version](https://img.shields.io/badge/version-2.6.0-blue?style=flat-square)](https://github.com/dksh3/toolio/releases)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-3800%2B%20passing-brightgreen?style=flat-square)](https://github.com/dksh3/toolio)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange?style=flat-square)](https://modelcontextprotocol.io/)

> Agents forget. Toolio remembers — what worked, what broke, and what your project already decided — and hands it back before the next task starts.

</div>

---

## Introduction

Every agent starts from zero. It re-reads the same files, re-derives the same decisions, and re-makes the same mistakes — every session, every task. Context windows fill up and get truncated. Nothing is learned.

**Toolio** is a tool system that sits behind any agent — not a single "learning layer", but 52 tools across memory, context, skills, planning, routing, and diagnostics. It stores what happened, compresses what no longer fits, recalls what matters before the next task starts, and learns from outcomes. It works with any agent that speaks [MCP](https://modelcontextprotocol.io/) or loads a plugin — coding, research, ops, support, or anything else.

- **Not a coding-agent tool.** Toolio runs behind *any* agent that speaks MCP or loads a plugin.
- **Nothing published yet.** Source install only — see [Install status](#install-status).
- **Honest numbers.** Every figure in this repo is counted from the repo itself by one script (`python toolio/islands/mkdata.py`).

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/dksh3/toolio.git
cd A-Toolio-For-AI

# 2. Install (editable, with the MCP extra)
pip install -e ".[mcp]"

# 3. Wire your agent
toolio install

# 4. Verify
toolio doctor
```

Then restart your agent. The `toolio`/`toolio` plugin (52 tools) and the MCP server become available.

> **Nothing is published to PyPI, npm, Homebrew, Chocolatey, or any installer channel.** The five steps above are the whole install. See [Install status](#install-status).

---

## What it does

| Without Toolio | With Toolio |
|---|---|
| Every session starts from zero | Memory persists across sessions and projects |
| Context window fills, then truncates | Context is compressed into named blocks; originals are kept |
| Decisions get re-derived | Decisions are recalled before the next task |
| Mistakes repeat | Failures are recorded and avoided |
| One agent, one window | One memory, shared across agents |

Core capabilities (52 tools total):

- **Memory** (9 tools) — store, recall, search, forget, lifecycle, observe, learn, knowledge, conflict detection, deduplication. Scoped per project; never leaks between projects.
- **Context engine** (5 tools) — count tokens, compress overflowing transcripts into named blocks, restore them on demand, inspect status and coexistence. Nothing is thrown away.
- **Skills** (13 tools) — create, search, use, evolve, share, and track agent skills (candidate → proven). Local + GitHub discovery, import, feedback.
- **Planning & precision** (12 tools) — clarify requirements, blueprint, edict, weave, compass, brainstorm, quantify, elicit, investigate, forge, chart, diagnose.
- **Routing & meta** (6 tools) — route decisions, confidence scoring, dashboard, progress, workflow, goal tracking.
- **MCP server** — all 52 tools over stdio, with budgeted resources (trimmed, never dumped) instead of a firehose.
- **CLI** — install, diagnose, visualize, run, and manage the whole system from the terminal.
- **Plugin** — auto-installs into OpenCode; works with any agent that speaks MCP or loads a plugin.

---

## How it works

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│  Agent   │────▶│  Bridge  │────▶│ Toolio engine│
│ (plugin/ │◀────│ (stdio)  │◀────│ (memory,     │
│  MCP)    │     │          │     │  context,    │
└──────────┘     └──────────┘     │  learning)   │
                                  └──────┬───────┘
                                         │
                                  ┌──────▼───────┐
                                  │ .toolio/     │
                                  │  memory/     │
                                  │  (per project)│
                                  └──────────────┘
```

- **Plugin path** — `toolio install` writes a plugin into your agent's config dir; the agent calls tools directly.
- **MCP path** — `python -m toolio.mcp` runs a stdio MCP server; any MCP client connects to it.
- **Storage** — memories live in `.toolio/memory/` inside the project (or a global dir), one JSON file per memory, plus an index.

---

## CLI

Run with `python -m toolio.cli <command>` (or `toolio <command>` if installed).

| Command | What it does |
|---|---|
| `version` | Print Toolio version |
| `status` | Show Toolio status |
| `install` | Install Toolio globally for OpenCode |
| `doctor` | Run diagnostics |
| `uninstall` | Uninstall from OpenCode |
| `mcp` | Run the MCP server over stdio, or print client config |
| `skills` | Skill management (list, search, create, use, feedback, status, evolve, …) |
| `context` | Context engine: status, compress, restore, switch, keep |
| `visualize` | Render visuals (sparkline, heatmap, donut, radar, …) |
| `clarion` | Discovery interview (idea → requirements) |
| `blueprint` | Design spec from an interview (idea → spec) |
| `edict` | Ordered commands + directives (spec → execution) |
| `weave` | Roadmap + timeline (plan → phases/lanes/critical path) |
| `compass` | Acceptance scenarios + checklist |
| `brainstorm` | Brainstorm, score, cluster, select (any topic, any domain) |
| `quantify` | Deterministic money/percent/risk/date checks with provenance |
| `elicit` | Find the material questions a plan is missing |
| `investigate` | Adaptive diagnosis (find what's wrong, why it keeps happening) |

Optional extras: `pip install -e ".[dev,web,semantic,mcp,ctx,all]"`.

---

## MCP

Toolio speaks MCP over stdio. Any MCP client can connect.

```json
{
  "mcpServers": {
    "toolio": {
      "command": "python",
      "args": ["-m", "toolio.mcp"]
    }
  }
}
```

Or generate the block for your client:

```bash
toolio mcp config claude   # .mcp.json / claude_desktop_config.json
toolio mcp config codex    # ~/.codex/config.toml
toolio mcp config          # generic block
```

**Budgeted resources** (trimmed, never dumped):

| Resource | What it returns |
|---|---|
| `toolio://context` | The live window, trimmed to the budget |
| `toolio://memories` | Stored memories |
| `toolio://skills` | Available skills |
| `toolio://prompt/relevant_context` | Relevant context for the current task |

Plus a `relevant_context` prompt and 52 `toolio_*` functions.

---

## Configuration & data

- **Memory location** — `.toolio/memory/` inside the project (or a global dir). One JSON file per memory, plus an index.
- **Project scoping** — memories are tagged per project; recall filters by project by default.
- **Environment variables** — `TOOLIO_LLM_API_KEY` (and friends) for the optional LLM-in-the-loop features. Without them, Toolio falls back to heuristics (no crash).
- **Optional extras** — `dev` (pytest, ruff, mypy), `web` (httpx, bs4), `semantic` (fastembed), `mcp` (mcp sdk), `ctx` (tree-sitter), `all`.

---

## Install status

Honest. Nothing is published. Source install is the only working path.

| Channel | Status |
|---|---|
| Source (`git clone` + `pip install -e .`) | ✅ Works today |
| PyPI (`pip install toolio`) | ⏳ Not published |
| npm | ⏳ Not published |
| Homebrew | ⏳ Not published |
| Chocolatey | ⏳ Not published |
| Windows installer | ⏳ Not built |
| Linux install script | ⏳ Not available |

If you want a published package, open an issue — the packaging scaffolding exists under `packaging/`.

---

## Development

```bash
# Install dev deps
pip install -e ".[dev,all]"

# Run the test suite
python -m pytest

# Run a focused subset
python -m pytest tests/unit/test_toolio_identity_compat.py -q
```

- **Layout** — `toolio/` (engine), `tests/` (unit + stress + fuzz), `docs/` (reference), `packaging/` (unbuilt channels).
- **Contributing** — PRs welcome. Keep the honest-numbers rule: every figure must be reproducible by a script in the repo.
- **Stress tests** — `tests/test_fuzz_*.py` run 10k–100k iterations; some are slow.

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

⭐️ **Show your support** — give this project a star if it helped you.

[![GitHub stars](https://img.shields.io/github/stars/dksh3/toolio?style=social)](https://github.com/dksh3/toolio)

</div>

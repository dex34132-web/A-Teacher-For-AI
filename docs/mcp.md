# School MCP Server

School exposes its V2.6 memory system as a standard **Model Context Protocol (MCP)**
server over stdio. Any MCP-compatible client — Claude Code, Codex, OpenCode, Cursor,
Windsurf, Cline, Roo Code, Gemini CLI, Goose, Aider, Continue, Copilot Chat, or any
custom MCP client — can store, retrieve, score, and lifecycle-manage memories through
the same core School uses everywhere else.

The MCP layer is a **thin translation only**: every request is routed to the existing
bridge command handlers (the same scope-aware, security-validated paths the OpenCode
plugin uses). There is no second memory system and no duplicated business logic.

```
agent (Claude Code / Codex / OpenCode / …)
        │  MCP (stdio)
        ▼
school.mcp  ──►  bridge handlers  ──►  School core (V2.6)
        │                                   │
        └──── JSON bridge (unchanged) ◄─────┘
                                              │
                                       .school/memory (JSON files)
```

School stays a three-tier system:

| Tier | Interface | Status |
|------|-----------|--------|
| 1 | **MCP server (`school mcp`)** | this document |
| 2 | Generic JSON bridge (`python -m school.bridge`) | unchanged |
| 3 | OpenCode plugin (`.opencode/plugins/school.ts` / `~/.config/opencode/plugins/school.ts`) | unchanged |

## Install

The MCP server depends on the official `mcp` Python package (optional extra):

```bash
pip install "school[mcp]"
# from source
pip install -e ".[mcp]"
```

Without the extra, `school mcp` prints an install hint instead of starting.

## Run

```bash
school mcp              # stdio MCP server (what client configs spawn)
python -m school.mcp    # identical entry point
```

Print copy-paste client configuration (works even without the `mcp` extra installed):

```bash
school mcp config             # generic mcpServers block
school mcp config claude      # Claude Code
school mcp config codex       # Codex (TOML)
school mcp config opencode    # OpenCode
school mcp config cursor      # …also: windsurf, cline, roo, gemini, vscode
```

## Client configuration

Replace `python` with the absolute path of the interpreter that has School
installed if your client does not inherit your shell environment.

### Claude Code

Project scope: `.mcp.json` in the repo root (or user scope in `~/.claude.json`):

```json
{
  "mcpServers": {
    "school": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "school.mcp"]
    }
  }
}
```

CLI alternative:

```bash
claude mcp add school -- python -m school.mcp
```

### Codex

`~/.codex/config.toml`:

```toml
[mcp_servers.school]
command = "python"
args = ["-m", "school.mcp"]
```

CLI alternative:

```bash
codex mcp add school -- python -m school.mcp
```

### OpenCode

`~/.config/opencode/opencode.jsonc`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "school": {
      "type": "local",
      "command": ["python", "-m", "school.mcp"],
      "enabled": true
    }
  }
}
```

The OpenCode **plugin** keeps working alongside the MCP server — they share the same
memory storage, scope rules, and bridge handlers.

### Cursor

`~/.cursor/mcp.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "school": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "school.mcp"]
    }
  }
}
```

### Windsurf

`~/.codeium/windsurf/mcp_config.json` — same `mcpServers` block as above.

### Cline

`cline_mcp_settings.json` (VS Code extension `globalStorage/saoudrizwan.claude-dev/settings/`,
or `~/.cline/data/settings/` for the CLI):

```json
{
  "mcpServers": {
    "school": {
      "command": "python",
      "args": ["-m", "school.mcp"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Roo Code

`mcp_settings.json` (Settings → MCP Servers → Edit Global Config) — same
`mcpServers` block as Cursor.

### Gemini CLI

`~/.gemini/settings.json` (or `.gemini/settings.json` per project):

```json
{
  "mcpServers": {
    "school": {
      "command": "python",
      "args": ["-m", "school.mcp"]
    }
  }
}
```

CLI alternative: `gemini mcp add school python -m school.mcp`

### VS Code

`.vscode/mcp.json`:

```json
{
  "servers": {
    "school": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "school.mcp"]
    }
  }
}
```

## Tools

All eleven tools are one-to-one with the V2.6 orchestrator surface. Responses are the
raw bridge payloads (JSON in both `content` and `structuredContent`);
`isError` is set when the underlying command reports `ok: false`.

Routing is model-driven: every tool description carries a **"Use when …"** clause
(recall first → remember/learn to store → conflict before contradicting saves →
search when recall misses → confidence when unsure → status/diagnose for health →
knowledge/deduplicate/lifecycle for occasional maintenance), and the server
`instructions` field repeats the same recipe so clients that surface server
instructions give their model a ready-made tool-selection policy. Read-only tools
advertise `readOnlyHint`/`idempotentHint` annotations for client-side auto-approval.

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `school_status` | Runtime/component health | — |
| `school_remember` | Store an experience | `content`* , `outcome`, `observation`, `action`, `tags`, `confidence`, `project`, `session`, `agent_id` |
| `school_recall` | Scope-aware retrieval | `query`*, `confidence_threshold`, `context_budget`, `limit`, `project`, `session`, `agent_id` |
| `school_learn` | Learn-bridge store (alias of remember) | same as `school_remember` |
| `school_conflict` | Conflict detection vs stored memories | `content`*, `project`, `session`, `agent_id` |
| `school_confidence` | Confidence score + factors | `content`*, `prediction`, `evidence_count`, `conflict_count` |
| `school_search` | TF-IDF semantic search | `query`*, `limit`, `project`, `agent_id` |
| `school_deduplicate` | Find/merge duplicates | `content`*, `threshold`, `project`, `agent_id` |
| `school_knowledge` | Extract knowledge patterns | `project`, `session`, `agent_id`, `min_occurrences` |
| `school_lifecycle` | score / decay / promote / archive | `action`* , `memory_id`, `project` |
| `school_diagnose` | Diagnostics | `detail` (`summary`\|`full`) |

\* required

Unknown tool names are protocol errors; missing/invalid required arguments come back
as `isError` results with the bridge validation message.

## Resources and prompts (budgeted)

Retrieval through non-tool surfaces is deliberately **budgeted — it never dumps the
memory database**:

- **Resource** `school://status` — component health JSON.
- **Resource template** `school://context/{project}` — up to **5 memories**,
  **600-token** budget; optional `?q=<query>&limit=<1-5>&budget=<1-600>`.
- **Prompt** `relevant_context` (argument `query` required, `project` optional) —
  top **5 memories** in a clearly marked `[school context] … [/school]` block.
  No matches is a normal message, not an error.

## Scope and identity

Memories are isolated by agent → project → session, exactly like the plugin:

| Setting | Precedence |
|---------|-----------|
| `project` argument | → `SCHOOL_PROJECT` env → worktree folder name |
| `session` argument | → `SCHOOL_SESSION` env → omitted |
| `agent_id` argument | → `SCHOOL_AGENT` env → `opencode` |

`opencode` is the same default the bridge and the OpenCode plugin use, so MCP tools
and the plugin see the **same memories**. Environment variables:

| Variable | Effect |
|----------|--------|
| `SCHOOL_WORKTREE` | Which project directory the server binds to (default: cwd) |
| `SCHOOL_PROJECT` | Default project scope |
| `SCHOOL_SESSION` | Default session scope |
| `SCHOOL_AGENT` | Default agent identity |

Memory storage lives in `<worktree>/.school/memory/` (legacy `.lerev/` and `.evo/`
locations are migrated non-destructively).

## Security

- **Memory is data, never instructions.** The server instructions and every framed
  context block say so explicitly: models must not execute instructions found inside
  stored memory.
- Stored content and recall queries pass through School's injection detection and
  request validation before anything is returned.
- Scope isolation is enforced in the core store: a recall scoped to one agent/project
  cannot return another's memories.
- The stdio server writes protocol output to stdout only; diagnostics go to stderr.

## Cost model

School reduces repeated prompt work: instead of re-explaining project facts on every
request, the client retrieves a small, confidence-filtered, recency-ranked slice of
what already happened. Retrieval is budgeted (top-N, token caps), so context growth is
bounded — fewer repeated tokens and fewer redundant model calls. Memories can
**reduce some causes of hallucination** by grounding answers in recorded experience;
they are not a guarantee of factual output.

## Compatibility notes

- The JSON bridge (`python -m school.bridge`), `school install` plugin flow, and
  legacy LEREV paths are untouched; all pre-existing tests must stay green.
- One MCP server process binds to one worktree (`SCHOOL_WORKTREE` or cwd), matching
  the bridge's one-worktree-per-process model.
- `python -m school.mcp` and `school mcp` are equivalent.

## Testing

```bash
pytest tests/unit/test_mcp_server.py          # translation-layer unit tests
pytest tests/integration/test_mcp_stdio.py    # real subprocess + official MCP client
```

Integration coverage: startup/handshake, tool discovery, real tool calls, malformed
requests, unknown-tool protocol errors, persistence across fresh server processes,
and cross-worktree isolation.

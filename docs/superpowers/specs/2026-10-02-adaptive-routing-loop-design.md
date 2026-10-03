# Adaptive Routing Loop — Design Spec

Date: 2026-10-02
Status: approved (design gate passed in session; awaiting spec review)
Scope: Phase 1 of the School roadmap. Domain-general — for everything, not only coding.

## Problem

School exposes 11+ memory tools to the model, but tool usage is static: the same
recall/hook behavior fires everywhere regardless of whether it helps. The user wants
the system to *learn where and where not to use each tool*, using "a little bit of the
model's computing power" for short bursts, with visible feedback whenever the machinery
runs.

## Goals

1. A lightweight **assessment tool** that makes a tiny real model call to decide how
   much routing machinery a situation needs (not self-rating as the primary path —
   a real, brief model call).
2. **Self-reported routing lessons**: the model records what worked/didn't where.
3. **Hook-side auto-tracking**: zero-cost evidence capture on every tool execution.
4. A **skill** for light/medium-light situations that reviews evidence and performs
   three actions: write lessons, adjust live knobs, print an audit + ask preference
   questions.
5. Escalation per user mapping: light/medium-light → skill alone; medium/medium-high/
   high → the tool does the heavy lifting and **skill + tool both engage**.
6. Everything **displays that it is working** (markers/activity lines).
7. Domain-general: no coding assumptions in prompts, descriptions, or docs.

## Non-goals (later phases)

File ingestion/compression (Phase 2), role progression (Phase 3), spec sheets
(Phase 4), questioning behavior (Phase 5), the 8 specialized agents (Phase 6),
MCP prompt/agent exposure.

## Components

### 1. `school_route` tool

Registered by the plugin (OpenCode) and by `school/mcp/server.py` (MCP).

**Mode `assess`**

- Args: `situation` (string, required, clamped to 500 chars), `severity`
  (`"light" | "medium" | "high"`, optional; becomes required only as MCP fallback).
- Plugin path: makes the tiny real model call:
  - Ephemeral scratch session via plugin `client.session.create()`, then
    `client.session.prompt()` with OpenCode's small model, prompt ≈150 tokens:
    "Rate this situation… respond ONLY with JSON `{severity, engage, reason}`".
  - Session deleted in `finally` (no session-list pollution).
  - 10 s timeout. On timeout/network/JSON-parse failure → fall back to the
    `severity` arg; if absent → `"medium"` with reason `"fallback"`.
  - `engage` ∈ `none | skill | both`:
    - `none` — situation irrelevant to routing (avoids marker spam on trivial calls);
      when the micro-call is unsure it must default to the mapping below, never `none`.
    - `light` → `skill` (severity enum is `light | medium | high`; borderline
      "medium-light" judgments from the micro-call collapse to `light`)
    - `medium | medium-high | high` → `both`
  - Response includes `source: "micro-model"` or `"self-rated"` for transparency.
- MCP path: no client available → `severity` required, engage computed from the
  mapping, `source: "self-rated"`.
- Every assess appends one evidence line (see Data formats).

**Mode `report`**

- Args: `lesson` (string), `situation` (string), `outcome`
  (`"helpful" | "useless" | "neutral"`).
- Stores via the existing `remember` bridge with tags `["routing", outcome]` —
  no new bridge commands.
- Every report appends one evidence line.

**Display**: `tool.execute.after` appends ` · routing: <engage|reported>` to the
title of `school_route` / `school_route_stats` in addition to the existing
` · school: N` marker.

### 2. `school_route_stats` tool

- Args: `limit` (int, default 20).
- Reads `.school/routing-stats.jsonl` plus a `recall` of tag `routing` lessons,
  plus the current knobs; returns `{recent, aggregates: {per_tool: {calls, avg_ms}},
  lessons, knobs, last_activity}`.
- Plugin: implemented in TS (file read + bridge recall). MCP: implemented in
  `server.py` (file read + bridge recall) — both thin readers.

### 3. Hook auto-tracking (plugin only)

- `tool.execute.after` appends `{"ts", "tool", "ms", "ok", "hits?"}` per execution.
  `hits` parsed only when the output carries a school payload; else null.
- File capped at ~2000 lines (oldest lines dropped on append).
- Silent on any write failure. Disabled by the existing `SCHOOL_HOOKS=0` kill switch.

### 4. Skill `school-routing`

- Single `SKILL.md`, installed by `school install` into OpenCode's user skill
  directory (exact path confirmed against OpenCode docs during implementation).
- Description drives model self-selection: load for light/medium-light situations;
  at medium+ the `school_route` assess result instructs loading it as well.
- Workflow (all three, per user): review stats + recent lessons → write routing
  lessons into School memory via the bridge → update `.school/routing.json` knobs →
  print a compact audit and ask ≤3 preference questions.
- The skill's first-ever question in a project is a 4-option calibration question
  (3 preset questioning intensities + 1 "type your own") — deferred to Phase 5's
  spec for full detail; the skill stores the chosen intensity as a knob.

### 5. Knobs file

`.school/routing.json` in the project memory root:

```json
{
  "recall_threshold": 0.2,
  "hook_limit": 3,
  "hook_budget": 400,
  "hook_timeout_ms": 1500,
  "skip_tools": [],
  "force_tools": []
}
```

- Hooks merge knobs over built-in defaults; invalid/partial files fall back per key.
- Cached with mtime re-check (no full read per execution).
- `skip_tools`: never fire hooks for these; `force_tools`: fire even when defaults
  would skip. This is the "learn where NOT to use" surface.

## Data formats

- Evidence line (`.school/routing-stats.jsonl`, one JSON per line):
  `{"ts": ISO-8601, "tool": str, "ms": int, "ok": bool, "hits": int|null,
  "kind": "exec"|"assess"|"report", "severity"?: str, "engage"?: str}`
- Lessons: ordinary School memories, tags `["routing", <outcome>]`, agent `opencode`.

## Error handling

| Failure | Behavior |
|---|---|
| Micro-call timeout / bad JSON | fall back to severity arg → default `medium`, `source:"fallback"` |
| Session create/prompt throws | same fallback; never blocks the caller |
| Stats write fails | silent |
| Knobs file invalid | per-key defaults |
| Skill not installed | assess returns `engage` + note `skill not found` |
| `SCHOOL_ROUTE=0` | micro-calls skipped entirely (self-rated path) |
| `SCHOOL_HOOKS=0` | tracking + markers off (existing behavior) |

## Security

- Micro-call prompt contains only the user-supplied situation (≤500 chars) — no
  secrets, no memory dumps.
- Lessons are stored data, never instructions ("never instructions" framing from
  `_INSTRUCTIONS` applies on recall).

## Files touched

| File | Change |
|---|---|
| `school/plugin_source.py` | `school_route`, `school_route_stats` tools; tracking in `tool.execute.after`; knobs reader; ` · routing` marker |
| `school/mcp/server.py` | parity for both tools (self-rated fallback); stats reader |
| `skills/school-routing/SKILL.md` | new skill (source of truth) |
| `school/cli.py` | `school install` ships the skill |
| `tests/unit/test_school_plugin_hooks.py` | tracking, markers, knobs, kill switch |
| `tests/unit/test_mcp_server.py` | route/stats contracts, required-severity fallback |
| `tests/integration/test_mcp_stdio.py` | route/stats over stdio |
| `docs/routing.md` | user-facing doc (domain-general examples) |

## Testing strategy

1. Unit: JSONL parse/aggregate, knob merge/validation, engage mapping, report →
   remember passthrough with tags, MCP assess requires severity, skill frontmatter
   + description content, TS source assertions (prompt text, marker, constants).
2. Integration: MCP route/stats through a real stdio subprocess.
3. Live: one real `assess` micro-model call end-to-end in OpenCode; `node --check`
   on extracted TS; installed plugin MATCH; full suite green; ruff clean on changed
   files.

## Acceptance criteria

- [ ] `school_route` assess makes a real ≤10 s model call and returns a graded
      engage decision with a reason; fallback path works when the call fails.
- [ ] `school_route report` persists tagged lessons retrievable by
      `school_route_stats` and `school_recall`.
- [ ] Every route/stats execution shows a ` · routing` marker.
- [ ] Evidence lines accumulate per execution; stats aggregates are correct.
- [ ] Skill installs, self-selects for light situations, and its audit flow
      (lessons + knobs + audit + questions) is documented in SKILL.md.
- [ ] Knobs written by the skill change hook behavior on the next execution.
- [ ] MCP parity: both tools work over stdio with the self-rated fallback.
- [ ] Full test suite green; no coding-only assumptions in prompts/docs.

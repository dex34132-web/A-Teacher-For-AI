### Task 1: TS routing core — helpers, knobs, evidence tracking, routing marker

**Files:**
- Modify: `teacher/plugin_source.py` (imports line 12; helpers after `hooksEnabled` ~line 246; `recallForExecution` ~line 321; `tool.execute.before/after` ~lines 968-996)
- Test: `tests/unit/test_teacher_routing.py` (create)

**Interfaces:**
- Consumes: existing `fileExists`, `resolve`, `hooksEnabled`, `HOOK_*` consts, `executionRecalls` map, `hasMemoryRoot`.
- Produces (TS, module scope): `engageFor(severity: string): string`, `normalizeSeverity(v: unknown): string`, `memoryRoot(worktree: string): string`, `readKnobs(worktree: string): RoutingKnobs`, `appendEvidence(worktree: string, entry: Record<string, unknown>): void`, consts `ROUTE_TIMEOUT_MS`, `ROUTE_STATS_MAX_LINES`, `DEFAULT_KNOBS`; map `executionStart: Map<string, number>`; `recallForExecution` now knob-aware; after-hook appends ` · routing: <engagement>` when `output.metadata.engagement` is a string.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_teacher_routing.py`:

```python
"""TS-source contract tests for the adaptive routing loop (Phase 1)."""

import re

from teacher.plugin_source import TS_PLUGIN_SOURCE


class TestRoutingCoreHelpers:
    def test_constants_present(self):
        assert "const ROUTE_TIMEOUT_MS = 10000" in TS_PLUGIN_SOURCE
        assert "const ROUTE_STATS_MAX_LINES = 2000" in TS_PLUGIN_SOURCE

    def test_engage_mapping(self):
        match = re.search(
            r"function engageFor\(severity: string\): string \{\n(.*?)\n\}",
            TS_PLUGIN_SOURCE,
            re.S,
        )
        assert match, "engageFor missing"
        body = match.group(1)
        assert '"light" ? "skill" : "both"' in body.replace(" ", " ").replace(
            "  ", ""
        ) or ('"light"' in body and '"skill"' in body and '"both"' in body)

    def test_evidence_append_and_cap(self):
        assert "function appendEvidence(" in TS_PLUGIN_SOURCE
        assert "routing-stats.jsonl" in TS_PLUGIN_SOURCE
        assert "ROUTE_STATS_MAX_LINES" in TS_PLUGIN_SOURCE
        assert "appendFileSync" in TS_PLUGIN_SOURCE
        assert "mkdirSync" in TS_PLUGIN_SOURCE

    def test_knobs_reader(self):
        assert "function readKnobs(" in TS_PLUGIN_SOURCE
        assert "routing.json" in TS_PLUGIN_SOURCE
        assert "skip_tools" in TS_PLUGIN_SOURCE
        assert "force_tools" in TS_PLUGIN_SOURCE
        assert "statSync" in TS_PLUGIN_SOURCE  # mtime cache check

    def test_knobs_used_in_recall_path(self):
        # recallForExecution reads knobs and applies them to the bridge call.
        idx = TS_PLUGIN_SOURCE.index("const recallForExecution")
        end = TS_PLUGIN_SOURCE.index("return {", idx)
        block = TS_PLUGIN_SOURCE[idx:end]
        assert "readKnobs" in block
        assert "confidence_threshold" in block
        assert "knobs.recall_threshold" in block

    def test_before_hook_skip_force(self):
        idx = TS_PLUGIN_SOURCE.index('"tool.execute.before"')
        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index('"tool.execute.after"')]
        assert "skip_tools" in block
        assert "force_tools" in block

    def test_after_hook_tracks_evidence_and_start_time(self):
        idx = TS_PLUGIN_SOURCE.index('"tool.execute.after"')
        end = TS_PLUGIN_SOURCE.index('"chat.message"', idx)
        block = TS_PLUGIN_SOURCE[idx:end]
        assert 'kind: "exec"' in block
        assert "executionStart" in block
        assert "Date.now()" in block

    def test_routing_marker_suffix(self):
        # After-hook appends the routing marker from metadata.engagement.
        idx = TS_PLUGIN_SOURCE.index('"tool.execute.after"')
        end = TS_PLUGIN_SOURCE.index('"chat.message"', idx)
        block = TS_PLUGIN_SOURCE[idx:end]
        assert "routing: " in block
        assert "metadata" in block

    def test_node_fs_imports_extended(self):
        match = re.search(r'import \{ ([^}]+) \} from "node:fs"', TS_PLUGIN_SOURCE)
        assert match, "node:fs import missing"
        names = {n.strip() for n in match.group(1).split(",")}
        assert {"existsSync", "appendFileSync", "readFileSync", "writeFileSync",
                "mkdirSync", "statSync"} <= names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_teacher_routing.py -q`
Expected: FAIL (helpers/markers absent).

- [ ] **Step 3: Implement TS core**

In `teacher/plugin_source.py`:

1. Replace the import line:
```python
from "node:fs"  →  import { existsSync, appendFileSync, readFileSync, writeFileSync, mkdirSync, statSync } from "node:fs"
```

2. After `hooksEnabled()` (line ~246) insert:

```ts
const ROUTE_TIMEOUT_MS = 10000
const ROUTE_STATS_MAX_LINES = 2000

interface RoutingKnobs {
  recall_threshold: number
  hook_limit: number
  hook_budget: number
  hook_timeout_ms: number
  skip_tools: string[]
  force_tools: string[]
}

const DEFAULT_KNOBS: RoutingKnobs = {
  recall_threshold: HOOK_THRESHOLD,
  hook_limit: HOOK_LIMIT,
  hook_budget: HOOK_BUDGET,
  hook_timeout_ms: HOOK_TIMEOUT_MS,
  skip_tools: [],
  force_tools: [],
}

function engageFor(severity: string): string {
  return severity === "light" ? "skill" : "both"
}

function normalizeSeverity(value: unknown): string {
  const s = String(value ?? "").toLowerCase().trim()
  return s === "light" || s === "medium" || s === "high" ? s : "medium"
}

function memoryRoot(worktree: string): string {
  for (const dir of [".teacher", ".lerev", ".evo"]) {
    const root = resolve(worktree, dir)
    if (fileExists(resolve(root, "memory"))) return root
  }
  return resolve(worktree, ".teacher")
}

function clampNum(v: unknown, fallback: number, lo: number, hi: number): number {
  const n = Number(v)
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback
}

function strList(v: unknown): string[] {
  return Array.isArray(v) ? v.map((x) => String(x)) : []
}

let knobsCache: { mtimeMs: number; knobs: RoutingKnobs } | null = null

function readKnobs(worktree: string): RoutingKnobs {
  try {
    const file = resolve(memoryRoot(worktree), "routing.json")
    if (!fileExists(file)) return DEFAULT_KNOBS
    const mtimeMs = statSync(file).mtimeMs
    if (knobsCache && knobsCache.mtimeMs === mtimeMs) return knobsCache.knobs
    const raw = JSON.parse(readFileSync(file, "utf8")) as Record<string, unknown>
    const knobs: RoutingKnobs = {
      recall_threshold: clampNum(raw.recall_threshold, DEFAULT_KNOBS.recall_threshold, 0, 1),
      hook_limit: clampNum(raw.hook_limit, DEFAULT_KNOBS.hook_limit, 1, 50),
      hook_budget: clampNum(raw.hook_budget, DEFAULT_KNOBS.hook_budget, 64, 8000),
      hook_timeout_ms: clampNum(raw.hook_timeout_ms, DEFAULT_KNOBS.hook_timeout_ms, 250, 5000),
      skip_tools: strList(raw.skip_tools),
      force_tools: strList(raw.force_tools),
    }
    knobsCache = { mtimeMs, knobs }
    return knobs
  } catch {
    return DEFAULT_KNOBS
  }
}

function appendEvidence(worktree: string, entry: Record<string, unknown>): void {
  try {
    const root = memoryRoot(worktree)
    if (!fileExists(root)) mkdirSync(root, { recursive: true })
    const file = resolve(root, "routing-stats.jsonl")
    if (fileExists(file)) {
      const lines = readFileSync(file, "utf8").split("\n").filter((l) => l.trim())
      if (lines.length >= ROUTE_STATS_MAX_LINES * 2) {
        writeFileSync(file, lines.slice(-ROUTE_STATS_MAX_LINES).join("\n") + "\n", "utf8")
      }
    }
    appendFileSync(file, JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n", "utf8")
  } catch {
    // Evidence tracking must never break execution.
  }
}
```

3. In `recallForExecution`, replace `HOOK_THRESHOLD/HOOK_BUDGET/HOOK_LIMIT/HOOK_TIMEOUT_MS` usages with `knobs.recall_threshold / knobs.hook_budget / knobs.hook_limit / knobs.hook_timeout_ms`, reading `const knobs = readKnobs(ctx.worktree)` at the top of the function (after the `!bridge` guard).

4. In `tool.execute.before`: after `hooksEnabled()` check add:
```ts
const knobs = readKnobs(ctx.worktree)
if (knobs.skip_tools.includes(input.tool) && !knobs.force_tools.includes(input.tool)) {
  executionRecalls.set(input.callID, null)
  return
}
executionStart.set(input.callID, Date.now())
```
And declare near `promptRecalls`: `const executionStart = new Map<string, number>()`.

5. In `tool.execute.after`, after the marker line (`const marker = ...`), add before title assignment:
```ts
const started = executionStart.get(input.callID) ?? Date.now()
executionStart.delete(input.callID)
const meta = (output as any).metadata as Record<string, unknown> | undefined
const engagement = meta && typeof meta.engagement === "string" ? meta.engagement : ""
const routingSuffix = engagement ? ` · routing: ${engagement}` : ""
output.title = `${output.title || input.tool}${marker}${routingSuffix}`
appendEvidence(ctx.worktree, {
  kind: "exec",
  tool: input.tool,
  ms: Date.now() - started,
  ok: typeof output.output === "string" && !output.output.startsWith("Error"),
  hits: rec ? rec.hits : null,
})
```
(replacing the existing single `output.title = ...` line; keep the existing context-block logic untouched).

- [ ] **Step 4: Extract TS, node --check, reinstall, MATCH**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\python.exe" -c "import pathlib; from teacher.plugin_source import TS_PLUGIN_SOURCE; p=pathlib.Path(r'C:\Users\dex34\AppData\Local\Temp\opencode\teacher_check.ts'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(TS_PLUGIN_SOURCE, encoding='utf-8'); print(p)"
node --check "C:\Users\dex34\AppData\Local\Temp\opencode\teacher_check.ts"
```
Expected: exit 0. Then `& ".venv\Scripts\python.exe" -m teacher install --force` and the MATCH snippet from prior sessions (read installed file, compare to `TS_PLUGIN_SOURCE`).

- [ ] **Step 5: Run tests to verify they pass**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_teacher_routing.py -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```powershell
git add teacher/plugin_source.py tests/unit/test_teacher_routing.py; if ($?) { git commit -m "feat(plugin): routing core - knobs, evidence tracking, engage mapping, routing marker" }
```

---


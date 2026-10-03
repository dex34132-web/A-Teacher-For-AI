## Commits
2c54e06 feat(plugin): routing core - knobs, evidence tracking, engage mapping, routing marker

## Stat
 teacher/plugin_source.py                | 123 ++++++++++++++++++++++++++++++--
 tests/unit/test_teacher_plugin_hooks.py |  11 ++-
 tests/unit/test_teacher_routing.py      |  75 +++++++++++++++++++
 3 files changed, 200 insertions(+), 9 deletions(-)

## Diff (-U10)
diff --git a/teacher/plugin_source.py b/teacher/plugin_source.py
index 9aa6c7d..77d760a 100644
--- a/teacher/plugin_source.py
+++ b/teacher/plugin_source.py
@@ -2,21 +2,22 @@
 
 from __future__ import annotations
 
 from teacher import __version__ as _TEACHER_VERSION
 
 _TS_PLUGIN_TEMPLATE = r'''import { tool } from "@opencode-ai/plugin/tool"
 import type { Plugin } from "@opencode-ai/plugin"
 import { execFile, spawn } from "node:child_process"
 import { promisify } from "node:util"
 import { resolve } from "node:path"
-import { existsSync } from "node:fs"
+import { existsSync, appendFileSync, readFileSync, writeFileSync,
+  mkdirSync, statSync } from "node:fs"
 import { execSync } from "node:child_process"
 
 const execFileAsync = promisify(execFile)
 
 /** Teacher version this plugin was generated from ΓÇö canonical source: teacher.__version__. */
 const TEACHER_VERSION = "__TEACHER_VERSION__"
 
 /**
  * Find a usable Python interpreter.
  */
@@ -234,24 +235,115 @@ interface RecallOutcome {
   hits: number
   lines: string[]
 }
 
 /** In-flight execution recalls, keyed by tool callID. */
 const executionRecalls = new Map<string, RecallOutcome | null>()
 
 /** Prompt recalls, keyed by sessionID ΓÇö injected exactly once per prompt. */
 const promptRecalls = new Map<string, RecallOutcome>()
 
+/** Execution start timestamps (ms), keyed by tool callID ΓÇö evidence timing. */
+const executionStart = new Map<string, number>()
+
 function hooksEnabled(): boolean {
   return process.env.TEACHER_HOOKS !== "0"
 }
 
+const ROUTE_TIMEOUT_MS = 10000
+const ROUTE_STATS_MAX_LINES = 2000
+
+interface RoutingKnobs {
+  recall_threshold: number
+  hook_limit: number
+  hook_budget: number
+  hook_timeout_ms: number
+  skip_tools: string[]
+  force_tools: string[]
+}
+
+const DEFAULT_KNOBS: RoutingKnobs = {
+  recall_threshold: HOOK_THRESHOLD,
+  hook_limit: HOOK_LIMIT,
+  hook_budget: HOOK_BUDGET,
+  hook_timeout_ms: HOOK_TIMEOUT_MS,
+  skip_tools: [],
+  force_tools: [],
+}
+
+function engageFor(severity: string): string {
+  return severity === "light" ? "skill" : "both"
+}
+
+function normalizeSeverity(value: unknown): string {
+  const s = String(value ?? "").toLowerCase().trim()
+  return s === "light" || s === "medium" || s === "high" ? s : "medium"
+}
+
+function memoryRoot(worktree: string): string {
+  for (const dir of [".teacher", ".lerev", ".evo"]) {
+    const root = resolve(worktree, dir)
+    if (fileExists(resolve(root, "memory"))) return root
+  }
+  return resolve(worktree, ".teacher")
+}
+
+function clampNum(v: unknown, fallback: number, lo: number, hi: number): number {
+  const n = Number(v)
+  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback
+}
+
+function strList(v: unknown): string[] {
+  return Array.isArray(v) ? v.map((x) => String(x)) : []
+}
+
+let knobsCache: { mtimeMs: number; knobs: RoutingKnobs } | null = null
+
+function readKnobs(worktree: string): RoutingKnobs {
+  try {
+    const file = resolve(memoryRoot(worktree), "routing.json")
+    if (!fileExists(file)) return DEFAULT_KNOBS
+    const mtimeMs = statSync(file).mtimeMs
+    if (knobsCache && knobsCache.mtimeMs === mtimeMs) return knobsCache.knobs
+    const raw = JSON.parse(readFileSync(file, "utf8")) as Record<string, unknown>
+    const knobs: RoutingKnobs = {
+      recall_threshold: clampNum(raw.recall_threshold, DEFAULT_KNOBS.recall_threshold, 0, 1),
+      hook_limit: clampNum(raw.hook_limit, DEFAULT_KNOBS.hook_limit, 1, 50),
+      hook_budget: clampNum(raw.hook_budget, DEFAULT_KNOBS.hook_budget, 64, 8000),
+      hook_timeout_ms: clampNum(raw.hook_timeout_ms, DEFAULT_KNOBS.hook_timeout_ms, 250, 5000),
+      skip_tools: strList(raw.skip_tools),
+      force_tools: strList(raw.force_tools),
+    }
+    knobsCache = { mtimeMs, knobs }
+    return knobs
+  } catch {
+    return DEFAULT_KNOBS
+  }
+}
+
+function appendEvidence(worktree: string, entry: Record<string, unknown>): void {
+  try {
+    const root = memoryRoot(worktree)
+    if (!fileExists(root)) mkdirSync(root, { recursive: true })
+    const file = resolve(root, "routing-stats.jsonl")
+    if (fileExists(file)) {
+      const lines = readFileSync(file, "utf8").split("\n").filter((l) => l.trim())
+      if (lines.length >= ROUTE_STATS_MAX_LINES * 2) {
+        writeFileSync(file, lines.slice(-ROUTE_STATS_MAX_LINES).join("\n") + "\n", "utf8")
+      }
+    }
+    appendFileSync(file, JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n", "utf8")
+  } catch {
+    // Evidence tracking must never break execution.
+  }
+}
+
 function hasMemoryRoot(worktree: string): boolean {
   for (const dir of [".teacher", ".lerev", ".evo"]) {
     if (fileExists(resolve(worktree, dir, "memory"))) return true
   }
   return false
 }
 
 function capMap(map: Map<string, unknown>): void {
   if (map.size > 300) map.clear()
 }
@@ -316,39 +408,40 @@ const Teacher: Plugin = async (ctx) => {
   /**
    * Budgeted recall for one execution or prompt through the existing bridge.
    * Returns null whenever Teacher is unavailable, the worktree has no memory,
    * or the bridge fails/times out ΓÇö callers degrade to a bare marker.
    */
   const recallForExecution = async (
     sessionID: string,
     query: string,
   ): Promise<RecallOutcome | null> => {
     if (!bridge) return null
+    const knobs = readKnobs(ctx.worktree)
     if (!query.trim()) return null
     if (!hasMemoryRoot(ctx.worktree)) return null
     const project = ctx.worktree.split(/[/\\]/).pop() || "unknown"
     try {
       const resp = await invokeBridge(
         python,
         bridgePath,
         {
           command: "recall",
           worktree: ctx.worktree,
           agent: "opencode",
           project,
           session: sessionID || undefined,
           query,
-          confidence_threshold: HOOK_THRESHOLD,
-          context_budget: HOOK_BUDGET,
-          limit: HOOK_LIMIT,
+          confidence_threshold: knobs.recall_threshold,
+          context_budget: knobs.hook_budget,
+          limit: knobs.hook_limit,
         },
-        HOOK_TIMEOUT_MS,
+        knobs.hook_timeout_ms,
       )
       if (!resp.ok) return null
       const memories = (resp as any).memories ?? []
       return { hits: memories.length, lines: formatRecallLines(memories) }
     } catch {
       return null
     }
   }
 
   return {
@@ -961,38 +1054,56 @@ const Teacher: Plugin = async (ctx) => {
             output: `System Health:\n${lines.join("\n")}`,
             metadata: result,
           }
         },
       }),
     },
 
     "tool.execute.before": async (input, output) => {
       try {
         if (!hooksEnabled()) return
+        const knobs = readKnobs(ctx.worktree)
+        if (knobs.skip_tools.includes(input.tool) && !knobs.force_tools.includes(input.tool)) {
+          executionRecalls.set(input.callID, null)
+          return
+        }
+        executionStart.set(input.callID, Date.now())
         const query = buildExecutionQuery(input.tool, output.args)
         const rec = await recallForExecution(input.sessionID, query)
         capMap(executionRecalls)
         executionRecalls.set(input.callID, rec)
       } catch {
         // Hooks must never break tool execution ΓÇö degrade to no context.
         executionRecalls.set(input.callID, null)
       }
     },
 
     "tool.execute.after": async (input, output) => {
       try {
         if (!hooksEnabled()) return
         const rec = executionRecalls.get(input.callID) ?? null
         executionRecalls.delete(input.callID)
         // Visible marker on EVERY execution ΓÇö hits, zero hits, and degraded.
         const marker = rec ? ` ┬╖ teacher: ${rec.hits}` : " ┬╖ teacher: ΓÇô"
-        output.title = `${output.title || input.tool}${marker}`
+        const started = executionStart.get(input.callID) ?? Date.now()
+        executionStart.delete(input.callID)
+        const meta = (output as any).metadata as Record<string, unknown> | undefined
+        const engagement = meta && typeof meta.engagement === "string" ? meta.engagement : ""
+        const routingSuffix = engagement ? ` ┬╖ routing: ${engagement}` : ""
+        output.title = `${output.title || input.tool}${marker}${routingSuffix}`
+        appendEvidence(ctx.worktree, {
+          kind: "exec",
+          tool: input.tool,
+          ms: Date.now() - started,
+          ok: typeof output.output === "string" && !output.output.startsWith("Error"),
+          hits: rec ? rec.hits : null,
+        })
         if (rec && rec.hits > 0 && typeof output.output === "string") {
           const block = `[teacher context]\n${rec.lines.join("\n")}\n[/teacher]`
           output.output = `${output.output}\n\n${block}`
         }
       } catch {
         // Teacher visibility must never break tool execution.
       }
     },
 
     "chat.message": async (input, output) => {
diff --git a/tests/unit/test_teacher_plugin_hooks.py b/tests/unit/test_teacher_plugin_hooks.py
index 615d7de..eb97c90 100644
--- a/tests/unit/test_teacher_plugin_hooks.py
+++ b/tests/unit/test_teacher_plugin_hooks.py
@@ -138,23 +138,28 @@ class TestPromptHooks:
 class TestRecallBudgetAndCostGuards:
     """Hook recalls are bounded: budgeted, thresholded, timeboxed, skippable."""
 
     def test_budget_constants_defined(self) -> None:
         assert "HOOK_LIMIT = 3" in TS_PLUGIN_SOURCE
         assert "HOOK_THRESHOLD = 0.2" in TS_PLUGIN_SOURCE
         assert "HOOK_BUDGET = 400" in TS_PLUGIN_SOURCE
         assert "HOOK_TIMEOUT_MS = 1500" in TS_PLUGIN_SOURCE
 
     def test_recall_uses_budget_constants(self) -> None:
-        assert "confidence_threshold: HOOK_THRESHOLD" in TS_PLUGIN_SOURCE
-        assert "context_budget: HOOK_BUDGET" in TS_PLUGIN_SOURCE
-        assert "limit: HOOK_LIMIT" in TS_PLUGIN_SOURCE
+        # Budget flows through knobs whose defaults are the HOOK_* consts.
+        assert "confidence_threshold: knobs.recall_threshold" in TS_PLUGIN_SOURCE
+        assert "context_budget: knobs.hook_budget" in TS_PLUGIN_SOURCE
+        assert "limit: knobs.hook_limit" in TS_PLUGIN_SOURCE
+        assert "recall_threshold: HOOK_THRESHOLD" in TS_PLUGIN_SOURCE
+        assert "hook_budget: HOOK_BUDGET" in TS_PLUGIN_SOURCE
+        assert "hook_limit: HOOK_LIMIT" in TS_PLUGIN_SOURCE
+        assert "hook_timeout_ms: HOOK_TIMEOUT_MS" in TS_PLUGIN_SOURCE
 
     def test_recall_is_timeboxed_through_bridge(self) -> None:
         assert "timeoutMs = 30000" in TS_PLUGIN_SOURCE  # default unchanged
         assert "HOOK_TIMEOUT_MS" in TS_PLUGIN_SOURCE
         block = _hook_block("tool.execute.before")
         assert "recallForExecution" in block
 
     def test_fast_skip_when_no_memory(self) -> None:
         assert "hasMemoryRoot" in TS_PLUGIN_SOURCE
         for legacy in ('".teacher"', '".lerev"', '".evo"'):
diff --git a/tests/unit/test_teacher_routing.py b/tests/unit/test_teacher_routing.py
new file mode 100644
index 0000000..dabeef1
--- /dev/null
+++ b/tests/unit/test_teacher_routing.py
@@ -0,0 +1,75 @@
+"""TS-source contract tests for the adaptive routing loop (Phase 1)."""
+
+import re
+
+from teacher.plugin_source import TS_PLUGIN_SOURCE
+
+
+class TestRoutingCoreHelpers:
+    def test_constants_present(self):
+        assert "const ROUTE_TIMEOUT_MS = 10000" in TS_PLUGIN_SOURCE
+        assert "const ROUTE_STATS_MAX_LINES = 2000" in TS_PLUGIN_SOURCE
+
+    def test_engage_mapping(self):
+        match = re.search(
+            r"function engageFor\(severity: string\): string \{\n(.*?)\n\}",
+            TS_PLUGIN_SOURCE,
+            re.S,
+        )
+        assert match, "engageFor missing"
+        body = match.group(1)
+        assert '"light" ? "skill" : "both"' in body.replace(" ", " ").replace(
+            "  ", ""
+        ) or ('"light"' in body and '"skill"' in body and '"both"' in body)
+
+    def test_evidence_append_and_cap(self):
+        assert "function appendEvidence(" in TS_PLUGIN_SOURCE
+        assert "routing-stats.jsonl" in TS_PLUGIN_SOURCE
+        assert "ROUTE_STATS_MAX_LINES" in TS_PLUGIN_SOURCE
+        assert "appendFileSync" in TS_PLUGIN_SOURCE
+        assert "mkdirSync" in TS_PLUGIN_SOURCE
+
+    def test_knobs_reader(self):
+        assert "function readKnobs(" in TS_PLUGIN_SOURCE
+        assert "routing.json" in TS_PLUGIN_SOURCE
+        assert "skip_tools" in TS_PLUGIN_SOURCE
+        assert "force_tools" in TS_PLUGIN_SOURCE
+        assert "statSync" in TS_PLUGIN_SOURCE  # mtime cache check
+
+    def test_knobs_used_in_recall_path(self):
+        # recallForExecution reads knobs and applies them to the bridge call.
+        idx = TS_PLUGIN_SOURCE.index("const recallForExecution")
+        end = TS_PLUGIN_SOURCE.index("return {", idx)
+        block = TS_PLUGIN_SOURCE[idx:end]
+        assert "readKnobs" in block
+        assert "confidence_threshold" in block
+        assert "knobs.recall_threshold" in block
+
+    def test_before_hook_skip_force(self):
+        idx = TS_PLUGIN_SOURCE.index('"tool.execute.before"')
+        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index('"tool.execute.after"')]
+        assert "skip_tools" in block
+        assert "force_tools" in block
+
+    def test_after_hook_tracks_evidence_and_start_time(self):
+        idx = TS_PLUGIN_SOURCE.index('"tool.execute.after"')
+        end = TS_PLUGIN_SOURCE.index('"chat.message"', idx)
+        block = TS_PLUGIN_SOURCE[idx:end]
+        assert 'kind: "exec"' in block
+        assert "executionStart" in block
+        assert "Date.now()" in block
+
+    def test_routing_marker_suffix(self):
+        # After-hook appends the routing marker from metadata.engagement.
+        idx = TS_PLUGIN_SOURCE.index('"tool.execute.after"')
+        end = TS_PLUGIN_SOURCE.index('"chat.message"', idx)
+        block = TS_PLUGIN_SOURCE[idx:end]
+        assert "routing: " in block
+        assert "metadata" in block
+
+    def test_node_fs_imports_extended(self):
+        match = re.search(r'import \{ ([^}]+) \} from "node:fs"', TS_PLUGIN_SOURCE)
+        assert match, "node:fs import missing"
+        names = {n.strip() for n in match.group(1).split(",")}
+        assert {"existsSync", "appendFileSync", "readFileSync", "writeFileSync",
+                "mkdirSync", "statSync"} <= names


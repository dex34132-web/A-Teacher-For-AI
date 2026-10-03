## Commits
e555fb9 feat(plugin): school_route (micro-model assess + lesson report) and school_route_stats tools

## Stat
 school/plugin_source.py                 | 330 +++++++++++++++++++++++++++++++
 tests/unit/test_school_plugin_bridge.py |  13 +-
 tests/unit/test_school_plugin_hooks.py  |   2 +-
 tests/unit/test_school_routing.py       |  65 ++++++
 4 files changed, 403 insertions(+), 7 deletions(-)

## Diff (-U10)
diff --git a/school/plugin_source.py b/school/plugin_source.py
index ca4799a..a20133f 100644
--- a/school/plugin_source.py
+++ b/school/plugin_source.py
@@ -438,20 +438,109 @@ const School: Plugin = async (ctx) => {
         knobs.hook_timeout_ms,
       )
       if (!resp.ok) return null
       const memories = (resp as any).memories ?? []
       return { hits: memories.length, lines: formatRecallLines(memories) }
     } catch {
       return null
     }
   }
 
+  interface RouteDecision { severity: string; engage: string; reason: string }
+
+  function routePrompt(situation: string): string {
+    return [
+      "You are a routing classifier for school tools. Situation: " + situation,
+      "severity: light (trivial) | medium (real task) | high (critical).",
+      "engage: skill for light, both for medium/high (tool and skill together).",
+      "Never choose engage none unless the situation is unrelated to tool routing.",
+      'Respond ONLY with JSON: {"severity":"...","engage":"...","reason":"..."}',
+    ].join("\n")
+  }
+
+  function parseRouteDecision(text: string): RouteDecision | null {
+    try {
+      const match = text.match(/\{[\s\S]*\}/)
+      if (!match) return null
+      const raw = JSON.parse(match[0]) as Record<string, unknown>
+      const severity = normalizeSeverity(raw.severity)
+      // engage stays "none" only when the micro-model said so verbatim;
+      // anything else falls back to the engageFor mapping (never "none").
+      const engage =
+        raw.engage === "none" || raw.engage === "skill" || raw.engage === "both"
+          ? String(raw.engage)
+          : engageFor(severity)
+      return { severity, engage, reason: String(raw.reason ?? "").slice(0, 300) }
+    } catch {
+      return null
+    }
+  }
+
+  async function microAssess(
+    client: unknown,
+    directory: string,
+    situation: string,
+  ): Promise<RouteDecision | null> {
+    if (process.env.SCHOOL_ROUTE === "0") return null
+    const c = client as any
+    if (!c?.session?.create || !c?.session?.prompt) return null
+    try {
+      const timeout = new Promise<RouteDecision | null>((r) =>
+        setTimeout(() => r(null), ROUTE_TIMEOUT_MS),
+      )
+      const work = (async (): Promise<RouteDecision | null> => {
+        const created = await c.session.create({
+          body: { title: "school-route" },
+          query: { directory },
+        })
+        const sessionID = created?.data?.id ?? created?.id
+        if (!sessionID) return null
+        try {
+          let model: { providerID: string; modelID: string } | undefined
+          try {
+            const cfg = await c.config?.get?.()
+            const small = cfg?.data?.small_model ?? cfg?.small_model
+            if (typeof small === "string" && small.includes("/")) {
+              const i = small.indexOf("/")
+              model = { providerID: small.slice(0, i), modelID: small.slice(i + 1) }
+            }
+          } catch {
+            // No small_model config ΓÇö session default is acceptable.
+          }
+          const resp = await c.session.prompt({
+            path: { id: sessionID },
+            query: { directory },
+            body: {
+              parts: [{ type: "text", text: routePrompt(situation) }],
+              ...(model ? { model } : {}),
+            },
+          })
+          const parts = resp?.data?.parts ?? resp?.parts ?? []
+          const text = parts
+            .filter((p: any) => p?.type === "text")
+            .map((p: any) => String(p.text ?? ""))
+            .join("\n")
+          return parseRouteDecision(text)
+        } finally {
+          try {
+            await c.session.delete({ path: { id: sessionID } })
+          } catch {
+            // Best-effort scratch-session cleanup.
+          }
+        }
+      })()
+      return await Promise.race([work, timeout])
+    } catch {
+      return null
+    }
+  }
+
   return {
     tool: {
       school_status: tool({
         description:
           "Check School runtime status: versions and component health " +
           "(V2.5 routing, V2.6 memory, persistence, security). Use when " +
           "School behaves unexpectedly or right after install/upgrade - " +
           "start here, before deeper diagnostics.",
         args: {},
         async execute(_args, context) {
@@ -1050,20 +1139,261 @@ const School: Plugin = async (ctx) => {
           const result = (resp as any).result ?? resp
           const health = result.health ?? {}
           const lines = Object.entries(health).map(([k, v]) => `  ${k}: ${v}`)
           return {
             title: "School Diagnose",
             output: `System Health:\n${lines.join("\n")}`,
             metadata: result,
           }
         },
       }),
+
+      school_route: tool({
+        description:
+          "Assess how much School routing machinery a situation needs " +
+          "(mode assess: tiny real model call -> engage skill or both) or " +
+          "store a routing lesson (mode report: what worked where, tagged " +
+          "and retrievable). Use when starting non-trivial work or after a " +
+          "tool call taught you something about routing - for anything, " +
+          "not only coding.",
+        args: {
+          mode: tool.schema
+            .string()
+            .describe('Mode: "assess" or "report"'),
+          situation: tool.schema
+            .string()
+            .describe("What is happening (max 500 chars)."),
+          severity: tool.schema
+            .string()
+            .optional()
+            .describe("assess fallback: light | medium | high"),
+          lesson: tool.schema
+            .string()
+            .optional()
+            .describe("report: the routing lesson to store."),
+          outcome: tool.schema
+            .string()
+            .optional()
+            .describe("report: helpful | useless | neutral"),
+        },
+        async execute(args, context) {
+          const mode = String(args.mode ?? "").trim()
+          const situation = String(args.situation ?? "").slice(0, 500)
+          if (!situation.trim()) {
+            return {
+              title: "School Route ΓÇö Failed",
+              output: "Error: situation is required (max 500 chars).",
+              metadata: { engagement: "failed" },
+            }
+          }
+
+          if (mode === "report") {
+            if (!bridge) {
+              return {
+                title: "School Route ΓÇö Failed",
+                output: "School: unavailable ΓÇö no bridge found. Run `school install`.",
+                metadata: { engagement: "failed" },
+              }
+            }
+            const lesson = String(args.lesson ?? "").trim().slice(0, 1000)
+            if (!lesson) {
+              return {
+                title: "School Route ΓÇö Failed",
+                output: "Error: lesson is required for mode=report.",
+                metadata: { engagement: "failed" },
+              }
+            }
+            const outcome =
+              args.outcome === "useless" || args.outcome === "neutral"
+                ? String(args.outcome)
+                : "helpful"
+            const resp = await invokeBridge(python, bridgePath, {
+              command: "remember",
+              worktree: context.worktree,
+              agent: "opencode",
+              project: context.worktree.split(/[/\\]/).pop() || "unknown",
+              session: context.sessionID || undefined,
+              content: `Routing lesson (${outcome}): ${lesson}`,
+              observation: situation || undefined,
+              outcome:
+                outcome === "helpful"
+                  ? "SUCCESS"
+                  : outcome === "useless"
+                    ? "FAILURE"
+                    : "NEUTRAL",
+              tags: ["routing", outcome],
+            })
+            if (hooksEnabled()) {
+              appendEvidence(context.worktree, {
+                kind: "report",
+                tool: "school_route",
+                ms: 0,
+                ok: Boolean(resp.ok),
+                outcome,
+              })
+            }
+            if (!resp.ok) {
+              const err = (resp as any).error ?? {}
+              return {
+                title: "School Route ΓÇö Failed",
+                output: `Error [${err.type}]: ${err.message}`,
+                metadata: { engagement: "failed" },
+              }
+            }
+            return {
+              title: "School Route ΓÇö Reported",
+              output:
+                `Stored routing lesson (id ${(resp as any).id ?? "?"}, ` +
+                `outcome ${outcome}).`,
+              metadata: { engagement: "reported" },
+            }
+          }
+
+          if (mode !== "assess") {
+            return {
+              title: "School Route ΓÇö Failed",
+              output: 'Error: mode must be "assess" or "report".',
+              metadata: { engagement: "failed" },
+            }
+          }
+
+          let decision = await microAssess(ctx.client, ctx.directory, situation)
+          let source = "micro-model"
+          if (!decision) {
+            const severity = normalizeSeverity(args.severity)
+            decision = {
+              severity,
+              engage: engageFor(severity),
+              reason: args.severity
+                ? "self-rated (severity argument)"
+                : "fallback default (micro-call unavailable)",
+            }
+            source = process.env.SCHOOL_ROUTE === "0"
+              ? "self-rated"
+              : args.severity
+                ? "self-rated"
+                : "fallback"
+          }
+          if (hooksEnabled()) {
+            appendEvidence(context.worktree, {
+              kind: "assess",
+              tool: "school_route",
+              ms: 0,
+              ok: true,
+              severity: decision.severity,
+              engage: decision.engage,
+            })
+          }
+          const nextStep =
+            decision.engage === "none"
+              ? "\nNo routing machinery needed for this situation."
+              : "\nNext: load the `school-routing` skill (skill tool) " +
+                "so the tool and skill work together."
+          return {
+            title: `School Route ΓÇö ${decision.severity}`,
+            output:
+              JSON.stringify({ source, ...decision }, null, 2) + nextStep,
+            metadata: { engagement: decision.engage },
+          }
+        },
+      }),
+
+      school_route_stats: tool({
+        description:
+          "Aggregated routing evidence: per-tool call counts and average " +
+          "durations, recent assess/report entries, current knobs, and " +
+          "recent routing lessons. Use before adjusting how School routes, " +
+          "or when the routing skill asks for current numbers - for " +
+          "anything, not only coding.",
+        args: {
+          limit: tool.schema
+            .number()
+            .min(1)
+            .max(100)
+            .optional()
+            .describe("Recent entries/lessons to include (default 20)"),
+        },
+        async execute(args, context) {
+          const limit = Math.min(Number(args.limit ?? 20) || 20, 100)
+          const file = resolve(memoryRoot(context.worktree), "routing-stats.jsonl")
+          let entries: Record<string, unknown>[] = []
+          if (fileExists(file)) {
+            try {
+              entries = readFileSync(file, "utf8")
+                .split("\n")
+                .filter((l) => l.trim())
+                .map((l) => JSON.parse(l))
+            } catch {
+              entries = []
+            }
+          }
+          const perTool: Record<string, { calls: number; total_ms: number }> = {}
+          for (const e of entries) {
+            if (e.kind !== "exec") continue
+            const t = String(e.tool)
+            const cur = perTool[t] ?? { calls: 0, total_ms: 0 }
+            cur.calls += 1
+            cur.total_ms += Number(e.ms ?? 0)
+            perTool[t] = cur
+          }
+          const aggregates: Record<string, { calls: number; avg_ms: number }> = {}
+          for (const [t, v] of Object.entries(perTool)) {
+            aggregates[t] = {
+              calls: v.calls,
+              avg_ms: v.calls ? Math.round(v.total_ms / v.calls) : 0,
+            }
+          }
+          let lessons: unknown[] = []
+          if (bridge) {
+            try {
+              const resp = await invokeBridge(
+                python,
+                bridgePath,
+                {
+                  command: "recall",
+                  worktree: context.worktree,
+                  agent: "opencode",
+                  project: context.worktree.split(/[/\\]/).pop() || "unknown",
+                  query: "routing lesson",
+                  confidence_threshold: 0,
+                  context_budget: 1500,
+                  limit: Math.min(limit, 10),
+                },
+                HOOK_TIMEOUT_MS,
+              )
+              if (resp.ok) lessons = (resp as any).memories ?? []
+            } catch {
+              lessons = []
+            }
+          }
+          const knobs = readKnobs(context.worktree)
+          const last = entries.length ? entries[entries.length - 1] : null
+          return {
+            title: "School Routing Stats",
+            output: JSON.stringify(
+              {
+                last_activity: last ? last.ts : null,
+                recent: entries.slice(-limit),
+                aggregates,
+                knobs,
+                lessons: lessons.map((m: any) => ({
+                  id: m.experience_id ?? m.id,
+                  content: String(m.content ?? "").slice(0, 300),
+                })),
+              },
+              null,
+              2,
+            ),
+            metadata: { engagement: "stats" },
+          }
+        },
+      }),
     },
 
     "tool.execute.before": async (input, output) => {
       try {
         if (!hooksEnabled()) return
         const knobs = readKnobs(ctx.worktree)
         if (knobs.skip_tools.includes(input.tool) && !knobs.force_tools.includes(input.tool)) {
           executionRecalls.set(input.callID, null)
           return
         }
diff --git a/tests/unit/test_school_plugin_bridge.py b/tests/unit/test_school_plugin_bridge.py
index 81be17a..3adf659 100644
--- a/tests/unit/test_school_plugin_bridge.py
+++ b/tests/unit/test_school_plugin_bridge.py
@@ -1,36 +1,36 @@
 """Tests for School plugin source and bridge protocol."""
 
 from __future__ import annotations
 
 import json
 import re
 from io import StringIO
 from unittest.mock import patch
 
-import pytest
-
 from school.plugin_source import TS_PLUGIN_SOURCE
 
 #: The approved agent-facing OpenCode tool surface (order matters).
 EXPECTED_OPENCODE_TOOLS = [
     "school_status",
     "school_remember",
     "school_recall",
     "school_learn",
     "school_conflict",
     "school_confidence",
     "school_search",
     "school_deduplicate",
     "school_knowledge",
     "school_lifecycle",
     "school_diagnose",
+    "school_route",
+    "school_route_stats",
 ]
 
 
 def _tool_names() -> list[str]:
     """Return the tool names registered by the TypeScript plugin, in order."""
     return re.findall(r"^\s+(school_\w+): tool\(", TS_PLUGIN_SOURCE, re.MULTILINE)
 
 
 def _tool_block(name: str) -> str:
     """Return the full source block of a single plugin tool."""
@@ -93,21 +93,22 @@ class TestPluginSource:
         """Plugin handles errors gracefully."""
         assert "catch" in TS_PLUGIN_SOURCE
         assert "bridge_error" in TS_PLUGIN_SOURCE
 
 
 class TestBridgeProtocol:
     """Test the bridge JSON protocol."""
 
     def test_bridge_module_importable(self) -> None:
         """school.bridge module is importable."""
-        from school.bridge import main, _COMMANDS
+        from school.bridge import _COMMANDS
+
         assert "status" in _COMMANDS
         assert "remember" in _COMMANDS
         assert "recall" in _COMMANDS
         assert "conflict" in _COMMANDS
         assert "confidence" in _COMMANDS
         assert "search" in _COMMANDS
         assert "deduplicate" in _COMMANDS
         assert "knowledge" in _COMMANDS
         assert "lifecycle" in _COMMANDS
         assert "diagnose" in _COMMANDS
@@ -164,25 +165,25 @@ class TestBridgeProtocol:
     def test_bridge_recall_requires_query(self) -> None:
         """Bridge recall command requires query."""
         from school.bridge import _handle_recall
 
         result = _handle_recall({"worktree": ".", "query": ""})
         assert result["ok"] is False
         assert result["error"]["type"] == "validation"
 
 
 class TestPluginToolSurface:
-    """The plugin must expose exactly the approved 11-tool surface."""
+    """The plugin must expose exactly the approved 13-tool surface."""
 
-    def test_exposes_exactly_11_tools(self) -> None:
+    def test_exposes_exactly_13_tools(self) -> None:
         names = _tool_names()
-        assert len(names) == 11, f"expected 11 tools, got {len(names)}: {names}"
+        assert len(names) == 13, f"expected 13 tools, got {len(names)}: {names}"
         assert set(names) == set(EXPECTED_OPENCODE_TOOLS)
 
     def test_tool_order_matches_approved_surface(self) -> None:
         assert _tool_names() == EXPECTED_OPENCODE_TOOLS
 
     def test_learn_registered_after_recall(self) -> None:
         names = _tool_names()
         assert "school_learn" in names
         assert names.index("school_learn") == names.index("school_recall") + 1
 
diff --git a/tests/unit/test_school_plugin_hooks.py b/tests/unit/test_school_plugin_hooks.py
index eb97c90..84b6d3c 100644
--- a/tests/unit/test_school_plugin_hooks.py
+++ b/tests/unit/test_school_plugin_hooks.py
@@ -33,21 +33,21 @@ def _hook_block(name: str) -> str:
 class TestExecutionHooksRegistered:
     """The plugin registers every execution/prompt hook."""
 
     def test_all_expected_hooks_registered(self) -> None:
         for hook in EXPECTED_HOOKS:
             assert f'"{hook}"' in TS_PLUGIN_SOURCE, f"missing hook: {hook}"
 
     def test_tool_surface_unchanged(self) -> None:
         """Hooks add visibility, not new tools."""
         names = re.findall(r"^\s+(school_\w+): tool\(", TS_PLUGIN_SOURCE, re.MULTILINE)
-        assert len(names) == 11, f"tool surface changed: {names}"
+        assert len(names) == 13, f"tool surface changed: {names}"
 
 
 class TestBeforeHook:
     """tool.execute.before runs a budgeted recall keyed to the execution."""
 
     def test_stashes_recall_by_call_id(self) -> None:
         block = _hook_block("tool.execute.before")
         assert "executionRecalls.set(input.callID" in block
 
     def test_query_is_built_from_tool_and_args(self) -> None:
diff --git a/tests/unit/test_school_routing.py b/tests/unit/test_school_routing.py
index 4dd49d1..7557cc0 100644
--- a/tests/unit/test_school_routing.py
+++ b/tests/unit/test_school_routing.py
@@ -86,10 +86,75 @@ class TestRoutingCoreHelpers:
         block = TS_PLUGIN_SOURCE[idx:end]
         assert "routing: " in block
         assert "metadata" in block
 
     def test_node_fs_imports_extended(self):
         match = re.search(r'import \{ ([^}]+) \} from "node:fs"', TS_PLUGIN_SOURCE)
         assert match, "node:fs import missing"
         names = {n.strip() for n in match.group(1).split(",")}
         assert {"existsSync", "appendFileSync", "readFileSync", "writeFileSync",
                 "mkdirSync", "statSync"} <= names
+
+
+class TestRouteTools:
+    def test_tools_registered(self):
+        names = re.findall(r"^\s+(school_\w+): tool\(", TS_PLUGIN_SOURCE, re.MULTILINE)
+        assert "school_route" in names
+        assert "school_route_stats" in names
+
+    def test_descriptions_are_routing_guided(self):
+        for name in ("school_route", "school_route_stats"):
+            match = re.search(
+                rf"{name}: tool\(.*?description:\s*\n(.*?),\n\s*args:",
+                TS_PLUGIN_SOURCE,
+                re.S,
+            )
+            assert match, name
+            text = " ".join(re.findall(r'"([^"]*)"', match.group(1)))
+            assert "Use" in text
+            assert "coding" in text  # domain-general framing present
+
+    def test_micro_assess_contract(self):
+        assert "function microAssess(" in TS_PLUGIN_SOURCE
+        assert "session.create" in TS_PLUGIN_SOURCE
+        assert "session.prompt" in TS_PLUGIN_SOURCE
+        assert "session.delete" in TS_PLUGIN_SOURCE
+        assert "small_model" in TS_PLUGIN_SOURCE  # config.get ΓåÆ small model
+        assert "Promise.race" in TS_PLUGIN_SOURCE
+        assert "ROUTE_TIMEOUT_MS" in TS_PLUGIN_SOURCE
+
+    def test_prompt_is_json_only(self):
+        assert "Respond ONLY with JSON" in TS_PLUGIN_SOURCE
+        assert (
+            "never choose engage none" in TS_PLUGIN_SOURCE.lower()
+            or "Never choose engage none" in TS_PLUGIN_SOURCE
+        )
+
+    def test_parse_route_decision(self):
+        assert "function parseRouteDecision(" in TS_PLUGIN_SOURCE
+        assert 'raw.engage === "none"' in TS_PLUGIN_SOURCE
+
+    def test_kill_switch(self):
+        assert 'process.env.SCHOOL_ROUTE === "0"' in TS_PLUGIN_SOURCE
+
+    def test_report_stores_tagged_lesson(self):
+        idx = TS_PLUGIN_SOURCE.index("school_route: tool(")
+        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index("school_route_stats: tool(")]
+        assert '"routing"' in block
+        assert '"helpful"' in block and '"useless"' in block and '"neutral"' in block
+        assert '"SUCCESS"' in block and '"FAILURE"' in block and '"NEUTRAL"' in block
+        assert 'command: "remember"' in block
+
+    def test_assess_appends_evidence_and_metadata(self):
+        idx = TS_PLUGIN_SOURCE.index("school_route: tool(")
+        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index("school_route_stats: tool(")]
+        assert 'kind: "assess"' in block
+        assert "engagement:" in block
+
+    def test_stats_aggregates(self):
+        idx = TS_PLUGIN_SOURCE.index("school_route_stats: tool(")
+        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index('"tool.execute.before"')]
+        assert "aggregates" in block
+        assert "avg_ms" in block
+        assert "last_activity" in block
+        assert 'kind: "report"' in TS_PLUGIN_SOURCE
+        assert "routing lesson" in TS_PLUGIN_SOURCE  # recall query for lessons


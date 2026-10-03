## Commits
c31fb54 fix(plugin): clampNum falls back to per-key default for null/boolean knob values

## Stat
 school/plugin_source.py           |  1 +
 tests/unit/test_school_routing.py | 20 ++++++++++++++++++++
 2 files changed, 21 insertions(+)

## Diff (-U10)
diff --git a/school/plugin_source.py b/school/plugin_source.py
index 77d760a..ca4799a 100644
--- a/school/plugin_source.py
+++ b/school/plugin_source.py
@@ -281,20 +281,21 @@ function normalizeSeverity(value: unknown): string {
 
 function memoryRoot(worktree: string): string {
   for (const dir of [".school", ".lerev", ".evo"]) {
     const root = resolve(worktree, dir)
     if (fileExists(resolve(root, "memory"))) return root
   }
   return resolve(worktree, ".school")
 }
 
 function clampNum(v: unknown, fallback: number, lo: number, hi: number): number {
+  if (v == null || typeof v === "boolean") return fallback
   const n = Number(v)
   return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback
 }
 
 function strList(v: unknown): string[] {
   return Array.isArray(v) ? v.map((x) => String(x)) : []
 }
 
 let knobsCache: { mtimeMs: number; knobs: RoutingKnobs } | null = null
 
diff --git a/tests/unit/test_school_routing.py b/tests/unit/test_school_routing.py
index dabeef1..4dd49d1 100644
--- a/tests/unit/test_school_routing.py
+++ b/tests/unit/test_school_routing.py
@@ -29,20 +29,40 @@ class TestRoutingCoreHelpers:
         assert "appendFileSync" in TS_PLUGIN_SOURCE
         assert "mkdirSync" in TS_PLUGIN_SOURCE
 
     def test_knobs_reader(self):
         assert "function readKnobs(" in TS_PLUGIN_SOURCE
         assert "routing.json" in TS_PLUGIN_SOURCE
         assert "skip_tools" in TS_PLUGIN_SOURCE
         assert "force_tools" in TS_PLUGIN_SOURCE
         assert "statSync" in TS_PLUGIN_SOURCE  # mtime cache check
 
+    def test_clamp_num_defaults_on_null_and_boolean(self):
+        # Null/boolean knob values are invalid -> per-key default, never coerced
+        # (Number(null) === 0 would silently override the default).
+        match = re.search(
+            r"function clampNum\([^)]*\): number \{\n(.*?)\n\}",
+            TS_PLUGIN_SOURCE,
+            re.S,
+        )
+        assert match, "clampNum missing"
+        body = match.group(1)
+        assert "v == null" in body
+        assert 'typeof v === "boolean"' in body
+        # Guard must run before Number(v), which would coerce null to 0.
+        assert body.index("v == null") < body.index("Number(v)")
+        # recall_threshold: null -> 0.2, hook_timeout_ms: null -> 1500.
+        assert "recall_threshold: HOOK_THRESHOLD" in TS_PLUGIN_SOURCE
+        assert "hook_timeout_ms: HOOK_TIMEOUT_MS" in TS_PLUGIN_SOURCE
+        assert "HOOK_THRESHOLD = 0.2" in TS_PLUGIN_SOURCE
+        assert "HOOK_TIMEOUT_MS = 1500" in TS_PLUGIN_SOURCE
+
     def test_knobs_used_in_recall_path(self):
         # recallForExecution reads knobs and applies them to the bridge call.
         idx = TS_PLUGIN_SOURCE.index("const recallForExecution")
         end = TS_PLUGIN_SOURCE.index("return {", idx)
         block = TS_PLUGIN_SOURCE[idx:end]
         assert "readKnobs" in block
         assert "confidence_threshold" in block
         assert "knobs.recall_threshold" in block
 
     def test_before_hook_skip_force(self):


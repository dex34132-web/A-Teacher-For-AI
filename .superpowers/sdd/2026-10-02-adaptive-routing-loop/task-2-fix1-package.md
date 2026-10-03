## Commits
740d6c4 fix(plugin): routePrompt truncates situation to 200 chars for <=150-token micro-call contract

## Stat
 teacher/plugin_source.py           |  2 +-
 tests/unit/test_teacher_routing.py | 18 ++++++++++++++++++
 2 files changed, 19 insertions(+), 1 deletion(-)

## Diff (-U10)
diff --git a/teacher/plugin_source.py b/teacher/plugin_source.py
index a20133f..90c9459 100644
--- a/teacher/plugin_source.py
+++ b/teacher/plugin_source.py
@@ -442,21 +442,21 @@ const Teacher: Plugin = async (ctx) => {
       return { hits: memories.length, lines: formatRecallLines(memories) }
     } catch {
       return null
     }
   }
 
   interface RouteDecision { severity: string; engage: string; reason: string }
 
   function routePrompt(situation: string): string {
     return [
-      "You are a routing classifier for teacher tools. Situation: " + situation,
+      "You are a routing classifier for teacher tools. Situation: " + situation.slice(0, 200),
       "severity: light (trivial) | medium (real task) | high (critical).",
       "engage: skill for light, both for medium/high (tool and skill together).",
       "Never choose engage none unless the situation is unrelated to tool routing.",
       'Respond ONLY with JSON: {"severity":"...","engage":"...","reason":"..."}',
     ].join("\n")
   }
 
   function parseRouteDecision(text: string): RouteDecision | null {
     try {
       const match = text.match(/\{[\s\S]*\}/)
diff --git a/tests/unit/test_teacher_routing.py b/tests/unit/test_teacher_routing.py
index 7557cc0..711b771 100644
--- a/tests/unit/test_teacher_routing.py
+++ b/tests/unit/test_teacher_routing.py
@@ -122,20 +122,38 @@ class TestRouteTools:
         assert "Promise.race" in TS_PLUGIN_SOURCE
         assert "ROUTE_TIMEOUT_MS" in TS_PLUGIN_SOURCE
 
     def test_prompt_is_json_only(self):
         assert "Respond ONLY with JSON" in TS_PLUGIN_SOURCE
         assert (
             "never choose engage none" in TS_PLUGIN_SOURCE.lower()
             or "Never choose engage none" in TS_PLUGIN_SOURCE
         )
 
+    def test_route_prompt_truncates_situation_within_budget(self):
+        # Micro-call contract: prompt <= 150 tokens. routePrompt must slice
+        # the situation itself ΓÇö the tool's 500-char cap alone still busts
+        # the token budget once the fixed template is added.
+        match = re.search(
+            r"function routePrompt\(situation: string\): string \{\n(.*?)\n  \}",
+            TS_PLUGIN_SOURCE,
+            re.S,
+        )
+        assert match, "routePrompt missing"
+        body = match.group(1)
+        assert " + situation.slice(0, 200)" in body
+        assert not re.search(r"\+ situation(?!\.slice)", body)
+        # Worst-case bound: fixed template literals + 200-char situation.
+        literals = re.findall(r"'([^']*)'|\"([^\"]*)\"", body)
+        template = sum(len(a or b) for a, b in literals)
+        assert template + 200 <= 700
+
     def test_parse_route_decision(self):
         assert "function parseRouteDecision(" in TS_PLUGIN_SOURCE
         assert 'raw.engage === "none"' in TS_PLUGIN_SOURCE
 
     def test_kill_switch(self):
         assert 'process.env.TEACHER_ROUTE === "0"' in TS_PLUGIN_SOURCE
 
     def test_report_stores_tagged_lesson(self):
         idx = TS_PLUGIN_SOURCE.index("teacher_route: tool(")
         block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index("teacher_route_stats: tool(")]


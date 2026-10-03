### Task 2: `teacher_route` + `teacher_route_stats` plugin tools

**Files:**
- Modify: `teacher/plugin_source.py` (helpers after Task 1 block; new tools inside `tool: {` object, after `teacher_diagnose`)
- Test: `tests/unit/test_teacher_routing.py` (extend)

**Interfaces:**
- Consumes: `engageFor`, `normalizeSeverity`, `memoryRoot`, `appendEvidence`, `readKnobs`, `invokeBridge/python/bridgePath`, `ctx.client`.
- Produces: TS functions `routePrompt(situation: string): string`, `parseRouteDecision(text: string): RouteDecision | null`, `microAssess(client: unknown, directory: string, situation: string): Promise<RouteDecision | null>`; tools `teacher_route` (args: `mode, situation, severity?, lesson?, outcome?`), `teacher_route_stats` (arg: `limit?`) returning `{title, output, metadata: {engagement}}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_teacher_routing.py`:

```python
class TestRouteTools:
    def test_tools_registered(self):
        names = re.findall(r"^\s+(teacher_\w+): tool\(", TS_PLUGIN_SOURCE, re.MULTILINE)
        assert "teacher_route" in names
        assert "teacher_route_stats" in names

    def test_descriptions_are_routing_guided(self):
        for name in ("teacher_route", "teacher_route_stats"):
            match = re.search(
                rf"{name}: tool\(.*?description:\s*\n(.*?),\n\s*args:",
                TS_PLUGIN_SOURCE,
                re.S,
            )
            assert match, name
            text = " ".join(re.findall(r'"([^"]*)"', match.group(1)))
            assert "Use" in text
            assert "coding" in text  # domain-general framing present

    def test_micro_assess_contract(self):
        assert "function microAssess(" in TS_PLUGIN_SOURCE
        assert "session.create" in TS_PLUGIN_SOURCE
        assert "session.prompt" in TS_PLUGIN_SOURCE
        assert "session.delete" in TS_PLUGIN_SOURCE
        assert "small_model" in TS_PLUGIN_SOURCE  # config.get → small model
        assert "Promise.race" in TS_PLUGIN_SOURCE
        assert "ROUTE_TIMEOUT_MS" in TS_PLUGIN_SOURCE

    def test_prompt_is_json_only(self):
        assert "Respond ONLY with JSON" in TS_PLUGIN_SOURCE
        assert "never choose engage none" in TS_PLUGIN_SOURCE.lower() or "Never choose engage none" in TS_PLUGIN_SOURCE

    def test_parse_route_decision(self):
        assert "function parseRouteDecision(" in TS_PLUGIN_SOURCE
        assert 'raw.engage === "none"' in TS_PLUGIN_SOURCE

    def test_kill_switch(self):
        assert 'process.env.TEACHER_ROUTE === "0"' in TS_PLUGIN_SOURCE

    def test_report_stores_tagged_lesson(self):
        idx = TS_PLUGIN_SOURCE.index("teacher_route: tool(")
        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index("teacher_route_stats: tool(")]
        assert '"routing"' in block
        assert '"helpful"' in block and '"useless"' in block and '"neutral"' in block
        assert '"SUCCESS"' in block and '"FAILURE"' in block and '"NEUTRAL"' in block
        assert 'command: "remember"' in block

    def test_assess_appends_evidence_and_metadata(self):
        idx = TS_PLUGIN_SOURCE.index("teacher_route: tool(")
        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index("teacher_route_stats: tool(")]
        assert 'kind: "assess"' in block
        assert "engagement:" in block

    def test_stats_aggregates(self):
        idx = TS_PLUGIN_SOURCE.index("teacher_route_stats: tool(")
        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index('"tool.execute.before"')]
        assert "aggregates" in block
        assert "avg_ms" in block
        assert "last_activity" in block
        assert 'kind: "report"' in TS_PLUGIN_SOURCE
        assert "routing lesson" in TS_PLUGIN_SOURCE  # recall query for lessons
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_teacher_routing.py -q`
Expected: FAIL on the new class.

- [ ] **Step 3: Implement the tools**

In `teacher/plugin_source.py`, inside the `Teacher` function (so `bridge/python/bridgePath/ctx` are in scope), after `recallForExecution` add:

```ts
  interface RouteDecision { severity: string; engage: string; reason: string }

  const routePrompt = (situation: string): string =>
    [
      "You are a routing classifier for teacher tools. Situation: " + situation,
      "severity: light (trivial) | medium (real task) | high (critical).",
      "engage: skill for light, both for medium/high (tool and skill together).",
      "Never choose engage none unless the situation is unrelated to tool routing.",
      'Respond ONLY with JSON: {"severity":"...","engage":"...","reason":"..."}',
    ].join("\n")

  const parseRouteDecision = (text: string): RouteDecision | null => {
    try {
      const match = text.match(/\{[\s\S]*\}/)
      if (!match) return null
      const raw = JSON.parse(match[0]) as Record<string, unknown>
      const severity = normalizeSeverity(raw.severity)
      const engage =
        raw.engage === "none" || raw.engage === "skill" || raw.engage === "both"
          ? String(raw.engage)
          : engageFor(severity)
      return { severity, engage, reason: String(raw.reason ?? "").slice(0, 300) }
    } catch {
      return null
    }
  }

  const microAssess = async (
    client: unknown,
    directory: string,
    situation: string,
  ): Promise<RouteDecision | null> => {
    if (process.env.TEACHER_ROUTE === "0") return null
    const c = client as any
    if (!c?.session?.create || !c?.session?.prompt) return null
    try {
      const timeout = new Promise<RouteDecision | null>((r) =>
        setTimeout(() => r(null), ROUTE_TIMEOUT_MS),
      )
      const work = (async (): Promise<RouteDecision | null> => {
        const created = await c.session.create({
          body: { title: "teacher-route" },
          query: { directory },
        })
        const sessionID = created?.data?.id ?? created?.id
        if (!sessionID) return null
        try {
          let model: { providerID: string; modelID: string } | undefined
          try {
            const cfg = await c.config?.get?.()
            const small = cfg?.data?.small_model ?? cfg?.small_model
            if (typeof small === "string" && small.includes("/")) {
              const i = small.indexOf("/")
              model = { providerID: small.slice(0, i), modelID: small.slice(i + 1) }
            }
          } catch {
            // No small_model config — session default is acceptable.
          }
          const resp = await c.session.prompt({
            path: { id: sessionID },
            query: { directory },
            body: {
              parts: [{ type: "text", text: routePrompt(situation) }],
              ...(model ? { model } : {}),
            },
          })
          const parts = resp?.data?.parts ?? resp?.parts ?? []
          const text = parts
            .filter((p: any) => p?.type === "text")
            .map((p: any) => String(p.text ?? ""))
            .join("\n")
          return parseRouteDecision(text)
        } finally {
          try {
            await c.session.delete({ path: { id: sessionID } })
          } catch {
            // Best-effort scratch-session cleanup.
          }
        }
      })()
      return await Promise.race([work, timeout])
    } catch {
      return null
    }
  }
```

Inside the `tool: {` object, after `teacher_diagnose`, add:

```ts
      teacher_route: tool({
        description:
          "Assess how much Teacher routing machinery a situation needs " +
          "(mode assess: tiny real model call -> engage skill or both) or " +
          "store a routing lesson (mode report: what worked where, tagged " +
          "and retrievable). Use when starting non-trivial work or after a " +
          "tool call taught you something about routing - for anything, " +
          "not only coding.",
        args: {
          mode: tool.schema
            .string()
            .describe('Mode: "assess" or "report"'),
          situation: tool.schema
            .string()
            .describe("What is happening (max 500 chars)."),
          severity: tool.schema
            .string()
            .optional()
            .describe("assess fallback: light | medium | high"),
          lesson: tool.schema
            .string()
            .optional()
            .describe("report: the routing lesson to store."),
          outcome: tool.schema
            .string()
            .optional()
            .describe("report: helpful | useless | neutral"),
        },
        async execute(args, context) {
          const mode = String(args.mode ?? "").trim()
          const situation = String(args.situation ?? "").slice(0, 500)
          if (!situation.trim()) {
            return {
              title: "Teacher Route — Failed",
              output: "Error: situation is required (max 500 chars).",
              metadata: { engagement: "failed" },
            }
          }

          if (mode === "report") {
            if (!bridge) {
              return {
                title: "Teacher Route — Failed",
                output: "Teacher: unavailable — no bridge found. Run `teacher install`.",
                metadata: { engagement: "failed" },
              }
            }
            const lesson = String(args.lesson ?? "").trim().slice(0, 1000)
            if (!lesson) {
              return {
                title: "Teacher Route — Failed",
                output: "Error: lesson is required for mode=report.",
                metadata: { engagement: "failed" },
              }
            }
            const outcome =
              args.outcome === "useless" || args.outcome === "neutral"
                ? String(args.outcome)
                : "helpful"
            const resp = await invokeBridge(python, bridgePath, {
              command: "remember",
              worktree: context.worktree,
              agent: "opencode",
              project: context.worktree.split(/[/\\]/).pop() || "unknown",
              session: context.sessionID || undefined,
              content: `Routing lesson (${outcome}): ${lesson}`,
              observation: situation || undefined,
              outcome:
                outcome === "helpful" ? "SUCCESS" : outcome === "useless" ? "FAILURE" : "NEUTRAL",
              tags: ["routing", outcome],
            })
            appendEvidence(context.worktree, {
              kind: "report",
              tool: "teacher_route",
              ms: 0,
              ok: Boolean(resp.ok),
              outcome,
            })
            if (!resp.ok) {
              const err = (resp as any).error ?? {}
              return {
                title: "Teacher Route — Failed",
                output: `Error [${err.type}]: ${err.message}`,
                metadata: { engagement: "failed" },
              }
            }
            return {
              title: "Teacher Route — Reported",
              output: `Stored routing lesson (id ${(resp as any).id ?? "?"}, outcome ${outcome}).`,
              metadata: { engagement: "reported" },
            }
          }

          if (mode !== "assess") {
            return {
              title: "Teacher Route — Failed",
              output: 'Error: mode must be "assess" or "report".',
              metadata: { engagement: "failed" },
            }
          }

          let decision = await microAssess(ctx.client, ctx.directory, situation)
          let source = "micro-model"
          if (!decision) {
            const severity = normalizeSeverity(args.severity)
            decision = {
              severity,
              engage: engageFor(severity),
              reason: args.severity
                ? "self-rated (severity argument)"
                : "fallback default (micro-call unavailable)",
            }
            source = process.env.TEACHER_ROUTE === "0"
              ? "self-rated"
              : args.severity
                ? "self-rated"
                : "fallback"
          }
          appendEvidence(context.worktree, {
            kind: "assess",
            tool: "teacher_route",
            ms: 0,
            ok: true,
            severity: decision.severity,
            engage: decision.engage,
          })
          const nextStep =
            decision.engage === "none"
              ? "\nNo routing machinery needed for this situation."
              : "\nNext: load the `teacher-routing` skill (skill tool) so the tool and skill work together."
          return {
            title: `Teacher Route — ${decision.severity}`,
            output:
              JSON.stringify({ source, ...decision }, null, 2) + nextStep,
            metadata: { engagement: decision.engage },
          }
        },
      }),

      teacher_route_stats: tool({
        description:
          "Aggregated routing evidence: per-tool call counts and average " +
          "durations, recent assess/report entries, current knobs, and " +
          "recent routing lessons. Use before adjusting how Teacher routes, " +
          "or when the routing skill asks for current numbers - for " +
          "anything, not only coding.",
        args: {
          limit: tool.schema
            .number()
            .min(1)
            .max(100)
            .optional()
            .describe("Recent entries/lessons to include (default 20)"),
        },
        async execute(args, context) {
          const limit = Math.min(Number(args.limit ?? 20) || 20, 100)
          const file = resolve(memoryRoot(context.worktree), "routing-stats.jsonl")
          let entries: Record<string, unknown>[] = []
          if (fileExists(file)) {
            try {
              entries = readFileSync(file, "utf8")
                .split("\n")
                .filter((l) => l.trim())
                .map((l) => JSON.parse(l))
            } catch {
              entries = []
            }
          }
          const perTool: Record<string, { calls: number; total_ms: number }> = {}
          for (const e of entries) {
            if (e.kind !== "exec") continue
            const t = String(e.tool)
            const cur = perTool[t] ?? { calls: 0, total_ms: 0 }
            cur.calls += 1
            cur.total_ms += Number(e.ms ?? 0)
            perTool[t] = cur
          }
          const aggregates: Record<string, { calls: number; avg_ms: number }> = {}
          for (const [t, v] of Object.entries(perTool)) {
            aggregates[t] = {
              calls: v.calls,
              avg_ms: v.calls ? Math.round(v.total_ms / v.calls) : 0,
            }
          }
          let lessons: unknown[] = []
          if (bridge) {
            try {
              const resp = await invokeBridge(
                python,
                bridgePath,
                {
                  command: "recall",
                  worktree: context.worktree,
                  agent: "opencode",
                  project: context.worktree.split(/[/\\]/).pop() || "unknown",
                  query: "routing lesson",
                  confidence_threshold: 0,
                  context_budget: 1500,
                  limit: Math.min(limit, 10),
                },
                HOOK_TIMEOUT_MS,
              )
              if (resp.ok) lessons = (resp as any).memories ?? []
            } catch {
              lessons = []
            }
          }
          const knobs = readKnobs(context.worktree)
          const last = entries.length ? entries[entries.length - 1] : null
          return {
            title: "Teacher Routing Stats",
            output: JSON.stringify(
              {
                last_activity: last ? last.ts : null,
                recent: entries.slice(-limit),
                aggregates,
                knobs,
                lessons: lessons.map((m: any) => ({
                  id: m.experience_id ?? m.id,
                  content: String(m.content ?? "").slice(0, 300),
                })),
              },
              null,
              2,
            ),
            metadata: { engagement: "stats" },
          }
        },
      }),
```

- [ ] **Step 4: Extract TS, node --check, reinstall, MATCH** (same commands as Task 1 Step 4). Expected: exit 0 + MATCH.

- [ ] **Step 5: Run tests to verify they pass**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_teacher_routing.py -q`
Expected: PASS.

- [ ] **Step 6: Run the full plugin test set + hooks tests for regressions**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_teacher_plugin_hooks.py tests/unit/test_teacher_plugin_bridge.py tests/unit/test_teacher_identity_compat.py -q`
Expected: PASS. (If the identity test's exact-tool-count assertions exist, update the expected tool list there to include the two new tools — additive only.)

- [ ] **Step 7: Commit**

```powershell
git add teacher/plugin_source.py tests/unit/test_teacher_routing.py; if ($?) { git commit -m "feat(plugin): teacher_route (micro-model assess + lesson report) and teacher_route_stats tools" }
```

---


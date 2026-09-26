"""Teacher plugin source — bundled TypeScript plugin for OpenCode."""

from __future__ import annotations

from teacher import __version__ as _TEACHER_VERSION

_TS_PLUGIN_TEMPLATE = r'''import { tool } from "@opencode-ai/plugin/tool"
import type { Plugin } from "@opencode-ai/plugin"
import { execFile, spawn } from "node:child_process"
import { promisify } from "node:util"
import { resolve } from "node:path"
import { existsSync } from "node:fs"
import { execSync } from "node:child_process"

const execFileAsync = promisify(execFile)

/** Teacher version this plugin was generated from — canonical source: teacher.__version__. */
const TEACHER_VERSION = "__TEACHER_VERSION__"

/**
 * Find a usable Python interpreter.
 */
async function findPython(): Promise<string | null> {
  for (const cmd of ["python3", "python"]) {
    try {
      const { stdout } = await execFileAsync(cmd, ["--version"], {
        timeout: 5000,
        windowsHide: true,
      })
      if (stdout.includes("Python")) return cmd
    } catch {
      continue
    }
  }
  return null
}

/**
 * Test if a Python module is available.
 */
async function testModule(python: string, module: string): Promise<boolean> {
  try {
    await execFileAsync(python, ["-c", `import ${module}`], {
      timeout: 5000,
      windowsHide: true,
    })
    return true
  } catch {
    return false
  }
}

/**
 * Check if a file exists.
 */
function fileExists(path: string): boolean {
  try {
    return existsSync(path)
  } catch {
    return false
  }
}

/**
 * Bridge discovery result.
 */
interface BridgeInfo {
  python: string
  bridgePath: string
  tier: string
}

/**
 * Discover the Teacher bridge using a 4-tier cascade.
 * Each tier also honours legacy pre-rename aliases (LEREV_HOME,
 * lerev-bridge, lerev.bridge, lerev_bridge.py) so existing installs
 * keep working; Teacher is always tried first.
 */
async function discoverBridge(worktree: string): Promise<BridgeInfo | null> {
  const python = await findPython()

  // Tier 1: TEACHER_HOME env var (legacy aliases: LEREV_HOME / EVO_HOME)
  const teacherHome =
    process.env.TEACHER_HOME ||
    process.env.LEREV_HOME ||
    process.env.EVO_HOME
  if (teacherHome) {
    for (const pkg of ["teacher", "lerev"]) {
      const bridgePath = resolve(teacherHome, pkg, "bridge.py")
      if (fileExists(bridgePath)) {
        return { python: python ?? "python3", bridgePath, tier: "TEACHER_HOME" }
      }
    }
  }

  // Tier 2: bridge launcher on PATH (legacy alias: lerev-bridge)
  for (const command of ["teacher-bridge", "lerev-bridge"]) {
    try {
      const isWin = process.platform === "win32"
      const whereCmd = isWin ? `where ${command}` : `which ${command}`
      const bridgeCmd = execSync(whereCmd, { windowsHide: true, timeout: 3000 })
        .toString().trim()
      if (bridgeCmd) {
        return { python: "", bridgePath: bridgeCmd, tier: "PATH" }
      }
    } catch {
      // Not on PATH — try next alias
    }
  }

  // Tier 3: installed module (legacy alias: lerev.bridge)
  if (python) {
    for (const module of ["teacher.bridge", "lerev.bridge"]) {
      const available = await testModule(python, module)
      if (available) {
        return { python, bridgePath: `-m ${module}`, tier: "installed_module" }
      }
    }
  }

  // Tier 4: Dev fallback (legacy alias: lerev_bridge.py)
  for (const script of ["teacher_bridge.py", "lerev_bridge.py"]) {
    const devBridge = resolve(worktree, "scripts", script)
    if (fileExists(devBridge)) {
      return { python: python ?? "python3", bridgePath: devBridge, tier: "dev_fallback" }
    }
  }

  return null
}

/**
 * Run the bridge child process with a JSON stdin payload.
 * Uses spawn + explicit stdin write: the execFile `input` option is
 * not delivered by every plugin runtime, which leaves the bridge
 * child blocked on stdin until the invoke timeout fires.
 */
function runBridge(
  python: string,
  args: string[],
  json: string,
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const cmd = `${python} ${args.join(" ")}`
    const child = spawn(python, args, { windowsHide: true })
    let stdout = ""
    let stderr = ""
    let settled = false

    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      child.kill()
      reject(new Error(`Command failed: ${cmd}`))
    }, 30000)

    child.stdout.on("data", (d) => {
      stdout += d
    })
    child.stderr.on("data", (d) => {
      stderr += d
    })
    child.on("error", (err) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      reject(err)
    })
    child.on("close", (code) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      if (code !== 0) {
        reject(new Error(`Command failed: ${cmd}`))
        return
      }
      resolve({ stdout, stderr })
    })
    child.stdin.on("error", () => {
      // child may exit before consuming stdin — surfaced via close
    })
    child.stdin.write(json)
    child.stdin.end()
  })
}

/**
 * Invoke the Teacher bridge with a JSON request.
 */
async function invokeBridge(
  python: string,
  bridgePath: string,
  request: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const json = JSON.stringify(request)
  // Module invocations arrive as "-m <module>" (teacher.bridge, or the
  // legacy lerev.bridge alias); anything else is a direct script path.
  const args = bridgePath.startsWith("-m ")
    ? ["-m", ...bridgePath.slice(3).split(" ")]
    : [bridgePath]

  try {
    const { stdout, stderr } = await runBridge(python, args, json)
    if (stderr) console.error("[teacher bridge stderr]", stderr)
    if (!stdout.trim()) {
      return {
        ok: false,
        error: { type: "protocol", message: "empty bridge response" },
      }
    }
    return JSON.parse(stdout.trim())
  } catch (err: any) {
    return {
      ok: false,
      error: { type: "bridge_error", message: err?.message ?? String(err) },
    }
  }
}

const Teacher: Plugin = async (ctx) => {
  const bridge = await discoverBridge(ctx.worktree)

  if (!bridge) {
    console.error("[teacher] No bridge found. Teacher tools will return errors.")
    console.error("[teacher] Run `teacher install` to set up Teacher globally.")
  }

  const python = bridge?.python ?? ""
  const bridgePath = bridge?.bridgePath ?? ""

  return {
    tool: {
      teacher_status: tool({
        description:
          "Check Teacher runtime status. Verifies Teacher, V2.5 routing, V2.6 memory, persistence, and security components are available.",
        args: {},
        async execute(_args, context) {
          if (!bridge) {
            return {
              title: "Teacher Status",
              output: "Teacher: unavailable — no bridge found. Run `teacher install`.",
            }
          }

          const resp = await invokeBridge(python, bridgePath, {
            command: "status",
            worktree: context.worktree,
          })

          if (!resp.ok) {
            return {
              title: "Teacher Status",
              output: `Teacher bridge error: ${(resp as any).error?.message ?? "unknown"}`,
            }
          }

          const components = (resp as any).components ?? {}
          const bridgeVersion = (resp as any).version ?? "unknown"
          const versionMatch = bridgeVersion === TEACHER_VERSION
          const lines = Object.entries(components).map(
            ([k, v]) => `  ${k}: ${v}`,
          )
          lines.push(`  Plugin version: ${TEACHER_VERSION}`)
          lines.push(`  Bridge version: ${bridgeVersion}`)
          lines.push(`  Version match: ${versionMatch ? "yes" : "MISMATCH"}`)
          return {
            title: "Teacher Status",
            output: `Teacher V2.6 Component Status:\n${lines.join("\n")}`,
            metadata: {
              ...components,
              compat: {
                plugin: TEACHER_VERSION,
                bridge: bridgeVersion,
                match: versionMatch,
              },
            },
          }
        },
      }),

      teacher_remember: tool({
        description:
          "Store an experience or memory through Teacher V2.6. Returns a real memory ID from Teacher's persistent memory system.",
        args: {
          content: tool.schema
            .string()
            .describe("The experience or memory content to store"),
          outcome: tool.schema
            .enum(["SUCCESS", "FAILURE", "NEUTRAL", "MIXED"])
            .optional()
            .describe("Outcome of the experience (default: NEUTRAL)"),
          project: tool.schema
            .string()
            .optional()
            .describe("Project scope identifier (default: from workspace)"),
          session: tool.schema
            .string()
            .optional()
            .describe("Session scope identifier (default: from runtime context)"),
          observation: tool.schema
            .string()
            .optional()
            .describe("What was observed (optional, defaults to content)"),
          action: tool.schema
            .string()
            .optional()
            .describe("What action was taken (optional)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return {
              title: "Teacher Remember",
              output: "Teacher: unavailable — no bridge found. Run `teacher install`.",
            }
          }

          const projectId = args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown"
          const sessionId = args.session ?? context.sessionID

          const resp = await invokeBridge(python, bridgePath, {
            command: "remember",
            worktree: context.worktree,
            agent: "opencode",
            project: projectId,
            session: sessionId,
            content: args.content,
            outcome: args.outcome ?? "NEUTRAL",
            observation: args.observation,
            action: args.action,
          })

          if (!resp.ok) {
            const err = (resp as any).error ?? {}
            return {
              title: "Teacher Remember — Failed",
              output: `Error [${err.type}]: ${err.message}`,
            }
          }

          const scope = (resp as any).scope ?? {}
          const scopeStr = [
            scope.agent && `agent=${scope.agent}`,
            scope.project && `project=${scope.project}`,
            scope.session && `session=${scope.session}`,
          ]
            .filter(Boolean)
            .join(", ")

          return {
            title: "Teacher Remember",
            output: [
              `Memory stored successfully.`,
              `  ID: ${(resp as any).id}`,
              `  Scope: ${scopeStr}`,
              `  Outcome: ${(resp as any).outcome}`,
            ].join("\n"),
            metadata: {
              id: (resp as any).id,
              scope: (resp as any).scope,
              outcome: (resp as any).outcome,
            },
          }
        },
      }),

      teacher_recall: tool({
        description:
          "Retrieve memories from Teacher V2.6 long-term memory. Returns relevant stored experiences matching the query, scoped to the current project/session.",
        args: {
          query: tool.schema
            .string()
            .describe("Search query to find relevant memories"),
          confidence_threshold: tool.schema
            .number()
            .min(0)
            .max(1)
            .optional()
            .describe("Minimum confidence threshold (0.0-1.0, default: 0.0)"),
          context_budget: tool.schema
            .number()
            .min(0)
            .optional()
            .describe("Maximum tokens for returned memories (default: 2000)"),
          limit: tool.schema
            .number()
            .min(0)
            .max(100)
            .optional()
            .describe("Maximum memories to return (default: 10)"),
          project: tool.schema
            .string()
            .optional()
            .describe("Project scope (default: from workspace)"),
          session: tool.schema
            .string()
            .optional()
            .describe("Session scope (default: from runtime context)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return {
              title: "Teacher Recall",
              output: "Teacher: unavailable — no bridge found. Run `teacher install`.",
            }
          }

          const projectId = args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown"
          const sessionId = args.session ?? context.sessionID

          const resp = await invokeBridge(python, bridgePath, {
            command: "recall",
            worktree: context.worktree,
            agent: "opencode",
            project: projectId,
            session: sessionId,
            query: args.query,
            confidence_threshold: args.confidence_threshold ?? 0.0,
            context_budget: args.context_budget ?? 2000,
            limit: args.limit ?? 10,
          })

          if (!resp.ok) {
            const err = (resp as any).error ?? {}
            return {
              title: "Teacher Recall — Failed",
              output: `Error [${err.type}]: ${err.message}`,
            }
          }

          const memories = (resp as any).memories ?? []
          if (memories.length === 0) {
            return {
              title: "Teacher Recall",
              output: "No matching memories found.",
              metadata: { total: 0 },
            }
          }

          const lines = memories.map(
            (m: any, i: number) =>
              `${i + 1}. [${m.kind}] (conf=${m.confidence.toFixed(2)}) ${m.content}`,
          )

          return {
            title: "Teacher Recall",
            output: [
              `Found ${(resp as any).total} matching memories (${memories.length} returned, cost=${(resp as any).context_cost} tokens):`,
              "",
              ...lines,
              "",
              `Provenance: ${memories.map((m: any) => m.id).join(", ")}`,
            ].join("\n"),
            metadata: {
              memories: memories.map((m: any) => ({
                id: m.id,
                kind: m.kind,
                confidence: m.confidence,
                content: m.content,
              })),
              total: (resp as any).total,
              truncated: (resp as any).truncated,
              context_cost: (resp as any).context_cost,
            },
          }
        },
      }),

      teacher_learn: tool({
        description:
          "Record a learning through Teacher's learn bridge command. Returns the stored memory ID.",
        args: {
          content: tool.schema
            .string()
            .describe("The learning content to record"),
          outcome: tool.schema
            .enum(["SUCCESS", "FAILURE", "NEUTRAL", "MIXED"])
            .optional()
            .describe("Outcome of the learning (default: NEUTRAL)"),
          project: tool.schema
            .string()
            .optional()
            .describe("Project scope identifier (default: from workspace)"),
          session: tool.schema
            .string()
            .optional()
            .describe("Session scope identifier (default: from runtime context)"),
          observation: tool.schema
            .string()
            .optional()
            .describe("What was observed (optional, defaults to content)"),
          action: tool.schema
            .string()
            .optional()
            .describe("What action was taken (optional)"),
          tags: tool.schema
            .array(tool.schema.string())
            .optional()
            .describe("Tags for filtering this learning (optional)"),
          confidence: tool.schema
            .number()
            .min(0)
            .max(1)
            .optional()
            .describe("Confidence in this learning [0,1] (default: 0.5)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return {
              title: "Teacher Learn",
              output: "Teacher: unavailable — no bridge found. Run `teacher install`.",
            }
          }

          const projectId = args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown"
          const sessionId = args.session ?? context.sessionID

          const resp = await invokeBridge(python, bridgePath, {
            command: "learn",
            worktree: context.worktree,
            agent: "opencode",
            project: projectId,
            session: sessionId,
            content: args.content,
            outcome: args.outcome ?? "NEUTRAL",
            observation: args.observation,
            action: args.action,
            tags: args.tags ?? [],
            confidence: args.confidence ?? 0.5,
          })

          if (!resp.ok) {
            const err = (resp as any).error ?? {}
            const errors = (resp as any).errors ?? []
            const detail = err.message ?? errors.join("; ") ?? "unknown error"
            return {
              title: "Teacher Learn — Failed",
              output: `Error [${err.type ?? "orchestrator"}]: ${detail}`,
            }
          }

          const result = (resp as any).result ?? resp
          return {
            title: "Teacher Learn",
            output: [
              "Learning recorded.",
              `  ID: ${result.experience_id ?? (resp as any).id ?? "unknown"}`,
              `  Stored: ${result.stored ?? true}`,
            ].join("\n"),
            metadata: {
              result,
              scope: { project: projectId, session: sessionId },
            },
          }
        },
      }),

      teacher_conflict: tool({
        description:
          "Detect conflicts between incoming content and stored memories. Returns conflicting memories with similarity scores.",
        args: {
          content: tool.schema
            .string()
            .describe("New content to check for conflicts"),
          project: tool.schema
            .string()
            .optional()
            .describe("Project scope"),
          session: tool.schema
            .string()
            .optional()
            .describe("Session scope"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Conflict", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "conflict",
            worktree: context.worktree,
            agent: "opencode",
            project: args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown",
            session: args.session ?? context.sessionID,
            content: args.content,
          })
          if (!resp.ok) {
            return { title: "Teacher Conflict — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const conflicts = (resp as any).result?.conflicts ?? (resp as any).conflicts ?? []
          if (conflicts.length === 0) {
            return { title: "Teacher Conflict", output: "No conflicts detected." }
          }
          const lines = conflicts.map((c: any, i: number) =>
            `${i + 1}. [${c.type ?? "unknown"}] sim=${(c.similarity ?? 0).toFixed(2)}: ${(c.content ?? "").slice(0, 100)}`
          )
          return {
            title: "Teacher Conflict",
            output: `Found ${conflicts.length} conflict(s):\n${lines.join("\n")}`,
            metadata: { conflicts },
          }
        },
      }),

      teacher_confidence: tool({
        description:
          "Compute confidence score for a prediction or memory. Returns score, band, and detailed factors.",
        args: {
          content: tool.schema.string().describe("Content to evaluate"),
          prediction: tool.schema.string().optional().describe("Predicted output"),
          evidence_count: tool.schema.number().optional().describe("Number of supporting evidence (default: 1)"),
          conflict_count: tool.schema.number().optional().describe("Number of conflicts (default: 0)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Confidence", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "confidence",
            worktree: context.worktree,
            content: args.content,
            prediction: args.prediction ?? "",
            evidence_count: args.evidence_count ?? 1,
            conflict_count: args.conflict_count ?? 0,
          })
          if (!resp.ok) {
            return { title: "Teacher Confidence — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const result = (resp as any).result ?? resp
          return {
            title: "Teacher Confidence",
            output: `Confidence: ${(result.confidence ?? 0).toFixed(3)} [${result.band ?? "unknown"}]`,
            metadata: result,
          }
        },
      }),

      teacher_search: tool({
        description:
          "Search memories by semantic similarity using TF-IDF ranking. Returns ranked results.",
        args: {
          query: tool.schema.string().describe("Search query"),
          limit: tool.schema.number().min(1).max(100).optional().describe("Max results (default: 10)"),
          project: tool.schema.string().optional().describe("Project scope"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Search", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "search",
            worktree: context.worktree,
            agent: "opencode",
            project: args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown",
            query: args.query,
            limit: args.limit ?? 10,
          })
          if (!resp.ok) {
            return { title: "Teacher Search — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const memories = (resp as any).result?.memories ?? (resp as any).memories ?? []
          if (memories.length === 0) {
            return { title: "Teacher Search", output: "No matching memories found." }
          }
          const lines = memories.map((m: any, i: number) =>
            `${i + 1}. [${m.kind}] (conf=${(m.confidence ?? 0).toFixed(2)}) ${m.content}`
          )
          return {
            title: "Teacher Search",
            output: `Found ${memories.length} result(s):\n${lines.join("\n")}`,
            metadata: { memories },
          }
        },
      }),

      teacher_deduplicate: tool({
        description:
          "Find and optionally merge duplicate/similar memories. Returns list of duplicates with similarity scores.",
        args: {
          content: tool.schema.string().describe("Content to check for duplicates"),
          project: tool.schema.string().optional().describe("Project scope"),
          threshold: tool.schema.number().optional().describe("Similarity threshold (0-1, default: 0.85)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Deduplicate", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "deduplicate",
            worktree: context.worktree,
            agent: "opencode",
            project: args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown",
            content: args.content,
            threshold: args.threshold ?? 0.85,
          })
          if (!resp.ok) {
            return { title: "Teacher Deduplicate — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const result = (resp as any).result ?? resp
          const dups = result.duplicates ?? []
          if (dups.length === 0) {
            return { title: "Teacher Deduplicate", output: "No duplicates found." }
          }
          const lines = dups.map((d: any, i: number) =>
            `${i + 1}. sim=${(d.similarity ?? 0).toFixed(2)}: ${(d.content ?? "").slice(0, 100)}`
          )
          return {
            title: "Teacher Deduplicate",
            output: `Found ${dups.length} duplicate(s):\n${lines.join("\n")}`,
            metadata: { duplicates: dups },
          }
        },
      }),

      teacher_knowledge: tool({
        description:
          "Extract learnings and knowledge patterns from consolidated memories.",
        args: {
          project: tool.schema.string().optional().describe("Project scope"),
          session: tool.schema.string().optional().describe("Session scope"),
          min_occurrences: tool.schema.number().optional().describe("Minimum occurrences to extract (default: 3)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Knowledge", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "knowledge",
            worktree: context.worktree,
            agent: "opencode",
            project: args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown",
            session: args.session ?? context.sessionID,
            min_occurrences: args.min_occurrences ?? 3,
          })
          if (!resp.ok) {
            return { title: "Teacher Knowledge — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const result = (resp as any).result ?? resp
          return {
            title: "Teacher Knowledge",
            output: `Knowledge extraction: promoted=${result.promoted_count ?? 0}, retained=${result.retained_count ?? 0}`,
            metadata: result,
          }
        },
      }),

      teacher_lifecycle: tool({
        description:
          "Manage memory lifecycle: score, decay, promote, or archive memories.",
        args: {
          action: tool.schema
            .enum(["score", "decay", "promote", "archive"])
            .describe("Lifecycle action to perform"),
          memory_id: tool.schema
            .string()
            .optional()
            .describe("Memory ID to operate on (required for promote/archive)"),
          project: tool.schema.string().optional().describe("Project scope"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Lifecycle", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "lifecycle",
            worktree: context.worktree,
            action: args.action,
            memory_id: args.memory_id ?? "",
            project: args.project ?? "",
          })
          if (!resp.ok) {
            return { title: "Teacher Lifecycle — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const result = (resp as any).result ?? resp
          return {
            title: "Teacher Lifecycle",
            output: `Action '${args.action}' completed: ${JSON.stringify(result)}`,
            metadata: result,
          }
        },
      }),

      teacher_diagnose: tool({
        description:
          "Full system diagnostics: health, stats, pipeline status.",
        args: {
          detail: tool.schema
            .enum(["summary", "full"])
            .optional()
            .describe("Detail level (default: summary)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return { title: "Teacher Diagnose", output: "Teacher: unavailable." }
          }
          const resp = await invokeBridge(python, bridgePath, {
            command: "diagnose",
            worktree: context.worktree,
            detail: args.detail ?? "summary",
          })
          if (!resp.ok) {
            return { title: "Teacher Diagnose — Failed", output: `Error: ${(resp as any).error?.message}` }
          }
          const result = (resp as any).result ?? resp
          const health = result.health ?? {}
          const lines = Object.entries(health).map(([k, v]) => `  ${k}: ${v}`)
          return {
            title: "Teacher Diagnose",
            output: `System Health:\n${lines.join("\n")}`,
            metadata: result,
          }
        },
      }),
    },
  }
}

export default Teacher
'''

TS_PLUGIN_SOURCE = _TS_PLUGIN_TEMPLATE.replace("__TEACHER_VERSION__", _TEACHER_VERSION)

import { tool } from "@opencode-ai/plugin/tool"
import type { Plugin } from "@opencode-ai/plugin"
import { execFile } from "node:child_process"
import { promisify } from "node:util"
import { resolve } from "node:path"
import { existsSync } from "node:fs"
import { execSync } from "node:child_process"

const execFileAsync = promisify(execFile)

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
 * Discover the Lerev bridge using a 4-tier cascade.
 */
async function discoverBridge(worktree: string): Promise<BridgeInfo | null> {
  const python = await findPython()

  // Tier 1: LEREV_HOME / EVO_HOME env var
  const lerevHome = process.env.LEREV_HOME || process.env.EVO_HOME
  if (lerevHome) {
    const bridgePath = resolve(lerevHome, "lerev", "bridge.py")
    if (fileExists(bridgePath)) {
      return { python: python ?? "python3", bridgePath, tier: "LEREV_HOME" }
    }
  }

  // Tier 2: lerev-bridge on PATH
  try {
    const bridgeCmd = execSync("where lerev-bridge", { windowsHide: true, timeout: 3000 })
      .toString().trim()
    if (bridgeCmd) {
      return { python: "", bridgePath: bridgeCmd, tier: "PATH" }
    }
  } catch {
    // Not on PATH
  }

  // Tier 3: python -m lerev.bridge
  if (python) {
    const available = await testModule(python, "lerev.bridge")
    if (available) {
      return { python, bridgePath: "-m lerev.bridge", tier: "installed_module" }
    }
  }

  // Tier 4: Dev fallback
  const devBridge = resolve(worktree, "scripts", "lerev_bridge.py")
  if (fileExists(devBridge)) {
    return { python: python ?? "python3", bridgePath: devBridge, tier: "dev_fallback" }
  }

  return null
}

/**
 * Invoke the Lerev bridge with a JSON request.
 */
async function invokeBridge(
  python: string,
  bridgePath: string,
  request: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const json = JSON.stringify(request)

  // Handle module invocation
  if (bridgePath === "-m lerev.bridge") {
    try {
      const { stdout, stderr } = await execFileAsync(python, ["-m", "lerev.bridge"], {
        input: json,
        timeout: 30000,
        windowsHide: true,
        maxBuffer: 1024 * 1024,
      })
      if (stderr) console.error("[lerev bridge stderr]", stderr)
      if (!stdout.trim()) {
        return { ok: false, error: { type: "protocol", message: "empty bridge response" } }
      }
      return JSON.parse(stdout.trim())
    } catch (err: any) {
      return {
        ok: false,
        error: { type: "bridge_error", message: err?.message ?? String(err) },
      }
    }
  }

  // Handle direct script invocation
  try {
    const { stdout, stderr } = await execFileAsync(python, [bridgePath], {
      input: json,
      timeout: 30000,
      windowsHide: true,
      maxBuffer: 1024 * 1024,
    })
    if (stderr) console.error("[lerev bridge stderr]", stderr)
    if (!stdout.trim()) {
      return { ok: false, error: { type: "protocol", message: "empty bridge response" } }
    }
    return JSON.parse(stdout.trim())
  } catch (err: any) {
    return {
      ok: false,
      error: { type: "bridge_error", message: err?.message ?? String(err) },
    }
  }
}

const LEREV: Plugin = async (ctx) => {
  const bridge = await discoverBridge(ctx.worktree)

  if (!bridge) {
    console.error("[lerev] No bridge found. Lerev tools will return errors.")
    console.error("[lerev] Run `lerev install` to set up Lerev globally.")
  }

  const python = bridge?.python ?? ""
  const bridgePath = bridge?.bridgePath ?? ""

  return {
    tool: {
      lerev_status: tool({
        description:
          "Check Lerev runtime status. Verifies Lerev, V2.5 routing, V2.6 memory, persistence, and security components are available.",
        args: {},
        async execute(_args, context) {
          if (!bridge) {
            return {
              title: "Lerev Status",
              output: "Lerev: unavailable — no bridge found. Run `lerev install`.",
            }
          }

          const resp = await invokeBridge(python, bridgePath, {
            command: "status",
            worktree: context.worktree,
          })

          if (!resp.ok) {
            return {
              title: "Lerev Status",
              output: `Lerev bridge error: ${(resp as any).error?.message ?? "unknown"}`,
            }
          }

          const components = (resp as any).components ?? {}
          const lines = Object.entries(components).map(
            ([k, v]) => `  ${k}: ${v}`,
          )
          return {
            title: "Lerev Status",
            output: `Lerev V2.6 Component Status:\n${lines.join("\n")}`,
            metadata: components,
          }
        },
      }),

      lerev_remember: tool({
        description:
          "Store an experience or memory through Lerev V2.6. Returns a real memory ID from Lerev's persistent memory system.",
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
              title: "Lerev Remember",
              output: "Lerev: unavailable — no bridge found. Run `lerev install`.",
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
              title: "Lerev Remember — Failed",
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
            title: "Lerev Remember",
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

      lerev_recall: tool({
        description:
          "Retrieve memories from Lerev V2.6 long-term memory. Returns relevant stored experiences matching the query, scoped to the current project/session.",
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
              title: "Lerev Recall",
              output: "Lerev: unavailable — no bridge found. Run `lerev install`.",
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
              title: "Lerev Recall — Failed",
              output: `Error [${err.type}]: ${err.message}`,
            }
          }

          const memories = (resp as any).memories ?? []
          if (memories.length === 0) {
            return {
              title: "Lerev Recall",
              output: "No matching memories found.",
              metadata: { total: 0 },
            }
          }

          const lines = memories.map(
            (m: any, i: number) =>
              `${i + 1}. [${m.kind}] (conf=${m.confidence.toFixed(2)}) ${m.content}`,
          )

          return {
            title: "Lerev Recall",
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
    },
  }
}

export default LEREV

// Plugin-layer probe: drives every School tool through the REAL plugin server()
// against the REAL bridge, so the per-tool wrappers (arg building, response
// shaping) are covered, not just the bridge handlers.
//
// Runs EVERY scenario from the bridge-level harness for each tool, so error
// branches and multi-action tools are exercised too.
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

const CASES = JSON.parse(readFileSync(process.argv[2], "utf8"))
const PLUGIN = process.argv[3]

async function main() {
  const mod = await import("file:///" + PLUGIN.replace(/\\/g, "/"))
  const def: any = mod.default
  const hooks: any = await def.server({ worktree: process.cwd(), directory: process.cwd() })
  const tools = hooks.tool ?? {}
  const names = Object.keys(tools).filter((n) => n.startsWith("school_")).sort()

  let pass = 0
  let runs = 0
  const fails: string[] = []
  for (const name of names) {
    const t = tools[name]
    const cmd = name.replace(/^school_/, "")
    const scenarios = CASES[cmd] ?? [{}]
    for (let si = 0; si < scenarios.length; si++) {
      const args = scenarios[si]
      const wt = mkdtempSync(join(tmpdir(), "plugin-probe-"))
      runs++
      try {
        writeFileSync(join(wt, "notes.md"), "probe notes paragraph\n".repeat(12))
        const ctx = { worktree: wt, directory: wt, sessionID: "probe-session", messageID: "m1", agent: "build" }
        const res: any = await Promise.race([
          t.execute(args, ctx),
          new Promise((_, rej) => setTimeout(() => rej(new Error("timeout 90s")), 90000)),
        ])
        const out = typeof res === "string" ? res : String(res?.output ?? res?.content ?? "")
        const bad: string[] = []
        if (out.includes("[object Object]")) bad.push("OBJECT_OBJECT")
        if (/bridge not found|no bridge found/i.test(out)) bad.push("BRIDGE")
        if (!out.trim()) bad.push("EMPTY")
        if (bad.length) {
          fails.push(`${name}[${si}]: ${bad.join(",")} :: ${out.slice(0, 200).replace(/\n/g, " | ")}`)
        } else {
          pass++
          if (si === 0) console.log(`OK   ${name.padEnd(28)} ${out.length} chars :: ${out.slice(0, 60).replace(/\n/g, " ")}`)
        }
      } catch (err: any) {
        fails.push(`${name}[${si}]: THREW :: ${String(err?.message ?? err).slice(0, 200)}`)
      } finally {
        try { rmSync(wt, { recursive: true, force: true }) } catch {}
      }
    }
  }

  console.log(`\nDONE tools=${names.length} runs=${runs} pass=${pass} fail=${fails.length}`)
  for (const f of fails) console.log("FAIL " + f)
}

main().catch((e) => {
  console.log("HARNESS ERROR " + String(e?.stack ?? e))
  process.exit(1)
})

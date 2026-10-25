import { writeFileSync } from "node:fs"
const mod = await import("file:///C:/Users/dex34/.config/opencode/plugins/school.ts")
const hooks = await mod.default.server({ worktree: process.cwd(), directory: process.cwd() })
const out = Object.entries(hooks.tool ?? {}).map(([name, t]) => ({ name, description: String(t.description ?? "") }))
writeFileSync("C:/Users/dex34/AppData/Local/Temp/opencode/tool_dump.json", JSON.stringify(out, null, 1))
console.log("tools", out.length)

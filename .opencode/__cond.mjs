import { readFileSync, writeFileSync } from "node:fs"
const t = JSON.parse(readFileSync("C:/Users/dex34/AppData/Local/Temp/opencode/tool_dump.json", "utf8"))
const lines = t.map(x => {
  const d = x.description.replace(/\s+/g, " ").trim()
  const first = d.split(/(?<=\.)\s/)[0]
  return x.name + " :: " + first.slice(0, 170)
})
writeFileSync("C:/Users/dex34/AppData/Local/Temp/opencode/tool_short.txt", lines.join("\n"))
console.log(lines.length)

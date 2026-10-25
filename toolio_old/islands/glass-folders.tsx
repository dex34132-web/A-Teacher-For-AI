import * as React from "react"
import { createRoot } from "react-dom/client"
import GlassFolder, { type FolderFile, type ArtPreset } from "../components/ui/glass-folder-cards"

/**
 * The tools section, as six glass folders.
 *
 * One folder per area of the product. Every tool in that area is a file
 * inside it — no descriptions, just the name, because the name is the whole
 * vocabulary. The chat key on each folder opens a dropdown of the tools in
 * that area: pick one and it comes to the front of the stack.
 */

type Area = {
  key: string
  label: string
  blurb: string
  art: ArtPreset
  seed: number
  tools: string[]
}

const AREAS: Area[] = [
  {
    key: "memory",
    label: "memory",
    blurb: "What the project already knows",
    art: "ember",
    seed: 11,
    tools: [
      "remember",
      "recall",
      "learn",
      "conflict",
      "confidence",
      "search",
      "deduplicate",
      "knowledge",
      "lifecycle",
      "diagnose",
    ],
  },
  {
    key: "context",
    label: "context",
    blurb: "What fits in the window right now",
    art: "aurora",
    seed: 23,
    tools: ["context_status", "context_compress", "context_restore", "observe", "read", "grep"],
  },
  {
    key: "plan",
    label: "plan",
    blurb: "Turning a request into a sequence",
    art: "dusk",
    seed: 37,
    tools: [
      "goal",
      "progress",
      "clarion",
      "blueprint",
      "edict",
      "weave",
      "compass",
      "brainstorm",
      "quantify",
      "elicit",
      "investigate",
    ],
  },
  {
    key: "build",
    label: "build",
    blurb: "Reading, running, shipping",
    art: "verdant",
    seed: 53,
    tools: ["session", "execute", "navigate", "workflow", "docs", "visualize", "research", "explore"],
  },
  {
    key: "skills",
    label: "skills",
    blurb: "Reusable procedures the agent grows",
    art: "glacier",
    seed: 71,
    tools: [
      "skill_list",
      "skill_search",
      "skill_create",
      "skill_use",
      "skill_feedback",
      "skill_status",
      "skill_evolve",
      "skill_search_github",
      "skill_discover",
      "skill_analyze_external",
      "skill_compare",
      "skill_import",
      "skills_menu",
    ],
  },
  {
    key: "ops",
    label: "ops",
    blurb: "The engine's own vitals",
    art: "aurora",
    seed: 97,
    tools: ["status", "dashboard", "route", "route_stats"],
  },
]

const SHEET_ART: ArtPreset[] = ["ember", "dusk", "glacier", "verdant", "aurora"]
// the colour each file's name band takes
const SHEET_ACCENT: string[] = ["#ff3d00", "#7fd0c6", "#9b87ff", "#ffb27a", "#a9d8d1"]

const HINT = "you can press the suggestions button to give suggestions for other tools in this category"

function name(tool: string) {
  return "school_" + tool
}

function Tools() {
  const [focus, setFocus] = React.useState<Record<string, string>>({})
  const [open, setOpen] = React.useState<Record<string, boolean>>({})
  // what people suggest lands in the folder as a new file
  const [extra, setExtra] = React.useState<Record<string, FolderFile[]>>({})

  return (
    <div className="gf-grid">
      {AREAS.map((area, ai) => {
        const files: FolderFile[] = [
          ...area.tools.map((tool, i) => ({
            name: name(tool),
            art: SHEET_ART[(i + ai) % SHEET_ART.length],
            accent: SHEET_ACCENT[(i + ai) % SHEET_ACCENT.length],
          })),
          ...(extra[area.key] ?? []),
        ]
        return (
          <div className="gf-cell" key={area.key}>
            <GlassFolder
              label={area.label}
              meta={area.tools.length + " tools"}
              tone="dark"
              art={area.art}
              seed={area.seed}
              files={files}
              action="suggest"
              hint={HINT}
              focusFile={focus[area.key]}
              open={open[area.key] ?? false}
              onOpenChange={(v) => setOpen((o) => ({ ...o, [area.key]: v }))}
              suggestions={area.tools.map((tool) => ({
                label: name(tool),
                onSelect: () => {
                  setFocus((f) => ({ ...f, [area.key]: name(tool) }))
                  setOpen((o) => ({ ...o, [area.key]: true }))
                },
              }))}
              onSuggest={(name, body) => {
            // no api, no database - it opens the maintainer's mail client
            const subject = "Tool suggestion: " + name;
            const text =
              "tool: " + name + "\n\nfolder: " + area.key + "\n\nwhy:\n" + body;
            window.location.href =
              "mailto:dex34132@gmail.com?subject=" +
              encodeURIComponent(subject) +
              "&body=" +
              encodeURIComponent(text);
          }}
              width={330}
              appearDelay={ai * 90}
            />
            <p className="gf-blurb">{area.blurb}</p>
          </div>
        )
      })}
    </div>
  )
}

const mount = document.getElementById("glassFolders")
if (mount) {
  const root = createRoot(mount)
  root.render(<Tools />)
}

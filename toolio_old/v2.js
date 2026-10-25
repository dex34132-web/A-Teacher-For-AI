/* ============================================================
   schoolio · v2 behaviour
   magnet cursor · tide transitions · slow, self-running instruments
   ============================================================ */
(() => {
  "use strict"
  const $ = (s, r = document) => r.querySelector(s)
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s))
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v))
  const root = document.documentElement
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches
  const TOOLSET = typeof TOOLS !== "undefined" ? TOOLS : []

  const fatal = (name, err) => {
    console.error("[schoolio:v2] " + name, err)
    let b = $("#__fatal")
    if (!b) {
      b = document.createElement("div")
      b.id = "__fatal"
      b.setAttribute(
        "style",
        "position:fixed;left:0;right:0;top:0;z-index:2147483647;background:#b3261e;color:#fff;font:12px/1.5 ui-monospace,monospace;padding:8px 12px",
      )
      document.body.appendChild(b)
    }
    b.textContent = (b.textContent ? b.textContent + " | " : "") + name + ": " + (err && err.message ? err.message : err)
  }
  const safe = (name, fn) => {
    try {
      fn()
    } catch (err) {
      fatal(name, err)
    }
  }

  /* ---------------------------------------------------------------
     1. MAGNET CURSOR — pulls components toward the pointer
     --------------------------------------------------------------- */
  const MAGNET_SVG = `<svg viewBox="0 0 48 48" aria-hidden="true">
      <path class="v2-magnet__u" d="M10 34 V20 a14 14 0 0 1 28 0 v14"></path>
      <path class="v2-magnet__p" d="M10 34 h9 v-14 a14 14 0 0 1 4.5-10.7 a14 14 0 0 0 4.5 10.7 v14 h9"></path>
      <rect class="v2-magnet__cap" x="10" y="34" width="9" height="6"></rect>
      <rect class="v2-magnet__cap" x="29" y="34" width="9" height="6"></rect>
    </svg>`

  const magnetCursor = () => {
  return; // the magnetism is gone - no magnet cursor, no attraction
    const host = document.createElement("div")
    host.className = "cursor v2-magnet"
    host.innerHTML =
      '<span class="v2-magnet__field"></span>' +
      '<span class="v2-magnet__ring"></span>' +
      '<span class="v2-magnet__body">' +
      MAGNET_SVG +
      "</span>" +
      '<span class="v2-magnet__read"><b>00</b> <span>0000 / 0000 mm</span></span>'
    document.body.appendChild(host)
    /* the magnet is invisible until a real mouse is seen — otherwise it
       floats in the middle of the page with its readout stuck at 0,0 */
    host.style.setProperty("display", "none", "important");
    const body = $(".v2-magnet__body", host)
    const read = $(".v2-magnet__read", host)
    const readIdx = $("b", read)
    const readDim = $("span", read)

    let x = innerWidth / 2
    let y = innerHeight / 2
    let tx = x
    let ty = y
    let live = false
    let hot = false
    const pulls = new Map()

    const wake = () => {
      if (live) return
      live = true
      host.classList.add("on")
      host.style.removeProperty("display")
      root.classList.add("has-cursor")
    }

    addEventListener(
      "pointermove",
      (e) => {
        if (e.pointerType === "touch") return
        wake()
        tx = e.clientX
        ty = e.clientY
      },
      { passive: true },
    )

    addEventListener(
      "pointerdown",
      () => {
        if (!live) return
        // a click slams the field shut: everything nearby snaps inward
        $$("[data-magnet]").forEach((el) => {
          const r = el.getBoundingClientRect()
          const cx = r.left + r.width / 2
          const cy = r.top + r.height / 2
          const d = Math.hypot(cx - x, cy - y)
          if (d > 220) return
          const k = (1 - d / 220) * 26
          const a = Math.atan2(y - cy, x - cx)
          el.style.translate = Math.cos(a) * k + "px " + Math.sin(a) * k + "px"
        })
      },
      { passive: true },
    )

    const sections = () => $$("section[id]")
    const frame = () => {
      x += (tx - x) * 0.28
      y += (ty - y) * 0.28
      host.style.transform = "translate3d(" + x + "px," + y + "px,0)"
      if (read) read.style.transform = "translate3d(" + (x + 26) + "px," + (y + 22) + "px,0)"
      if (body) body.style.transform = "rotate(-16deg) scale(" + (hot ? 1.12 : 1) + ")"

      // pull nearby components toward the magnet
      let near = 0
      $$("[data-magnet]").forEach((el) => {
        const r = el.getBoundingClientRect()
        const cx = r.left + r.width / 2
        const cy = r.top + r.height / 2
        const dx = x - cx
        const dy = y - cy
        const d = Math.hypot(dx, dy)
        const reach = 150
        if (d < reach && d > 1) {
          const k = (1 - d / reach) * 20
          el.style.translate = (dx / d) * k + "px " + (dy / d) * k + "px"
          el.classList.add("is-pulled")
          near++
        } else if (!pulls.has(el)) {
          el.style.translate = ""
          el.classList.remove("is-pulled")
        }
      })
      hot = near > 0
      host.classList.toggle("is-hot", hot)

      // readout: chapter index + depth
      const secs = sections()
      const probe = innerHeight * 0.42
      let idx = 0
      secs.forEach((s, i) => {
        const r = s.getBoundingClientRect()
        if (r.top <= probe) idx = i
      })
      if (readIdx) readIdx.textContent = String(idx).padStart(2, "0")
      if (readDim) {
        const depth = Math.round(clamp(scrollY / (document.body.scrollHeight - innerHeight), 0, 1) * 240)
        readDim.textContent =
          String(Math.round((x * 0.42) | 0)).padStart(4, "0") + " / " + String(depth).padStart(4, "0") + " mm"
      }
      requestAnimationFrame(frame)
    }
    requestAnimationFrame(frame)
  }

  /* ---------------------------------------------------------------
     2. TIDE TRANSITION — water rushes down, shores show the target
     --------------------------------------------------------------- */
  const tide = () => {
    const el = document.createElement("div")
    el.className = "v2-tide"
    el.innerHTML =
      '<svg viewBox="0 0 1440 900" preserveAspectRatio="none" aria-hidden="true">' +
      '<path class="v2-tide__wave" d="M0 0 H1440 V760 Q1080 900 720 860 T0 780 Z"></path>' +
      '<path class="v2-tide__edge" d="M0 780 Q360 900 720 860 T1440 760"></path>' +
      "</svg>" +
      '<span class="v2-tide__label">loading</span>'
    document.body.appendChild(el)
    const label = $(".v2-tide__label", el)
    let busy = false

    addEventListener("click", (e) => {
      const a = e.target.closest && e.target.closest('a[href^="#"]')
      if (!a) return
      const id = a.getAttribute("href").slice(1)
      const target = id ? document.getElementById(id) : null
      if (!target || busy) return
      e.preventDefault()
      busy = true
      const name = (a.getAttribute("data-tide") || target.id || "section").toUpperCase()
      if (label) label.textContent = name
      el.classList.remove("is-out")
      el.classList.add("is-in")
      // The sections above the target keep expanding while the wave plays
      // (reveal sheets, counters, the terminal), so a single scroll lands
      // short. Re-aim a few times as the page settles.
      const land = () => {
        const y = target.getBoundingClientRect().top + scrollY - 84
        window.scrollTo({ top: Math.max(0, y), behavior: "auto" })
      }
      setTimeout(() => {
        land()
        target.classList.add("v2-glitch")
        setTimeout(land, 320)
        setTimeout(land, 700)
        el.classList.remove("is-in")
        el.classList.add("is-out")
        setTimeout(() => {
          target.classList.remove("v2-glitch")
          el.classList.remove("is-out")
          busy = false
        }, 950)
      }, 860)
    })
  }

  /* ---------------------------------------------------------------
     3. FORGETTING — a slow, legible session replay
     --------------------------------------------------------------- */
  const TRANSCRIPT = [
    ["user", "explain the retry policy again", 320],
    ["agent", "backoff is 3 tries, then dead letter", 280],
    ["user", "no — 5 tries, and the queue is per tenant", 300],
    ["agent", "got it: 5 tries, per tenant queue", 260],
    ["agent", "patching core/queue.py", 240],
    ["test", "ok 44 passed, 1 skipped", 220],
    ["agent", "that skip is the flaky one we discussed", 300],
    ["user", "yes, only fails on the sandbox runner", 290],
    ["agent", "noted, will skip it on sandbox", 250],
    ["user", "that is the whole policy, thanks", 270],
    ["agent", "summary: backoff 5, per tenant, skip sandbox", 300],
    ["user", "perfect", 180],
  ]

  const forgetV2 = () => {
    return; // the compression stage (compress.js) owns this section now
    const lines = $("#ctx-lines")
    const fill = $("#ctx-fill")
    const cut = $("#ctx-cut")
    const tokens = $("#ctx-tokens")
    const label = $("#ctx-label")
    const stamp = $("#stamp")
    const beats = $$("#beats .beat")
    const bar = $("#beats-bar")
    if (!lines || !fill) return
    const MAX = 128

    const cycle = () => {
      lines.innerHTML = ""
      fill.style.width = "0%"
      if (cut) cut.style.width = "0%"
      if (stamp) stamp.classList.remove("land")
      if (bar) bar.innerHTML = "<i></i>"
      beats.forEach((b) => b.classList.remove("is-on"))
      if (label) label.textContent = "context window"

      let i = 0
      let used = 0
      const step = () => {
        if (i >= TRANSCRIPT.length) {
          // compress
          if (label) label.textContent = "compressed — 1 block, originals kept"
          if (cut) cut.style.width = "62%"
          if (fill) fill.style.width = "34%"
          if (tokens) tokens.textContent = "43k / 128k"
          if (stamp) setTimeout(() => stamp.classList.add("land"), 450)
          beats.forEach((b, k) => setTimeout(() => b.classList.add("is-on"), 700 + k * 1500))
          const barIn = bar && bar.querySelector("i")
          if (barIn) setTimeout(() => (barIn.style.width = "100%"), 700)
          setTimeout(() => cycle(), 14000)
          return
        }
        const [who, text, cost] = TRANSCRIPT[i]
        const li = document.createElement("li")
        li.innerHTML = "<b>" + who + "</b>  " + text
        lines.appendChild(li)
        requestAnimationFrame(() => li.classList.add("on"))
        used += cost
        const pct = Math.min(100, (used / (MAX * 10)) * 100)
        if (fill) fill.style.width = pct + "%"
        if (tokens) tokens.textContent = Math.min(MAX, Math.round(used / 10)) + "k / 128k"
        if (i === 5) beats[0] && beats[0].classList.add("is-on")
        if (i === 8) beats[1] && beats[1].classList.add("is-on")
        if (i === 10) beats[2] && beats[2].classList.add("is-on")
        i++
        setTimeout(step, 520)
      }
      setTimeout(step, 500)
    }
    cycle()
  }

  /* ---------------------------------------------------------------
     4. PIPELINE — the request walks the hops
     --------------------------------------------------------------- */
  const pipeV2 = () => {
    const nodes = $$("#pipe-nodes .v2-pnode")
    const stations = $$("#pipe-stations .v2-station")
    if (!nodes.length) return
    let i = 0
    const tick = () => {
      nodes.forEach((n, k) => n.classList.toggle("is-live", k === i))
      stations.forEach((s, k) => s.classList.toggle("is-live", k === i))
      i = (i + 1) % nodes.length
      setTimeout(tick, 1400)
    }
    tick()
  }

  /* ---------------------------------------------------------------
     5. ANATOMY — blocks form, tokens drop
     --------------------------------------------------------------- */
  const anatV2 = () => {
    const grid = $("#cellgrid")
    const steps = $$(".v2-astep")
    const before = $("#anat-before")
    const after = $("#anat-after")
    const saved = $("#anat-saved")
    if (!grid) return
    grid.innerHTML = ""
    for (let n = 0; n < 48; n++) grid.appendChild(document.createElement("i"))
    const cells = $$("i", grid)
    const BLOCKS = [
      { id: "b1", from: 0, to: 4 },
      { id: "b3", from: 8, to: 12 },
      { id: "b7", from: 24, to: 31 },
    ]

    const count = (el, to, dur) => {
      if (!el) return
      const t0 = performance.now()
      const step = () => {
        const t = clamp((performance.now() - t0) / dur, 0, 1)
        const v = Math.round(128000 * (1 - t) + 9400 * t)
        el.textContent = v.toLocaleString("en-US").replace(/,/g, " ")
        /* the saved figure must follow the number, or the panel contradicts
           itself for the second and a half the count runs */
        if (saved) saved.textContent = ((1 - v / 128000) * 100).toFixed(1) + "%"
        if (t < 1) requestAnimationFrame(step)
      }
      requestAnimationFrame(step)
    }

    let bi = 0
    const cycle = () => {
      const b = BLOCKS[bi]
      cells.forEach((c, n) => {
        c.classList.remove("lit", "block", "scan")
        if (n >= b.from && n < b.to) c.classList.add("lit")
        if (n === b.from) c.classList.add("scan")
      })
      setTimeout(() => {
        for (let n = b.from; n < b.to; n++) cells[n] && cells[n].classList.add("block")
      }, 500)
      steps.forEach((s, k) => s.classList.toggle("is-on", k === bi))
      if (before) before.textContent = "128 000"
      count(after, 9400, 1600)
      if (saved) saved.textContent = "92.6%"
      bi = (bi + 1) % BLOCKS.length
      setTimeout(cycle, 4200)
    }
    cycle()
  }

  /* ---------------------------------------------------------------
     6. TOOLS — every one of the 52 explained
     --------------------------------------------------------------- */
  const PURPOSE = {
    memory: "store what matters, scoped to this project",
    context: "keep the window small without losing the detail",
    plan: "turn a conversation into a plan you can execute",
    build: "touch files and run things on the machine",
    skills: "teach the agent a procedure it can reuse",
    ops: "see what the system is doing right now",
  }
  const MCP_TOOLS = [
  "remember",
  "recall",
  "learn",
  "search",
  "conflict",
  "confidence",
  "deduplicate",
  "knowledge",
  "lifecycle",
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
  "observe",
  "goal",
  "research",
  "explore",
  "progress",
  "session",
  "execute",
  "navigate",
  "clarion",
  "blueprint",
  "edict",
  "weave",
  "compass",
  "brainstorm",
  "quantify",
  "elicit",
  "investigate",
  "context_status",
  "context_compress",
  "context_restore",
  "read",
  "grep",
  "status",
  "dashboard",
  "route",
  "route_stats",
  "diagnose",
  "visualize",
  "workflow",
  "docs",
]

  const toolsV2 = () => {
    return // the tools section is the glass-folder island now (assets/glass-folders.js)
    const track = $("#tooltrack")
    const count = $("#toolcount")
    const filters = $("#filters")
    if (!track) return

    track.innerHTML = ""
    TOOLSET.forEach((t, i) => {
      const name = t[0]
      const desc = t[1] || ""
      const cat = t[2] || "ops"
      const isMcp = MCP_TOOLS.indexOf(name.replace(/^school_/, "")) >= 0
      const card = document.createElement("article")
      card.className = "tool" + (isMcp ? " is-mcp" : "")
      card.dataset.cat = cat
      card.dataset.mcp = isMcp ? "1" : ""
      card.dataset.magnet = "1"
      card.innerHTML =
        '<div class="tool__top"><span class="tool__i">school_' +
        name +
        '</span><span class="tool__cat">' +
        cat +
        "</span></div>" +
        '<p class="tool__d">' +
        desc +
        "</p>" +
        '<p class="tool__use">' +
        (PURPOSE[cat] || "part of the engine") +
        "</p>" +
        (isMcp ? '<span class="tool__mcp">mcp</span>' : "") +
        '<span class="tool__bar"><i></i></span>'
      card.addEventListener("pointermove", (e) => {
        const r = card.getBoundingClientRect()
        card.style.setProperty("--mx", e.clientX - r.left + "px")
        card.style.setProperty("--my", e.clientY - r.top + "px")
      })
      track.appendChild(card)
    })


    const apply = (cat) => {
      let shown = 0
      $$(".tool", track).forEach((c) => {
        const on = cat === "all" || (cat === "mcp" ? c.dataset.mcp === "1" : c.dataset.cat === cat)
        c.style.display = on ? "" : "none"
        if (on) shown++
      })
      if (count) count.textContent = shown + " / " + TOOLSET.length + " shown"
      $$(".chip", filters || document).forEach((c) => c.classList.toggle("is-on", c.dataset.cat === cat))
    }
    $$(".chip", filters || document).forEach((c) =>
      c.addEventListener("click", () => apply(c.dataset.cat || "all")),
    )
    apply("all")
  }

  /* ---------------------------------------------------------------
     7. MCP — client configs + the tool surface
     --------------------------------------------------------------- */
  /* ---------------------------------------------------------------
     6b. TOOL RAIL — drag it like a tape
     --------------------------------------------------------------- */
  const railDrag = () => {
    return; // the tool rail is a grid now - no drag, no wheel trap
    const vp = $("#toolviewport")
    const track = $("#tooltrack")
    if (!vp || !track) return
    let down = false
    let sx = 0
    let start = 0
    let vel = 0
    const sl = () => parseFloat(track.dataset.sl || "0")
    vp.addEventListener("pointerdown", (e) => {
      down = true
      sx = e.clientX
      start = sl()
      vel = 0
      try {
        vp.setPointerCapture(e.pointerId)
      } catch (err) {}
    })
    vp.addEventListener("pointermove", (e) => {
      if (!down) return
      const dx = e.clientX - sx
      vel = dx * 0.35
      track.dataset.sl = String(start + dx)
      track.style.transform = "translate3d(" + (start + dx) + "px,0,0)"
    })
    const up = () => {
      if (!down) return
      down = false
      const step = () => {
        if (Math.abs(vel) > 0.4) {
          const v = sl() + vel
          vel *= 0.94
          track.dataset.sl = String(v)
          track.style.transform = "translate3d(" + v + "px,0,0)"
          requestAnimationFrame(step)
        } else vel = 0
      }
      requestAnimationFrame(step)
    }
    vp.addEventListener("pointerup", up)
    vp.addEventListener("pointercancel", up)
    vp.addEventListener(
      "wheel",
      (e) => {
        if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
          const v = sl() - e.deltaX
          track.dataset.sl = String(v)
          track.style.transform = "translate3d(" + v + "px,0,0)"
          e.preventDefault()
        }
      },
      { passive: false },
    )
  }

  /* ---------------------------------------------------------------
     6c. V2 REVEAL — its own observer, with a fallback that always settles
     --------------------------------------------------------------- */
  const v2Reveal = () => {
    const targets = $$(
      ".v2-station, .v2-astep, .v2-pnode, .v2-os, .v2-mcp__list li, .v2-mcp__res li, .v2-anat__meter div, .v2-forget .beat, .tool, .figure, .v2-pipe__nodes > li, .v2-pipe__stations > li, .v2-anat__steps > li, .v2-anat__side li",
    )
    targets.forEach((el) => el.classList.add("v2-rv"))
    const show = (el) => el.classList.add("is-in")
    if (!("IntersectionObserver" in window)) {
      targets.forEach(show)
      return
    }
    const io = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (!e.isIntersecting) return
          show(e.target)
          io.unobserve(e.target)
        })
      },
      { threshold: 0.2 },
    )
    targets.forEach((el) => io.observe(el))
    const sweep = () => {
      targets.forEach((el) => {
        if (el.classList.contains("is-in")) return
        const r = el.getBoundingClientRect()
        if (r.top < innerHeight && r.bottom > 0) show(el)
      })
    }
    setTimeout(sweep, 1400)
    setInterval(sweep, 900)
    // Final safety: nothing may stay hidden. If the observer never fires
    // (background tab, throttled renderer, clipped rail) everything shows.
    setTimeout(() => targets.forEach(show), 5200)
  }

  const mcpV2 = () => {
    const body = $("#mcp-body")
    const list = $("#mcp-list")
    if (!body) return
    const CONFIGS = {
      claude:
        '$ school mcp config claude\n\n{\n  "mcpServers": {\n    "school": {\n      "command": "python",\n      "args": ["-m", "school.mcp"]\n    }\n  }\n}\n\n# claude code    -> .mcp.json (project) or ~/.claude.json (global)\n# claude desktop -> claude_desktop_config.json\n# restart the client: 52 school_* tools appear',
      codex:
        '$ school mcp config codex\n\n# ~/.codex/config.toml\n[mcp_servers.school]\ncommand = "python"\nargs = ["-m", "school.mcp"]\n\n# restart codex: the same engine, the same memory',
      generic:
        "$ school mcp config\n\n# prints the mcpServers block for the client you name,\n# or a generic one every MCP client can read.\n#\n# server    : python -m school.mcp        (stdio)\n# also      : school mcp                 (same server)\n# tools     : 52 school_* functions\n# resources : school://context, school://memories,\n#             school://skills, school://prompt/relevant_context\n# prompt    : relevant_context\n# budget    : every resource is trimmed, never dumped",
    }
    const tabs = $$(".v2-mcp__tab")
    const show = (k) => {
      body.textContent = CONFIGS[k] || CONFIGS.generic
      tabs.forEach((t) => t.classList.toggle("is-on", t.dataset.mcp === k))
      body.animate ? body.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 420, easing: "ease-out" }) : null
    }
    tabs.forEach((t) => t.addEventListener("click", () => show(t.dataset.mcp)))
    show("claude")

    if (list) {
      list.innerHTML = ""
      MCP_TOOLS.forEach((n) => {
        const li = document.createElement("li")
        li.textContent = "school_" + n
        li.dataset.magnet = "1"
        list.appendChild(li)
      })
    }
  }

  /* ---------------------------------------------------------------
     8. INSTALL — every platform, one click
     --------------------------------------------------------------- */
  const installV2 = () => {
    const grid = $("#inst-grid")
    const title = $("#term-title")
    const cmd = $("#term-cmd")
    const copy = $("#copy-install")
    if (!grid) return
    const WAYS = {
      clone: {
        label: "1 \xB7 clone",
        cmd: "git clone https://github.com/dex34132-web/A-School-For-AI.git && cd A-School-For-AI",
        out: [
          "Cloning into 'A-School-For-AI'...",
          "This is the only install path that works today.",
          "No PyPI package, no Homebrew tap, no Chocolatey",
          "package, no npm package, no built installer.",
        ],
      },
      pip: {
        label: "2 \xB7 install",
        cmd: 'pip install -e ".[mcp]"',
        out: [
          "Obtaining file:///.../A-School-For-AI",
          "Installing collected packages: school",
          "Successfully installed school-2.6.0",
          "The [mcp] extra adds the MCP server.",
        ],
      },
      wire: {
        label: "3 \xB7 wire your agent",
        cmd: "school install",
        out: [
          "Detected agents: opencode",
          "  plugin -> ~/.config/opencode/plugins/school.ts",
          "  config -> ~/.config/opencode/opencode.jsonc",
          "  bridge -> school-bridge",
          "Other agents: school mcp config <client>",
        ],
      },
      mcp: {
        label: "4 \xB7 or speak MCP",
        cmd: "python -m school.mcp",
        out: [
          "A standard MCP server on stdio. Any MCP client works:",
          "Claude Code, Codex, Cursor, Windsurf, Cline, Roo Code,",
          "Gemini CLI, Goose, Aider, Continue, Copilot Chat.",
          "52 tools, four budgeted resources, one prompt.",
        ],
      },
      check: {
        label: "5 \xB7 verify",
        cmd: "school doctor",
        out: [
          "PASS  python",
          "PASS  school package",
          "PASS  memory store",
          "PASS  routing",
          "PASS  bridge",
          "RESULT: SCHOOL IS READY",
        ],
      },
    }
    let current = "clone"

    const paint = (k) => {
      current = k
      const w = WAYS[k]
      if (title) title.textContent = w.label
      if (cmd) cmd.textContent = w.cmd
      const out = $("#term-out")
      if (out) {
        out.innerHTML = (w.out || [])
          .map((line, i) => `<span class="terminal__line${i === 0 ? " is-h" : ""}">${line}</span>`)
          .join("")
      }
      $$(".v2-os", grid).forEach((b) => b.classList.toggle("is-on", b.dataset.os === k))
    }
    $$(".v2-os", grid).forEach((b) => {
      b.dataset.magnet = "1"
      b.addEventListener("click", () => paint(b.dataset.os))
    })

    // the first working step, every time
    paint("clone")

    if (copy) {
      copy.addEventListener("click", () => {
        const text = WAYS[current].cmd
        const done = () => {
          const old = copy.textContent
          copy.textContent = "copied"
          setTimeout(() => (copy.textContent = old), 1400)
        }
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done)
        else done()
      })
    }
  }

  /* ---------------------------------------------------------------
     9. CORE SAMPLE — drills on its own, never tied to the scroll
     --------------------------------------------------------------- */
  const coreV2 = () => {
    const cv = $("#core")
    if (!cv) return
    const c = cv.getContext("2d")
    const W = cv.width
    const H = cv.height
    const yEl = $("#core-y")
    const kEl = $("#core-k")
    const STRATA = 11

    const draw = (p) => {
      c.clearRect(0, 0, W, H)
      for (let s = 0; s < STRATA; s++) {
        const y = (s / STRATA) * H
        const h = H / STRATA
        const g = c.createLinearGradient(0, y, 0, y + h)
        const tone = 16 + s * 3
        g.addColorStop(0, "rgba(" + tone + "," + tone + "," + (tone + 4) + ",1)")
        g.addColorStop(1, "rgba(" + (tone + 6) + "," + (tone + 6) + "," + (tone + 10) + ",1)")
        c.fillStyle = g
        c.fillRect(0, y, W, h - 1)
        c.fillStyle = "rgba(239,234,224,.10)"
        for (let i = 0; i < 5; i++) {
          const yy = y + 4 + i * ((h - 8) / 5)
          c.fillRect(0, yy, W, 1)
        }
      }
      const fy = p * H
      c.fillStyle = "rgba(255,61,0,.16)"
      c.fillRect(0, fy - 36, W, 72)
      c.strokeStyle = "rgba(255,61,0,.9)"
      c.lineWidth = 1
      c.beginPath()
      c.moveTo(0, fy)
      c.lineTo(W, fy)
      c.stroke()
      c.fillStyle = "rgba(239,234,224,.35)"
      for (let i = 0; i <= 20; i++) {
        const ry = (i / 20) * H
        c.fillRect(0, ry, i % 5 === 0 ? 16 : 8, 1)
      }
      if (yEl) yEl.textContent = "depth " + (p * 240).toFixed(2) + " m"
      if (kEl) kEl.textContent = "strata " + String(Math.min(STRATA, Math.floor(p * STRATA) + 1)).padStart(2, "0")
    }

    let t = 0
    const t0 = performance.now()
    const loop = () => {
      t = (performance.now() - t0) / 24000
      const p = 0.5 + 0.5 * Math.sin(t * Math.PI * 2)
      draw(p)
      requestAnimationFrame(loop)
    }
    draw(0.5)
    requestAnimationFrame(loop)
  }

  /* ---------------------------------------------------------------
     10. boot
     --------------------------------------------------------------- */
  const start = () => {
    safe("magnetCursor", magnetCursor)
    safe("tide", tide)
    safe("coreV2", coreV2)
    safe("forgetV2", forgetV2)
    safe("pipeV2", pipeV2)
    safe("anatV2", anatV2)
    safe("toolsV2", toolsV2)
    safe("mcpV2", mcpV2)
    safe("installV2", installV2)
    safe("railDrag", railDrag)
    safe("v2Reveal", v2Reveal)
    // mark the interactive pieces as magnetic
    $$(".btn, .chip, .v2-os, .rail__list a, .topbar__link").forEach((el) => {
      if (!el.hasAttribute("data-magnet")) el.setAttribute("data-magnet", "1")
    })
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start)
  else start()
})()

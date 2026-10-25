const TOOLS = [
    ["status","Runtime status: versions and component health.","ops"],
    ["dashboard","One glance: routing, next tools, savings, recall, diagnostics.","ops"],
    ["remember","Store an experience or memory. Returns its id.","memory"],
    ["recall","Retrieve scoped memories before you start work.","memory"],
    ["learn","Record a learning after a meaningful outcome.","memory"],
    ["conflict","Detect contradictions before saving new information.","memory"],
    ["confidence","Score how well supported a claim or memory is.","memory"],
    ["search","TF-IDF search across stored memories, ranked.","memory"],
    ["deduplicate","Find and optionally merge near-duplicate memories.","memory"],
    ["knowledge","Extract recurring learnings from consolidated memory.","memory"],
    ["lifecycle","Score, decay, promote or archive a memory.","memory"],
    ["diagnose","Health, stats and pipeline, in one report.","memory"],
    ["route","Assess how much routing machinery a task needs.","ops"],
    ["route_stats","Per-tool call counts and average durations.","ops"],
    ["context_status","Blocks stored, restores, tokens saved, view mode.","context"],
    ["context_compress","Compress session messages into addressable blocks.","context"],
    ["context_restore","Restore blocks by id. Empty id restores all.","context"],
    ["observe","Record agent behaviour and extract a pattern.","context"],
    ["read","Read a file through the context optimizer.","context"],
    ["grep","Regex search with path:line:content results.","context"],
    ["goal","Set, complete, block, pause or resume a goal.","plan"],
    ["progress","Track learning progress with visual bars.","plan"],
    ["clarion","Interview to capture requirements for any work.","plan"],
    ["blueprint","Turn an interview into a design specification.","plan"],
    ["edict","Turn an interview into ordered commands and rules.","plan"],
    ["weave","Shape commands into phases, lanes and dependencies.","plan"],
    ["compass","Derive acceptance criteria from an interview.","plan"],
    ["brainstorm","Diverge then converge on ideas, with techniques.","plan"],
    ["quantify","Deterministic precision checks on a plan's numbers.","plan"],
    ["elicit","Find the material questions a plan is missing.","plan"],
    ["investigate","Run an adaptive diagnostic case.","plan"],
    ["session","Create, resume, summarize, export or list sessions.","build"],
    ["execute","Run a shell command and learn from its outcome.","build"],
    ["navigate","Read, list, search or map files in a workspace.","build"],
    ["workflow","Structured tdd, debug, brainstorm and review runs.","build"],
    ["docs","Fetch reference docs with a local cache.","build"],
    ["visualize","Render data as terminal-native visuals.","build"],
    ["research","Research a query against internal knowledge first.","build"],
    ["explore","Extract structure, patterns and conventions.","build"],
    ["skill_list","List the skill registry with state and confidence.","skills"],
    ["skill_search","Ranked skill matches for a task query.","skills"],
    ["skill_create","Save a validated, agent-authored skill.","skills"],
    ["skill_use","Retrieve one skill and record the reuse.","skills"],
    ["skill_feedback","Report whether a reused skill worked.","skills"],
    ["skill_status","Counters: states, model calls, reuse, budget.","skills"],
    ["skill_evolve","Consolidate duplicates and version a skill.","skills"],
    ["skill_search_github","Bounded GitHub search for a capability gap.","skills"],
    ["skill_discover","Scan GitHub results for skill-like files.","skills"],
    ["skill_analyze_external","Budgeted analysis of one GitHub candidate.","skills"],
    ["skill_compare","Compare a candidate against local skills.","skills"],
    ["skill_import","Import an approved candidate into the registry.","skills"],
    ["skills_menu","Drive the whole skill engine from one menu.","skills"]
  ]
const CATS = ["all","memory","context","plan","build","skills","ops"];

/* ==========================================================================
   schoolio — INSTRUMENT LAYER
   Every animation here is self-running or one-shot. Nothing is scrubbed by
   the scroll position: each instrument powers on, performs, and settles.
   ========================================================================== */
(() => {
  "use strict"

  const $ = (s, r = document) => r.querySelector(s)
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s))
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v)
  const lerp = (a, b, t) => a + (b - a) * t
  const mq = (q) => window.matchMedia(q)
  const reduced = mq("(prefers-reduced-motion: reduce)").matches
  const fine = mq("(hover: hover) and (pointer: fine)").matches
  const root = document.documentElement
  const TOOLSET = typeof TOOLS !== "undefined" ? TOOLS : []
  const CATSET = typeof CATS !== "undefined" ? CATS : ["all"]

  /* ---- dynamic style sheet (keyframes + rules that need to be late) ---- */
  const style = document.createElement("style")
  style.textContent = `
    @keyframes tickerRun { from { transform: translate3d(0,0,0) } to { transform: translate3d(-50%,0,0) } }
    .ticker__track { animation: tickerRun 52s linear infinite; will-change: transform; }
    .ticker__track.rev { animation-direction: reverse; }
    .anatomy__grid i.wave { opacity: .45; transform: scale(.88); }
    .anatomy__grid i.lit, .anatomy__grid i.is-lit { opacity: 1; transform: none; }
    .rv { position: relative; overflow: hidden; }
    .rv::after {
      content: ""; position: absolute; inset: 0; background: var(--signal);
      transform-origin: right; transform: scaleX(1); pointer-events: none;
    }
    .rv.is-in { animation: rvIn .64s cubic-bezier(.19,1,.22,1) both; }
    .rv.is-in::after { animation: rvSheet .64s cubic-bezier(.19,1,.22,1) both; }
    @keyframes rvSheet {
      0% { transform: scaleX(1); transform-origin: right; }
      49% { transform: scaleX(1); transform-origin: right; }
      50% { transform: scaleX(1); transform-origin: left; }
      100% { transform: scaleX(0); transform-origin: left; }
    }
    @keyframes rvIn { from { transform: translateX(-16px); } to { transform: none; } }
    .mode { position: relative; overflow: hidden; }
    .mode::after {
      content: ""; position: absolute; inset: 0; background: var(--signal);
      transform: translateY(101%); transition: transform .32s cubic-bezier(.19,1,.22,1);
    }
    .mode.is-on::after { transform: none; }
    .mode__dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
    .mode.is-on .mode__dot { background: var(--ink); }
    .boot__fill { transition: width .2s linear; }
  `
  document.head.appendChild(style)

  /* ======================================================================
     1. BOOT — core extraction
     ====================================================================== */
  const boot = () => {
    const el = document.createElement("div")
    el.className = "boot"
    el.innerHTML = `
      <div class="boot__box">
        <div class="boot__label"><span>extracting core sample</span><b id="boot-pct">0%</b></div>
        <div class="boot__bar"><span class="boot__fill" id="boot-fill"></span></div>
        <div class="boot__ticks">${Array.from({ length: 10 }, () => "<i></i>").join("")}</div>
      </div>`
    document.body.appendChild(el)
    const fill = $("#boot-fill", el)
    const pct = $("#boot-pct", el)
    let p = 0
    const tick = setInterval(() => {
      p = Math.min(100, p + 7 + Math.random() * 18)
      fill.style.width = p + "%"
      pct.textContent = Math.round(p) + "%"
      if (p >= 100) {
        clearInterval(tick)
        setTimeout(() => {
          el.classList.add("is-done")
          setTimeout(() => el.remove(), 700)
        }, 260)
      }
    }, 70)
  }

  /* ======================================================================
     2. CURSOR — the core sampler
     ====================================================================== */
  const cursor = () => {
    const host = $(".cursor")
    if (!host) return
    host.innerHTML = `
      <span class="cursor__cross cursor__cross--x"></span>
      <span class="cursor__cross cursor__cross--y"></span>
      <span class="cursor__aperture"></span>
      <span class="cursor__read mono"><b class="cursor__idx">00</b> <span class="cursor__depth">0010 m</span></span>
      <span class="cursor__tag mono"></span>`
    const ap = $(".cursor__aperture", host)
    const cx = $(".cursor__cross--x", host)
    const cy = $(".cursor__cross--y", host)
    const idx = $(".cursor__idx", host)
    const dep = $(".cursor__depth", host)
    const read = $(".cursor__read", host)
    const tag = $(".cursor__tag", host)
    const trail = []
    for (let i = 0; i < 5; i++) {
      const t = document.createElement("span")
      t.className = "cursor__trail"
      host.appendChild(t)
      trail.push(t)
    }
    // The native pointer is only hidden once a real mouse has actually been
    // seen. A touch-first laptop, a remote session or any browser that
    // reports a coarse pointer must keep its own cursor — and if the mouse
    // never arrives, the user must never be left with no cursor at all.
    let live = false
    const wake = () => {
      if (live) return
      live = true
      root.classList.add("has-cursor")
      host.classList.add("on")
    }
    let tx = innerWidth / 2
    let ty = innerHeight / 2
    const set = (x, y) => {
      root.style.setProperty("--mx", x + "px")
      root.style.setProperty("--my", y + "px")
      cx.style.transform = `translate3d(${x}px,0,0)`
      cy.style.transform = `translate3d(0,${y}px,0)`
      ap.style.transform = `translate3d(${x}px,${y}px,0) translate(-50%,-50%)`
      tag.style.transform = `translate3d(${x + 18}px,${y - 4}px,0)`
      read.style.transform = `translate3d(${x + 26}px,${y + 22}px,0)`
      const r = Math.round(x * 0.42).toString().padStart(4, "0")
      const d = Math.round(y * 0.42).toString().padStart(4, "0")
      dep.textContent = r + " / " + d + " mm"
    }
    set(tx, ty)
    addEventListener(
      "pointermove",
      (e) => {
        if (e.pointerType === "touch") return
        wake()
        tx = e.clientX
        ty = e.clientY
        set(tx, ty)
        trail.forEach((t, i) => {
          t.style.transform = `translate3d(${tx}px,${ty}px,0)`
          t.style.opacity = String(0.5 - i * 0.1)
          t.style.transitionDelay = i * 0.05 + "s"
        })
      },
      { passive: true },
    )
    addEventListener("pointerdown", () => host.classList.add("is-press"))
    addEventListener("pointerup", () => host.classList.remove("is-press"))
    const labelFor = (el) => {
      if (!el) return ""
      const t = el.closest("[data-cursor], .tool, .cmd, .btn, .win, .terminal, .station, .chip, a")
      if (!t) return ""
      if (t.hasAttribute("data-cursor")) return t.getAttribute("data-cursor")
      if (t.classList.contains("tool")) return "tool"
      if (t.classList.contains("cmd")) return "copy"
      if (t.classList.contains("btn")) return "go"
      if (t.classList.contains("win")) return "sample"
      if (t.classList.contains("terminal")) return "shell"
      if (t.classList.contains("station")) return "hop"
      if (t.classList.contains("chip")) return "filter"
      return (t.textContent || "").trim().slice(0, 18)
    }
    addEventListener(
      "pointerover",
      (e) => {
        const l = labelFor(e.target)
        if (l) {
          tag.textContent = l
          tag.classList.add("on")
        } else tag.classList.remove("on")
      },
      { passive: true },
    )
    window.__cursorIndex = (n) => {
      idx.textContent = String(n).padStart(2, "0")
    }
  }

  /* ======================================================================
     3. STATUS STRIP — the live readout
     ====================================================================== */
  const strip = () => {
    /* The bottom status bar was removed: a permanent chrome strip fought the
       page and the new halftone footer ends the document on its own. The one
       thing it was still good for — telling the magnet cursor's HUD which
       chapter is on screen — stays. */
    const sections = $$("section[id]")
    const tick = () => {
      const hit = sections.find((s) => {
        const r = s.getBoundingClientRect()
        return r.top <= innerHeight * 0.42 && r.bottom > innerHeight * 0.42
      })
      if (hit) {
        const n = sections.indexOf(hit)
        if (window.__cursorIndex) window.__cursorIndex(n)
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }

  /* ======================================================================
     4. TICKER — 52 tools, scrolling
     ====================================================================== */
  const ticker = () => {
    const track = $("#ticker")
    if (!track) return
    const one = TOOLSET.map((t) => `<span class="ticker__item">school_${t[0]}</span>`).join("")
    track.innerHTML = one + one
    if (reduced) return
    let last = scrollY
    let dir = 1
    addEventListener(
      "scroll",
      () => {
        const d = scrollY - last
        last = scrollY
        if (Math.abs(d) > 4) {
          dir = d > 0 ? 1 : -1
          track.classList.toggle("rev", dir < 0)
        }
      },
      { passive: true },
    )
  }

  /* ======================================================================
     5. CORE SAMPLE CANVAS
     ====================================================================== */
  const core = () => {
    const cv = $("#core")
    if (!cv) return
    const c = cv.getContext("2d")
    const dpr = Math.min(2, devicePixelRatio || 1)
    const W = 420
    const H = 760
    cv.width = W * dpr
    cv.height = H * dpr
    c.scale(dpr, dpr)
    const layers = []
    let seed = 7
    const rnd = () => {
      seed = (seed * 16807) % 2147483647
      return seed / 2147483647
    }
    for (let i = 0; i < 11; i++) {
      const top = (i / 11) * H
      const h = H / 11 + rnd() * 16
      layers.push({ top, h, tone: 0.06 + rnd() * 0.1, grain: 40 + Math.floor(rnd() * 90) })
    }
    const yEl = $("#core-y")
    const kEl = $("#core-k")
    const draw = () => {
      const p = clamp(scrollY / (innerHeight * 1.1), 0, 1)
      c.clearRect(0, 0, W, H)
      c.fillStyle = "#0d0d0f"
      c.fillRect(0, 0, W, H)
      layers.forEach((L, i) => {
        c.fillStyle = `rgba(239,234,224,${L.tone})`
        c.fillRect(0, L.top, W, L.h)
        c.strokeStyle = "rgba(239,234,224,.16)"
        c.lineWidth = 1
        c.beginPath()
        c.moveTo(0, L.top + L.h)
        c.lineTo(W, L.top + L.h)
        c.stroke()
        c.fillStyle = "rgba(239,234,224,.1)"
        for (let g = 0; g < L.grain; g++) {
          const gx = rnd() * W
          const gy = L.top + rnd() * L.h
          c.fillRect(gx, gy, 1.6, 1)
        }
      })
      /* focus band follows the probe */
      const fy = p * H
      c.fillStyle = "rgba(255,61,0,.14)"
      c.fillRect(0, fy - 34, W, 68)
      c.strokeStyle = "rgba(255,61,0,.9)"
      c.lineWidth = 1
      c.beginPath()
      c.moveTo(0, fy)
      c.lineTo(W, fy)
      c.stroke()
      /* ruler */
      c.fillStyle = "rgba(239,234,224,.35)"
      for (let i = 0; i <= 20; i++) {
        const ry = (i / 20) * H
        const long = i % 5 === 0
        c.fillRect(0, ry, long ? 16 : 8, 1)
      }
      if (yEl) yEl.textContent = "depth " + (p * 240).toFixed(2) + " m"
      if (kEl) kEl.textContent = "strata " + String(Math.min(11, Math.floor(p * 11) + 1)).padStart(2, "0")
    }
    let raf = 0
    addEventListener(
      "scroll",
      () => {
        if (raf) return
        raf = requestAnimationFrame(() => {
          raf = 0
          draw()
        })
      },
      { passive: true },
    )
    draw()
  }

  /* ======================================================================
     6. RAIL + DEPTH METER
     ====================================================================== */
  const rail = () => {
    const links = $$("[data-rail]")
    const depth = $("#depth")
    const sections = links.map((a) => $(`#${a.getAttribute("data-rail")}`)).filter(Boolean)
    const tick = () => {
      const probe = innerHeight * 0.4
      let active = 0
      sections.forEach((s, i) => {
        const r = s.getBoundingClientRect()
        if (r.top <= probe) active = i
      })
      links.forEach((a, i) => a.classList.toggle("is-active", i === active))
      if (depth) depth.textContent = String(Math.round(clamp(scrollY / (document.body.scrollHeight - innerHeight), 0, 1) * 240)).padStart(4, "0")
    }
    let raf = 0
    addEventListener(
      "scroll",
      () => {
        if (raf) return
        raf = requestAnimationFrame(() => {
          raf = 0
          tick()
        })
      },
      { passive: true },
    )
    tick()
  }

  /* ======================================================================
     7. FORGETTING — a self-playing replay
     ====================================================================== */
  const SESSION = [
    "user  explain the retry policy again",
    "agent  got it, backoff is 3 tries then dead letter",
    "user  no, 5 tries, and the queue is per-tenant",
    "agent  understood: 5 tries, per-tenant queue",
    "agent  patching core/queue.py",
    "test   ok 44 passed, 1 skipped",
    "agent  that skip is the flaky one we discussed",
    "user  yes — it only fails on the sandbox runner",
    "agent  noted, will skip it on sandbox",
    "user  thanks, that is the whole policy",
    "agent  summary: backoff 5, per-tenant, skip sandbox",
    "user  perfect",
  ]
  const forget = () => {
    return; // the compression stage (compress.js) owns this section now
    const list = $("#ctx-lines")
    const fill = $("#ctx-fill")
    const cut = $("#ctx-cut")
    const label = $("#ctx-label")
    const stamp = $("#stamp")
    const bar = $("#beats-bar")
    const beats = $$(".beat")
    const host = $("#forgetting")
    if (!host || !list) return
    list.innerHTML = SESSION.map((l) => `<li class="mono">${l}</li>`).join("")
    const lines = $$("li", list)
    const total = 8192
    let run = 0
    const cycle = () => {
      if (run++ > 0) {
        lines.forEach((l) => l.classList.remove("typed", "is-cut"))
        stamp.classList.remove("land")
        if (fill) fill.style.width = "100%"
        if (cut) cut.style.width = "0%"
        if (label) label.textContent = total.toLocaleString() + " tok"
        beats.forEach((b) => b.classList.remove("is-on"))
        bar && (bar.style.width = "0%")
      }
      let i = 0
      const type = () => {
        if (i < lines.length) {
          lines[i].classList.add("typed")
          if (label) label.textContent = Math.round(total * (1 - (i + 1) / (lines.length + 4))).toLocaleString() + " tok"
          i++
          setTimeout(type, 52)
        } else {
          /* drain */
          if (fill) fill.style.width = "22%"
          if (cut) cut.style.width = "78%"
          if (label) label.textContent = "1,806 tok"
          lines.slice(3).forEach((l) => l.classList.add("is-cut"))
          setTimeout(() => {
            stamp && stamp.classList.add("land")
            let b = 0
            const step = () => {
              if (b >= beats.length) {
                setTimeout(cycle, 3200)
                return
              }
              beats.forEach((x) => x.classList.remove("is-on"))
              beats[b].classList.add("is-on")
              if (bar) bar.style.width = (((b + 1) / beats.length) * 100).toFixed(1) + "%"
              b++
              setTimeout(step, 900)
            }
            step()
          }, 700)
        }
      }
      setTimeout(type, 420)
    }
    /* start when it is on screen, then loop forever */
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (es) => {
          if (es[0].isIntersecting) {
            cycle()
            io.disconnect()
          }
        },
        { threshold: 0.25 },
      )
      io.observe(host)
    } else cycle()
  }

  /* ======================================================================
     8. PIPELINE — a signal that runs on its own
     ====================================================================== */
  const pipe = () => {
    const svg = $(".pipe__svg")
    const path = $("#pipe-path")
    const stations = $$(".station")
    if (!svg || !path) return
    const pulse = document.createElementNS("http://www.w3.org/2000/svg", "path")
    pulse.setAttribute("d", path.getAttribute("d"))
    pulse.setAttribute("class", "pipe__pulse")
    path.parentNode.appendChild(pulse)
    let i = 0
    setInterval(() => {
      stations.forEach((s, k) => s.classList.toggle("is-live", k === i))
      i = (i + 1) % Math.max(1, stations.length)
    }, 900)
  }

  /* ======================================================================
     9. ANATOMY — wave fill + auto scan
     ====================================================================== */
  const BLOCKS = [
    { step: 0, label: "b1", from: 0, to: 4 },
    { step: 1, label: "b3", from: 8, to: 12 },
    { step: 2, label: "b7", from: 24, to: 31 },
  ]
  const anatomy = () => {
    const grid = $("#cellgrid")
    if (!grid) return
    const cols = 8
    const rows = 6
    grid.innerHTML = Array.from({ length: cols * rows }, () => "<i></i>").join("")
    const cells = $$("i", grid)
    const scan = document.createElement("span")
    scan.className = "anatomy__scan"
    grid.appendChild(scan)
    const steps = $$(".step")
    let b = 0
    const apply = (n) => {
      const blk = BLOCKS[n]
      cells.forEach((c, i) => {
        const inBlock = i >= blk.from && i < blk.to
        c.classList.toggle("lit", inBlock)
        c.classList.toggle("is-lit", inBlock)
        c.classList.toggle("scan", inBlock && i === blk.to - 1)
      })
      steps.forEach((s, k) => s.classList.toggle("is-on", k === blk.step))
    }
    const wave = () => {
      cells.forEach((c, i) => {
        setTimeout(() => {
          c.classList.add("wave")
          if (i % 7 === 0) c.classList.add("lit")
        }, i * 14)
      })
      setTimeout(() => {
        scan.classList.add("run")
        apply(0)
        setInterval(() => {
          b = (b + 1) % BLOCKS.length
          apply(b)
        }, 4600)
      }, 900)
    }
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (es) => {
          if (es[0].isIntersecting) {
            wave()
            io.disconnect()
          }
        },
        { threshold: 0.2 },
      )
      io.observe(grid)
    } else wave()
  }

  /* ======================================================================
     10. TOOLS — rail with spotlight, tilt, shimmer, drag
     ====================================================================== */
  const tools = () => {
    return // the tools section is the glass-folder island now (assets/glass-folders.js)
    const track = $("#tooltrack")
    const count = $("#toolcount")
    const chips = $$("#filters .chip")
    if (!track) return
    const render = (cat) => {
      const list = TOOLSET.filter((t) => cat === "all" || t[2] === cat)
      track.innerHTML = list
        .map((t, i) => {
          const n = String(i + 1).padStart(2, "0")
          return `<article class="tool" data-cat="${t[2]}" data-i="${n}">
            <div class="tool__top"><span class="tool__i mono">${n}</span><span class="tool__cat mono">${t[2]}</span></div>
            <h3>school_${t[0]}</h3>
            <p>${t[1]}</p>
            <span class="tool__bar"><i></i></span>
          </article>`
        })
        .join("")
      const cards = $$(".tool", track)
      cards.forEach((c, i) => {
        setTimeout(() => c.classList.add("is-in"), 40 + i * 22)
        c.addEventListener("pointermove", (e) => {
          const r = c.getBoundingClientRect()
          c.style.setProperty("--mx", e.clientX - r.left + "px")
          c.style.setProperty("--my", e.clientY - r.top + "px")
        })
        c.addEventListener("pointerenter", () => {
          c.style.transition = "transform .35s cubic-bezier(.19,1,.22,1), border-color .2s"
          c.style.transform = "perspective(700px) rotateX(6deg) translateY(-6px)"
        })
        c.addEventListener("pointerleave", () => {
          c.style.transform = ""
        })
      })
      if (count) count.textContent = `${list.length} / ${TOOLSET.length} shown`
      chips.forEach((ch) => {
        const n = ch.getAttribute("data-cat")
        const badge = $(".chip__n", ch)
        if (badge) badge.textContent = n === "all" ? TOOLSET.length : TOOLSET.filter((t) => t[2] === n).length
      })
    }
    chips.forEach((ch) =>
      ch.addEventListener("click", () => {
        chips.forEach((c) => c.classList.remove("is-on"))
        ch.classList.add("is-on")
        render(ch.getAttribute("data-cat"))
      }),
    )
    render("all")

    /* drag the rail with momentum */
    const vp = $("#toolviewport")
    if (!vp) return
    let down = false
    let sx = 0
    let sl = 0
    let vel = 0
    let lastX = 0
    vp.classList.add("is-drag")
    const step = () => {
      if (Math.abs(vel) > 0.4) {
        sl += vel
        vel *= 0.94
        track.style.transform = `translate3d(${sl}px,0,0)`
        requestAnimationFrame(step)
      } else vel = 0
    }
    vp.addEventListener("pointerdown", (e) => {
      down = true
      sx = e.clientX
      lastX = sl
      vel = 0
      vp.setPointerCapture(e.pointerId)
    })
    vp.addEventListener("pointermove", (e) => {
      if (!down) return
      const dx = e.clientX - sx
      sl = lastX + dx
      vel = dx * 0.35
      track.style.transform = `translate3d(${sl}px,0,0)`
    })
    const up = () => {
      if (!down) return
      down = false
      requestAnimationFrame(step)
    }
    vp.addEventListener("pointerup", up)
    vp.addEventListener("pointercancel", up)
    vp.addEventListener(
      "wheel",
      (e) => {
        if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
          sl -= e.deltaX
          track.style.transform = `translate3d(${sl}px,0,0)`
          e.preventDefault()
        }
      },
      { passive: false },
    )
  }

  /* ======================================================================
     11. FIGURES — odometer counters
     ====================================================================== */
  const figures = () => {
    return // the figures are the measurements island now (assets/measurements.js)
    const nums = $$(".figure__n")
    const fmt = (n) => n.toLocaleString("en-US")
    nums.forEach((el) => {
      const to = Number(el.getAttribute("data-to") || 0)
      const suffix = el.getAttribute("data-suffix") || ""
      // The odometer ghost slides up to stand in for the counted value, so it
      // needs the *formatted* number. Kept in its own attribute because
      // data-to has to stay numeric for the counter to re-read it.
      el.setAttribute("data-final", fmt(to) + suffix)
      const fig = el.closest(".figure")
      const paint = (v) => {
        el.textContent = fmt(v) + suffix
      }
      paint(0)
      let started = false
      const run = () => {
        if (started) return
        started = true
        const dur = 1900
        const t0 = performance.now()
        const step = () => {
          const t = clamp((performance.now() - t0) / dur, 0, 1)
          const eased = 1 - Math.pow(1 - t, 3)
          paint(Math.round(to * eased))
          if (t < 1) requestAnimationFrame(step)
          else {
            paint(to)
            fig && fig.classList.add("is-set")
          }
        }
        requestAnimationFrame(step)
        setTimeout(() => {
          paint(to)
          fig && fig.classList.add("is-set")
        }, dur + 200)
      }
      if ("IntersectionObserver" in window) {
        const io = new IntersectionObserver(
          (es) => {
            if (es[0].isIntersecting) {
              run()
              io.disconnect()
            }
          },
          { threshold: 0.4 },
        )
        io.observe(fig || el)
      } else run()
    })
  }

  /* ======================================================================
     12. INSTALL — tabs, live terminal, copy
     ====================================================================== */
  const CMDS = {
    pip: "pip install school",
    npm: "npm install -g @dksh/school",
    brew: "brew install school",
    choco: "choco install school",
    win: "School-Setup.exe",
    src: "git clone https://github.com/dex34132-web/A-School-For-AI.git && cd lerev && pip install -e .",
  }
  const install = () => {
    const body = $("#term-body")
    const title = $("#term-title")
    const term = $(".terminal")
    const copy = $("#copy-install")
    const tabs = $$(".tab")
    if (!body) return
    const type = (text) => {
      if (!term) return
      term.classList.add("is-typing")
      term.classList.remove("is-ok")
      body.innerHTML = `<code><span class="t-prompt">$ </span><span id="typed"></span><span class="terminal__caret"></span></code>`
      const out = $("#typed")
      let i = 0
      const step = () => {
        if (i >= text.length) {
          term.classList.remove("is-typing")
          term.classList.add("is-ok")
          return
        }
        out.textContent = text.slice(0, ++i)
        setTimeout(step, 14)
      }
      step()
    }
    tabs.forEach((t) =>
      t.addEventListener("click", () => {
        tabs.forEach((x) => x.classList.remove("is-on"))
        t.classList.add("is-on")
        const k = t.getAttribute("data-tab")
        if (title) title.textContent = k
        type(CMDS[k] || k)
      }),
    )
    if (copy) {
      copy.addEventListener("click", async () => {
        const k = ($(".tab.is-on") || {}).getAttribute ? $(".tab.is-on").getAttribute("data-tab") : "pip"
        const text = CMDS[k] || "pip install school"
        try {
          await navigator.clipboard.writeText(text)
        } catch {
          const ta = document.createElement("textarea")
          ta.value = text
          document.body.appendChild(ta)
          ta.select()
          document.execCommand("copy")
          ta.remove()
        }
        const old = copy.textContent
        copy.textContent = "copied"
        setTimeout(() => (copy.textContent = old), 1200)
      })
    }
    /* the hero command chip copies too */
    $$(".cmd[data-copy]").forEach((c) =>
      c.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(c.getAttribute("data-copy"))
        } catch {
          /* clipboard blocked — the hint still shows */
        }
        const hint = $(".cmd__hint", c)
        if (hint) {
          const old = hint.textContent
          hint.textContent = "copied"
          setTimeout(() => (hint.textContent = old), 1200)
        }
      }),
    )
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (es) => {
          if (es[0].isIntersecting) {
            type(CMDS.pip)
            io.disconnect()
          }
        },
        { threshold: 0.35 },
      )
      io.observe($(".install") || body)
    } else type(CMDS.pip)
  }

  /* ======================================================================
     13. REVEALS + SCRAMBLE
     ====================================================================== */
  const reveal = () => {
    const targets = [
      ...$$(".chapter__head > *"),
      ...$$(".figure"),
      ...$$(".station"),
      ...$$(".step"),
      ...$$(".installer"),
      ...$$(".footer__grid > *"),
    ]
    targets.forEach((el) => el.classList.add("rv"))
    const show = (el) => el.classList.add("is-in")
    if (!("IntersectionObserver" in window)) {
      targets.forEach(show)
      return
    }
    const io = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (!e.isIntersecting) return
          const sibs = e.target.parentElement ? $$(":scope > *", e.target.parentElement) : []
          const k = Math.max(0, sibs.indexOf(e.target))
          e.target.style.setProperty("--rd", Math.min(0.3, k * 0.05) + "s")
          show(e.target)
          io.unobserve(e.target)
        })
      },
      { threshold: 0.25, rootMargin: "0px 0px -8% 0px" },
    )
    targets.forEach((el) => io.observe(el))
  }
  const heroChars = () => {
    const title = $(".hero__title")
    if (!title) return
    const walk = (node) => {
      for (const child of [...node.childNodes]) {
        if (child.nodeType === 3) {
          // whitespace between the title lines must stay whitespace: turning
          // it into an inline span would create a phantom line box and blow
          // the line spacing apart.
          if (!child.textContent.trim()) continue
          const frag = document.createDocumentFragment()
          for (const ch of child.textContent) {
            const s = document.createElement("i")
            s.className = "ch"
            s.textContent = ch === " " ? "\u00a0" : ch
            frag.appendChild(s)
          }
          node.replaceChild(frag, child)
        } else if (child.nodeType === 1) {
          walk(child)
        }
      }
    }
    walk(title)
    title.querySelectorAll(".ch").forEach((c, i) => {
      c.style.animationDelay = 0.1 + i * 0.02 + "s"
    })
    setTimeout(() => title.classList.add("go"), 40)
  }

  const scramble = () => {
    const els = $$(".chapter__title")
    const GLYPHS = "▓▒░#%&@*+=/\\|<>0123456789ABCDEFGHJKLMNPRSTUVWXYZ"
    els.forEach((el) => {
      const text = el.textContent
      el.innerHTML = ""
      const spans = []
      // Each word gets its own inline-block wrapper so a line can only ever
      // break at a space, never inside a word. The characters are <i> inside
      // a .scr wrapper, which is what the stylesheet targets.
      for (const part of text.split(/(\s+)/)) {
        if (!part) continue
        if (/^\s+$/.test(part)) {
          el.appendChild(document.createTextNode(" "))
          continue
        }
        const word = document.createElement("span")
        word.className = "scr"
        for (const ch of part) {
          const s = document.createElement("i")
          s.dataset.ch = ch
          s.textContent = GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
          word.appendChild(s)
          spans.push(s)
        }
        el.appendChild(word)
      }
      let i = 0
      const tick = () => {
        if (i >= spans.length) {
          spans.forEach((s) => s.classList.add("on"))
          // the accent is a signal, not a colour scheme: hand the title back
          // to the section's own ink once the scramble has resolved
          el.classList.add("done")
          return
        }
        const s = spans[i]
        s.textContent = s.dataset.ch
        s.classList.add("on")
        i++
        setTimeout(tick, 74)
      }
      setTimeout(tick, 220)
    })
  }

  /* ======================================================================
     14. BLUEPRINT MODE
     ====================================================================== */
  const mode = () => {
    const btn = $(".mode")
    if (!btn) return
    btn.addEventListener("click", () => {
      const on = root.getAttribute("data-mode") === "blueprint"
      if (on) root.removeAttribute("data-mode")
      else root.setAttribute("data-mode", "blueprint")
      btn.classList.toggle("is-on", !on)
      btn.setAttribute("aria-pressed", String(!on))
      const lab = $(".mode__label", btn)
      if (lab) lab.textContent = on ? "blueprint" : "archive"
    })
  }

  /* ======================================================================
     15. MAGNETIC CONTROLS
     ====================================================================== */
  const magnet = () => {
    if (!fine || reduced) return
    $$(".btn, .cmd").forEach((el) => {
      el.classList.add("magnet")
      el.addEventListener("pointermove", (e) => {
        const r = el.getBoundingClientRect()
        const dx = (e.clientX - (r.left + r.width / 2)) * 0.22
        const dy = (e.clientY - (r.top + r.height / 2)) * 0.3
        el.style.transform = `translate3d(${dx}px,${dy}px,0)`
      })
      el.addEventListener("pointerleave", () => {
        el.style.transform = ""
      })
    })
  }

  /* ======================================================================
     16. FIGURE MARKS + STAMP
     ====================================================================== */
  const marks = () => {
    const COUNT = {
      stage: "poster",
      forgetting: "12 lines",
      pipeline: "5 hops",
      anatomy: "48 cells",
      tools: "52 tools",
      numbers: "4 figures",
      install: "6 methods",
    }
    $$("section.chapter").forEach((s) => {
      ;["tl", "tr", "bl", "br"].forEach((p) => {
        const m = document.createElement("span")
        m.className = "figmark figmark--" + p
        s.appendChild(m)
      })
      const num = $(".chapter__num", s)
      const title = $(".chapter__title", s)
      if (num && title) {
        const t = title.textContent.trim().toLowerCase()
        num.setAttribute("data-fig", "FIG. " + num.textContent.trim() + " — " + t.slice(0, 28).toUpperCase())
      }
    })
    $$("[data-rail]").forEach((a) => {
      const id = a.getAttribute("data-rail")
      if (COUNT[id]) a.setAttribute("data-count", COUNT[id])
    })
    const cmd = $(".cmd")
    if (cmd) cmd.classList.remove("conic")
  }

  /* ======================================================================
     17. TOPBAR STATE + CLOCK
     ====================================================================== */
  const chrome = () => {
    const bar = $(".topbar")
    const clock = $("#clock")
    const sync = () => bar && bar.classList.toggle("is-stuck", scrollY > 40)
    addEventListener("scroll", sync, { passive: true })
    sync()
    if (clock) {
      const t = () => {
        clock.textContent = new Date().toLocaleTimeString("en-GB", { hour12: false })
      }
      t()
      setInterval(t, 1000)
    }
  }

  /* ---- go ---- */
  const fatal = (name, err) => {
    const msg = name + ": " + ((err && err.message) || String(err))
    console.error("[schoolio] " + msg, err)
    try {
      let b = document.getElementById("__fatal")
      if (!b) { b = document.createElement("div"); b.id = "__fatal"; document.body.appendChild(b) }
      b.textContent = (b.textContent ? b.textContent + "  |  " : "") + msg
      b.setAttribute("style", "position:fixed;left:0;right:0;top:0;z-index:2147483647;background:#b3261e;color:#fff;font:12px/1.5 ui-monospace,monospace;padding:8px 12px")
    } catch {}
  }
  /* ======================================================================
     20. RESCUE - a content watchdog
     Some environments never deliver IntersectionObserver callbacks (a
     background tab, an aggressively throttled renderer, or an element that
     was already on screen at load). Anything that waits on an observer would
     then stay empty or stay covered by its reveal sheet, which reads as a
     completely broken page. This watchdog resolves whatever is in view.
     ====================================================================== */
  const rescue = () => {
    const settle = () => {
      $$(".figure__n").forEach((el) => {
        const fig = el.closest(".figure")
        if (!fig || fig.classList.contains("is-set")) return
        const r = fig.getBoundingClientRect()
        if (r.top >= innerHeight || r.bottom <= 0) return
        const to = Number(el.getAttribute("data-to") || 0)
        const suffix = el.getAttribute("data-suffix") || ""
        el.textContent = to.toLocaleString("en-US") + suffix
        fig.classList.add("is-set")
      })
      $$(".rv").forEach((sheet) => {
        if (sheet.classList.contains("is-in")) return
        const r = sheet.getBoundingClientRect()
        if (r.top >= innerHeight || r.bottom <= 0) return
        sheet.classList.add("is-in")
      })
      // A renderer that never advances animations (a throttled background
      // tab, a headless capture) freezes every element in its FROM state:
      // blurred, offset, or collapsed to zero width. The reveal rules are
      // written to be safe on their own, but anything that animates in from
      // a hidden state can still strand. If an element has been sitting in
      // that state for more than a couple of seconds, cut the animation and
      // let it settle where it is.
      const stuck = new WeakMap()
      $$(".v2-rv, .rv > .rv__i, .v2-divider__rule, .hero__title .ch").forEach((el) => {
        const st = getComputedStyle(el)
        const hidden =
          (st.filter && st.filter !== "none" && st.filter.indexOf("blur(") !== -1) ||
          st.transform === "matrix(0, 0, 0, 1, 0, 0)" ||
          (st.opacity !== "" && parseFloat(st.opacity) < 0.05)
        if (!hidden) {
          stuck.delete(el)
          return
        }
        const first = stuck.get(el)
        if (first === undefined) {
          stuck.set(el, Date.now())
          return
        }
        if (Date.now() - first < 2500) return
        stuck.delete(el)
        el.style.animation = "none"
        el.style.filter = "none"
        el.style.opacity = "1"
        el.style.transform = "none"
      })
    }
    settle()
    setInterval(settle, 800)
  }

  const start = () => {
    const safe = (name, fn) => { try { fn() } catch (err) { fatal(name, err) } }
    safe("strip", strip)
    safe("ticker", ticker)
    safe("rail", rail)
    safe("figures", figures)
    safe("reveal", reveal)
    safe("heroChars", heroChars)
    safe("scramble", scramble)
    safe("magnet", magnet)
    safe("marks", marks)
    safe("rescue", rescue)
    safe("chrome", chrome)
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start)
  else start()
})()

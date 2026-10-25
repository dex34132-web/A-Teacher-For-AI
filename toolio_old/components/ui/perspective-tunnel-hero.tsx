"use client"

/**
 * Perspective Tunnel Hero — School edition.
 *
 * Adapted from the 21st.dev `perspective-tunnel-hero` component:
 *   - the 9 image panels are replaced by TERMINAL COMMAND panels (product content)
 *   - the headline is "AI Agents, But Better"
 *   - the palette is the site's LIGHT theme (paper #f4f1ea, ink #17171c, signal #ff3d00)
 *
 * Drop-in for a shadcn + Tailwind + TypeScript app:
 *   npx shadcn@latest add "https://21st.dev/r/<author>/perspective-tunnel-hero"
 * or copy this file to components/ui/perspective-tunnel-hero.tsx
 * (components/ui is the shadcn default path).
 */

import * as React from "react"
import { cn } from "@/lib/utils"

type Card = {
  tag: string
  /** Local picture in /public/assets. Falls back to a real photograph. */
  img: string
  /** Seed for the fallback photograph. */
  seed: string
  out: string
}

/** The ecosystem, in pictures. Drop your own into /public/assets/card-N.jpg. */
const CARDS: Card[] = [
  { tag: "opencode", img: "/assets/card-1.jpg", seed: "school-opencode", out: "the open source AI coding agent" },
  { tag: "hermes", img: "/assets/card-2.jpg", seed: "school-hermes", out: "hermes agent" },
  { tag: "openclaw", img: "/assets/card-3.jpg", seed: "school-openclaw", out: "openclaw" },
  { tag: "code", img: "/assets/card-4.jpg", seed: "school-code", out: "an agent writing code" },
  { tag: "editor", img: "/assets/card-5.jpg", seed: "school-editor", out: "the workbench" },
  { tag: "script", img: "/assets/card-6.jpg", seed: "school-script", out: "the run" },
  { tag: "terminal", img: "/assets/card-7.jpg", seed: "school-terminal", out: "the bridge" },
  { tag: "ops", img: "/assets/card-8.jpg", seed: "school-ops", out: "ops on a loop" },
  { tag: "agents", img: "/assets/card-9.jpg", seed: "school-agents", out: "agents that learn" },
]

const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

export function PerspectiveTunnelHero({
  className,
  headline = "AI Agents,",
  headlineAccent = "But Better",
  headlineTail = "and they learn.",
}: {
  className?: string
  headline?: string
  headlineAccent?: string
  headlineTail?: string
}) {
  const hostRef = React.useRef<HTMLDivElement>(null)
  const cardRefs = React.useRef<(HTMLDivElement | null)[]>([])
  const targetRef = React.useRef(0.16) // panels are already waiting in the dark
  const pRef = React.useRef(0.16)
  const pointerRef = React.useRef({ x: 0, y: 0 })
  const easedPointer = React.useRef({ x: 0, y: 0 })
  const rafRef = React.useRef<number | null>(null)

  React.useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const host = hostRef.current
    if (!host) return

    const onPointer = (e: PointerEvent) => {
      if (e.pointerType === "touch") return
      const r = host.getBoundingClientRect()
      pointerRef.current = {
        x: (e.clientX - r.left) / r.width - 0.5,
        y: (e.clientY - r.top) / r.height - 0.5,
      }
    }

    const onWheel = (e: WheelEvent) => {
      const t = targetRef.current
      // Never trap the page: release the wheel at either end of the tunnel.
      if (e.deltaY > 0 && t >= 0.999) return
      if (e.deltaY < 0 && t <= 0.001) return
      if (t <= 0 || t >= 1) return
      e.preventDefault()
      targetRef.current = clamp(t + e.deltaY * 0.00085, 0, 1)
    }

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) targetRef.current = 1
        }
      },
      { threshold: 0 },
    )
    io.observe(host)

    const tick = () => {
      const dt = 1 / 60
      pRef.current += (targetRef.current - pRef.current) * (1 - Math.exp(-dt * 5.5))
      const p = pRef.current

      if (!reduced) {
        easedPointer.current.x +=
          (pointerRef.current.x - easedPointer.current.x) * (1 - Math.exp(-dt * 4.5))
        easedPointer.current.y +=
          (pointerRef.current.y - easedPointer.current.y) * (1 - Math.exp(-dt * 4.5))
      }

      const n = CARDS.length
      const small = window.innerWidth < 768

      cardRefs.current.forEach((el, i) => {
        if (!el) return
        // golden-angle placement
        const angle = (i * 137.5 * Math.PI) / 180
        const rx = 0.26 + (i % 3) * 0.085
        const ry = 0.24 + (i % 2) * 0.095
        const rot = (i % 2 ? 1 : -1) * (3 + (i % 5) * 2)

        const start = (i / n) * 0.45
        const local = clamp((p - start) / 0.55, 0, 1)
        const z = small ? lerp(-1200, 350, local) : lerp(-1700, 500, local)

        const ox = Math.cos(angle) * rx * 900 + easedPointer.current.x * 90
        const oy = Math.sin(angle) * ry * 620 + easedPointer.current.y * 60

        const opacity =
          local <= 0.22 ? lerp(0.16, 1, local / 0.22) : local > 0.8 ? 1 - (local - 0.8) / 0.2 : 1
        const copy = local <= 0.5 ? lerp(0.72, 1, local / 0.5) : lerp(1, 1.28, (local - 0.5) / 0.5)
        const copyOpacity = local <= 0.3 ? lerp(0.3, 1, local / 0.3) : local > 0.75 ? 1 - (local - 0.75) / 0.25 : 1

        el.style.opacity = String(opacity)
        el.style.zIndex = String(10 + Math.round(local * 20))
        el.style.transform = `translate3d(calc(-50% + ${ox}px), calc(-50% + ${oy}px), ${z}px) rotateZ(${rot}deg)`
        el.style.setProperty("--copy-scale", String(copy))
        el.style.setProperty("--copy-opacity", String(copyOpacity))
      })

      rafRef.current = requestAnimationFrame(tick)
    }

    if (reduced) {
      targetRef.current = 1
      pRef.current = 1
    }
    rafRef.current = requestAnimationFrame(tick)

    host.addEventListener("pointermove", onPointer)
    host.addEventListener("wheel", onWheel, { passive: false })
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      io.disconnect()
      host.removeEventListener("pointermove", onPointer)
      host.removeEventListener("wheel", onWheel)
    }
  }, [])

  return (
    <section
      ref={hostRef}
      className={cn(
        "relative flex min-h-[100svh] items-center justify-center overflow-hidden",
        "bg-[radial-gradient(120%_90%_at_50%_10%,#fbf9f4_0%,#f4f1ea_45%,#e9e4d8_100%)]",
        className,
      )}
    >
      {/* dot field */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage: "radial-gradient(rgba(23,23,28,.18) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          maskImage: "radial-gradient(ellipse at 50% 45%, #000 0%, transparent 72%)",
          WebkitMaskImage: "radial-gradient(ellipse at 50% 45%, #000 0%, transparent 72%)",
          transform: "translateZ(-420px)",
        }}
      />
      {/* orange glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 h-[52vmin] w-[52vmin] -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(255,61,0,.16) 0%, transparent 68%)" }}
      />
      {/* rings */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 h-[46vmin] w-[46vmin] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#17171c]/12"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 h-[76vmin] w-[76vmin] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-[#17171c]/10"
      />

      {/* the tunnel */}
      <div className="absolute inset-0 [perspective:1200px] [transform-style:preserve-3d]">
        {CARDS.map((c, i) => (
          <div
            key={c.tag}
            ref={(el) => {
              cardRefs.current[i] = el
            }}
            className="absolute left-1/2 top-1/2 will-change-transform"
            style={{ width: "clamp(186px, 16.4vw, 262px)", aspectRatio: "4 / 5" }}
          >
            <div className="group relative h-full w-full overflow-hidden rounded-[10px] border border-[#17171c]/10 bg-white/95 shadow-[0_26px_60px_-34px_rgba(23,23,28,.45)] transition-colors duration-300 hover:border-[#ff3d00]/60 hover:shadow-[0_26px_70px_-30px_rgba(255,61,0,.55)]">
              <img
                src={c.img}
                alt={c.tag}
                className="absolute inset-0 h-full w-full object-cover"
                onError={(e) => {
                  const el = e.currentTarget
                  if (el.dataset.fallback) return
                  el.dataset.fallback = "1"
                  el.src = `https://picsum.photos/seed/${c.seed}/900/1125`
                }}
                style={{
                  transform: "scale(var(--copy-scale, 1))",
                  opacity: "var(--copy-opacity, 1)",
                }}
              />
              <div className="absolute inset-x-0 bottom-0 flex items-center gap-2 bg-gradient-to-t from-black/70 to-transparent px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-white/80">
                <span className="size-1.5 shrink-0 rounded-full bg-[#ff3d00]" />
                <span className="font-semibold text-white">{c.tag}</span>
                <span className="ml-auto truncate opacity-70">{c.out}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* copy */}
      <style>{`
        @font-face { font-family: "Pusab"; src: url("/fonts/Pusab-Regular.ttf") format("truetype"); font-display: swap; }
        @font-face { font-family: "BlowBrush"; src: url("/fonts/BlowBrush-Regular.ttf") format("truetype"); font-display: swap; }
        .pth-title { font-family: "Pusab", ui-monospace, monospace; text-transform: lowercase; }
        .pth-accent { font-family: "BlowBrush", cursive; font-size: 1.24em; transform: rotate(-3.5deg); display: inline-block; }
      `}</style>
      <div className="relative z-10 mx-auto flex max-w-[940px] flex-col items-center px-6 text-center">
        <p className="mb-5 font-mono text-[11px] uppercase tracking-[0.3em] text-[#6a6459]">
          [ the learning layer for every agent ]
        </p>
        <h1 className="pth-title text-[clamp(54px,8.4vw,126px)] leading-[0.98] tracking-[-0.02em] text-[#17171c]">
          {headline}
          <br />
          <em className="pth-accent not-italic text-[#ff3d00]">{headlineAccent}</em>
          <br />
          {headlineTail}
        </h1>
        <p className="mt-7 max-w-[58ch] text-[17px] leading-relaxed text-[#4a453c]">
          School is the learning layer behind an agent — coding, research, ops, support, anything
          that runs on a loop. It learns what worked, what broke, and what your project already
          decided, then hands it back before the next task starts.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <a
            href="#install"
            className="group inline-flex items-center gap-2 border border-[#17171c]/20 bg-white px-5 py-3 font-mono text-[13px] text-[#17171c] transition-colors hover:border-[#ff3d00]"
          >
            <span className="text-[#ff3d00]">$</span> pip install school
          </a>
          <a
            href="https://github.com/dex34132-web/lerev"
            className="inline-flex items-center gap-2 border border-[#17171c]/20 px-5 py-3 font-mono text-[13px] text-[#17171c] transition-colors hover:border-[#ff3d00]"
          >
            GitHub ↗
          </a>
        </div>
      </div>
    </section>
  )
}

export default PerspectiveTunnelHero

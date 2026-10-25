# School — Perspective Tunnel Hero (setup)

Two deliverables live in this folder:

| File | What it is |
|---|---|
| `components/ui/perspective-tunnel-hero.tsx` | The adapted component. Terminal-command panels instead of images, light theme, "AI Agents, But Better" headline. |
| `components/demo.tsx` | A mount that renders the hero. |
| `tunnel.css` + `tunnel.js` | The same behaviour, ported to the **static** `schoolio/` site (no build step, no dependencies). The live site uses these. |

---

## A. If your app already has shadcn + Tailwind + TypeScript

This repo does **not** (there is no `package.json`, `tailwind.config.*`, `tsconfig.json` or `components.json` anywhere in it) — so use one of the two routes below.

### A1. Copy the file in

```bash
mkdir -p components/ui
cp components/ui/perspective-tunnel-hero.tsx your-app/components/ui/
```

`components/ui` is the shadcn default path, so the file drops straight into the registry convention.

The component imports one helper:

```ts
import { cn } from "@/lib/utils"
```

shadcn generates that file for you — if you don't have it yet:

```bash
npx shadcn@latest init
```

If you would rather not depend on `cn`, replace the import with a local helper:

```ts
const cn = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(" ")
```

### A2. Install the upstream component and adapt it

```bash
npx shadcn@latest add "https://21st.dev/r/<author>/perspective-tunnel-hero"
```

Full directory: <https://21st.dev/llms.txt> · 21st MCP: <https://21st.dev/mcp>

Then swap the 9 image panels for the terminal cards in `CARDS` and set the headline to
`AI Agents,` / `But Better` / `with memory.`

### A3. Tailwind bits the component expects

- a serif display face — `font-[family-name:var(--font-instrument-serif,Georgia,serif)]` falls back to Georgia, so it works with no font installed;
- arbitrary values are used for the palette (`#f4f1ea` paper, `#17171c` ink, `#ff3d00` signal, `#0e8a80` teal) so the component renders correctly even before you wire a theme;
- if your Tailwind version is v3, run `npx @tailwindcss/upgrade` — the component uses the v4 arbitrary-value syntax for the mask/gradient layers.

---

## B. If your app has no Tailwind/React at all

The **static** site in this folder needs none of it. `tunnel.css` + `tunnel.js` implement the same
perspective tunnel with plain DOM:

```html
<link rel="stylesheet" href="tunnel.css" />
<script src="tunnel.js" defer></script>
```

`index.html` links them already. The behaviour matches the React version:

- 9 terminal panels arranged on a golden angle (137.5° apart);
- the tunnel advances as you scroll **inside the hero** — the wheel is released at both ends so the
  page is never trapped;
- pointer position parallaxes the panels;
- `prefers-reduced-motion` disables the parallax and the wheel hijack.

---

## C. Verify

```bash
python -m http.server 8123 --directory .
# open http://localhost:8123/
```

The hero should show the headline over a field of terminal panels; scroll to push the panels forward.

---

## Halftone wordmark footer

`components/ui/halftone-wordmark-footer.tsx` is a second component in the same
family: a footer whose wordmark is set enormous, cropped by the bottom edge and
printed as a field of halftone dots. Each dot is sized by how much of the letter
covers its cell, so the type keeps its edges at any scale. Move across it and
the dots part around the pointer on springs, warming in colour as they are
pushed off their place; click and a shock ring runs through the word. A fixed
tile of print grain is laid over every frame.

The wordmark on the School site is `school`, and the palette is the site's
own: ink `#0b0b0d`, bone `#efeae0`, signal `#ff3d00`.

### A. You already have a shadcn app (recommended)

```bash
npx shadcn@latest add "https://21st.dev/r/<author>/halftone-wordmark-footer"
```

…or just copy the file in — it depends on nothing but React:

```bash
cp schoolio/components/ui/halftone-wordmark-footer.tsx components/ui/
```

**Why `components/ui` matters.** It is where shadcn puts components on
purpose: `components.json` points `aliases.components` at that path, so
`npx shadcn@latest add …` writes there and every
`import { X } from "@/components/ui/x"` resolves. A component dropped
anywhere else is invisible to the registry — the CLI will not update it, and
the `@/` alias will not match it — so it quietly rots out of sync with the
rest of the design system.

It is a `"use client"` component (it measures a canvas and listens to the
pointer), so it must be rendered from a client boundary.
`components/demo.tsx` is the ready-made page for it.

### B. Starting from scratch

```bash
npx create-next-app@latest schoolio --ts --tailwind --eslint --app
cd schoolio
npx shadcn@latest init
```

### C. The static route (what the live site runs)

`halftone.css` + `halftone.js` are the framework-free port of the same
component — no build step, no dependencies:

```html
<link rel="stylesheet" href="halftone.css" />
<script src="halftone.js"></script>
<footer class="hwf-root" id="hwf">
  <canvas id="hwf-canvas"></canvas>
  <span class="hwf-sr">school</span>
  <div class="hwf-top"> … brand + link columns … </div>
  <div class="hwf-rule"> … hairline, clock, back-to-top … </div>
</footer>
```

One rule matters on the live site: `light.css` forces every `footer` to paper
with `!important`, so the halftone footer re-pins its own surface with
`footer.hwf-root { background: #0b0b0d !important; color: #efeae0 !important; }`.
It is the one dark band on the page and it closes the document in ink.

### Verify

```bash
python -m http.server 8123 --directory schoolio
```

## Fonts — Pusab + BlowBrush (self-hosted)

Neither face is on Google Fonts, so both are shipped in the repo and declared in
`fonts.css`:

| File | Family | Use |
| --- | --- | --- |
| `fonts/Pusab-Regular.ttf` | Pusab (Flat-it) | hero display type, footer wordmark |
| `fonts/BlowBrush-Regular.ttf` | BlowBrush (Raz) | the hand-written accent |

```css
@font-face { font-family: "Pusab"; src: url("/fonts/Pusab-Regular.ttf") format("truetype"); font-display: swap; }
@font-face { font-family: "BlowBrush"; src: url("/fonts/BlowBrush-Regular.ttf") format("truetype"); font-display: swap; }
```

In a Next.js app put the files in `public/fonts/` and load them with
`next/font/local`:

```ts
import localFont from "next/font/local"

export const pusab = localFont({
  src: "../../public/fonts/Pusab-Regular.ttf",
  variable: "--font-pusab",
  display: "swap",
})
```

Pusab has no bold — never ask for `font-weight: 800`, the synthetic bold smears
the pixels. The footer wordmark is set at `400` for exactly that reason.

## Card pictures

The nine tunnel cards look for `assets/card-N.jpg` and fall back to a real
photograph if the file is missing, so the intro never shows a broken image.

| Slot | Picture |
| --- | --- |
| card-1.jpg | opencode logo |
| card-2.jpg | hermes-agent logo |
| card-3.jpg | openclaw logo |
| card-4.jpg | neon code editor |
| card-5.jpg | VS Code window |
| card-6.jpg | jQuery authenticateUser script |
| card-7.jpg | terminal |
| card-8.jpg | ops dashboard |
| card-9.jpg | agents at work |

Drop your own files in `schoolio/assets/` (static) or `public/assets/`
(Next.js) with those names. See `assets/README.txt`.
## Liquid glass (components/ui/liquid-glass.tsx)

### Does this repo support shadcn + Tailwind + TypeScript?

**No � not yet.** The live site is a hand-written static build with no bundler:

| Expected | Present? |
| --- | --- |
| `package.json` | no |
| `components.json` (shadcn config) | no |
| `tsconfig.json` | no |
| `tailwind.config.*` | no |
| `next.config.*` / `vite.config.*` | no |

What *is* here is the `schoolio/components/` folder, which already follows the
shadcn convention (`components/ui/<name>.tsx`, one component per file, `demo.tsx`
next to it) plus a `cn`-free style so the files compile standalone.

### The default path for components is `/components/ui` � keep it there

shadcn does not ship a library; it copies source into *your* repo and edits it
in place. The destination comes from `components.json`:

```json
{ "aliases": { "components": "@/components", "ui": "@/components/ui", "utils": "@/lib/utils" } }
```

`ui` is the sub-folder for *unstyled primitives* (buttons, panels, glass, etc.)
while `components` holds composed, app-specific pieces. If you move a component
out of `components/ui`:

- `npx shadcn@latest add <url>` will write a **second copy** into the canonical
  folder, and your moved copy silently stops receiving upstream updates;
- the `@/components/ui/...` import used by every demo and by the registry
  metadata no longer resolves, so `npx shadcn@latest view <name>` shows nothing;
- the file drifts out of sync with the registry version and rots.

`components/ui` is also where the 21st.dev install path expects it:
`npx shadcn@latest add "https://21st.dev/r/<author>/liquid-glass"`.

### Setting the project up (the React route)

```bash
# 1. Next.js + TypeScript (or swap for: npm create vite@latest -- --template react-ts)
npx create-next-app@latest schoolio-app --ts --tailwind --eslint --app --src-dir=false
cd schoolio-app

# 2. shadcn init � writes components.json, lib/utils.ts, the cn() helper
npx shadcn@latest init

# 3. the component
npx shadcn@latest add "https://21st.dev/r/<author>/liquid-glass"
#    �or just copy  schoolio/components/ui/liquid-glass.tsx  ->  <app>/components/ui/liquid-glass.tsx
```

Requirements the component has:

| Dependency | Why | Install |
| --- | --- | --- |
| `react`, `react-dom` | `"use client"` component | comes with the app |
| `clsx` + `tailwind-merge` | the `cn()` helper shadcn's `lib/utils.ts` uses | `npx shadcn@latest add` installs it |
| `lucide-react` | optional � use for SVG logos instead of `<img>` | `npm i lucide-react` |
| Tailwind CSS v4 | the utility classes | `npm i tailwindcss @tailwindcss/postcss` |

Path alias � `tsconfig.json` must map `@/*` or every import above fails:

```json
{ "compilerOptions": { "paths": { "@/*": ["./*"] } } }
```

### What changed versus the snippet you pasted

| Snippet | Shipped | Why |
| --- | --- | --- |
| `rounded-inherit` | `rounded-[inherit]` | `rounded-inherit` is not a Tailwind class; the browser drops it and the glass layers get square corners |
| `rounded-4xl` | `rounded-[2rem]` | `rounded-4xl` only exists in Tailwind v4; the arbitrary value works on v3 and v4 |
| `<GlassFilter />` rendered by hand | mounted automatically | `filter: url(#glass-distortion)` on an element whose filter id is missing makes the browser **drop the element**. A `useEffect` injects the SVG once into `<body>`, so `GlassDock` works standalone |
| 21st.dev CDN dock icons | Unsplash photographs | zero binary assets in the repo; swap for `assets/card-N.png` locally if you prefer |
| � | `GlassEffect` / `GlassDock` / `GlassButton` / `GlassFilter` exported | so they can be composed instead of only the demo |

No context provider, store or hook is required � the component is purely
presentational. The only state it owns is the mounted SVG filter.

### Where it belongs in the app

* **Hero** � the glass dock under the headline, icons linking to the agents that
  plug into School (opencode, hermes, openclaw, VS Code).
* **Install** � a glass CTA above the terminal: *"Ask School what it already
  remembers"*.
* **Tool rail** � the dock is the natural drag target for a horizontal rail.

### The static route (what the live site uses)

The live `schoolio/` site has no bundler, so the component was ported by hand:

* `schoolio/glass.css` � the layer stack (blur -> tint -> lit edge -> content)
  plus the liquid border-radius morph and the dock/CTA styles.
* `schoolio/glass.js` � builds the dock from `assets/card-N.png` with a remote
  fallback, and mounts it into `#glassDock`.
* `index.html` links `glass.css` and `glass.js`; the mount point is
  `<div class="glass-dock" id="glassDock" data-magnet></div>` inside the hero,
  right after the stat block.

Both files are the vanilla twin of `components/ui/liquid-glass.tsx` � keep them
in sync when you change the React version.
## Glass folder cards — the tools section

The tools section is a real React island: six glass folders, one per area of
the product, each holding the tools of that area as files. The component is
`components/ui/glass-folder-cards.tsx`; the site mounts the built bundle.

### The shadcn / Tailwind / TypeScript route

This repository is **not** a React app. It is a hand-written static site
(`index.html` + plain CSS + vanilla JS), so there is no `package.json`,
`tsconfig.json`, `tailwind.config` or `components.json` yet. If you want
the shadcn route, set it up once at the root:

```bash
npx shadcn@latest init            # writes components.json + tailwind + tsconfig
npx shadcn@latest add "https://21st.dev/r/<author>/glass-folder-cards"
```

`npx shadcn@latest add` writes the component into the folder named by
`components.json` → `aliases.components`, which is `components/ui` by
default. **That is the default path, and it matters:** the alias is what
`@/components/ui/...` resolves to. A component that lives anywhere else
gets a *second* copy the next time somebody runs `shadcn add`, its import
breaks, and the two copies rot out of sync. Keep everything in
`components/ui`.

Deps for the component as written: `react` and `react-dom` only. The
artwork is generated on a canvas, so there are no image assets to fetch and
no icon library to install (the chat glyph is inline SVG). If you swap the
art for stock photography, drop the files in `public/assets/` and pass
`image` instead of `art`.

### The static route (what the live site uses)

The site has no build step, so the island is compiled once and committed:

```bash
npm i react react-dom esbuild
node schoolio/islands/build.mjs        # -> schoolio/assets/glass-folders.js
```

The bundle is self-contained (React is inside it) and `index.html` loads it
with `<script src="assets/glass-folders.js?v=N">`. Bump `?v=N` whenever
you rebuild, or the browser keeps the old bundle.

### The props this site uses

| Prop | Value here | Why |
| --- | --- | --- |
| `label` | the area (`memory`, `plan`, …) | the folder's name |
| `meta` | `"10 tools"` | the count, on the glass |
| `files` | `{ name: "school_remember", art: "ember" }` | name only — no descriptions |
| `action` | `"suggest"` | the key is a chat bubble, not a plus |
| `suggestions` | the area's other tools | the dropdown's items |
| `hint` | the line under the folder | as asked, under every folder |
| `tone` | `"dark"` | the site is dark |
| `focusFile` | the chosen suggestion | brings that file to the front |

### Extra props added for this site

- `action: "suggest"` — the key renders a chat bubble and the menu holds
  only the suggestions (no automatic Open/Close row).
- `suggestions?: FolderMenuItem[]` — the dropdown's contents.
- `hint?: string` — a line printed under the folder; the root grows to make
  room for it.
- `focusFile?: string` — change the value to bring that file to the front
  of the stack (the dropdown uses it to surface a tool).


## Terminal + Contribution Skyline — the measurements section

Two more 21st.dev components live in `components/ui`:

| File | What it is | Used by |
|---|---|---|
| `components/ui/terminal.tsx` | a terminal window whose lines type themselves out (`TypingAnimation`) and fade in (`AnimatedSpan`), optionally sequenced one line after the next | the proof terminal in section 06 |
| `components/ui/contribution-skyline.tsx` | a GitHub-style heat map that folds into an isometric skyline; one camera swings between the two views | section 06 — "Measured, not asserted" |

### The default path for components is `/components/ui` — and here is why it matters

shadcn does not ship components; it copies them into **your** repo, and the
folder it copies into is `components.json → aliases.components`, which
defaults to `@/components/ui`.

If a component lives anywhere else:

1. `npx shadcn@latest add …` will not find it, so the next person adds a
   **second copy** under `components/ui`.
2. Your import (`@/components/ui/terminal`) and the new copy drift apart.
3. The registry has no idea your version exists, so it never updates it, and
   it quietly rots.

So `/components/ui` is not a convention, it is the contract between the
registry and your tree. Keep every shadcn component there.

### Route A — a real shadcn + Tailwind + TypeScript project

This repository has **no** React/Tailwind/TypeScript toolchain (there is no
`package.json`, `tsconfig.json`, `tailwind.config.*` or `components.json`).
The live site is hand-written static HTML, so the components are delivered two
ways: the TSX for a real project, and a compiled island for this site.

To stand up a real project beside it:

```bash
npx create-next-app@latest schoolio-app --typescript --tailwind --eslint --app --src-dir
cd schoolio-app
npx shadcn@latest init
npx shadcn@latest add "https://21st.dev/r/<author>/terminal"
npx shadcn@latest add "https://21st.dev/r/<author>/contribution-skyline"
npm i motion
```

- **Tailwind v4** needs no `tailwind.config.js`; the theme lives in CSS via
  `@theme`. If you are on v3, run `npx @tailwindcss/upgrade`.
- **TypeScript**: `components/ui/*.tsx` expect `"jsx": "react-jsx"` and
  `"moduleResolution": "bundler"`.
- **The `cn` helper** — `lib/utils.ts` here is dependency-free so the static
  build works. In a real shadcn project replace it with the canonical:

  ```ts
  import { type ClassValue } from "clsx"
  import { twMerge } from "tailwind-merge"
  export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
  }
  ```

- **Deps**: `react`, `react-dom`, `motion` (the `motion/react` entry point
  — not the deprecated `framer-motion`). No image assets are needed: the
  skyline is drawn on a canvas and the folder art is generated.

### Route B — the static route (what this site actually runs)

The site has no bundler, so the islands are compiled by esbuild and committed:

```bash
npm i react react-dom motion esbuild
node schoolio/islands/build.mjs
```

That writes:

- `assets/glass-folders.js` — the tools section
- `assets/measurements.js` — the measurements section

Both are self-contained (React, ReactDOM and motion are bundled in; no CDN).
The build maps the shadcn alias `@` to the site root, so `@/lib/utils`
resolves exactly as it would in a real project.

**Tailwind without Tailwind.** The components use Tailwind utility classes.
On this static site those utilities are hand-compiled into
`assets/tw.css` — a subset covering only the classes these two components
use, with the same class names, so the TSX stays byte-for-byte what the
registry gave you. In a real Tailwind project you delete `tw.css` and let
Tailwind compile the same utilities.

### Two props added for this site

Both are additive and optional; the component behaves exactly as shipped
without them.

| Prop | Type | Default | What it does here |
|---|---|---|---|
| `spanDays` | `number` | `364` | The grid spans a year. School's grid spans the project's own 3 months (`92`), so the heat map is the project and not a mostly-empty ribbon. |
| `statLabels` | `[string,string,string,string]` | `["1 year total","Busiest day","Longest streak","Current streak"]` | Relabels the four stat blocks — here "Lines written", "Busiest day", "Longest streak", "Current streak". |

### What the data actually is

The skyline is **not** a GitHub contribution graph. Every cell is one real
working day of this repository, read from `git log --numstat`: 16 working
days, 91 commits, 244,013 lines written and rewritten. The 3D view is the
same grid seen from the corner — one camera swinging between the two views,
not two charts.

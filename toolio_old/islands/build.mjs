/**
 * Builds the React islands into single self-contained scripts.
 *
 * The site is plain static HTML — there is no bundler in the repo — so each
 * React island is compiled here and committed under `assets/`:
 *
 *   assets/glass-folders.js   the tools section (six glass folders)
 *   assets/measurements.js    the "Measured, not asserted" section
 *   assets/holo.js            the holo card in the poster stage
 *
 * React, ReactDOM and motion are bundled in, so an island has no runtime
 * dependency and no CDN.
 *
 *   npm i react react-dom motion esbuild     # once, anywhere
 *   node islands/build.mjs
 *
 * `nodePaths` points at wherever the dependencies were installed; change
 * `BUILD` (or set SCHOOL_ISLAND_MODULES) if you keep them somewhere else.
 *
 * The `@/…` alias is the shadcn import alias — it points at the site root, so
 * `@/lib/utils` resolves to `lib/utils.ts` exactly as it would in a real
 * shadcn project.
 */
import { createRequire } from "node:module"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const SITE = resolve(HERE, "..")
const BUILD = process.env.SCHOOL_ISLAND_MODULES || "C:/Users/dex34/AppData/Local/Temp/opencode/islandbuild"

// esbuild lives next to react/motion in BUILD, not next to this script, so it
// is required from there rather than resolved from the site's folder.
const require = createRequire(BUILD.replace(/\\/g, "/") + "/package.json")
const esbuild = require("esbuild")

const ISLANDS = [
  { entry: "glass-folders.tsx", out: "glass-folders.js" },
  { entry: "measurements.tsx", out: "measurements.js" },
  { entry: "holo.tsx", out: "holo.js" },
]

for (const island of ISLANDS) {
  await esbuild.build({
    entryPoints: [resolve(HERE, island.entry)],
    bundle: true,
    outfile: resolve(SITE, "assets", island.out),
    format: "iife",
    jsx: "automatic",
    loader: { ".tsx": "tsx", ".ts": "ts" },
    define: { "process.env.NODE_ENV": '"production"' },
    nodePaths: [BUILD + "/node_modules"],
    alias: { "@": SITE },
    minify: true,
    logLevel: "info",
  })
  console.log("BUILT -> assets/" + island.out)
}

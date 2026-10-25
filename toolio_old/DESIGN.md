# School site — design rules (researched, not guessed)

Sources read 2026-10-22: Dokle design awards (Signal-A SOTD 18 Oct 2026, OFFF Forum SOTD 16 Oct 2026), Abduzeedo (Monolith Studio), CSS Nectar gallery (Index_Georgia), Exhibita editorial awards, Website Design Awards editorial category, and three anti-slop references (Ad-Astra "Slop Taxonomy" 39 tells, Nutlope/hallmark anti-patterns, funboy322/avoid-ai-design 67-tell catalogue, mblode/agent-skills aesthetic-direction, booplex, rottoways).

## The non-negotiables (what actually wins awards)

1. **One typeface, one job each.** Signal-A: a condensed serif for names/claims, a grotesk for emphasis + dense paragraphs, a **mono for everything you'd call data** — menu, clock, scope, project numbers. OFFF: a flared serif carries the mood, a tight black grotesk carries the facts. "None of them wanders into another's job." → **ours: Pusab = display claims only · Archivo = prose · IBM Plex Mono = every number, command, label.**
2. **One governing grid that the words are justified to.** Signal-A runs every word through one six-column grid; Index_Georgia is a strict 4-column Swiss experiment with a single font weight. → our sections must sit on a declared column grid, and the copy must align to it, not float.
3. **Almost no colour, no decoration, no illustration.** Signal-A: "almost no colour, almost no decoration, and no illustration. The site is black type on white with photographs from the work." → **one accent (orange #ff3d00), hairline rules, empty space left alone.**
4. **Tables and spec sheets, not card grids.** OFFF's media room is "the plainest page on the site and one of the best": a two-column table (Object / Dates & Location / Image) pushed into the right half, the empty left half doing a sidebar's job. → a metric is a **row in a table with its provenance**, not a card with a big number.
5. **Labels are black slabs the width of the word and no wider** (OFFF page titles; the user's own request for the folder file heads). "It works like a label on a box, and it's the only colour change on the page."
6. **Big display type that reads as mass, not text** (Monolith: "the display type at a weight where individual strokes read as mass, not text"). Headlines set enormous so the words are the picture (50% of editorial winners).
7. **Asymmetry.** "Left-align everything except the hero. Asymmetry is what makes a page feel composed instead of templated."

## The AI-slop tells we must not commit (the catalogue)

- **First-order slop:** purple→blue gradient hero · Inter for everything · 3 equal feature cards with icons above headings · card-in-card nesting · gradient-filled headline (`background-clip:text`) · **thick coloured border on one card edge (4–6px "side-stripe")** · full-viewport centred hero · rounded-2xl + shadow-lg + backdrop-blur everywhere · buzzword headlines ("Elevate your workflow", "seamless, powerful, stunning") · everything in threes · a row of big round numbers with no provenance · "trusted by 10,000+ teams" · light-grey-on-white text you squint at.
- **Second-order slop (the dangerous one — this is what we had):** cream + terracotta · **near-black with one vermilion/acid-green signal** · broadsheet hairlines · tracked all-caps eyebrows · `A · B · C` meta strings. "Ask it to look less AI and you get the *next* same page." → **we were near-black + one orange + hairlines + tracked caps. Break the pattern deliberately somewhere: one section inverts to paper.**
- "Glass, glow, blur, grids and noise used as atmosphere without a content or brand role" — three or more on one surface reads as assembled, not designed. Our glass lens + wave + grid overlay + radial gradients must each have a *content* reason, or go.
- "Invented proof, and product framing that shows something the product does not do" — absolute, regardless of count. Every number on this site must be checkable and every capability must be real.
- Fixes that are explicitly endorsed: hairline border all around instead of a side stripe · a small accent square beside the heading · one containment layer (not card-in-card) · "a row of big round numbers" → replace with a table · delete the gradient-filled headline → solid ink · left-align · let the section be the height of its content.

## Our system (derived, not copied)

- **Palette:** one ground per act. The stage is `#161616`; the lower half is `#0d0d0f`; **the measurements act is paper** (`#f4f1ea` ground, `#17171c` ink) — an intentional break of the dark pattern. One accent throughout: `#ff3d00`. Ice `#a9d8d1` and teal `#7fd0c6` only inside data/art, never as decoration.
- **Type roles:** Pusab (display) → section titles and the wordmark only. Archivo (grotesk) → prose, ledes, descriptions. IBM Plex Mono → every number, every command, every label, every table cell. Nothing crosses over.
- **Structure:** a declared 6-column grid per act; headlines justified to it; tables with hairline rules; a slab label the width of its word; empty space left alone; no card-in-card; no side stripes; no big numbers without a provenance column.
- **Copy:** declarative and specific. Name the file, the command, the count, the date. No adjective where a number works. No "seamless / powerful / stunning / elevate".
- **Motion:** one idea per section, self-running, and it must end where it started. Nothing accumulates without bound.

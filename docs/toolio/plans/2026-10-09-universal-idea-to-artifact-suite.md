# Universal Ideaâ†’Artifact Suite â€” Design & Build Plan

**Date:** 2026-10-09
**Status:** PLAN (pending name/scope confirmation before build)
**Scope:** Every kind of AI agent â€” coding, writing, research, planning, business,
education, creative, ops, life. NOT coding-only.
**Standing constraint:** Apple-grade presentation. Fail-open everywhere. Kill switches.
Visual output via the existing 101-renderer system.

---

## 1. Vision

Turn a fuzzy user intent into a complete, actionable set of artifacts by asking
**accurate adaptive questions** and letting the user answer with **pick-one-or-custom**
choices. The engine then synthesizes everything the user named â€” a design spec,
commands, directives, formations, and more â€” each with its **own distinct name**
(not everything under one "specer" banner).

This is toolio' brainstorming + writing-plans + SDD workflow, rebuilt **10x
better** and made **universal**, with the industry's best techniques folded in and
sharpened.

### What "10x better" means concretely
| toolio does | Our 10x |
|---|---|
| Free-form "ask clarifying questions one at a time" | **Structured adaptive interview** with scored dimensions, branching follow-ups, pick-or-custom answers |
| 3 fixed paths (spike/bounded/architectural) | **Continuous scope meter** + auto-decomposition into sub-projects |
| Prose design doc | **5 distinct generated artifacts** (spec + commands + directives + formations + acceptance), each named |
| Brainstorming = "propose 2-3 approaches" | **Multi-technique divergent engine** (first-principles, SCAMPER, role-storm, analogical, inversion) + convergent scoring + clustering |
| Text-only output | **Visual output** via Toolio's 101 renderers (radar, mind-map, kanban, decision-matrix, timelineâ€¦) |
| Coding-centric ("write failing test", "git commit") | **Universal domain templates** (coding, writing, research, business, education, creative, ops, life) |
| Manual spec self-review | **Automated lint** (placeholders, contradictions, ambiguity, scope) with scores |

---

## 2. Research findings (what we're improving on)

### 2.1 toolio (local source read)
- **brainstorming/SKILL.md** â€” HARD-GATE approval, 3 paths (spike/bounded/architectural),
  one-question-at-a-time, 2-3 approaches, sectioned design, spec self-review, visual
  companion (browser), red-flags table. Strengths: discipline, approval gate, YAGNI.
  Weaknesses: free-form questioning (not systematic), text-only, coding-centric, one output.
- **writing-plans/SKILL.md** â€” bite-sized 2-5 min tasks, TDD, exact file paths, task
  right-sizing, plan header for agentic workers. Good skeleton to inherit.
- **14 skills total** â€” brainstorming, writing-plans, TDD, systematic-debugging,
  verification-before-completion, dispatching-parallel-agents, code-review, git-worktrees,
  writing-skills, etc. We will 10x and rename the valuable ones.

### 2.2 Internet best practice (fetched 2026)
- **SDD:** spec is the primary artifact; must be readable by agents + people; the right
  amount of detail; keep specâ†”impl in sync; acceptance criteria with concrete I/O.
- **Spec anatomy (Augment/SSOJet):** mandatory sections = goal, non-goals, acceptance
  criteria (Given/When/Then), constraints, open questions, success metrics.
- **Brainstorming:** divergentâ†’convergent; GPS framework (3-level: goalâ†’approachâ†’detail);
  first-principles; SCAMPER; role-storming; impact-vs-effort scoring; clustering.
- **Requirements interview:** discovery questions (purpose, users, constraints, success,
  risks, edge cases); acceptance criteria as the definition of "done".

---

## 3. The Suite â€” distinct names (NOT all "specer")

The interview engine produces **five named artifacts**, and the ideation + skill
abilities each carry their own name. Recommended codename theme: **craft of turning
intent into reality**. (Alternative names in Â§8 â€” user picks before build.)

### 3.1 The core engine + its 5 named outputs

| # | Name | Role | Output |
|---|---|---|---|
| **A** | **`clarion`** | The **Discovery Interview** engine (the "specer" core). Asks accurate, adaptive, scored questions; user answers pick-one-or-custom; branches follow-ups. | A structured **Requirement Set** (intent, audience, scope, constraints, success, resources, risks, sequence, edge-cases) |
| **B** | **`blueprint`** | The **Design Spec** builder. | goals Â· non-goals Â· architecture Â· components Â· data-flow Â· acceptance-criteria (Given/When/Then) Â· risks Â· decomposition Â· glossary Â· success-metrics |
| **C** | **`edict`** | **Commands & Directives** generator. | **Commands** = ordered executable actions/instructions. **Directives** = governing "always/never" rules that must hold throughout |
| **D** | **`weave`** | **Formations** builder. | The structure & sequencing: phases, roadmap, dependency graph, parallel lanes, milestones, critical-path |
| **E** | **`compass`** | **Acceptance & alignment**. | Testable acceptance checklist, success metrics, definition-of-done, verification steps |

> Flow: `clarion` (ask) â†’ user answers â†’ synthesizes `blueprint` + `edict` + `weave`
> + `compass` in one pass (or one-at-a-time). Each artifact is separately named,
> versioned, and rendered with visuals.

### 3.2 The brainstorming engine (10x toolio' brainstorming)

| Name | Role |
|---|---|
| **`prism`** | **Ideation engine** â€” splits intent into a spectrum of possibilities. Divergent (first-principles, SCAMPER, role-storm, analogical, inversion, random-association) â†’ convergent (impact/effort scoring, feasibility, novelty) â†’ clustered synthesis â†’ feeds `clarion`. |

### 3.3 The skill pack (10x the industry's best, renamed)

Each is a named skill, universal (not coding-only), with visual output:

| New name | 10x of | Universal twist |
|---|---|---|
| **`forge`** | test-driven-development | Test/verify-first for ANY deliverable (essays, plans, campaigns) |
| **`triage`** | systematic-debugging | Root-cause method for any failure (a bug, a lost customer, a bad grade) |
| **`chart`** | writing-plans | Roadmap/bite-sized-step writer for any project |
| **`gate`** | verification-before-completion | Definition-of-done checker with a visual checklist |
| **`relay`** | dispatching-parallel-agents | Fan-out work decomposition + merge, any agent |
| **`scrutinize`** | code-review (requesting/receiving) | Review & self-critique for any artifact |
| **`compass`** | (new) | Acceptance/alignment (from Â§3.1) |

---

## 4. Universal domain model (every agent, not just coding)

`clarion`/`blueprint`/etc. are **domain-aware**. A `domain` field selects the template
that shapes questions + artifact language. Built-in domains:

`coding` Â· `writing` Â· `research` Â· `business` Â· `planning` Â· `education` Â·
`creative` Â· `ops` Â· `data` Â· `life` Â· `general`

- **coding** acceptance: "unit tests pass", "Given/When/Then"
- **writing** acceptance: "tone matches brief", "word count", "audience satisfied"
- **research** acceptance: "sources cited", "question answered", "confidence stated"
- **business** acceptance: "stakeholder sign-off", "metric moved", "budget respected"
- **education** acceptance: "learner can demonstrate X", "rubric met"
- **creative** acceptance: "brief honored", "originality", "emotional impact"
- â€¦ each domain ships a question-bank + artifact template + acceptance style.

Unknown/other â†’ `general` domain (generic intent/goals/constraints/success).

---

## 5. The interview engine (`clarion`) in detail

### 5.1 Adaptive question model
Each **question** = `{ id, dimension, prompt, type, options[], allow_custom, followups }`
- `type`: `choice` (pick-one, one option = "customâ€¦"), `multi`, `scale`, `text`, `confirm`
- **pick-one-or-custom**: every choice question includes a `"(your own)â€¦"` free-text escape.
- **Adaptive branching**: an answer selects follow-up questions (e.g. choosing
  `audience=enterprise` surfaces compliance questions).
- **Scored dimensions**: each dimension has a confidence score; the engine keeps asking
  in the weakest dimension until confidence â‰¥ threshold (or user says enough).

### 5.2 Dimensions (universal)
`intent` Â· `audience` Â· `scope` Â· `constraints` Â· `success` Â· `resources` Â· `risks` Â·
`sequence` Â· `style` Â· `edge_cases` Â· `glossary` Â· `open_questions`

### 5.3 Interaction modes
- **Interview mode** â€” one question per turn, pick-or-custom (the default).
- **Batch mode** â€” dump a form of all questions; user fills; engine parses.
- **Auto mode** â€” engine infers answers from a description + repo/context, marks low-confidence items as open questions (for a fast path).
- **Import mode** â€” start from an existing doc/PRD/repo and interview only the gaps.

---

## 6. Output artifacts (what the user asked: "spec, commands, directives, formations, and everything")

1. **`blueprint`** â€” the design spec (Â§3.1 B). Markdown + visual (architecture tree, dashboard).
2. **`edict.commands`** â€” ordered, executable action list (each step: do-X, inputs, done-when).
3. **`edict.directives`** â€” governing rules ("always â€¦", "never â€¦", "when X, do Y").
4. **`weave.formations`** â€” phases, roadmap, dependency graph, parallel lanes, critical path (visual timeline / Gantt / kanban).
5. **`compass.acceptance`** â€” Given/When/Then + checklist + success metrics.
6. **Everything-else bundle** â€” glossary, open questions, risks register, decomposition
   into sub-projects, traceability matrix (requirement â†’ command â†’ acceptance).

All artifacts are stored as structured JSON (`.toolio/forge/<slug>/â€¦`) + rendered as
Markdown + Toolio visuals. Versioned; re-interviewable; exportable.

---

## 7. Technical architecture & wiring

```
core/forge/                      # new Python package (engine, universal)
  clarion.py      # interview engine (questions, branching, scoring)
  blueprint.py    # spec builder
  edict.py        # commands + directives
  weave.py        # formations / roadmap / sequencing
  compass.py      # acceptance / metrics
  prism.py        # brainstorming (divergent/convergent)
  domains/        # question-banks + templates per domain
  models.py       # dataclasses: Requirement, Question, Spec, Command, Directive, Formation
  render.py       # artifact â†’ Markdown + Toolio visuals (reuse visual_dispatch)
```

Wired across all three surfaces like every other Toolio tool:
- **Bridge** commands: `clarion`, `blueprint`, `edict`, `weave`, `compass`, `prism`
- **TS plugin** tools: `toolio_clarion`, `toolio_blueprint`, `toolio_edict`,
  `toolio_weave`, `toolio_compass`, `toolio_brainstorm` (+ dominance + guard + visuals)
- **MCP** tools: same 6
- **CLI**: `toolio clarion|blueprint|edict|weave|compass|brainstorm`
- **Skills**: `clarion`, `prism`, `forge`, `triage`, `chart`, `gate`, `relay`, `scrutinize`

Guard: every competitor (toolio brainstorming, writing-plans, spec tools) maps to
the matching Toolio tool via the existing 11-layer guard + duel-proof banner.

---

## 8. Naming â€” pick before build (names are important)

**Recommended set** (craft-of-creation theme, all distinct, none is "specer"):

`clarion` (interview) Â· `blueprint` (spec) Â· `edict` (commands/directives) Â·
`weave` (formations) Â· `compass` (acceptance) Â· `prism` (brainstorm) Â·
`forge`/`triage`/`chart`/`gate`/`relay`/`scrutinize` (skill pack)

**Alternative themes (if you prefer a different flavor):**

- **Navigation theme:** `compass`/`chart`/`beacon`/`horizon`/`anchor`/`compass-rose`
- **Architecture theme:** `blueprint`/`scaffold`/`keystone`/`arch`/`lintel`/`mortar`
- **Command theme:** `clarion`/`edict`/`mandate`/`decree`/`writ`/`canon`
- **One-word-neutral:** `ask`/`spec`/`plan`/`build`/`check`/`ideate`

Tool prefixes stay `toolio_*` for consistency with the existing surface; the **skill**
and **artifact** names carry the distinct flavor.

---

## 9. Build plan (phases)

**Phase 0 â€” confirm names & scope** (this step). Lock the naming theme + domain list.

**Phase 1 â€” core models + `clarion` interview engine**
- `models.py`, `clarion.py`, domain question-banks (all 11 domains)
- Interview modes (interview/batch/auto/import), branching, scoring
- Tests: question flow, pick-or-custom, branching, scoring, fail-open, kill switch

**Phase 2 â€” artifact builders**
- `blueprint.py`, `edict.py`, `weave.py`, `compass.py` (+ `render.py` to Markdown + visuals)
- Tests: each builder emits correct structure + visuals + acceptance criteria

**Phase 3 â€” `prism` brainstorming**
- divergent techniques, convergent scoring, clustering, visual output
- Tests: multi-technique generation, scoring, cluster, feed-to-clarion

**Phase 4 â€” skill pack + universal templates**
- `forge`/`triage`/`chart`/`gate`/`relay`/`scrutinize` skills (SKILL.md each, 10x content)
- domain templates + acceptance styles

**Phase 5 â€” surface wiring + guard + visuals**
- bridge/TS/MCP/CLI for all 6 tools; dominance + 11-layer guard; visual footers
- `node --check`, ruff, tool-surface tests

**Phase 6 â€” competitive duels + hardening**
- duels vs toolio (brainstorming/writing-plans/SDD) + spec tools â€” Toolio must win
- adversarial fuzz (reuse `tests/stress/fuzz_harness.py`) on every tool/feature â‰¥2000Ã—
- full battery green

Each phase: TDD, Apple-grade visuals, fail-open, kill switch (`TOOLIO_FORGE=0`, etc.).

---

## 10. Success criteria
- 6 new tools across bridge/TS/MCP/CLI + 6+ named skills
- 11 domains supported (universal)
- 5 distinct named artifacts produced from one interview
- Beats toolio in a head-to-head duel (breadth, structure, visuals, universality)
- Full test battery green; ruff clean; `node --check` valid
- Every tool â‰¥2000 adversarial iterations without crashing

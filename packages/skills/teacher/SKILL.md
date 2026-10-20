---
name: teacher
description: Use when a task starts and you need the right School/Forge tool and skill from the whole suite — "what should I use here?", planning, precision, diagnosis, budgeted questions, or a verdict. One entry point that routes. Any domain — not only coding. Not a replacement for the skills themselves — load those for the method.
---

# Teacher — one entry point to the whole suite

The suite only pays off when the right tool and the right skill meet the task.
This skill is that meeting point: a map of the whole workshop, so nothing is
invisible and nothing is used for the wrong job. It is universal by contract —
software, writing, research, business, planning, creative, life.

## The map — intent → tool → skill

| The user wants… | Tool(s) | Skill |
|---|---|---|
| Ideas, options, a direction | `school_brainstorm` (CLI: `school prism` is the legacy alias) | `chart` (to plan the pick) |
| Requirements discovered | `school_clarion` | `chart` |
| A design spec | `school_blueprint` | `chart` |
| Ordered steps + always/never rules | `school_edict` | `forge` |
| A roadmap with lanes and critical path | `school_weave` | `chart` / `relay` |
| Acceptance criteria | `school_compass` | `gate` |
| A plan big enough to need a map | — | `chart` |
| Work executed with proof of done | — | `forge` |
| Something broken diagnosed | — | `triage` |
| An unknown problem hunted | `school_investigate` | `investigate` |
| Numbers/dates/questions checked | `school_quantify`, `school_elicit` | `precision` |
| A pass/fail verdict | — | `gate` |
| Adversarial self-review | — | `scrutinize` |
| Parallel lanes without collisions | — | `relay` |
| How School tools should route | `school_route` | `school-routing` |

## The chain

Most real work is a chain, not a single tool: **brainstorm → clarion →
blueprint → edict → weave → chart → forge → scrutinize → gate**. Precision
(`elicit` → `quantify`) runs beside any link; `investigate` enters whenever
something unexplained appears; `relay` multiplies lanes when the plan has them.
Artifacts carry constraints the whole way — chart → forge → gate.

## Budgeted questions

When the task is fuzzy, do not guess — ask. `school_elicit` runs the adaptive
question controller: the user sets the maximum number of questions (1–100,
default 20); follow-ups share the budget; duplicates never refill it; budget
exhaustion is **not** success and unresolved material questions block closure.
Answers land in the session dict; pass it back and the count survives.

## Honesty rules (every skill, every tool)

- Evidence kinds are distinct. Simulated feedback is never human feedback;
  missing evidence is never success; UNVERIFIED counts as FAIL where a gate
  requires proof.
- A deterministic check beats a confident paragraph. Never override a failed
  check with a nicer story.
- Reports ship where the work lives: `reports/<skill>-<deliverable>.md`.
  Durable lessons go to `school_remember`.
- Every claim in a verdict links to evidence or is marked UNVERIFIED.

## Suite map — artifacts → School tools

- `clarion` → `school_clarion` · `blueprint` → `school_blueprint` · `edict` →
  `school_edict` · `weave` → `school_weave` · `compass` → `school_compass` ·
  `brainstorm` → `school_brainstorm`
- Precision: `quantify` → `school_quantify` · `elicit` → `school_elicit` ·
  `investigate` → `school_investigate`
- CLI mirrors every tool: `school clarion|blueprint|edict|weave|compass|
  brainstorm|quantify|elicit|investigate` (`school prism` is the legacy alias
  of `brainstorm`). Bridge wire names match the CLI names.

The workshop is universal — the map is what keeps it usable. Route first, load
the skill for the method, and let the evidence do the talking — any kind of
work, not only coding.

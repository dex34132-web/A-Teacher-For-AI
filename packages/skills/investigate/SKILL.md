---
name: investigate
description: Use when a system, repo, or plan needs adaptive diagnosis beyond a checklist — "find what's wrong", "why does this keep happening?", "audit this before we trust it". Discover, hypothesize, probe with evidence, follow new leads, report findings honestly. Any domain — not only coding. Not triage (one failure, one root cause) and not gate (final verdict).
---

# Investigate — adaptive diagnostic investigation

Investigation is diagnosis that is allowed to change its own mind. A checklist
runs what someone already thought of; an investigation discovers what nobody
thought of, tests it against evidence, and says plainly what remains unknown.

It is universal by contract: a repo audit, a failing product launch, and a
household budget problem share one loop — observe, suspect, probe, revise.

## When to use me

- "Find the real problems in this before we ship/publish/decide."
- "Something is wrong but we don't know what."
- "Check whether the claims in this report are actually supported."

Not for: one known failure with a repro (use `triage`), building the work
(`forge`), or issuing the acceptance verdict (`gate`).

## The loop

1. **Scope + acceptance criteria** — what would count as covered.
2. **Map the territory** — entry points, contracts, boundaries. Repository
   evidence first; never ask a human for what the repo can answer.
3. **Suspect** — behavior that looks wrong, coverage gaps, contradictions,
   unverified assumptions. Each becomes an explicit **hypothesis** with a
   justification and a confidence — not a vibe.
4. **Probe** — run the command, read the code, trace the call. Every claim
   gets evidence or stays a hypothesis. A probe that fails is still evidence.
5. **Record findings** — one stable id each: expected vs observed, repro,
   evidence refs, severity (must-fix / should-fix / note), classification
   (CONFIRMED DEFECT / LIKELY DEFECT / DESIGN GAP / COVERAGE GAP /
   ENVIRONMENTAL FAILURE / UNKNOWN), confidence + why, root cause **only when
   supported**.
6. **Follow new leads** — the checklist is not the mission. When a probe
   reveals something else, add it and re-prioritize.
7. **Stop honestly** — when scope is covered, no useful authorized work
   remains, or a stated blocker stands. Never claim exhaustive discovery.

## Rules

- A symptom is not a root cause. A good root cause predicts a second,
  independently observable consequence.
- Missing evidence is never proof of success. Status `FIXED`/`VERIFIED`
  without evidence is refused outright.
- Do not label an environmental cause as confirmed without supporting
  evidence — if it cannot be reproduced, say NOT REPRODUCED and move on.
- Invalid states and malformed inputs fail closed; they never reset the case
  into a fresh, empty investigation.
- Ask a question only when the answer materially changes the investigation and
  cannot be established from available evidence.
- The report distinguishes confirmed defects, hypotheses, design gaps, and
  unknowns — and carries its own limitations.

## Status vocabulary

`OPEN · INVESTIGATING · BLOCKED · FIXED · VERIFIED · NOT REPRODUCED` with
severities `must-fix / should-fix / note`. UNRESOLVED questions mark affected
conclusions BLOCKED.

## Suite map — artifacts → School tools

- `investigate` (case) → `school_investigate` · CLI: `school investigate`
  (actions: report | status | next | probe; the case dict round-trips, so
  every probe is persisted and resumable).
- Deterministic checks inside a probe: `school_quantify` (see the `precision`
  skill). Discipline handoffs: `triage` for a single failure, `scrutinize` for
  adversarial review, `gate` for the verdict.
- Ship the report as `reports/investigate-<subject>.md`; durable lessons go to
  `school_remember`.

Investigation is universal and resumable: the case file is the memory, evidence
is the currency, and honesty is the product — any domain, not only coding.

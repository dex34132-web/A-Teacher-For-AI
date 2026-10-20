---
name: precision
description: Use when a plan has numbers, dates, budgets, risks, or acceptance claims that must be checked — missing material questions, "is this budget right?", "does the math hold?", "what don't we know yet?". Deterministic checks with provenance and honest unknowns. Any domain — not only coding. Not for execution (forge) or the final verdict (gate).
---

# Precision — deterministic numbers, questions, and constraints

Precision is the discipline that separates a plan that *sounds* right from a plan
whose arithmetic, dates, and constraints have been checked. It is universal by
contract: a book budget, a research timeline, and a product launch are all the
same shape — money, dates, unknowns, hard rules.

You never manufacture precision. A missing input stays missing and visible; a
failed check returns **no value**; an unknown probability is never quietly zero.

## When to use me

- "What are we assuming that we shouldn't?" — material-unknown analysis.
- "Does the budget add up?" / "Is that percentage right?" — calculation checks.
- "The deadline looks wrong" — date and schedule validation.
- "We can't exceed $200 / exactly 3 phases" — hard-constraint certification.

Not for: running the work (`forge`), the pass/fail verdict on finished work
(`gate`), or finding root causes of failures (`triage`/`investigate`).

## The two moves

**1. Elicit — find the questions worth asking.**
Feed the goal + knowns to `school_elicit`. It returns prioritized material
unknowns (never asks what can be derived, never re-asks, respects dependencies),
a question batch under a budget, and an honest completion status. The question
budget is user-set (1–100, default 20): follow-ups share it, exhaustion is
**not** success. Pass the session dict back to keep state.

**2. Quantify — check every number and rule.**
Feed the plan to `school_quantify`: budget lines (Decimal money, explicit
currency), percentage claims (numerator/denominator/scope/period/source),
before/after changes (percentage-points vs relative change), risks (probability
class or honest "unknown"), scenarios (E[X] only when probabilities sum to 1),
dates (never invented; ambiguous `04/05/2026` needs a convention), and hard
constraints. The report carries provenance: inputs, formula, intermediates,
rounding, source. A self-contradicting schedule (deadline before start) forces
NO-GO; time-relative warnings are reported, never silently promoted.

## Rules

- Money is Decimal with an explicit currency. Mixed currency without a
  documented conversion source is an error, not a conversion.
- Zero denominators are explicit: "undefined" — never 0, never infinity.
- 40→50 is +10pp **and** +25%. Report both; they mean different things.
- An ordinal 1–5 matrix is a priority, never a "risk percentage".
- Evidence kinds are distinct: `machine_checked`, `human_verified`, `simulated`,
  `inferred`, `missing`. Simulated feedback is never presented as human feedback;
  missing evidence is never success.
- A deterministic check that fails cannot be overridden by the model's opinion.

## Status vocabulary

`PASS · FAIL · UNVERIFIED (counts FAIL) · SIMULATED (proxy, ≥3 named personas;
counts UNVERIFIED unless the user accepted the proxy before the verdict) ·
EXPLORATORY (claim downgraded; never "done")`

## Suite map — artifacts → School tools

- `elicit` (questions) → `school_elicit` · `quantify` (checks) → `school_quantify`
- CLI: `school elicit`, `school quantify` (same reports, byte-identical)
- Ship reports as `reports/precision-<deliverable>.md`; durable lessons go to
  `school_remember`.

The precision layer is universal and deterministic; the intelligence is in what
you feed it. Ask the material questions first, then check every claim — any
kind of work, not only coding.

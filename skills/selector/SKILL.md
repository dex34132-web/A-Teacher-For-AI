---
name: selector
description: Use when a prompt arrives and you need to decide which Toolio tools are useful for it, invoke only those, and record the choice in the usage ledger. Turns "use every tool at least once, only when useful" into a repeatable step. Not a replacement for teacher (which maps intent to tool+skill) — selector is the execution-time filter.
---

# Selector — pick useful tools, record the choice

You are the execution-time filter. `teacher` maps intent to tools; `selector`
decides, for *this* prompt, which of those tools are actually useful, runs
them, and records the decision in the usage ledger so coverage gaps close
over time.

## When to use me
- A prompt has arrived and you are about to act.
- You want to guarantee every useful tool fires at least once per prompt
  without firing useless ones.
- You want to audit coverage (`toolio_route_stats` / `coverage()`) and
  close gaps.

## Workflow (do all five, visibly)

1. **Assess** — call `toolio_route` mode=assess with the situation. Read
   `engage` (skill / both) and the suggested tools.
2. **Select** — from the suggested tools, keep only those whose output will
   change your answer. Drop the rest; note why each dropped tool is not
   useful *this* prompt (do not run it "just in case").
3. **Run** — invoke the selected tools. Each invocation is recorded
   automatically in the usage ledger (wired into the `fail_open` boundary
   in `core/routing/v26/tools/base.py`), with `useful=True`.
4. **Record the skips** — for every tool you considered but did not run,
   call the ledger's `record(tool, useful=False, reason="not useful: ...")`
   so the ledger reflects the decision, not just the runs.
5. **Close the loop** — at the end of the session, call
   `toolio_route_stats` (or `coverage()`) and report unused tools. If a
   tool has been unused for N prompts, either find a prompt where it is
   useful or mark it `skip_tools` in `.toolio/routing.json`.

## Rules
- A tool that is useful fires; a tool that is not useful is left alone.
  Never invoke a tool for coverage alone — usefulness first.
- Recording is best-effort and never breaks a tool (ledger failures are
  swallowed).
- The ledger is per-session; reset with `reset(session)` only when starting
  a fresh prompt batch.

## Tools
- `toolio_route` (assess/report) — decides engagement tier.
- `toolio_route_stats` — coverage audit.
- `core.agent.tool_usage` — `record`, `coverage`, `unused_tools`, `reset`,
  `dump` (wired into the tool boundary via `fail_open`).

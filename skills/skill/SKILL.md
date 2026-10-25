---
name: skill
description: Use when the user types "skill" or "skills" in chat, or asks to see the Toolio skill menu, list skill engines, or choose a skill engine to run. Renders the Toolio skills menu directly in the chat and handles navigation through chat replies. Not for executing one specific engine directly (load that engine's own skill instead).
---

# Toolio Skill Menu — In-Chat Navigation

The menu lives in the chat. Never open a TUI, a file dump, or a web page for it.

## Protocol

1. **Open**: call `toolio_skills_menu` with no arguments (omit `choice`). Announce `skills-menu used`.
   Fallback if that tool is unavailable: run `python toolio/cli.py skills-menu --print` via shell with `q` on
   stdin (prints the menu, then exits).
2. **Render** the returned menu in the chat as a numbered list. `toolio/skills_menu.py`
   (`MENU_ITEMS`) is the single source of truth — never hardcode the action list.
3. **Invite**: tell the user to reply with a number (`1`-`12`), an action name, or `q` to quit.
4. **Navigate**: for each reply, call `toolio_skills_menu` with `choice: <action>`. When an action
   needs parameters, pass them as `fields: {…}`. Announce `skills-menu used`.
5. **Loop**: show the action's outcome in chat, then re-offer the menu (or exit on `q`/`exit`/`cancel`).

## Rules

- While the menu loop is open, treat bare replies like `3` or `search foo` as menu choices.
- If the user types `skill` or `skills` again mid-loop, re-open the menu.
- Every tool call announces itself (`<tool> used`) per the tool-discipline rule.
- Budget: if the user asked for one specific engine (e.g. "run precision on this plan"), skip the
  menu and load that engine's skill directly.

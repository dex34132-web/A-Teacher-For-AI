"""Tool usage ledger — tracks which tools are invoked per prompt/session.

Supports the "gated by usefulness" coverage goal: every prompt, the system
decides which tools are useful and invokes those; this ledger records what ran
so coverage gaps (tools that never fire) are visible and can be closed.

Stdlib only. Thread-safe via a simple lock.
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_LEDGER: dict[str, list[dict[str, Any]]] = defaultdict(list)


def record(tool_name: str, *, session: str = "default", prompt_id: str | None = None, useful: bool = True, reason: str = "") -> None:
    """Record a tool invocation."""
    entry = {
        "tool": tool_name,
        "session": session,
        "prompt_id": prompt_id,
        "useful": useful,
        "reason": reason,
        "ts": time.time(),
    }
    with _LOCK:
        _LEDGER[session].append(entry)


def coverage(session: str = "default", known_tools: list[str] | None = None) -> dict[str, Any]:
    """Return coverage stats: which tools have been used at least once."""
    with _LOCK:
        used = {e["tool"] for e in _LEDGER.get(session, [])}
    known = set(known_tools or [])
    unused = sorted(known - used) if known else []
    return {
        "session": session,
        "used_count": len(used),
        "used_tools": sorted(used),
        "unused_tools": unused,
        "total_invocations": len(_LEDGER.get(session, [])),
    }


def unused_tools(session: str = "default", known_tools: list[str] | None = None) -> list[str]:
    return coverage(session, known_tools)["unused_tools"]


def reset(session: str = "default") -> None:
    with _LOCK:
        _LEDGER.pop(session, None)


def dump(path: str | Path, session: str = "default") -> None:
    """Persist the ledger for a session to JSON."""
    with _LOCK:
        data = list(_LEDGER.get(session, []))
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


__all__ = ["record", "coverage", "unused_tools", "reset", "dump"]

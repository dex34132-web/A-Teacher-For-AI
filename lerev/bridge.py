"""Legacy shim — ``python -m lerev.bridge`` (alias of teacher.bridge)."""

from __future__ import annotations

from teacher.bridge import _COMMANDS, main

__all__ = ["_COMMANDS", "main"]

if __name__ == "__main__":
    main()

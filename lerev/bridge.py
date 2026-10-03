"""Legacy shim — ``python -m lerev.bridge`` (alias of school.bridge)."""

from __future__ import annotations

from school.bridge import _COMMANDS, main

__all__ = ["_COMMANDS", "main"]

if __name__ == "__main__":
    main()

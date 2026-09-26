"""Legacy shim — ``lerev`` CLI (alias of the Teacher CLI)."""

from __future__ import annotations

from teacher.cli import _auto_install, main

__all__ = ["_auto_install", "main"]

if __name__ == "__main__":
    main()

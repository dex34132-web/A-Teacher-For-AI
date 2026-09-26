"""Legacy shim — ``python -m lerev`` (alias of the Teacher CLI)."""

from __future__ import annotations

from teacher.cli import main

if __name__ == "__main__":
    main()

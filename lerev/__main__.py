"""Legacy shim — ``python -m lerev`` (alias of the School CLI)."""

from __future__ import annotations

from school.cli import main

if __name__ == "__main__":
    main()

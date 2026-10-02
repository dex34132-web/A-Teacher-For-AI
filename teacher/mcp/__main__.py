"""Allow running the Teacher MCP server via ``python -m teacher.mcp``."""

from __future__ import annotations

import sys

try:
    from teacher.mcp.server import main
except ImportError as exc:
    sys.stderr.write(
        "Teacher MCP server requires the optional 'mcp' package.\n"
        "Install it with: pip install 'teacher[mcp]'\n"
        f"(import failed: {exc})\n"
    )
    raise SystemExit(1) from exc

if __name__ == "__main__":
    main()

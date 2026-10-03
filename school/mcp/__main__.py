"""Allow running the School MCP server via ``python -m school.mcp``."""

from __future__ import annotations

import sys

try:
    from school.mcp.server import main
except ImportError as exc:
    sys.stderr.write(
        "School MCP server requires the optional 'mcp' package.\n"
        "Install it with: pip install 'school[mcp]'\n"
        f"(import failed: {exc})\n"
    )
    raise SystemExit(1) from exc

if __name__ == "__main__":
    main()

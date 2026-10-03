### Task 3: MCP parity — two tools + helpers

**Files:**
- Modify: `teacher/mcp/server.py` (`_TOOLS` dict after `teacher_diagnose`; helpers after `_build_request`; `_call_tool` special-cases)
- Test: `tests/unit/test_mcp_server.py` (extend)

**Interfaces:**
- Consumes: `_TOOLS`, `_build_request(worktree, tool, args)`, `_bridge_call(command, req)`, `_list_tools`, existing `types` import; `pathlib`/`json`/`os` already imported or to be imported.
- Produces: `_engage_for(severity: str) -> str`, `_append_evidence(worktree: str, entry: dict) -> None`, `_read_stats(worktree: str, limit: int) -> dict`, `_call_route(worktree: str, arguments: dict) -> types.CallToolResult`, `_call_route_stats(worktree: str, arguments: dict) -> types.CallToolResult`; `_call_tool` dispatches `teacher_route` / `teacher_route_stats` to them before `_build_request`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_mcp_server.py`:

```python
class TestRouteToolsMCP:
    def test_tools_present_with_use_guidance(self):
        from teacher.mcp.server import _TOOLS
        for name in ("teacher_route", "teacher_route_stats"):
            assert name in _TOOLS
            assert "Use" in _TOOLS[name]["description"]
            assert "coding" in _TOOLS[name]["description"]

    def test_route_schema(self):
        from teacher.mcp.server import _TOOLS
        props = _TOOLS["teacher_route"]["schema"]["properties"]
        assert props["mode"]["enum"] == ["assess", "report"]
        assert props["severity"]["enum"] == ["light", "medium", "high"]
        assert "situation" in _TOOLS["teacher_route"]["schema"]["required"]

    def test_stats_annotations(self):
        from teacher.mcp.server import _TOOLS
        ann = _TOOLS["teacher_route_stats"]["annotations"]
        assert ann["read_only_hint"] is True

    def test_engage_mapping_parity(self):
        from teacher.mcp.server import _engage_for
        assert _engage_for("light") == "skill"
        assert _engage_for("medium") == "both"
        assert _engage_for("high") == "both"

    def test_assess_requires_severity_and_writes_evidence(self, tmp_path):
        from teacher.mcp.server import _call_tool
        wt = str(tmp_path)
        with pytest.raises(ValueError) as exc:
            _call_tool(wt, "teacher_route",
                       {"mode": "assess", "situation": "planning a trip"})
        assert "severity" in str(exc.value).lower()
        res = _call_tool(wt, "teacher_route",
                         {"mode": "assess", "situation": "planning a trip",
                          "severity": "light"})
        assert res.is_error is False
        data = res.structured_content
        assert data["source"] == "self-rated"
        assert data["engage"] == "skill"
        ev = tmp_path / ".teacher" / "routing-stats.jsonl"
        assert ev.exists()
        assert "assess" in ev.read_text(encoding="utf-8")

    def test_report_stores_tagged_lesson(self, tmp_path, monkeypatch):
        from teacher.mcp.server import _call_tool
        res = _call_tool(str(tmp_path), "teacher_route",
                         {"mode": "report", "situation": "debugging session",
                          "lesson": "recall first, search second",
                          "outcome": "helpful"})
        assert res.is_error is False
        assert res.structured_content["ok"] is True
        # Lesson is retrievable through the normal recall path.
        res2 = _call_tool(str(tmp_path), "teacher_recall",
                          {"query": "routing lesson"})
        assert res2.is_error is False
        found = " ".join(
            str(m.get("content", ""))
            for m in res2.structured_content.get("memories", [])
        )
        assert "recall first" in found

    def test_stats_aggregates(self, tmp_path):
        from teacher.mcp.server import _call_tool
        _call_tool(str(tmp_path), "teacher_route",
                   {"mode": "assess", "situation": "x", "severity": "high"})
        res = _call_tool(str(tmp_path), "teacher_route_stats", {"limit": 5})
        assert res.is_error is False
        data = res.structured_content
        assert data["last_activity"]
        assert any(e.get("kind") == "assess" for e in data["recent"])
        assert "knobs" in data

    def test_default_assess_without_severity_fails(self, tmp_path):
        # MCP has no model client: severity is mandatory.
        from teacher.mcp.server import _call_tool
        with pytest.raises(ValueError):
            _call_tool(str(tmp_path), "teacher_route",
                       {"mode": "assess", "situation": "x"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_mcp_server.py -q -k "Route" `
Expected: FAIL (`_engage_for` missing, tools missing).

- [ ] **Step 3: Implement MCP parity**

In `teacher/mcp/server.py`:

1. Append to `_TOOLS` (after `teacher_diagnose`):

```python
    "teacher_route": {
        "description": (
            "Assess how much Teacher routing machinery a situation needs "
            "(MCP fallback: self-rated severity - light engages the skill, "
            "medium/high engages tool and skill together) or store a "
            "routing lesson tagged for later review. Use when starting "
            "non-trivial work or after a tool call taught you something "
            "about routing - for anything, not only coding."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["assess", "report"],
                    "description": "assess = routing decision; report = store a lesson.",
                },
                "situation": {
                    "type": "string",
                    "description": "What is happening (max 500 chars).",
                },
                "severity": {
                    "type": "string",
                    "enum": ["light", "medium", "high"],
                    "description": "Required for assess: self-rated urgency (no model client on MCP).",
                },
                "lesson": {
                    "type": "string",
                    "description": "report: the routing lesson to store.",
                },
                "outcome": {
                    "type": "string",
                    "enum": ["helpful", "useless", "neutral"],
                    "description": "report: how the routing worked out.",
                },
            },
            "required": ["mode", "situation"],
        },
    },
    "teacher_route_stats": {
        "description": (
            "Aggregated routing evidence: per-tool call counts and average "
            "durations, recent assess/report entries, current knobs, and "
            "recent routing lessons. Use before adjusting how Teacher "
            "routes, or when the routing skill asks for current numbers - "
            "for anything, not only coding."
        ),
        "annotations": {"read_only_hint": True, "idempotent_hint": True},
        "schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Recent entries/lessons to include (default 20).",
                }
            },
        },
    },
```

2. After `_build_request`, add:

```python
_ROUTE_STATS_FILE = "routing-stats.jsonl"
_ROUTE_KNOBS_FILE = "routing.json"
_ROUTE_MAX_LINES = 2000

_DEFAULT_KNOBS: dict[str, Any] = {
    "recall_threshold": 0.2,
    "hook_limit": 3,
    "hook_budget": 400,
    "hook_timeout_ms": 1500,
    "skip_tools": [],
    "force_tools": [],
}


def _engage_for(severity: str) -> str:
    """Parity with the plugin's engageFor()."""
    return "skill" if severity == "light" else "both"


def _memory_root(worktree: str) -> "Path":
    for sub in (".teacher", ".lerev", ".evo"):
        root = Path(worktree) / sub
        if (root / "memory").is_dir():
            return root
    return Path(worktree) / ".teacher"


def _append_evidence(worktree: str, entry: dict[str, Any]) -> None:
    """Append one JSONL evidence line; silent on failure (spec: never breaks)."""
    try:
        root = _memory_root(worktree)
        root.mkdir(parents=True, exist_ok=True)
        path = root / _ROUTE_STATS_FILE
        if path.exists():
            lines = [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if len(lines) >= _ROUTE_MAX_LINES * 2:
                path.write_text(
                    "\n".join(lines[-_ROUTE_MAX_LINES:]) + "\n", encoding="utf-8"
                )
        payload = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - evidence is best-effort
        pass


def _read_knobs(worktree: str) -> dict[str, Any]:
    try:
        raw = json.loads((_memory_root(worktree) / _ROUTE_KNOBS_FILE).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - invalid knobs fall back per spec
        return dict(_DEFAULT_KNOBS)
    knobs = dict(_DEFAULT_KNOBS)
    if isinstance(raw, dict):
        for key in ("recall_threshold", "hook_limit", "hook_budget", "hook_timeout_ms"):
            if isinstance(raw.get(key), (int, float)):
                knobs[key] = raw[key]
        for key in ("skip_tools", "force_tools"):
            if isinstance(raw.get(key), list):
                knobs[key] = [str(v) for v in raw[key]]
    return knobs


def _read_stats(worktree: str, limit: int) -> dict[str, Any]:
    path = _memory_root(worktree) / _ROUTE_STATS_FILE
    entries: list[dict[str, Any]] = []
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entries.append(json.loads(line))
        except Exception:  # noqa: BLE001 - corrupt lines are skipped
            entries = []
    per_tool: dict[str, dict[str, int]] = {}
    for entry in entries:
        if entry.get("kind") != "exec":
            continue
        tool = str(entry.get("tool", "?"))
        cur = per_tool.setdefault(tool, {"calls": 0, "total_ms": 0})
        cur["calls"] += 1
        cur["total_ms"] += int(entry.get("ms") or 0)
    aggregates = {
        tool: {
            "calls": counts["calls"],
            "avg_ms": round(counts["total_ms"] / counts["calls"])
            if counts["calls"]
            else 0,
        }
        for tool, counts in per_tool.items()
    }
    last = entries[-1] if entries else None
    return {
        "last_activity": last.get("ts") if last else None,
        "recent": entries[-limit:],
        "aggregates": aggregates,
        "knobs": _read_knobs(worktree),
    }
```

(Add `from datetime import datetime, timezone` and `from pathlib import Path` to the module imports if absent.)

3. Replace `_call_tool` body with dispatch:

```python
def _call_tool(worktree: str, name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    if name not in _TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    if name == "teacher_route":
        return _call_route(worktree, arguments)
    if name == "teacher_route_stats":
        return _call_route_stats(worktree, arguments)
    req = _build_request(worktree, name, arguments)
    resp = _bridge_call(name.removeprefix("teacher_"), req)
    payload = json.dumps(resp, default=str, ensure_ascii=False)
    structured = json.loads(payload)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=payload)],
        structured_content=structured,
        is_error=not bool(resp.get("ok", False)),
    )
```

4. Add the two handlers (before `_call_tool`):

```python
def _route_result(data: dict[str, Any]) -> types.CallToolResult:
    payload = json.dumps(data, default=str, ensure_ascii=False)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=payload)],
        structured_content=json.loads(payload),
        is_error=bool(data.get("ok", False) is False and data.get("source") is None),
    )


def _call_route(worktree: str, arguments: dict[str, Any]) -> types.CallToolResult:
    mode = str(arguments.get("mode", "")).strip()
    situation = str(arguments.get("situation", ""))[:500]
    if not situation.strip():
        raise ValueError("situation is required (max 500 chars)")
    if mode == "assess":
        severity = str(arguments.get("severity", "")).lower().strip()
        if severity not in {"light", "medium", "high"}:
            raise ValueError(
                "severity is required for assess on MCP (light | medium | high)"
            )
        engage = _engage_for(severity)
        _append_evidence(
            worktree,
            {
                "kind": "assess",
                "tool": "teacher_route",
                "ms": 0,
                "ok": True,
                "severity": severity,
                "engage": engage,
            },
        )
        return _route_result(
            {
                "source": "self-rated",
                "severity": severity,
                "engage": engage,
                "reason": "self-rated (MCP has no model client)",
                "next": "Load the `teacher-routing` skill so tool and skill work together.",
            }
        )
    if mode == "report":
        lesson = str(arguments.get("lesson", "")).strip()[:1000]
        if not lesson:
            raise ValueError("lesson is required for mode=report")
        outcome = (
            arguments.get("outcome")
            if arguments.get("outcome") in {"helpful", "useless", "neutral"}
            else "helpful"
        )
        req = _build_request(
            worktree,
            "teacher_remember",
            {
                "content": f"Routing lesson ({outcome}): {lesson}",
                "observation": situation or None,
                "outcome": {
                    "helpful": "SUCCESS",
                    "useless": "FAILURE",
                    "neutral": "NEUTRAL",
                }[outcome],
                "tags": ["routing", outcome],
            },
        )
        resp = _bridge_call("remember", req)
        _append_evidence(
            worktree,
            {
                "kind": "report",
                "tool": "teacher_route",
                "ms": 0,
                "ok": bool(resp.get("ok")),
                "outcome": outcome,
            },
        )
        return _route_result(resp)
    raise ValueError('mode must be "assess" or "report"')


def _call_route_stats(worktree: str, arguments: dict[str, Any]) -> types.CallToolResult:
    limit_raw = arguments.get("limit", 20)
    try:
        limit = max(1, min(int(limit_raw), 100))
    except (TypeError, ValueError):
        limit = 20
    data = _read_stats(worktree, limit)
    recall_req = _build_request(
        worktree,
        "teacher_recall",
        {"query": "routing lesson", "confidence_threshold": 0, "limit": min(limit, 10)},
    )
    recall_req["context_budget"] = 1500
    resp = _bridge_call("recall", recall_req)
    lessons = resp.get("memories", []) if resp.get("ok") else []
    data["lessons"] = [
        {
            "id": m.get("experience_id") or m.get("id"),
            "content": str(m.get("content", ""))[:300],
        }
        for m in lessons
    ]
    return _route_result(data)
```

- [ ] **Step 4: Run unit tests**

Run: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_mcp_server.py -q`
Expected: PASS — including the pre-existing description-parity test, which now covers the two new tools automatically.

- [ ] **Step 5: Ruff on changed files**

Run: `& ".venv\Scripts\python.exe" -m ruff check teacher/mcp/server.py tests/unit/test_mcp_server.py`
Expected: clean (fix any line-length/import issues it reports).

- [ ] **Step 6: Commit**

```powershell
git add teacher/mcp/server.py tests/unit/test_mcp_server.py; if ($?) { git commit -m "feat(mcp): teacher_route and teacher_route_stats with self-rated fallback" }
```

---


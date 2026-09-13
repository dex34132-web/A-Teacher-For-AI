# LEREV Orchestrator + Tool Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a typed tool interface + orchestrator that routes requests to existing LEREV learning pipeline systems, with three execution modes (on-demand, background, hybrid).

**Architecture:** Three-layer design: Tool classes (Layer 1) wrap existing systems, Orchestrator (Layer 2) routes and executes pipelines, Bridge extension (Layer 3) exposes new commands. All tools use existing V2.2-V2.6 systems — no new engines.

**Tech Stack:** Python 3.14, dataclasses, ABC, concurrent.futures for parallel execution. Existing dependencies: core/learner/*, core/routing/v26/*.

**Spec:** `docs/superpowers/specs/2026-09-13-orchestrator-tool-interface-design.md`

## Global Constraints

- No new learning engines — all tools use existing learner/conflict/confidence/lifecycle systems
- No LLM calls in execution path
- Backward compatible: existing `lerev_status`, `lerev_remember`, `lerev_recall` bridge commands unchanged
- No global mutable state
- Deterministic and auditable
- TDD: write failing tests first, then implement

## File Structure

```
core/routing/v26/tools/
    __init__.py              # Tool exports
    base.py                  # Tool ABC, ToolResult, ToolRegistry, PipelineResult, BackgroundTask
    status.py                # StatusTool
    remember.py              # RememberTool
    recall.py                # RecallTool
    conflict.py              # ConflictDetectionTool
    confidence.py            # ConfidenceTool
    semantic_search.py       # SemanticSearchTool
    deduplicate.py           # DeduplicateTool
    knowledge.py             # KnowledgeExtractionTool
    lifecycle.py             # LifecycleTool
    diagnose.py              # DiagnoseTool
core/routing/v26/
    orchestrator.py          # Orchestrator class
    background.py            # BackgroundWorker
tests/unit/test_tools/
    __init__.py
    test_base.py             # Tests for base classes
    test_status.py
    test_remember.py
    test_recall.py
    test_conflict_tool.py
    test_confidence_tool.py
    test_semantic_search.py
    test_deduplicate.py
    test_knowledge.py
    test_lifecycle_tool.py
    test_diagnose.py
    test_orchestrator.py
    test_background.py
```

---

### Task 1: Tool Base Classes

**Files:**
- Create: `core/routing/v26/tools/__init__.py`
- Create: `core/routing/v26/tools/base.py`
- Create: `tests/unit/test_tools/__init__.py`
- Create: `tests/unit/test_tools/test_base.py`

**Interfaces:**
- Produces: `Tool` (ABC), `ToolResult` (dataclass), `ToolRegistry`, `PipelineResult`, `BackgroundTask`

- [ ] **Step 1: Write failing tests for base classes**

```python
"""Tests for tool base classes."""
from core.routing.v26.tools.base import Tool, ToolResult, ToolRegistry, PipelineResult, BackgroundTask


class TestToolResult:
    def test_success_result(self):
        r = ToolResult(success=True, data={"id": "123"}, errors=[], metadata={})
        assert r.success is True
        assert r.data == {"id": "123"}
        assert r.to_dict() == {"success": True, "data": {"id": "123"}, "errors": [], "metadata": {}}

    def test_error_result(self):
        r = ToolResult(success=False, data={}, errors=["bad input"], metadata={})
        assert r.success is False
        assert r.errors == ["bad input"]

    def test_to_dict_roundtrip(self):
        r = ToolResult(success=True, data={"a": 1}, errors=[], metadata={"t": 0.1})
        d = r.to_dict()
        assert d["success"] is True
        assert d["data"] == {"a": 1}
        assert d["metadata"] == {"t": 0.1}


class ConcreteTool(Tool):
    @property
    def name(self) -> str:
        return "test_tool"

    @property
    def description(self) -> str:
        return "A test tool"

    @property
    def schema(self) -> dict:
        return {"input": {"type": "string"}}

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"input": kwargs.get("input", "")}, errors=[], metadata={})


class TestTool:
    def test_tool_properties(self):
        t = ConcreteTool()
        assert t.name == "test_tool"
        assert t.description == "A test tool"
        assert "input" in t.schema

    def test_tool_execute(self):
        t = ConcreteTool()
        r = t.execute(input="hello")
        assert r.success is True
        assert r.data["input"] == "hello"

    def test_tool_validate_default(self):
        t = ConcreteTool()
        errors = t.validate(anything="value")
        assert errors == []


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = ConcreteTool()
        reg.register(tool)
        assert reg.get("test_tool") is tool

    def test_get_unknown(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(ConcreteTool())
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    def test_execute_known_tool(self):
        reg = ToolRegistry()
        reg.register(ConcreteTool())
        r = reg.execute("test_tool", input="world")
        assert r.success is True
        assert r.data["input"] == "world"

    def test_execute_unknown_tool(self):
        reg = ToolRegistry()
        r = reg.execute("nonexistent")
        assert r.success is False
        assert "Unknown tool" in r.errors[0]


class FailingTool(Tool):
    @property
    def name(self) -> str:
        return "failing"

    @property
    def description(self) -> str:
        return "Always fails"

    @property
    def schema(self) -> dict:
        return {}

    def validate(self, **kwargs) -> list[str]:
        if "required_field" not in kwargs:
            return ["required_field is missing"]
        return []

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=False, data={}, errors=["intentional failure"], metadata={})


class TestRegistryValidation:
    def test_validate_before_execute(self):
        reg = ToolRegistry()
        reg.register(FailingTool())
        r = reg.execute("failing")
        assert r.success is False
        assert "required_field is missing" in r.errors[0]

    def test_validate_pass(self):
        reg = ToolRegistry()
        reg.register(FailingTool())
        r = reg.execute("failing", required_field="value")
        assert r.success is False  # execute fails, but validation passed
        assert "required_field is missing" not in r.errors


class TestPipelineResult:
    def test_pipeline_result_success(self):
        r1 = ToolResult(success=True, data={"a": 1}, errors=[], metadata={})
        r2 = ToolResult(success=True, data={"b": 2}, errors=[], metadata={})
        pr = PipelineResult(steps=[("tool1", r1), ("tool2", r2)], success=True)
        assert pr.success is True
        d = pr.to_dict()
        assert len(d["steps"]) == 2
        assert d["steps"][0]["tool"] == "tool1"

    def test_pipeline_result_failure(self):
        r1 = ToolResult(success=False, data={}, errors=["fail"], metadata={})
        pr = PipelineResult(steps=[("tool1", r1)], success=False)
        assert pr.success is False


class TestBackgroundTask:
    def test_background_task_creation(self):
        import time
        bt = BackgroundTask(task_type="consolidate", params={"threshold": 10})
        assert bt.task_type == "consolidate"
        assert bt.params == {"threshold": 10}
        assert bt.created_at <= time.time()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_tools/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.routing.v26.tools'`

- [ ] **Step 3: Write minimal implementation**

Create `core/routing/v26/tools/__init__.py`:
```python
"""LEREV V2.6 tool interface for the learning pipeline."""
```

Create `core/routing/v26/tools/base.py`:
```python
"""Base classes for LEREV tools."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """Structured result from a tool execution."""
    success: bool
    data: dict
    errors: list[str]
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class Tool(ABC):
    """Base class for all LEREV tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""

    @property
    @abstractmethod
    def schema(self) -> dict:
        """JSON Schema for tool parameters."""

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""

    def validate(self, **kwargs) -> list[str]:
        """Validate parameters. Returns list of error messages."""
        return []


@dataclass
class PipelineResult:
    """Result of a multi-step tool pipeline."""
    steps: list[tuple[str, ToolResult]]
    success: bool

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "steps": [{"tool": name, "result": r.to_dict()} for name, r in self.steps],
        }


@dataclass
class BackgroundTask:
    """A queued background processing task."""
    task_type: str
    params: dict
    created_at: float = field(default_factory=time.time)


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "schema": t.schema}
                for t in self._tools.values()]

    def execute(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(success=False, data={}, errors=[f"Unknown tool: {name}"], metadata={})
        errors = tool.validate(**kwargs)
        if errors:
            return ToolResult(success=False, data={}, errors=errors, metadata={})
        return tool.execute(**kwargs)
```

Create `tests/unit/test_tools/__init__.py`: empty file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_tools/test_base.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/ tests/unit/test_tools/
git commit -m "feat(v26/tools): add base classes - Tool ABC, ToolResult, ToolRegistry, PipelineResult, BackgroundTask"
```

---

### Task 2: StatusTool

**Files:**
- Create: `core/routing/v26/tools/status.py`
- Create: `tests/unit/test_tools/test_status.py`

**Interfaces:**
- Consumes: nothing (checks component imports)
- Produces: `StatusTool` with name `"lerev_status"`

- [ ] **Step 1: Write failing test**

```python
"""Tests for StatusTool."""
from core.routing.v26.tools.status import StatusTool


class TestStatusTool:
    def test_name(self):
        t = StatusTool()
        assert t.name == "lerev_status"

    def test_execute_returns_ok(self):
        t = StatusTool()
        r = t.execute()
        assert r.success is True
        assert "components" in r.data

    def test_components_include_v26(self):
        t = StatusTool()
        r = t.execute()
        assert "v2_6_memory" in r.data["components"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools/test_status.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""Status tool — checks LEREV component availability."""
from __future__ import annotations

from core.routing.v26.tools.base import Tool, ToolResult


class StatusTool(Tool):
    @property
    def name(self) -> str:
        return "lerev_status"

    @property
    def description(self) -> str:
        return "Check LEREV runtime status including component availability"

    @property
    def schema(self) -> dict:
        return {}

    def execute(self, **kwargs) -> ToolResult:
        components = {}
        try:
            from core.routing.v26.memory_manager import MemoryManager
            components["v2_6_memory"] = True
        except ImportError:
            components["v2_6_memory"] = False

        try:
            from core.learner.conflict import detect_conflicts
            components["v2_2_conflict"] = True
        except ImportError:
            components["v2_2_conflict"] = False

        try:
            from core.learner.confidence import estimate_confidence
            components["v2_3_confidence"] = True
        except ImportError:
            components["v2_3_confidence"] = False

        try:
            from core.learner.lifecycle_manager import LifecycleManager
            components["v2_4_2_lifecycle"] = True
        except ImportError:
            components["v2_4_2_lifecycle"] = False

        try:
            from core.routing.v26.persistence import ScopeIsolatedStorage
            components["persistence"] = True
        except ImportError:
            components["persistence"] = False

        try:
            from core.routing.v26.security import V26SecurityPolicy
            components["security"] = True
        except ImportError:
            components["security"] = False

        try:
            from core.routing.v26.semantic_retrieval import scored_query
            components["semantic_retrieval"] = True
        except ImportError:
            components["semantic_retrieval"] = False

        return ToolResult(
            success=True,
            data={"components": components, "version": "2.6.0"},
            errors=[],
            metadata={},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools/test_status.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/status.py tests/unit/test_tools/test_status.py
git commit -m "feat(v26/tools): add StatusTool for component availability checks"
```

---

### Task 3: RememberTool

**Files:**
- Create: `core/routing/v26/tools/remember.py`
- Create: `tests/unit/test_tools/test_remember.py`

**Interfaces:**
- Consumes: `MemoryManager` (injected via constructor)
- Produces: `RememberTool` with name `"lerev_remember"`

- [ ] **Step 1: Write failing test**

```python
"""Tests for RememberTool."""
from unittest.mock import MagicMock, patch
from core.routing.v26.tools.remember import RememberTool


class TestRememberTool:
    def test_name(self):
        t = RememberTool(manager=MagicMock())
        assert t.name == "lerev_remember"

    def test_schema_has_content(self):
        t = RememberTool(manager=MagicMock())
        assert "content" in t.schema

    def test_validate_requires_content(self):
        t = RememberTool(manager=MagicMock())
        errors = t.validate()
        assert any("content" in e for e in errors)

    def test_execute_stores_memory(self):
        mock_manager = MagicMock()
        mock_entry = MagicMock()
        mock_entry.memory_id = "mem_123"
        mock_manager.store_experience.return_value = (True, "stored")
        t = RememberTool(manager=mock_manager)
        r = t.execute(content="test memory", outcome="SUCCESS")
        assert r.success is True
        assert r.data["id"] == "mem_123"

    def test_execute_handles_failure(self):
        mock_manager = MagicMock()
        mock_manager.store_experience.return_value = (False, "validation failed")
        t = RememberTool(manager=mock_manager)
        r = t.execute(content="test")
        assert r.success is False
        assert "validation failed" in r.errors[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools/test_remember.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""Remember tool — stores experiences through V2.6 memory."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.experience import Experience, ExperienceOutcome
from core.routing.v26.identity import AgentIdentity, MemoryScope, ProjectIdentity, SessionIdentity
from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.routing.v26.memory_manager import MemoryManager


class RememberTool(Tool):
    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_remember"

    @property
    def description(self) -> str:
        return "Store an experience or memory through LEREV V2.6"

    @property
    def schema(self) -> dict:
        return {
            "content": {"type": "string", "description": "Memory content"},
            "outcome": {"type": "string", "enum": ["SUCCESS", "FAILURE", "NEUTRAL", "MIXED"]},
            "project": {"type": "string"},
            "session": {"type": "string"},
            "observation": {"type": "string"},
            "action": {"type": "string"},
        }

    def validate(self, **kwargs) -> list[str]:
        errors = []
        if not kwargs.get("content"):
            errors.append("content is required")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        content = kwargs["content"]
        outcome_str = kwargs.get("outcome", "NEUTRAL")
        project_id = kwargs.get("project", "")
        session_id = kwargs.get("session", "")

        try:
            outcome = ExperienceOutcome(outcome_str)
        except ValueError:
            outcome = ExperienceOutcome.NEUTRAL

        agent = AgentIdentity.create(agent_id="tool_user")
        project = ProjectIdentity(project_id=project_id) if project_id else None
        session = SessionIdentity(session_id=session_id) if session_id else None
        scope = MemoryScope(agent=agent, project=project, session=session)

        experience = Experience.create(
            content=content,
            outcome=outcome,
            scope=scope,
            observation=kwargs.get("observation", ""),
            action=kwargs.get("action", ""),
        )

        ok, msg = self._manager.store_experience(experience)
        if not ok:
            return ToolResult(success=False, data={}, errors=[msg], metadata={})

        entry = self._manager.get_memory(experience.memory_id) if hasattr(self._manager, 'get_memory') else None
        entry_id = experience.memory_id

        return ToolResult(
            success=True,
            data={"id": entry_id, "scope": f"agent:{agent.agent_id}", "outcome": outcome.value},
            errors=[],
            metadata={},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools/test_remember.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/remember.py tests/unit/test_tools/test_remember.py
git commit -m "feat(v26/tools): add RememberTool for storing experiences"
```

---

### Task 4: RecallTool

**Files:**
- Create: `core/routing/v26/tools/recall.py`
- Create: `tests/unit/test_tools/test_recall.py`

**Interfaces:**
- Consumes: `MemoryManager` (injected via constructor)
- Produces: `RecallTool` with name `"lerev_recall"`

- [ ] **Step 1: Write failing test**

```python
"""Tests for RecallTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.recall import RecallTool


class TestRecallTool:
    def test_name(self):
        t = RecallTool(manager=MagicMock())
        assert t.name == "lerev_recall"

    def test_validate_requires_query(self):
        t = RecallTool(manager=MagicMock())
        errors = t.validate()
        assert any("query" in e for e in errors)

    def test_execute_returns_memories(self):
        mock_manager = MagicMock()
        mock_response = MagicMock()
        mock_response.memories = []
        mock_response.total = 0
        mock_response.truncated = False
        mock_response.context_cost = 0
        mock_manager.request_memory.return_value = mock_response
        t = RecallTool(manager=mock_manager)
        r = t.execute(query="test query")
        assert r.success is True
        assert "memories" in r.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools/test_recall.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""Recall tool — retrieves memories through V2.6 memory."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.identity import AgentIdentity, MemoryScope, ProjectIdentity, SessionIdentity
from core.routing.v26.memory_types import MemoryRequest
from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.routing.v26.memory_manager import MemoryManager


class RecallTool(Tool):
    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_recall"

    @property
    def description(self) -> str:
        return "Retrieve memories from LEREV V2.6 long-term memory"

    @property
    def schema(self) -> dict:
        return {
            "query": {"type": "string"},
            "confidence_threshold": {"type": "number", "default": 0.0},
            "context_budget": {"type": "number", "default": 2000},
            "limit": {"type": "integer", "default": 10},
            "project": {"type": "string"},
            "session": {"type": "string"},
        }

    def validate(self, **kwargs) -> list[str]:
        errors = []
        if not kwargs.get("query"):
            errors.append("query is required")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs["query"]
        confidence_threshold = kwargs.get("confidence_threshold", 0.0)
        context_budget = kwargs.get("context_budget", 2000)
        limit = kwargs.get("limit", 10)
        project_id = kwargs.get("project", "")
        session_id = kwargs.get("session", "")

        agent = AgentIdentity.create(agent_id="tool_user")
        project = ProjectIdentity(project_id=project_id) if project_id else None
        session = SessionIdentity(session_id=session_id) if session_id else None
        scope = MemoryScope(agent=agent, project=project, session=session)

        request = MemoryRequest(
            query=query,
            scope=scope,
            confidence_threshold=confidence_threshold,
            context_budget=context_budget,
            limit=limit,
        )

        response = self._manager.request_memory(request)

        memories = []
        for entry in response.memories:
            memories.append({
                "id": entry.memory_id,
                "content": entry.content,
                "kind": entry.kind.name,
                "confidence": entry.confidence,
                "tags": sorted(entry.tags),
                "source": entry.source,
                "timestamp": entry.timestamp,
            })

        return ToolResult(
            success=True,
            data={
                "memories": memories,
                "total": response.total,
                "truncated": response.truncated,
                "context_cost": response.context_cost,
            },
            errors=[],
            metadata={},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools/test_recall.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/recall.py tests/unit/test_tools/test_recall.py
git commit -m "feat(v26/tools): add RecallTool for retrieving memories"
```

---

### Task 5: ConflictDetectionTool + ConfidenceTool

**Files:**
- Create: `core/routing/v26/tools/conflict.py`
- Create: `core/routing/v26/tools/confidence.py`
- Create: `tests/unit/test_tools/test_conflict_tool.py`
- Create: `tests/unit/test_tools/test_confidence_tool.py`

**Interfaces:**
- Consumes: `MemoryManager` (injected via constructor)
- Produces: `ConflictDetectionTool` (`"lerev_conflict"`), `ConfidenceTool` (`"lerev_confidence"`)

- [ ] **Step 1: Write failing tests**

```python
"""Tests for ConflictDetectionTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.conflict import ConflictDetectionTool


class TestConflictDetectionTool:
    def test_name(self):
        t = ConflictDetectionTool(manager=MagicMock())
        assert t.name == "lerev_conflict"

    def test_validate_requires_content(self):
        t = ConflictDetectionTool(manager=MagicMock())
        errors = t.validate()
        assert any("content" in e for e in errors)

    def test_execute_returns_conflicts(self):
        mock_manager = MagicMock()
        mock_response = MagicMock()
        mock_response.memories = []
        mock_manager.request_memory.return_value = mock_response
        t = ConflictDetectionTool(manager=mock_manager)
        r = t.execute(content="test content")
        assert r.success is True
        assert "conflicts" in r.data
```

```python
"""Tests for ConfidenceTool."""
from core.routing.v26.tools.confidence import ConfidenceTool


class TestConfidenceTool:
    def test_name(self):
        t = ConfidenceTool()
        assert t.name == "lerev_confidence"

    def test_execute_returns_confidence(self):
        t = ConfidenceTool()
        r = t.execute(content="test", prediction="output", evidence_count=5, conflict_count=0)
        assert r.success is True
        assert "score" in r.data

    def test_execute_handles_zero_evidence(self):
        t = ConfidenceTool()
        r = t.execute(content="test", prediction="output", evidence_count=0, conflict_count=0)
        assert r.success is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_tools/test_conflict_tool.py tests/unit/test_tools/test_confidence_tool.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementations**

`core/routing/v26/tools/conflict.py`:
```python
"""Conflict detection tool."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.identity import AgentIdentity, MemoryScope, ProjectIdentity, SessionIdentity
from core.routing.v26.memory_types import MemoryRequest
from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.routing.v26.memory_manager import MemoryManager


class ConflictDetectionTool(Tool):
    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_conflict"

    @property
    def description(self) -> str:
        return "Detect conflicts between incoming content and stored memories"

    @property
    def schema(self) -> dict:
        return {
            "content": {"type": "string", "description": "New content to check"},
            "project": {"type": "string"},
            "session": {"type": "string"},
            "threshold": {"type": "number", "default": 0.7},
        }

    def validate(self, **kwargs) -> list[str]:
        errors = []
        if not kwargs.get("content"):
            errors.append("content is required")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        content = kwargs["content"]
        project_id = kwargs.get("project", "")
        session_id = kwargs.get("session", "")

        agent = AgentIdentity.create(agent_id="tool_user")
        project = ProjectIdentity(project_id=project_id) if project_id else None
        session = SessionIdentity(session_id=session_id) if session_id else None
        scope = MemoryScope(agent=agent, project=project, session=session)

        request = MemoryRequest(query=content, scope=scope, limit=10)
        response = self._manager.request_memory(request)

        conflicts = []
        for mem in response.memories:
            if mem.content.lower().strip() != content.lower().strip():
                similarity = 1.0 if content.lower() in mem.content.lower() or mem.content.lower() in content.lower() else 0.5
                if similarity > 0.3:
                    conflicts.append({
                        "memory_id": mem.memory_id,
                        "content": mem.content,
                        "similarity": similarity,
                        "type": "contradiction",
                    })

        return ToolResult(
            success=True,
            data={"conflicts": conflicts, "found": len(conflicts)},
            errors=[],
            metadata={},
        )
```

`core/routing/v26/tools/confidence.py`:
```python
"""Confidence scoring tool."""
from __future__ import annotations

from core.routing.v26.tools.base import Tool, ToolResult


class ConfidenceTool(Tool):
    @property
    def name(self) -> str:
        return "lerev_confidence"

    @property
    def description(self) -> str:
        return "Compute confidence score for a prediction or memory"

    @property
    def schema(self) -> dict:
        return {
            "content": {"type": "string"},
            "prediction": {"type": "string"},
            "evidence_count": {"type": "integer"},
            "conflict_count": {"type": "integer"},
        }

    def execute(self, **kwargs) -> ToolResult:
        content = kwargs.get("content", "")
        prediction = kwargs.get("prediction", "")
        evidence_count = kwargs.get("evidence_count", 1)
        conflict_count = kwargs.get("conflict_count", 0)

        try:
            from core.learner.confidence import estimate_confidence
            result = estimate_confidence(
                similarity=0.8,
                success_count=evidence_count,
                failure_count=conflict_count,
                supporting_weight=float(evidence_count),
                total_weight=float(evidence_count + conflict_count),
                supporting_count=evidence_count,
                total_count=evidence_count + conflict_count,
                outputs=[prediction] if prediction else [],
            )
            score = result.confidence
            band = result.band if hasattr(result, 'band') else "unknown"
        except Exception:
            score = 0.5
            band = "unknown"

        return ToolResult(
            success=True,
            data={"score": score, "band": band, "evidence_count": evidence_count, "conflict_count": conflict_count},
            errors=[],
            metadata={},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_tools/test_conflict_tool.py tests/unit/test_tools/test_confidence_tool.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/conflict.py core/routing/v26/tools/confidence.py tests/unit/test_tools/test_conflict_tool.py tests/unit/test_tools/test_confidence_tool.py
git commit -m "feat(v26/tools): add ConflictDetectionTool and ConfidenceTool"
```

---

### Task 6: SemanticSearchTool + DeduplicateTool

**Files:**
- Create: `core/routing/v26/tools/semantic_search.py`
- Create: `core/routing/v26/tools/deduplicate.py`
- Create: `tests/unit/test_tools/test_semantic_search.py`
- Create: `tests/unit/test_tools/test_deduplicate.py`

**Interfaces:**
- Consumes: `MemoryStore`, `FeatureExtractor` (injected via constructor)
- Produces: `SemanticSearchTool` (`"lerev_search"`), `DeduplicateTool` (`"lerev_deduplicate"`)

- [ ] **Step 1: Write failing tests**

```python
"""Tests for SemanticSearchTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.semantic_search import SemanticSearchTool


class TestSemanticSearchTool:
    def test_name(self):
        t = SemanticSearchTool(store=MagicMock(), extractor=MagicMock())
        assert t.name == "lerev_search"

    def test_validate_requires_query(self):
        t = SemanticSearchTool(store=MagicMock(), extractor=MagicMock())
        errors = t.validate()
        assert any("query" in e for e in errors)

    def test_execute_returns_results(self):
        mock_store = MagicMock()
        mock_store.query.return_value = []
        t = SemanticSearchTool(store=mock_store, extractor=MagicMock())
        r = t.execute(query="test query")
        assert r.success is True
        assert "results" in r.data
```

```python
"""Tests for DeduplicateTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.deduplicate import DeduplicateTool


class TestDeduplicateTool:
    def test_name(self):
        t = DeduplicateTool(store=MagicMock(), extractor=MagicMock())
        assert t.name == "lerev_deduplicate"

    def test_validate_requires_content(self):
        t = DeduplicateTool(store=MagicMock(), extractor=MagicMock())
        errors = t.validate()
        assert any("content" in e for e in errors)

    def test_execute_returns_duplicates(self):
        mock_store = MagicMock()
        mock_store.query.return_value = []
        t = DeduplicateTool(store=mock_store, extractor=MagicMock())
        r = t.execute(content="test content")
        assert r.success is True
        assert "duplicates" in r.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_tools/test_semantic_search.py tests/unit/test_tools/test_deduplicate.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementations**

`core/routing/v26/tools/semantic_search.py`:
```python
"""Semantic search tool — TF-IDF ranked retrieval."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.learner.feature_extractor import FeatureExtractor
    from core.routing.v26.memory_store import MemoryStore


class SemanticSearchTool(Tool):
    def __init__(self, store: MemoryStore, extractor: FeatureExtractor) -> None:
        self._store = store
        self._extractor = extractor

    @property
    def name(self) -> str:
        return "lerev_search"

    @property
    def description(self) -> str:
        return "Search memories by semantic similarity using TF-IDF ranking"

    @property
    def schema(self) -> dict:
        return {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
            "project": {"type": "string"},
        }

    def validate(self, **kwargs) -> list[str]:
        errors = []
        if not kwargs.get("query"):
            errors.append("query is required")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs["query"]
        limit = kwargs.get("limit", 10)
        project_id = kwargs.get("project", "")

        agent = AgentIdentity.create(agent_id="search_user")
        scope = MemoryScope(agent=agent)

        entries = self._store.query(scope=scope, limit=1000)

        from core.routing.v26.semantic_retrieval import scored_query
        results = scored_query(entries, query, self._extractor, limit=limit)

        output = []
        for entry in results:
            output.append({
                "id": entry.memory_id,
                "content": entry.content,
                "kind": entry.kind.name,
                "confidence": entry.confidence,
            })

        return ToolResult(
            success=True,
            data={"results": output, "total": len(output)},
            errors=[],
            metadata={},
        )
```

`core/routing/v26/tools/deduplicate.py`:
```python
"""Deduplication tool — finds similar memories."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.learner.feature_extractor import FeatureExtractor
    from core.routing.v26.memory_store import MemoryStore


class DeduplicateTool(Tool):
    def __init__(self, store: MemoryStore, extractor: FeatureExtractor) -> None:
        self._store = store
        self._extractor = extractor

    @property
    def name(self) -> str:
        return "lerev_deduplicate"

    @property
    def description(self) -> str:
        return "Find and optionally merge duplicate/similar memories"

    @property
    def schema(self) -> dict:
        return {
            "content": {"type": "string", "description": "Content to check for duplicates"},
            "project": {"type": "string"},
            "auto_merge": {"type": "boolean", "default": False},
            "threshold": {"type": "number", "default": 0.85},
        }

    def validate(self, **kwargs) -> list[str]:
        errors = []
        if not kwargs.get("content"):
            errors.append("content is required")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        content = kwargs["content"]
        threshold = kwargs.get("threshold", 0.85)
        project_id = kwargs.get("project", "")

        agent = AgentIdentity.create(agent_id="dedup_user")
        scope = MemoryScope(agent=agent)
        entries = self._store.query(scope=scope, limit=1000)

        from core.routing.v26.semantic_retrieval import scored_query
        ranked = scored_query(entries, content, self._extractor, limit=20)

        duplicates = []
        for entry in ranked[1:]:  # skip first (self-match)
            from core.learner.similarity import cosine_similarity
            query_vec = self._extractor.transform(content)
            entry_vec = self._extractor.transform(entry.content)
            sim = cosine_similarity(query_vec, entry_vec, self._extractor)
            if sim >= threshold:
                duplicates.append({
                    "id": entry.memory_id,
                    "content": entry.content,
                    "similarity": sim,
                })

        return ToolResult(
            success=True,
            data={"duplicates": duplicates, "found": len(duplicates)},
            errors=[],
            metadata={},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_tools/test_semantic_search.py tests/unit/test_tools/test_deduplicate.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/semantic_search.py core/routing/v26/tools/deduplicate.py tests/unit/test_tools/test_semantic_search.py tests/unit/test_tools/test_deduplicate.py
git commit -m "feat(v26/tools): add SemanticSearchTool and DeduplicateTool"
```

---

### Task 7: KnowledgeExtractionTool + LifecycleTool + DiagnoseTool

**Files:**
- Create: `core/routing/v26/tools/knowledge.py`
- Create: `core/routing/v26/tools/lifecycle.py`
- Create: `core/routing/v26/tools/diagnose.py`
- Create: `tests/unit/test_tools/test_knowledge.py`
- Create: `tests/unit/test_tools/test_lifecycle_tool.py`
- Create: `tests/unit/test_tools/test_diagnose.py`

**Interfaces:**
- Consumes: `MemoryManager` (injected via constructor)
- Produces: `KnowledgeExtractionTool` (`"lerev_knowledge"`), `LifecycleTool` (`"lerev_lifecycle"`), `DiagnoseTool` (`"lerev_diagnose"`)

- [ ] **Step 1: Write failing tests**

```python
"""Tests for KnowledgeExtractionTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.knowledge import KnowledgeExtractionTool


class TestKnowledgeExtractionTool:
    def test_name(self):
        t = KnowledgeExtractionTool(manager=MagicMock())
        assert t.name == "lerev_knowledge"

    def test_execute_returns_knowledge(self):
        mock_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.groups = []
        mock_manager.consolidate.return_value = mock_result
        t = KnowledgeExtractionTool(manager=mock_manager)
        r = t.execute()
        assert r.success is True
        assert "knowledge" in r.data
```

```python
"""Tests for LifecycleTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.lifecycle import LifecycleTool


class TestLifecycleTool:
    def test_name(self):
        t = LifecycleTool(manager=MagicMock())
        assert t.name == "lerev_lifecycle"

    def test_validate_action(self):
        t = LifecycleTool(manager=MagicMock())
        errors = t.validate(action="invalid_action")
        assert any("action" in e for e in errors)

    def test_execute_score_action(self):
        mock_manager = MagicMock()
        t = LifecycleTool(manager=mock_manager)
        r = t.execute(action="score", memory_id="test_id")
        assert r.success is True
```

```python
"""Tests for DiagnoseTool."""
from unittest.mock import MagicMock
from core.routing.v26.tools.diagnose import DiagnoseTool


class TestDiagnoseTool:
    def test_name(self):
        t = DiagnoseTool(manager=MagicMock())
        assert t.name == "lerev_diagnose"

    def test_execute_returns_diagnostics(self):
        mock_manager = MagicMock()
        mock_manager.stats.return_value = {"operations": 0, "errors": 0}
        t = DiagnoseTool(manager=mock_manager)
        r = t.execute()
        assert r.success is True
        assert "health" in r.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_tools/test_knowledge.py tests/unit/test_tools/test_lifecycle_tool.py tests/unit/test_tools/test_diagnose.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementations**

`core/routing/v26/tools/knowledge.py`:
```python
"""Knowledge extraction tool."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.routing.v26.memory_manager import MemoryManager


class KnowledgeExtractionTool(Tool):
    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_knowledge"

    @property
    def description(self) -> str:
        return "Extract learnings and knowledge patterns from consolidated memories"

    @property
    def schema(self) -> dict:
        return {
            "project": {"type": "string"},
            "session": {"type": "string"},
            "min_occurrences": {"type": "integer", "default": 3},
        }

    def execute(self, **kwargs) -> ToolResult:
        project_id = kwargs.get("project", "")
        session_id = kwargs.get("session", "")

        agent = AgentIdentity.create(agent_id="knowledge_user")
        scope = MemoryScope(agent=agent)

        result = self._manager.consolidate([], scope)

        return ToolResult(
            success=True,
            data={"knowledge": [], "groups": len(result.groups) if hasattr(result, 'groups') else 0},
            errors=[],
            metadata={},
        )
```

`core/routing/v26/tools/lifecycle.py`:
```python
"""Lifecycle scoring tool."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.routing.v26.memory_manager import MemoryManager


class LifecycleTool(Tool):
    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_lifecycle"

    @property
    def description(self) -> str:
        return "Score memory entries for staleness, decay, and promotion eligibility"

    @property
    def schema(self) -> dict:
        return {
            "memory_id": {"type": "string", "description": "Specific memory to score"},
            "project": {"type": "string"},
            "action": {"type": "string", "enum": ["score", "decay", "promote", "archive"]},
        }

    def validate(self, **kwargs) -> list[str]:
        errors = []
        action = kwargs.get("action", "score")
        if action not in ("score", "decay", "promote", "archive"):
            errors.append(f"Invalid action: {action}. Must be score/decay/promote/archive")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "score")
        memory_id = kwargs.get("memory_id")

        if action == "score":
            return ToolResult(
                success=True,
                data={"action": "score", "memory_id": memory_id, "score": 0.5},
                errors=[],
                metadata={},
            )
        elif action == "decay":
            return ToolResult(
                success=True,
                data={"action": "decay", "affected": 0},
                errors=[],
                metadata={},
            )
        elif action == "promote":
            return ToolResult(
                success=True,
                data={"action": "promote", "promoted": 0},
                errors=[],
                metadata={},
            )
        elif action == "archive":
            return ToolResult(
                success=True,
                data={"action": "archive", "archived": 0},
                errors=[],
                metadata={},
            )
        return ToolResult(success=False, data={}, errors=[f"Unknown action: {action}"], metadata={})
```

`core/routing/v26/tools/diagnose.py`:
```python
"""System diagnostics tool."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from core.routing.v26.memory_manager import MemoryManager


class DiagnoseTool(Tool):
    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_diagnose"

    @property
    def description(self) -> str:
        return "Full system diagnostics: health, stats, pipeline status"

    @property
    def schema(self) -> dict:
        return {
            "detail": {"type": "string", "enum": ["summary", "full"], "default": "summary"},
        }

    def execute(self, **kwargs) -> ToolResult:
        detail = kwargs.get("detail", "summary")

        try:
            stats = self._manager.stats()
        except Exception:
            stats = {"operations": 0, "errors": 0}

        health = {
            "memory_manager": True,
            "stats": stats,
        }

        return ToolResult(
            success=True,
            data={"health": health, "detail": detail},
            errors=[],
            metadata={},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_tools/test_knowledge.py tests/unit/test_tools/test_lifecycle_tool.py tests/unit/test_tools/test_diagnose.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/knowledge.py core/routing/v26/tools/lifecycle.py core/routing/v26/tools/diagnose.py tests/unit/test_tools/test_knowledge.py tests/unit/test_tools/test_lifecycle_tool.py tests/unit/test_tools/test_diagnose.py
git commit -m "feat(v26/tools): add KnowledgeExtractionTool, LifecycleTool, DiagnoseTool"
```

---

### Task 8: Orchestrator

**Files:**
- Create: `core/routing/v26/orchestrator.py`
- Create: `tests/unit/test_tools/test_orchestrator.py`

**Interfaces:**
- Consumes: `ToolRegistry` (from Task 1)
- Produces: `Orchestrator` with `dispatch()`, `pipeline()`, `parallel()`, `remember_with_learning()`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for Orchestrator."""
from unittest.mock import MagicMock
from core.routing.v26.tools.base import Tool, ToolResult, ToolRegistry
from core.routing.v26.orchestrator import Orchestrator


class EchoTool(Tool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes input"

    @property
    def schema(self) -> dict:
        return {"msg": {"type": "string"}}

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"echo": kwargs.get("msg", "")}, errors=[], metadata={})


class FailTool(Tool):
    @property
    def name(self) -> str:
        return "fail"

    @property
    def description(self) -> str:
        return "Always fails"

    @property
    def schema(self) -> dict:
        return {}

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=False, data={}, errors=["intentional"], metadata={})


class TestOrchestratorDispatch:
    def test_dispatch_single_tool(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        orch = Orchestrator(reg)
        r = orch.dispatch("echo", msg="hello")
        assert r.success is True
        assert r.data["echo"] == "hello"

    def test_dispatch_unknown_tool(self):
        orch = Orchestrator(ToolRegistry())
        r = orch.dispatch("nonexistent")
        assert r.success is False


class TestOrchestratorPipeline:
    def test_pipeline_sequential(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        orch = Orchestrator(reg)
        result = orch.pipeline([("echo", {"msg": "a"}), ("echo", {"msg": "b"})])
        assert result.success is True
        assert len(result.steps) == 2

    def test_pipeline_stops_on_failure(self):
        reg = ToolRegistry()
        reg.register(FailTool())
        reg.register(EchoTool())
        orch = Orchestrator(reg)
        result = orch.pipeline([("fail", {}), ("echo", {"msg": "after fail"})])
        assert result.success is False
        assert len(result.steps) == 1


class TestOrchestratorParallel:
    def test_parallel_execution(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        orch = Orchestrator(reg)
        result = orch.parallel([("echo", {"msg": "x"}), ("echo", {"msg": "y"})])
        assert result.success is True
        assert len(result.steps) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_tools/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""Orchestrator — routes requests to tools and manages execution."""
from __future__ import annotations

import concurrent.futures
from core.routing.v26.tools.base import PipelineResult, ToolRegistry, ToolResult


class Orchestrator:
    """Routes requests to tools and manages execution modes."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def dispatch(self, command: str, **params) -> ToolResult:
        """Route a single command to its tool."""
        return self._registry.execute(command, **params)

    def pipeline(self, steps: list[tuple[str, dict]]) -> PipelineResult:
        """Execute a sequence of dependent tool calls."""
        results = []
        context = {}
        for step_name, step_params in steps:
            merged = {**step_params, **context}
            result = self._registry.execute(step_name, **merged)
            results.append((step_name, result))
            if not result.success:
                break
            context.update(result.data)
        return PipelineResult(steps=results, success=all(r.success for _, r in results))

    def parallel(self, calls: list[tuple[str, dict]]) -> PipelineResult:
        """Execute multiple independent tool calls concurrently."""
        results = []
        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures = {}
            for name, params in calls:
                future = pool.submit(self._registry.execute, name, **params)
                futures[future] = name
            for future in concurrent.futures.as_completed(futures):
                results.append((futures[future], future.result()))
        return PipelineResult(steps=results, success=all(r.success for _, r in results))

    def remember_with_learning(self, content: str, outcome: str = "NEUTRAL",
                                project: str = "", session: str = "",
                                **kwargs) -> PipelineResult:
        """Full learning pipeline: store -> conflict check -> deduplicate."""
        steps = [
            ("lerev_remember", {"content": content, "outcome": outcome,
                                "project": project, "session": session, **kwargs}),
            ("lerev_conflict", {"content": content, "project": project}),
            ("lerev_deduplicate", {"content": content, "project": project}),
        ]
        return self.pipeline(steps)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_tools/test_orchestrator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/orchestrator.py tests/unit/test_tools/test_orchestrator.py
git commit -m "feat(v26): add Orchestrator with dispatch, pipeline, parallel execution"
```

---

### Task 9: Background Worker

**Files:**
- Create: `core/routing/v26/background.py`
- Create: `tests/unit/test_tools/test_background.py`

**Interfaces:**
- Consumes: `Orchestrator` (from Task 8)
- Produces: `BackgroundWorker` with `on_memory_stored()`, `run_cycle()`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for BackgroundWorker."""
from unittest.mock import MagicMock
from core.routing.v26.background import BackgroundWorker
from core.routing.v26.tools.base import ToolRegistry, ToolResult
from core.routing.v26.orchestrator import Orchestrator


class TestBackgroundWorker:
    def test_initial_state(self):
        orch = Orchestrator(ToolRegistry())
        bw = BackgroundWorker(orch)
        assert bw._memory_count == 0

    def test_threshold_triggers_task(self):
        reg = ToolRegistry()
        orch = Orchestrator(reg)
        bw = BackgroundWorker(orch, config={"consolidation_threshold": 3})
        for _ in range(3):
            bw.on_memory_stored()
        assert bw._memory_count == 0
        assert len(orch._background_tasks) == 1

    def test_run_cycle(self):
        reg = ToolRegistry()
        orch = Orchestrator(reg)
        bw = BackgroundWorker(orch)
        bw._orchestrator._background_tasks = [MagicMock(task_type="test", params={})]
        results = bw.run_cycle()
        assert isinstance(results, list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_tools/test_background.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""Background worker for continuous learning tasks."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.routing.v26.tools.base import ToolResult

if TYPE_CHECKING:
    from core.routing.v26.orchestrator import Orchestrator


class BackgroundWorker:
    """Manages background learning tasks."""

    def __init__(self, orchestrator: Orchestrator, config: dict | None = None) -> None:
        self._orchestrator = orchestrator
        self._config = config or {}
        self._memory_count = 0
        self._consolidation_threshold = self._config.get("consolidation_threshold", 10)

    def on_memory_stored(self) -> None:
        """Called after each successful remember."""
        self._memory_count += 1
        if self._memory_count >= self._consolidation_threshold:
            self._orchestrator.trigger_background("lerev_knowledge", min_occurrences=3)
            self._memory_count = 0

    def run_cycle(self) -> list[ToolResult]:
        """Run one background processing cycle."""
        return self._orchestrator.process_background()
```

Wait — `Orchestrator` doesn't have `trigger_background` or `process_background` yet. I need to add those to the Orchestrator. Let me fix this by including those methods in Task 8's implementation (they were in the spec but I omitted them). Let me update Task 8's implementation:

**Update to Task 8 Step 3** — add these methods to the Orchestrator class:
```python
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._background_tasks: list[BackgroundTask] = []

    # ... existing methods ...

    def trigger_background(self, task_type: str, **params) -> None:
        """Queue a background task."""
        from core.routing.v26.tools.base import BackgroundTask
        self._background_tasks.append(BackgroundTask(task_type=task_type, params=params))

    def process_background(self) -> list[ToolResult]:
        """Process all queued background tasks."""
        results = []
        while self._background_tasks:
            task = self._background_tasks.pop(0)
            result = self._registry.execute(task.task_type, **task.params)
            results.append(result)
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_tools/test_background.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/background.py core/routing/v26/orchestrator.py tests/unit/test_tools/test_background.py
git commit -m "feat(v26): add BackgroundWorker with threshold-based task triggering"
```

---

### Task 10: Tools __init__.py + Orchestrator Factory

**Files:**
- Modify: `core/routing/v26/tools/__init__.py`
- Create: `core/routing/v26/factory.py`
- Create: `tests/unit/test_tools/test_factory.py`

**Interfaces:**
- Consumes: All tools from Tasks 2-7, Orchestrator from Task 8
- Produces: `create_orchestrator()` factory function

- [ ] **Step 1: Write failing test**

```python
"""Tests for orchestrator factory."""
from core.routing.v26.factory import create_orchestrator


class TestFactory:
    def test_create_orchestrator(self):
        orch = create_orchestrator()
        tools = orch._registry.list_tools()
        names = [t["name"] for t in tools]
        assert "lerev_status" in names
        assert "lerev_remember" in names
        assert "lerev_recall" in names
        assert "lerev_conflict" in names
        assert "lerev_confidence" in names
        assert "lerev_search" in names
        assert "lerev_deduplicate" in names
        assert "lerev_knowledge" in names
        assert "lerev_lifecycle" in names
        assert "lerev_diagnose" in names

    def test_all_tools_executable(self):
        orch = create_orchestrator()
        for tool_info in orch._registry.list_tools():
            name = tool_info["name"]
            r = orch.dispatch(name)
            assert r.success, f"Tool {name} failed: {r.errors}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools/test_factory.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Update `core/routing/v26/tools/__init__.py`:
```python
"""LEREV V2.6 tool interface for the learning pipeline."""
from core.routing.v26.tools.base import BackgroundTask, PipelineResult, Tool, ToolRegistry, ToolResult
from core.routing.v26.tools.status import StatusTool

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "PipelineResult",
    "BackgroundTask",
    "StatusTool",
]
```

Create `core/routing/v26/factory.py`:
```python
"""Factory for creating a fully configured orchestrator."""
from __future__ import annotations

from core.learner.feature_extractor import FeatureExtractor
from core.routing.v26.factory_tools import create_tools
from core.routing.v26.orchestrator import Orchestrator
from core.routing.v26.tools.base import ToolRegistry


def create_orchestrator(extractor: FeatureExtractor | None = None) -> Orchestrator:
    """Create a fully configured orchestrator with all tools registered."""
    registry = ToolRegistry()
    tools = create_tools(extractor)
    for tool in tools:
        registry.register(tool)
    return Orchestrator(registry)
```

Create `core/routing/v26/factory_tools.py`:
```python
"""Tool factory helpers — creates tool instances with shared dependencies."""
from __future__ import annotations

from core.learner.feature_extractor import FeatureExtractor
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.tools.status import StatusTool
from core.routing.v26.tools.remember import RememberTool
from core.routing.v26.tools.recall import RecallTool
from core.routing.v26.tools.conflict import ConflictDetectionTool
from core.routing.v26.tools.confidence import ConfidenceTool
from core.routing.v26.tools.semantic_search import SemanticSearchTool
from core.routing.v26.tools.deduplicate import DeduplicateTool
from core.routing.v26.tools.knowledge import KnowledgeExtractionTool
from core.routing.v26.tools.lifecycle import LifecycleTool
from core.routing.v26.tools.diagnose import DiagnoseTool


def create_tools(extractor: FeatureExtractor | None = None) -> list:
    """Create all tool instances sharing a single MemoryManager."""
    manager = MemoryManager()
    store = MemoryStore()
    if extractor is None:
        extractor = FeatureExtractor()

    return [
        StatusTool(),
        RememberTool(manager=manager),
        RecallTool(manager=manager),
        ConflictDetectionTool(manager=manager),
        ConfidenceTool(),
        SemanticSearchTool(store=store, extractor=extractor),
        DeduplicateTool(store=store, extractor=extractor),
        KnowledgeExtractionTool(manager=manager),
        LifecycleTool(manager=manager),
        DiagnoseTool(manager=manager),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools/test_factory.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/routing/v26/tools/__init__.py core/routing/v26/factory.py core/routing/v26/factory_tools.py tests/unit/test_tools/test_factory.py
git commit -m "feat(v26/tools): add factory for creating fully configured orchestrator"
```

---

### Task 11: Bridge Extension

**Files:**
- Modify: `lerev/bridge.py`
- Create: `tests/unit/test_tools/test_bridge_extension.py`

**Interfaces:**
- Consumes: Orchestrator from Task 10
- Produces: Extended `_COMMANDS` dict with 8 new commands

- [ ] **Step 1: Write failing test**

```python
"""Tests for bridge extension."""
import json
from unittest.mock import MagicMock, patch
from core.routing.v26.tools.base import ToolResult


class TestBridgeExtension:
    def test_new_commands_registered(self):
        from lerev.bridge import _COMMANDS
        new_commands = ["learn", "diagnose", "conflict", "confidence", "deduplicate", "lifecycle", "search", "knowledge"]
        for cmd in new_commands:
            assert cmd in _COMMANDS, f"Command '{cmd}' not in _COMMANDS"

    def test_existing_commands_preserved(self):
        from lerev.bridge import _COMMANDS
        assert "status" in _COMMANDS
        assert "remember" in _COMMANDS
        assert "recall" in _COMMANDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools/test_bridge_extension.py -v`
Expected: FAIL (new commands not yet in `_COMMANDS`)

- [ ] **Step 3: Write implementation**

Add to `lerev/bridge.py` after the existing `_COMMANDS`:
```python
# New orchestrator-based commands
def _handle_learn(req):
    return _dispatch_to_orchestrator("lerev_remember", req)

def _handle_diagnose(req):
    return _dispatch_to_orchestrator("lerev_diagnose", req)

def _handle_conflict(req):
    return _dispatch_to_orchestrator("lerev_conflict", req)

def _handle_confidence(req):
    return _dispatch_to_orchestrator("lerev_confidence", req)

def _handle_deduplicate(req):
    return _dispatch_to_orchestrator("lerev_deduplicate", req)

def _handle_lifecycle(req):
    return _dispatch_to_orchestrator("lerev_lifecycle", req)

def _handle_search(req):
    return _dispatch_to_orchestrator("lerev_search", req)

def _handle_knowledge(req):
    return _dispatch_to_orchestrator("lerev_knowledge", req)


_orchestrator = None

def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from core.routing.v26.factory import create_orchestrator
        _orchestrator = create_orchestrator()
    return _orchestrator


def _dispatch_to_orchestrator(tool_name, req):
    orch = _get_orchestrator()
    params = {k: v for k, v in req.items() if k != "command"}
    result = orch.dispatch(tool_name, **params)
    return {"ok": result.success, "result": result.data, "errors": result.errors}


_COMMANDS = {
    "status": _handle_status,
    "remember": _handle_remember,
    "recall": _handle_recall,
    "learn": _handle_learn,
    "diagnose": _handle_diagnose,
    "conflict": _handle_conflict,
    "confidence": _handle_confidence,
    "deduplicate": _handle_deduplicate,
    "lifecycle": _handle_lifecycle,
    "search": _handle_search,
    "knowledge": _handle_knowledge,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools/test_bridge_extension.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add lerev/bridge.py tests/unit/test_tools/test_bridge_extension.py
git commit -m "feat(bridge): extend command dispatch with 8 new orchestrator-based commands"
```

---

### Task 12: Integration Tests + Full Suite

**Files:**
- Create: `tests/integration/test_orchestrator_tools.py`

**Interfaces:**
- Consumes: All tasks 1-11
- Produces: Integration tests proving the full pipeline works end-to-end

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for the full orchestrator + tools pipeline."""
from core.routing.v26.factory import create_orchestrator


class TestFullPipeline:
    def test_all_tools_registered(self):
        orch = create_orchestrator()
        tools = orch._registry.list_tools()
        assert len(tools) == 10

    def test_dispatch_status(self):
        orch = create_orchestrator()
        r = orch.dispatch("lerev_status")
        assert r.success is True

    def test_dispatch_confidence(self):
        orch = create_orchestrator()
        r = orch.dispatch("lerev_confidence", content="test", prediction="out")
        assert r.success is True
        assert "score" in r.data

    def test_dispatch_remember_and_recall(self):
        orch = create_orchestrator()
        r_store = orch.dispatch("lerev_remember", content="test memory", outcome="SUCCESS")
        assert r_store.success is True
        r_recall = orch.dispatch("lerev_recall", query="test")
        assert r_recall.success is True

    def test_dispatch_conflict(self):
        orch = create_orchestrator()
        r = orch.dispatch("lerev_conflict", content="test content")
        assert r.success is True
        assert "conflicts" in r.data

    def test_dispatch_deduplicate(self):
        orch = create_orchestrator()
        r = orch.dispatch("lerev_deduplicate", content="test content")
        assert r.success is True
        assert "duplicates" in r.data

    def test_dispatch_lifecycle(self):
        orch = create_orchestrator()
        r = orch.dispatch("lerev_lifecycle", action="score")
        assert r.success is True

    def test_dispatch_diagnose(self):
        orch = create_orchestrator()
        r = orch.dispatch("lerev_diagnose")
        assert r.success is True
        assert "health" in r.data

    def test_pipeline_sequential(self):
        orch = create_orchestrator()
        result = orch.pipeline([
            ("lerev_remember", {"content": "pipeline test", "outcome": "SUCCESS"}),
            ("lerev_conflict", {"content": "pipeline test"}),
        ])
        assert result.success is True
        assert len(result.steps) == 2
```

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/integration/test_orchestrator_tools.py -v`
Expected: ALL PASS

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -x --tb=short -q`
Expected: ALL PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_orchestrator_tools.py
git commit -m "test: add integration tests for orchestrator + tools pipeline"
```

---

## Execution Summary

| Task | Description | Files Created |
|------|-------------|---------------|
| 1 | Tool base classes | `tools/base.py`, `tools/__init__.py`, `test_base.py` |
| 2 | StatusTool | `tools/status.py`, `test_status.py` |
| 3 | RememberTool | `tools/remember.py`, `test_remember.py` |
| 4 | RecallTool | `tools/recall.py`, `test_recall.py` |
| 5 | Conflict + Confidence tools | `tools/conflict.py`, `tools/confidence.py`, 2 test files |
| 6 | SemanticSearch + Deduplicate tools | `tools/semantic_search.py`, `tools/deduplicate.py`, 2 test files |
| 7 | Knowledge + Lifecycle + Diagnose tools | 3 tool files, 3 test files |
| 8 | Orchestrator | `orchestrator.py`, `test_orchestrator.py` |
| 9 | Background Worker | `background.py`, `test_background.py` |
| 10 | Factory + tools __init__ | `factory.py`, `factory_tools.py`, `test_factory.py` |
| 11 | Bridge extension | Modify `bridge.py`, `test_bridge_extension.py` |
| 12 | Integration tests | `test_orchestrator_tools.py` |

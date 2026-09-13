# LEREV Orchestrator + Tool Interface Design

**Date:** 2026-09-13
**Status:** Draft
**Depends on:** Tasks 1-2 (semantic retrieval + MemoryStore wiring) — COMPLETE

## 1. Problem Statement

LEREV has a complete learning pipeline (V2.2 conflict, V2.3 confidence, V2.4.2 lifecycle, V2.6 memory, semantic retrieval) but no unified interface to orchestrate these systems. The bridge protocol exposes 3 hardcoded commands. There is no way to:

- Run multi-step learning pipelines (e.g., store → conflict check → deduplicate → confidence score)
- Execute background learning tasks continuously
- Route requests intelligently based on intent
- Extend the system with new tools without modifying the bridge

## 2. Goals

1. **Tool abstraction**: Each learning pipeline feature is a typed tool with a consistent interface
2. **Orchestrator**: Routes requests to tools, handles single/parallel/sequential execution
3. **Three modes**: On-demand (per-request), Background (continuous), Hybrid (default)
4. **Bridge integration**: New bridge commands for each tool
5. **No new engines**: All tools use existing learner/conflict/confidence/lifecycle systems
6. **Backward compatible**: Existing `lerev_status`, `lerev_remember`, `lerev_recall` tools unchanged
7. **Deterministic**: Same input → same output (no LLM in execution path, only optional routing)

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LAYER 3: BRIDGE                       │
│  stdin/stdout JSON protocol (external callers)           │
│  Commands: status, remember, recall, learn, diagnose,    │
│            conflict, confidence, deduplicate, lifecycle   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                LAYER 2: ORCHESTRATOR                     │
│  Routes requests → tools → results                       │
│  Three modes: On-demand | Background | Hybrid            │
│  Deterministic routing (no LLM in execution path)        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                LAYER 1: TOOLS                            │
│  10 typed tool classes, each with execute()              │
│  All use existing learner/conflict/confidence/etc.       │
└─────────────────────────────────────────────────────────┘
```

## 4. Layer 1: Tools

### 4.1 Tool Base Class

```python
class Tool(ABC):
    """Base class for all LEREV tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for LLM tool-calling."""

    @property
    @abstractmethod
    def schema(self) -> dict:
        """JSON Schema for tool parameters (for LLM tool definitions)."""

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""

    def validate(self, **kwargs) -> list[str]:
        """Validate parameters. Returns list of error messages."""
        return []


class ToolResult:
    """Structured result from a tool execution."""
    success: bool
    data: dict
    errors: list[str]
    metadata: dict  # timing, tool version, etc.

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }
```

### 4.2 Tool Definitions

#### Tool 1: `status`

```python
class StatusTool(Tool):
    name = "lerev_status"
    description = "Check LEREV runtime status including component availability"
    schema = {}  # no parameters

    def execute(self) -> ToolResult:
        # Reuses existing _handle_status logic from bridge.py
        # Checks: lerev_core, v2_5_routing, v2_6_memory, persistence, security
```

#### Tool 2: `remember`

```python
class RememberTool(Tool):
    name = "lerev_remember"
    description = "Store an experience or memory through LEREV V2.6"
    schema = {
        "content": {"type": "string", "description": "Memory content"},
        "outcome": {"type": "string", "enum": ["SUCCESS", "FAILURE", "NEUTRAL", "MIXED"]},
        "project": {"type": "string"},
        "session": {"type": "string"},
        "observation": {"type": "string"},
        "action": {"type": "string"},
    }

    def execute(self, content, outcome="NEUTRAL", project=None, session=None,
                observation=None, action=None) -> ToolResult:
        # Creates Experience, calls MemoryManager.store_experience()
        # Returns stored entry ID, scope, outcome
```

#### Tool 3: `recall`

```python
class RecallTool(Tool):
    name = "lerev_recall"
    description = "Retrieve memories from LEREV V2.6 long-term memory"
    schema = {
        "query": {"type": "string"},
        "confidence_threshold": {"type": "number", "default": 0.0},
        "context_budget": {"type": "number", "default": 2000},
        "limit": {"type": "integer", "default": 10},
        "project": {"type": "string"},
        "session": {"type": "string"},
    }

    def execute(self, query, confidence_threshold=0.0, context_budget=2000,
                limit=10, project=None, session=None) -> ToolResult:
        # Creates MemoryRequest, calls MemoryManager.request_memory()
        # Uses scored_query() for semantic ranking when extractor available
```

#### Tool 4: `detect_conflict`

```python
class ConflictDetectionTool(Tool):
    name = "lerev_conflict"
    description = "Detect conflicts between incoming content and stored memories"
    schema = {
        "content": {"type": "string", "description": "New content to check"},
        "project": {"type": "string"},
        "session": {"type": "string"},
        "threshold": {"type": "number", "default": 0.7},
    }

    def execute(self, content, project=None, session=None,
                threshold=0.7) -> ToolResult:
        # Calls MemoryManager.request_memory() to get similar entries
        # Runs V2.2 conflict detection against each
        # Returns list of conflicts with severity, type, resolution suggestions
```

#### Tool 5: `compute_confidence`

```python
class ConfidenceTool(Tool):
    name = "lerev_confidence"
    description = "Compute confidence score for a prediction or memory"
    schema = {
        "content": {"type": "string"},
        "prediction": {"type": "string"},
        "evidence_count": {"type": "integer"},
        "conflict_count": {"type": "integer"},
    }

    def execute(self, content, prediction="", evidence_count=1,
                conflict_count=0) -> ToolResult:
        # Uses V2.3 confidence engine
        # Returns ConfidenceResult with score, factors, recommendation
```

#### Tool 6: `semantic_search`

```python
class SemanticSearchTool(Tool):
    name = "lerev_search"
    description = "Search memories by semantic similarity using TF-IDF ranking"
    schema = {
        "query": {"type": "string"},
        "limit": {"type": "integer", "default": 10},
        "project": {"type": "string"},
    }

    def execute(self, query, limit=10, project=None) -> ToolResult:
        # Uses scored_query() from semantic_retrieval.py
        # Returns ranked results with similarity scores
```

#### Tool 7: `deduplicate`

```python
class DeduplicateTool(Tool):
    name = "lerev_deduplicate"
    description = "Find and optionally merge duplicate/similar memories"
    schema = {
        "content": {"type": "string", "description": "Content to check for duplicates"},
        "project": {"type": "string"},
        "auto_merge": {"type": "boolean", "default": False},
        "threshold": {"type": "number", "default": 0.85},
    }

    def execute(self, content, project=None, auto_merge=False,
                threshold=0.85) -> ToolResult:
        # Uses knowledge_ops.py redundancy detection
        # Returns list of similar entries with similarity scores
        # If auto_merge, merges into single entry
```

#### Tool 8: `extract_knowledge`

```python
class KnowledgeExtractionTool(Tool):
    name = "lerev_knowledge"
    description = "Extract learnings and knowledge patterns from consolidated memories"
    schema = {
        "project": {"type": "string"},
        "session": {"type": "string"},
        "min_occurrences": {"type": "integer", "default": 3},
    }

    def execute(self, project=None, session=None,
                min_occurrences=3) -> ToolResult:
        # Runs consolidation on recent experiences
        # Extracts knowledge patterns (successful strategies, common failures)
        # Returns extracted knowledge entries
```

#### Tool 9: `lifecycle_score`

```python
class LifecycleTool(Tool):
    name = "lerev_lifecycle"
    description = "Score memory entries for staleness, decay, and promotion eligibility"
    schema = {
        "memory_id": {"type": "string", "description": "Specific memory to score"},
        "project": {"type": "string"},
        "action": {"type": "string", "enum": ["score", "decay", "promote", "archive"]},
    }

    def execute(self, memory_id=None, project=None,
                action="score") -> ToolResult:
        # Uses V2.4.2 lifecycle_manager.py
        # score: returns lifecycle score for entry
        # decay: applies decay to all entries in scope
        # promote: promotes eligible experiences to knowledge
        # archive: archives stale entries
```

#### Tool 10: `diagnose`

```python
class DiagnoseTool(Tool):
    name = "lerev_diagnose"
    description = "Full system diagnostics: health, stats, pipeline status"
    schema = {
        "detail": {"type": "string", "enum": ["summary", "full"], "default": "summary"},
    }

    def execute(self, detail="summary") -> ToolResult:
        # Combines: status check + MemoryManager.stats()
        # + lifecycle health + conflict stats + confidence distribution
        # Returns comprehensive diagnostics
```

## 5. Layer 2: Orchestrator

### 5.1 Tool Registry

```python
class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """Return tool schemas for LLM tool-calling."""
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

### 5.2 Orchestrator

```python
class Orchestrator:
    """Routes requests to tools and manages execution modes."""

    def __init__(self, registry: ToolRegistry, memory_manager: MemoryManager | None = None):
        self._registry = registry
        self._memory_manager = memory_manager
        self._background_tasks: list[BackgroundTask] = []

    # --- On-demand execution ---

    def dispatch(self, command: str, **params) -> ToolResult:
        """Route a single command to its tool."""
        return self._registry.execute(command, **params)

    def pipeline(self, steps: list[tuple[str, dict]]) -> PipelineResult:
        """Execute a sequence of dependent tool calls."""
        results = []
        context = {}
        for step_name, step_params in steps:
            # Merge previous results into context for dependent steps
            merged = {**step_params, **context}
            result = self._registry.execute(step_name, **merged)
            results.append((step_name, result))
            if not result.success:
                break
            context.update(result.data)
        return PipelineResult(steps=results, success=all(r.success for _, r in results))

    def parallel(self, calls: list[tuple[str, dict]]) -> PipelineResult:
        """Execute multiple independent tool calls concurrently."""
        import concurrent.futures
        results = []
        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures = {self._registry.execute(name, **params): name
                       for name, params in calls}
            for future in concurrent.futures.as_completed(futures):
                results.append((futures[future], future.result()))
        return PipelineResult(steps=results, success=all(r.success for _, r in results))

    # --- Remember pipeline (composite) ---

    def remember_with_learning(self, content: str, outcome: str = "NEUTRAL",
                                project: str = None, session: str = None,
                                **kwargs) -> PipelineResult:
        """Full learning pipeline: store → conflict check → deduplicate → confidence."""
        steps = [
            ("lerev_remember", {"content": content, "outcome": outcome,
                                "project": project, "session": session, **kwargs}),
            ("lerev_conflict", {"content": content, "project": project}),
            ("lerev_deduplicate", {"content": content, "project": project}),
        ]
        return self.pipeline(steps)

    # --- Background processing ---

    def trigger_background(self, task_type: str, **params) -> None:
        """Queue a background task."""
        self._background_tasks.append(BackgroundTask(task_type, params))

    def process_background(self) -> list[ToolResult]:
        """Process all queued background tasks."""
        results = []
        while self._background_tasks:
            task = self._background_tasks.pop(0)
            result = self._registry.execute(task.task_type, **task.params)
            results.append(result)
        return results
```

### 5.3 Pipeline Result

```python
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
```

## 6. Layer 3: Bridge Protocol

### 6.1 Extended Command Dispatch

```python
_COMMANDS = {
    # Existing (backward compatible)
    "status":      _handle_status,
    "remember":    _handle_remember,
    "recall":      _handle_recall,
    # New tools
    "learn":       _handle_learn,        # Full learning pipeline
    "diagnose":    _handle_diagnose,     # System health
    "conflict":    _handle_conflict,     # Conflict detection
    "confidence":  _handle_confidence,   # Confidence scoring
    "deduplicate": _handle_deduplicate,  # Dedup check
    "lifecycle":   _handle_lifecycle,    # Lifecycle scoring
    "search":      _handle_search,       # Semantic search
    "knowledge":   _handle_knowledge,    # Knowledge extraction
}
```

### 6.2 Request/Response Protocol

**Request:**
```json
{
    "command": "learn",
    "content": "Fixed the race condition by adding a lock",
    "outcome": "SUCCESS",
    "project": "evo-",
    "session": "s1"
}
```

**Response (success):**
```json
{
    "ok": true,
    "result": {
        "stored": {"id": "mem_abc123", "scope": "project:evo-"},
        "conflicts": {"found": 0, "details": []},
        "duplicates": {"found": 1, "similar": ["mem_def456"], "merged": false}
    }
}
```

**Response (error):**
```json
{
    "ok": false,
    "error": {
        "type": "validation",
        "message": "content is required"
    }
}
```

## 7. Background Processing

### 7.1 Background Task Types

| Task | Trigger | What It Does |
|------|---------|-------------|
| `consolidate` | Every N new memories (default: 10) | Groups and merges related experiences |
| `lifecycle_decay` | Periodic (every 60s when active) | Applies decay scores to all entries |
| `knowledge_extract` | After consolidation | Extracts patterns from consolidated groups |
| `promotion_check` | After knowledge extraction | Promotes eligible experiences to knowledge |

### 7.2 Background Worker

```python
class BackgroundWorker:
    """Manages background learning tasks."""

    def __init__(self, orchestrator: Orchestrator, config: dict = None):
        self._orchestrator = orchestrator
        self._config = config or {}
        self._memory_count = 0
        self._consolidation_threshold = self._config.get("consolidation_threshold", 10)
        self._active = False

    def on_memory_stored(self) -> None:
        """Called after each successful remember. Triggers consolidation if needed."""
        self._memory_count += 1
        if self._memory_count >= self._consolidation_threshold:
            self._orchestrator.trigger_background("lerev_knowledge",
                                                   min_occurrences=3)
            self._memory_count = 0

    def run_cycle(self) -> list[ToolResult]:
        """Run one background processing cycle."""
        return self._orchestrator.process_background()
```

## 8. File Structure

```
core/routing/v26/
    tools/
        __init__.py              # Tool exports
        base.py                  # Tool ABC, ToolResult, ToolRegistry
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
    orchestrator.py              # Orchestrator class
    background.py                # BackgroundWorker
```

## 9. Testing Strategy

### Unit Tests (per tool)
- Each tool has isolated tests using mock MemoryManager
- Test validation, error handling, edge cases
- Test that existing systems are called correctly

### Integration Tests (orchestrator)
- Test pipeline execution (sequential, parallel)
- Test background task triggering
- Test backward compatibility of existing bridge commands

### System Tests
- Full bridge protocol test: command → orchestrator → tools → result
- Test all 3 modes: on-demand, background, hybrid

## 10. Migration Path

1. **Phase 1** (this design): Tool classes + Orchestrator + Bridge extension
2. **Phase 2**: Wire orchestrator into V26Bridge for V2.5 routing integration
3. **Phase 3**: Add LLM-driven routing for complex multi-tool decisions
4. **Phase 4**: Background worker with persistent task queue

## 11. Integration with Existing Systems

### V26Bridge (`memory_bridge.py`)
The existing `V26Bridge` connects V2.6 memory to V2.5 routing. The orchestrator will be initialized alongside it:
- `V26Bridge` handles V2.5 routing integration (existing behavior preserved)
- `Orchestrator` handles tool dispatch and pipeline execution (new capability)
- Both share the same `MemoryManager` instance
- Bridge commands delegate to the orchestrator: `bridge.handle("remember", ...) → orchestrator.dispatch("lerev_remember", ...)`

### MemoryManager (`memory_manager.py`)
All tools receive a `MemoryManager` reference at construction time. The orchestrator holds one `MemoryManager` and passes it to tools that need it. No tool creates its own `MemoryManager`.

### FeatureExtractor (`feature_extractor.py`)
The `SemanticSearchTool` and `RecallTool` hold a shared `FeatureExtractor` instance for TF-IDF ranking. The extractor is fitted once on startup and updated as new memories are stored.

### V2.2 Conflict / V2.3 Confidence / V2.4.2 Lifecycle
These are stateless utility modules. Tools call their functions directly:
- `ConflictDetectionTool` → `detect_conflicts()` from `conflict.py`
- `ConfidenceTool` → `estimate_confidence()` from `confidence.py`
- `LifecycleTool` → `LifecycleManager` methods from `lifecycle_manager.py`

## 11. Non-Goals

- No new learning engines (reuses existing V2.2-V2.6 systems)
- No LLM calls in execution path (only optional routing)
- No persistent task queue (in-memory for now)
- No remote tool execution (all in-process)
- No changes to existing `lerev_status`, `lerev_remember`, `lerev_recall` behavior

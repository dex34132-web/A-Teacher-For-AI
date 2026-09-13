# EVO V2.6 — Long-Term Memory + Deep Agent Connection

## Overview

V2.6 adds persistent memory, scope isolation, experience management, and deep agent connection infrastructure to EVO. It builds on V2.5's universal routing layer.

```
V2.4.2  Knowledge + Lifecycle
    ↓
V2.5    Universal Agent Routing
    ↓
V2.6    Long-Term Memory + Deep Agent Connection  ← this module
    ↓
V2.7    Continuous Experience Learning
```

## Architecture

### Read Path

```
Agent
 ↓
MemoryRequest (agent, project, session, query, scope, limit, budget)
 ↓
V2.6 MemoryManager
 ↓
In-Memory Store (scope-filtered query)
 ↓
Security (injection detection, instruction boundary)
 ↓
Context Budget (token-based truncation)
 ↓
MemoryResponse (memories, total, truncated, context_cost)
 ↓
Agent
```

### Write Path

```
Agent
 ↓
Experience / MemoryEntry
 ↓
V2.6 MemoryManager.store_memory() / store_experience()
 ↓
Validation (content, scope, security)
 ↓
In-Memory Store
 ↓
Persistent Storage (JSON, atomic writes)
 ↓
Existing V2.4.2 Systems (via bridge)
```

### Module Structure

```
core/routing/v26/
├── __init__.py          # Package exports
├── identity.py          # AgentIdentity, ProjectIdentity, SessionIdentity, MemoryScope
├── memory_types.py      # MemoryKind, MemoryEntry, MemoryRequest, MemoryResponse
├── memory_store.py      # In-memory store with scope filtering
├── persistence.py       # ScopeIsolatedStorage (JSON, atomic writes)
├── security.py          # V26SecurityPolicy, injection detection, scope validation
├── experience.py        # Experience, ExperienceOutcome, promotion checks
├── consolidation.py     # Experience grouping and promotion
├── memory_manager.py    # Central coordinator (read/write/promote/consolidate)
└── memory_bridge.py     # V2.6 ↔ V2.5 routing bridge
```

## Identity Model

Three identity levels form a hierarchy:

| Identity | Scope | Required |
|----------|-------|----------|
| `AgentIdentity` | Agent | Yes |
| `ProjectIdentity` | Project | Optional |
| `SessionIdentity` | Session | Optional |

Identity is provider/model/adapter agnostic. Provider and model are metadata, not identity.

## Memory Kinds

| Kind | Semantics | Lifecycle |
|------|-----------|-----------|
| `WORKING` | Short-lived context | Ephemeral |
| `EPISODIC` | Events, observations | May be promoted |
| `LEARNED` | Verified knowledge | Persistent |

## Scope Isolation

Memory is isolated across three dimensions:

- **Agent**: Agent A cannot access Agent B's memories
- **Project**: Project A cannot access Project B's memories
- **Session**: Session A cannot access Session B's memories

Scope validation occurs at every access point.

## Security

Stored memory is DATA. Memory containing injection-like content (e.g., "ignore previous instructions") is:

1. Detected by injection patterns
2. Flagged by `enforce_instruction_boundary()`
3. Never escalated to instruction priority

The `V26SecurityPolicy` enforces:
- Content length limits
- Metadata key limits
- Tag count limits
- Blocked patterns
- Injection detection

## Persistence

`ScopeIsolatedStorage` provides:

- JSON-based durability
- Atomic writes (temp file + rename, Windows fallback)
- Schema versioning (`SCHEMA_VERSION = "2.6.0"`)
- Recovery from malformed/truncated files
- Scope-preserving queries

## Consolidation

`consolidate_experiences()` groups experiences by:

1. Scope (agent → project → session)
2. Outcome consistency (SUCCESS/FAILURE grouped separately)
3. Minimum group size (default: 2)

Consistent groups are promoted to `LEARNED` memory with provenance tracking.

## Bridge

`V26Bridge` connects V2.6 to V2.5 routing:

- Uses public V2.5 APIs only
- Registers handlers for EXPERIENCE/KNOWLEDGE packets
- Routes memory operations through `MemoryManager`

## What V2.6 DOES

- Connect agents to long-term memory
- Manage memory requests with scope isolation
- Persist experiences durably
- Retrieve relevant memories with context budgets
- Preserve provenance across all operations
- Provide secure memory boundaries
- Prepare infrastructure for future agent adapters

## What V2.6 DOES NOT

- Implement OpenCode/Claude/Codex connectivity (adapters are future)
- Implement V2.7 continuous learning
- Replace V2.3 confidence, V2.2 conflict, V2.4.2 lifecycle, V2.5 routing
- Become coding-agent-specific

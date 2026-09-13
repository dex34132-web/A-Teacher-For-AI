"""Lerev V2.6 — Long-Term Memory + Deep Agent Connection.

This module provides the persistent memory, scope isolation, experience
management, and deep agent connection infrastructure that builds on
V2.5's universal routing layer.

Architecture:
    V2.4.2 Knowledge + Lifecycle
        ↓
    V2.5 Universal Agent Routing
        ↓
    V2.6 Long-Term Memory + Deep Agent Connection  ← this module
        ↓
    V2.7 Continuous Experience Learning

Design principles:
- Provider/model/agent-framework agnostic
- No global mutable state
- Deterministic and auditable
- Scope-isolated across agent/project/session
- Stored memory is DATA, never instructions
- Reuses existing Lerev systems (confidence, conflict, lifecycle)
"""

from __future__ import annotations

from core.routing.v26.consolidation import (
    ConsolidationResult,
    consolidate_experiences,
    should_consolidate,
)
from core.routing.v26.experience import (
    Experience,
    ExperienceOutcome,
    is_promotable,
    validate_experience_content,
)
from core.routing.v26.identity import (
    AgentIdentity,
    MemoryScope,
    ProjectIdentity,
    SessionIdentity,
)
from core.routing.v26.memory_bridge import V26Bridge
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.memory_types import (
    MemoryEntry,
    MemoryKind,
    MemoryRequest,
    MemoryResponse,
)
from core.routing.v26.persistence import SCHEMA_VERSION, ScopeIsolatedStorage
from core.routing.v26.security import (
    V26SecurityPolicy,
    detect_injection,
    enforce_instruction_boundary,
    validate_memory_content,
    validate_memory_request,
    validate_scope_access,
)

__all__ = [
    # Identity
    "AgentIdentity",
    "ProjectIdentity",
    "SessionIdentity",
    "MemoryScope",
    # Memory types
    "MemoryKind",
    "MemoryEntry",
    "MemoryRequest",
    "MemoryResponse",
    # Storage
    "MemoryStore",
    "ScopeIsolatedStorage",
    "SCHEMA_VERSION",
    # Experience
    "Experience",
    "ExperienceOutcome",
    "is_promotable",
    "validate_experience_content",
    # Consolidation
    "ConsolidationResult",
    "consolidate_experiences",
    "should_consolidate",
    # Manager
    "MemoryManager",
    # Bridge
    "V26Bridge",
    # Security
    "V26SecurityPolicy",
    "detect_injection",
    "validate_memory_request",
    "validate_memory_content",
    "validate_scope_access",
    "enforce_instruction_boundary",
]

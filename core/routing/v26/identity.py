"""Universal identity abstractions for Lerev V2.6.

Provides stable, serializable, deterministic identity primitives for
agents, projects, and sessions. Identity must NOT depend on any specific
AI provider, model, or framework.

Design principles:
- Provider/model/adapter are metadata, not identity
- Identity is serializable (to/from dict, JSON-safe)
- Identity is deterministic (same inputs → same ID)
- Identity is validated on construction
- Scope-aware: agent → project → session hierarchy
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


def _stable_hash(*parts: str) -> str:
    """Compute a deterministic short hash from string parts."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# AgentIdentity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    """Unique identity for an AI agent.

    Attributes:
        agent_id: Stable unique identifier.
        provider: Optional provider name (e.g. "openai", "anthropic").
        model: Optional model name (e.g. "gpt-4", "claude-3").
        adapter: Optional adapter name (e.g. "opencode", "claude_code").
        metadata: Additional identity metadata.
    """

    agent_id: str
    provider: str = ""
    model: str = ""
    adapter: str = ""
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id must not be empty")

    @classmethod
    def create(cls, agent_id: str, **kwargs: Any) -> AgentIdentity:
        """Create an AgentIdentity with validation."""
        return cls(agent_id=agent_id, **kwargs)

    @classmethod
    def from_provider(cls, provider: str, model: str, **kwargs: Any) -> AgentIdentity:
        """Create an AgentIdentity from provider/model (generates stable ID)."""
        agent_id = _stable_hash(provider, model)
        return cls(agent_id=agent_id, provider=provider, model=model, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        d: dict[str, Any] = {"agent_id": self.agent_id}
        if self.provider:
            d["provider"] = self.provider
        if self.model:
            d["model"] = self.model
        if self.adapter:
            d["adapter"] = self.adapter
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentIdentity:
        """Deserialize from dictionary.

        Uses a sentinel for empty agent_id to allow deserialization
        of incomplete data without raising.
        """
        agent_id = str(data.get("agent_id", ""))
        if not agent_id:
            agent_id = "__unresolved__"
        return cls(
            agent_id=agent_id,
            provider=str(data.get("provider", "")),
            model=str(data.get("model", "")),
            adapter=str(data.get("adapter", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def scope_key(self) -> str:
        """Return a deterministic key for scope-based lookups."""
        return f"agent:{self.agent_id}"


# ---------------------------------------------------------------------------
# ProjectIdentity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectIdentity:
    """Unique identity for a project scope.

    Attributes:
        project_id: Stable unique identifier.
        name: Human-readable project name.
        agent_id: Owning agent's ID (optional, for multi-agent).
        metadata: Additional project metadata.
    """

    project_id: str
    name: str = ""
    agent_id: str = ""
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id must not be empty")

    @classmethod
    def create(cls, project_id: str, **kwargs: Any) -> ProjectIdentity:
        """Create a ProjectIdentity with validation."""
        return cls(project_id=project_id, **kwargs)

    @classmethod
    def from_name(cls, name: str, agent_id: str = "", **kwargs: Any) -> ProjectIdentity:
        """Create a ProjectIdentity from a name (generates stable ID)."""
        project_id = _stable_hash(name, agent_id)
        return cls(project_id=project_id, name=name, agent_id=agent_id, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        d: dict[str, Any] = {"project_id": self.project_id}
        if self.name:
            d["name"] = self.name
        if self.agent_id:
            d["agent_id"] = self.agent_id
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectIdentity:
        """Deserialize from dictionary."""
        return cls(
            project_id=str(data.get("project_id", "")),
            name=str(data.get("name", "")),
            agent_id=str(data.get("agent_id", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def scope_key(self) -> str:
        """Return a deterministic key for scope-based lookups."""
        return f"project:{self.project_id}"


# ---------------------------------------------------------------------------
# SessionIdentity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionIdentity:
    """Unique identity for a session scope.

    Attributes:
        session_id: Stable unique identifier.
        project_id: Owning project's ID.
        agent_id: Owning agent's ID.
        metadata: Additional session metadata.
    """

    session_id: str
    project_id: str = ""
    agent_id: str = ""
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")

    @classmethod
    def create(cls, session_id: str, **kwargs: Any) -> SessionIdentity:
        """Create a SessionIdentity with validation."""
        return cls(session_id=session_id, **kwargs)

    @classmethod
    def from_context(
        cls, agent_id: str, project_id: str, **kwargs: Any
    ) -> SessionIdentity:
        """Create a SessionIdentity from agent/project context (generates stable ID)."""
        session_id = _stable_hash(agent_id, project_id)
        return cls(
            session_id=session_id,
            project_id=project_id,
            agent_id=agent_id,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        d: dict[str, Any] = {"session_id": self.session_id}
        if self.project_id:
            d["project_id"] = self.project_id
        if self.agent_id:
            d["agent_id"] = self.agent_id
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionIdentity:
        """Deserialize from dictionary."""
        return cls(
            session_id=str(data.get("session_id", "")),
            project_id=str(data.get("project_id", "")),
            agent_id=str(data.get("agent_id", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def scope_key(self) -> str:
        """Return a deterministic key for scope-based lookups."""
        return f"session:{self.session_id}"


# ---------------------------------------------------------------------------
# Composite scope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MemoryScope:
    """Composite scope for memory operations.

    Encapsulates the full agent → project → session hierarchy
    used for memory isolation and retrieval.

    Attributes:
        agent: Agent identity.
        project: Optional project identity.
        session: Optional session identity.
    """

    agent: AgentIdentity
    project: ProjectIdentity | None = None
    session: SessionIdentity | None = None

    def scope_key(self) -> str:
        """Return a deterministic composite scope key."""
        parts = [f"agent:{self.agent.agent_id}"]
        if self.project:
            parts.append(f"project:{self.project.project_id}")
        if self.session:
            parts.append(f"session:{self.session.session_id}")
        return "|".join(parts)

    def includes(self, other: MemoryScope) -> bool:
        """Check if this scope includes the other scope.

        Scope A includes scope B if:
        - A.agent == B.agent (or A.agent is unspecified)
        - A.project includes B.project (or A.project is unspecified)
        - A.session includes B.session (or A.session is unspecified)
        """
        if self.agent.agent_id and self.agent.agent_id != other.agent.agent_id:
            return False
        if self.project and self.project.project_id:
            if other.project is None or self.project.project_id != other.project.project_id:
                return False
        if self.session and self.session.session_id:
            if other.session is None or self.session.session_id != other.session.session_id:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        d: dict[str, Any] = {"agent": self.agent.to_dict()}
        if self.project:
            d["project"] = self.project.to_dict()
        if self.session:
            d["session"] = self.session.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryScope:
        """Deserialize from dictionary."""
        return cls(
            agent=AgentIdentity.from_dict(data.get("agent", {})),
            project=ProjectIdentity.from_dict(data["project"]) if "project" in data else None,
            session=SessionIdentity.from_dict(data["session"]) if "session" in data else None,
        )

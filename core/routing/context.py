"""Context awareness for Lerev V2.5 routing.

Tracks the current routing context to enable context-aware routing
decisions. The context abstraction includes current task, context size,
available budget, active information, and recent routing decisions.

Do not assume that every agent has the same context model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContextBudget:
    """Context window budget information.

    Attributes:
        max_tokens: Maximum tokens available in context window.
        used_tokens: Tokens currently used.
        reserved_tokens: Tokens reserved for response.
        overhead_tokens: Tokens used by system prompt / instructions.
    """

    max_tokens: int = 128_000
    used_tokens: int = 0
    reserved_tokens: int = 4_096
    overhead_tokens: int = 0

    @property
    def available_tokens(self) -> int:
        """Tokens available for information."""
        return max(
            0,
            self.max_tokens - self.used_tokens - self.reserved_tokens - self.overhead_tokens,
        )

    @property
    def usage_ratio(self) -> float:
        """Ratio of used tokens to max tokens."""
        if self.max_tokens <= 0:
            return 1.0
        return min(1.0, self.used_tokens / self.max_tokens)

    @property
    def is_near_capacity(self) -> bool:
        """Check if context is near capacity (>80%)."""
        return self.usage_ratio > 0.8

    @property
    def is_full(self) -> bool:
        """Check if context is full."""
        return self.available_tokens <= 0

    def can_fit(self, estimated_tokens: int) -> bool:
        """Check if estimated tokens can fit in available context."""
        return estimated_tokens <= self.available_tokens

    def reserve(self, tokens: int) -> ContextBudget:
        """Return a new budget with additional tokens reserved."""
        return ContextBudget(
            max_tokens=self.max_tokens,
            used_tokens=self.used_tokens,
            reserved_tokens=self.reserved_tokens + tokens,
            overhead_tokens=self.overhead_tokens,
        )

    def consume(self, tokens: int) -> ContextBudget:
        """Return a new budget with tokens consumed."""
        return ContextBudget(
            max_tokens=self.max_tokens,
            used_tokens=self.used_tokens + tokens,
            reserved_tokens=self.reserved_tokens,
            overhead_tokens=self.overhead_tokens,
        )


@dataclass
class ContextState:
    """Current routing context state.

    Tracks the state of the routing system to enable context-aware
    decisions. Mutable — updated as routing progresses.

    Attributes:
        current_task: Description of the current task.
        budget: Context window budget.
        active_scopes: Currently active scopes.
        recent_destinations: Recently used destinations (most recent last).
        recent_types: Recently seen information types.
        operation_count: Total routing operations performed.
        deferred_count: Number of deferred operations.
        batch_count: Number of batched operations.
        custom: Extensible context data.
    """

    current_task: str = ""
    budget: ContextBudget = field(default_factory=ContextBudget)
    active_scopes: list[str] = field(default_factory=list)
    recent_destinations: list[str] = field(default_factory=list)
    recent_types: list[str] = field(default_factory=list)
    operation_count: int = 0
    deferred_count: int = 0
    batch_count: int = 0
    custom: dict[str, Any] = field(default_factory=dict)

    def record_routing(
        self,
        destination_name: str,
        information_type_name: str,
    ) -> None:
        """Record a routing operation in the context."""
        self.operation_count += 1
        self.recent_destinations.append(destination_name)
        if len(self.recent_destinations) > 100:
            self.recent_destinations = self.recent_destinations[-100:]
        self.recent_types.append(information_type_name)
        if len(self.recent_types) > 100:
            self.recent_types = self.recent_types[-100:]

    def record_deferral(self) -> None:
        """Record a deferral operation."""
        self.deferred_count += 1

    def record_batch(self) -> None:
        """Record a batch operation."""
        self.batch_count += 1

    def get_recent_destination_frequency(self, destination_name: str) -> int:
        """Count how many times a destination was used recently."""
        return self.recent_destinations.count(destination_name)

    def get_recent_type_frequency(self, type_name: str) -> int:
        """Count how many times an information type was seen recently."""
        return self.recent_types.count(type_name)

    def has_scope(self, scope: str) -> bool:
        """Check if a scope is currently active."""
        return scope in self.active_scopes

    def enter_scope(self, scope: str) -> None:
        """Enter a scope."""
        if scope not in self.active_scopes:
            self.active_scopes.append(scope)

    def exit_scope(self, scope: str) -> None:
        """Exit a scope."""
        if scope in self.active_scopes:
            self.active_scopes.remove(scope)

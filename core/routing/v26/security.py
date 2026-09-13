"""Security policy for EVO V2.6 long-term memory.

Enforces agent/project/session isolation, validates memory requests,
validates stored content, and ensures instruction/data boundaries.

Key principle:
    Stored memory is DATA. If a memory contains text like
    "ignore previous instructions", it must remain data.
    It must never gain instruction priority merely because
    it was retrieved from memory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.routing.v26.identity import MemoryScope
from core.routing.v26.memory_types import MemoryEntry, MemoryRequest

# ---------------------------------------------------------------------------
# Security policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class V26SecurityPolicy:
    """Security policy for V2.6 memory operations.

    Attributes:
        max_content_length: Maximum allowed memory content length.
        max_metadata_keys: Maximum keys in metadata dict.
        max_tags: Maximum number of tags per memory.
        blocked_patterns: Regex patterns that block content.
        enable_injection_detection: Whether to detect injection attempts.
        max_context_budget: Maximum allowed context budget in requests.
        max_limit: Maximum memories per request.
    """

    max_content_length: int = 100_000
    max_metadata_keys: int = 50
    max_tags: int = 20
    blocked_patterns: tuple[str, ...] = ()
    enable_injection_detection: bool = True
    max_context_budget: int = 100_000
    max_limit: int = 1000


# ---------------------------------------------------------------------------
# Injection patterns (DATA must not become INSTRUCTIONS)
# ---------------------------------------------------------------------------


_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(prior|previous|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+are", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"override\s+(all\s+)?instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(your|previous)\s+", re.IGNORECASE),
    re.compile(r"\[SYSTEM\]", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"ADMIN\s+MODE", re.IGNORECASE),
    re.compile(r"developer\s+mode", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(secrets?|keys?|password)", re.IGNORECASE),
)


def detect_injection(content: str) -> tuple[bool, str]:
    """Detect potential prompt injection in content.

    Returns:
        Tuple of (is_injection, matched_pattern).
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(content):
            return True, pattern.pattern
    return False, ""


# ---------------------------------------------------------------------------
# Scope isolation validation
# ---------------------------------------------------------------------------


def validate_scope_access(
    requestor: MemoryScope,
    target: MemoryScope,
) -> tuple[bool, str]:
    """Validate that requestor has access to target scope.

    Access rules:
    - Agent A cannot access Agent B's memories
    - Project A cannot access Project B's memories
    - Session A cannot access Session B's memories (unless project-wide)
    - Project-wide access requires matching project_id

    Returns:
        Tuple of (allowed, reason).
    """
    # Agent isolation: must match
    if requestor.agent.agent_id != target.agent.agent_id:
        return False, (
            f"Agent isolation violation: requestor={requestor.agent.agent_id}, "
            f"target={target.agent.agent_id}"
        )

    # Project isolation: if requestor has project, target must match
    if requestor.project and requestor.project.project_id:
        if target.project is None or requestor.project.project_id != target.project.project_id:
            return False, (
                f"Project isolation violation: requestor={requestor.project.project_id}, "
                f"target={target.project.project_id if target.project else 'none'}"
            )

    # Session isolation: if requestor has session, target must match
    if requestor.session and requestor.session.session_id:
        if target.session is None or requestor.session.session_id != target.session.session_id:
            return False, (
                f"Session isolation violation: requestor={requestor.session.session_id}, "
                f"target={target.session.session_id if target.session else 'none'}"
            )

    return True, ""


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def validate_memory_request(
    request: MemoryRequest,
    policy: V26SecurityPolicy | None = None,
) -> tuple[bool, str]:
    """Validate a memory request against security policy.

    Returns:
        Tuple of (is_valid, reason).
    """
    if policy is None:
        policy = V26SecurityPolicy()

    # Basic request validation
    is_valid, reason = request.validate()
    if not is_valid:
        return False, reason

    # Policy checks
    if len(request.query) > policy.max_content_length:
        return False, (
            f"Query length {len(request.query)} exceeds "
            f"maximum {policy.max_content_length}"
        )

    if request.limit > policy.max_limit:
        return False, f"Limit {request.limit} exceeds maximum {policy.max_limit}"

    if request.context_budget > policy.max_context_budget:
        return False, (
            f"Context budget {request.context_budget} exceeds "
            f"maximum {policy.max_context_budget}"
        )

    # Injection detection on query
    if policy.enable_injection_detection:
        is_injection, pattern = detect_injection(request.query)
        if is_injection:
            return False, f"Potential injection detected in query: {pattern}"

    return True, ""


# ---------------------------------------------------------------------------
# Content validation
# ---------------------------------------------------------------------------


def validate_memory_content(
    entry: MemoryEntry,
    policy: V26SecurityPolicy | None = None,
) -> tuple[bool, str]:
    """Validate a memory entry's content against security policy.

    Returns:
        Tuple of (is_valid, reason).
    """
    if policy is None:
        policy = V26SecurityPolicy()

    if not entry.content:
        return False, "Memory content must not be empty"

    if len(entry.content) > policy.max_content_length:
        return False, (
            f"Content length {len(entry.content)} exceeds maximum {policy.max_content_length}"
        )

    if len(entry.metadata) > policy.max_metadata_keys:
        return False, (
            f"Metadata keys {len(entry.metadata)} exceeds maximum {policy.max_metadata_keys}"
        )

    if len(entry.tags) > policy.max_tags:
        return False, f"Tags count {len(entry.tags)} exceeds maximum {policy.max_tags}"

    # Blocked patterns
    for pattern_str in policy.blocked_patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        if pattern.search(entry.content):
            return False, f"Content matches blocked pattern: {pattern_str}"

    return True, ""


# ---------------------------------------------------------------------------
# Instruction boundary enforcement
# ---------------------------------------------------------------------------


def enforce_instruction_boundary(entry: MemoryEntry) -> tuple[bool, str]:
    """Ensure stored memory remains data, never instructions.

    This is the critical security check. Memory content containing
    injection-like text must be flagged but NOT escalated to instruction
    priority.

    Returns:
        Tuple of (safe, warning). safe=True means the memory can be
        returned as data. If safe=False, the memory should be rejected
        or returned with a warning. The warning is informational.
    """
    is_injection, pattern = detect_injection(entry.content)
    if is_injection:
        return False, (
            f"Memory {entry.memory_id} contains injection-like content "
            f"(pattern: {pattern}). MUST be treated as DATA only."
        )
    return True, ""

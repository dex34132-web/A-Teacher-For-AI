"""Security model for Lerev V2.5 routing.

Maintains clear boundaries between information, instruction, policy,
and system control. Prevents prompt-injection-like content from gaining
instruction-level authority.

Key principle:
    An information packet containing text like "ignore previous instructions..."
    must remain DATA. It must never automatically gain instruction-level
    authority simply because Lerev retrieved or routed it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.routing.information import InformationPacket, InformationType, SensitivityLevel

# ---------------------------------------------------------------------------
# Security policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Security policy for routing.

    Attributes:
        max_sensitivity_allowed: Maximum sensitivity level this policy allows.
        allow_instructions: Whether instructions can be routed.
        allow_external_content: Whether external content is allowed.
        blocked_patterns: Regex patterns that block information.
        sensitive_patterns: Regex patterns that trigger sensitive classification.
        max_content_length: Maximum allowed content length.
        enable_injection_detection: Whether to detect prompt injection attempts.
    """

    max_sensitivity_allowed: SensitivityLevel = SensitivityLevel.PRIVATE
    allow_instructions: bool = True
    allow_external_content: bool = True
    blocked_patterns: tuple[str, ...] = ()
    sensitive_patterns: tuple[str, ...] = ()
    max_content_length: int = 100_000
    enable_injection_detection: bool = True

    def is_sensitivity_allowed(self, level: SensitivityLevel) -> bool:
        """Check if a sensitivity level is allowed by this policy."""
        return level.value <= self.max_sensitivity_allowed.value


# ---------------------------------------------------------------------------
# Prompt injection patterns
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
)


def detect_injection(content: str) -> tuple[bool, str]:
    """Detect potential prompt injection in content.

    Args:
        content: The content to check.

    Returns:
        Tuple of (is_injection, matched_pattern).
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(content):
            return True, pattern.pattern
    return False, ""


def validate_instruction_boundary(packet: InformationPacket) -> tuple[bool, str]:
    """Validate that data content does not masquerade as instructions.

    This is the core security check. Information packets classified as
    DATA must not contain instruction-like content that could be
    interpreted as commands.

    Args:
        packet: The information packet to validate.

    Returns:
        Tuple of (is_valid, reason).
    """
    # Instructions are expected to contain instruction-like content
    if packet.information_type == InformationType.INSTRUCTION:
        return True, ""

    # Check for injection patterns in non-instruction content
    if packet.information_type != InformationType.INSTRUCTION:
        is_injection, pattern = detect_injection(packet.content)
        if is_injection:
            return False, f"Potential injection detected: {pattern}"

    return True, ""


# ---------------------------------------------------------------------------
# Content sanitization
# ---------------------------------------------------------------------------


def sanitize_for_logging(
    packet: InformationPacket,
    max_length: int = 200,
) -> str:
    """Sanitize packet content for safe logging.

    Truncates content and masks sensitive data.

    Args:
        packet: The packet to sanitize.
        max_length: Maximum content length in output.

    Returns:
        Sanitized string safe for logging.
    """
    content = packet.content
    if packet.sensitivity == SensitivityLevel.SECRET:
        content = "[REDACTED]"
    elif packet.sensitivity == SensitivityLevel.SENSITIVE:
        content = content[:50] + "[...REDACTED...]"
    elif len(content) > max_length:
        content = content[:max_length] + "[...]"

    return (
        f"Packet(id={packet.id}, type={packet.information_type.name}, "
        f"sensitivity={packet.sensitivity.name}, content={content!r})"
    )


def sanitize_for_telemetry(
    packet: InformationPacket,
    max_content_length: int = 100,
) -> dict[str, Any]:
    """Sanitize packet for telemetry (no secrets).

    Args:
        packet: The packet to sanitize.
        max_content_length: Maximum content length in output.

    Returns:
        Dictionary safe for telemetry.
    """
    content = packet.content
    if packet.sensitivity in {SensitivityLevel.SECRET, SensitivityLevel.SENSITIVE}:
        content = "[REDACTED]"
    elif len(content) > max_content_length:
        content = content[:max_content_length] + "[...]"

    return {
        "packet_id": packet.id,
        "information_type": packet.information_type.name,
        "source": packet.source.name,
        "sensitivity": packet.sensitivity.name,
        "priority": packet.priority,
        "content_length": packet.content_length,
        "content_preview": content,
    }


# ---------------------------------------------------------------------------
# Policy enforcement
# ---------------------------------------------------------------------------


def enforce_policy(
    packet: InformationPacket,
    policy: SecurityPolicy,
) -> tuple[bool, str]:
    """Enforce security policy on a packet.

    Args:
        packet: The packet to check.
        policy: The security policy to enforce.

    Returns:
        Tuple of (allowed, reason).
    """
    # Check sensitivity
    if not policy.is_sensitivity_allowed(packet.sensitivity):
        return False, f"Sensitivity {packet.sensitivity.name} exceeds policy maximum"

    # Check content length
    if packet.content_length > policy.max_content_length:
        return (
            False,
            f"Content length {packet.content_length} exceeds "
            f"maximum {policy.max_content_length}",
        )

    # Check blocked patterns
    for pattern_str in policy.blocked_patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        if pattern.search(packet.content):
            return False, f"Content matches blocked pattern: {pattern_str}"

    # Check injection
    if policy.enable_injection_detection and packet.information_type != InformationType.INSTRUCTION:
        is_injection, matched = detect_injection(packet.content)
        if is_injection:
            return False, f"Potential injection detected: {matched}"

    return True, ""

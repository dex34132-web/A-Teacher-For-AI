"""Cost model for Lerev V2.5 routing.

Explicitly treats agent interaction as a resource with measurable costs.
Supports estimated, measured, and unknown cost states.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class CostType(Enum):
    """Types of costs that can be estimated or measured."""

    TOKEN = auto()  # Token cost (for LLM-based agents)
    MODEL_CALL = auto()  # Model API call cost
    LATENCY = auto()  # Latency cost (ms)
    PROCESSING = auto()  # CPU processing cost
    CONTEXT_POLLUTION = auto()  # Context window usage cost
    TOOL_CALL = auto()  # Tool invocation cost


class CostPrecision(Enum):
    """Precision of cost estimates."""

    ESTIMATED = auto()  # Rough estimate
    MEASURED = auto()  # Actual measurement
    UNKNOWN = auto()  # Cannot determine cost


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Estimated or measured cost of an operation.

    Attributes:
        cost_type: Type of cost.
        value: Cost value.
        precision: Whether this is estimated or measured.
        currency: Cost unit (e.g., 'tokens', 'usd', 'ms').
    """

    cost_type: CostType
    value: float
    precision: CostPrecision = CostPrecision.ESTIMATED
    currency: str = ""

    @property
    def is_measured(self) -> bool:
        """Check if this is an actual measurement."""
        return self.precision == CostPrecision.MEASURED

    @property
    def is_estimate(self) -> bool:
        """Check if this is an estimate."""
        return self.precision == CostPrecision.ESTIMATED

    @property
    def is_unknown(self) -> bool:
        """Check if cost is unknown."""
        return self.precision == CostPrecision.UNKNOWN


def estimate_tokens(text: str) -> int:
    """Rough token estimate from text (chars / 4)."""
    return max(1, len(text) // 4)


def estimate_cost_from_tokens(
    token_count: int,
    cost_per_1k_tokens: float = 0.001,
) -> CostEstimate:
    """Estimate cost from token count.

    Args:
        token_count: Number of tokens.
        cost_per_1k_tokens: Cost per 1000 tokens.

    Returns:
        Cost estimate.
    """
    return CostEstimate(
        cost_type=CostType.TOKEN,
        value=(token_count / 1000.0) * cost_per_1k_tokens,
        precision=CostPrecision.ESTIMATED,
        currency="usd",
    )


def estimate_latency_cost(latency_ms: float) -> CostEstimate:
    """Create a latency cost estimate.

    Args:
        latency_ms: Latency in milliseconds.

    Returns:
        Cost estimate.
    """
    return CostEstimate(
        cost_type=CostType.LATENCY,
        value=latency_ms,
        precision=CostPrecision.MEASURED,
        currency="ms",
    )

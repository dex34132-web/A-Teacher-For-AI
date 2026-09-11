"""Efficiency controller for EVO V2.5 routing.

Decides whether operations should be executed, deferred, batched,
simplified, or rejected based on expected value vs cost.

The objective is:
    Maximum useful information with minimum unnecessary agent cost.

Do not sacrifice correctness merely to save tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from core.routing.context import ContextState
from core.routing.cost import CostEstimate, CostPrecision, CostType
from core.routing.information import InformationPacket, InformationType
from core.routing.priority import Priority, PriorityConfig


class EfficiencyDecision(Enum):
    """What the efficiency controller recommends."""

    EXECUTE = auto()  # Process immediately
    DEFER = auto()  # Defer for later
    BATCH = auto()  # Add to batch
    SIMPLIFY = auto()  # Reduce information before processing
    REJECT = auto()  # Reject as not worth processing


@dataclass(frozen=True, slots=True)
class EfficiencyConfig:
    """Configuration for the efficiency controller.

    Attributes:
        min_value_threshold: Minimum expected value to process (0.0-1.0).
        max_cost_threshold: Maximum cost to accept without deferral.
        batch_cooldown_seconds: Minimum time between batch flushes.
        simplification_threshold: Content length above which to simplify.
        enable_batching: Whether batching is enabled.
        enable_simplification: Whether simplification is enabled.
    """

    min_value_threshold: float = 0.1
    max_cost_threshold: float = 1.0
    batch_cooldown_seconds: float = 5.0
    simplification_threshold: int = 5_000
    enable_batching: bool = True
    enable_simplification: bool = True


def estimate_information_value(packet: InformationPacket) -> float:
    """Estimate the value of processing this information.

    Higher value means more useful to process.

    Args:
        packet: The information packet.

    Returns:
        Value score between 0.0 and 1.0.
    """
    value = 0.5  # Base value

    # Type-based value adjustments
    type_values = {
        InformationType.INSTRUCTION: 0.9,
        InformationType.TASK: 0.8,
        InformationType.FEEDBACK: 0.7,
        InformationType.OUTCOME: 0.7,
        InformationType.EVIDENCE: 0.6,
        InformationType.OBSERVATION: 0.5,
        InformationType.CONTEXT: 0.5,
        InformationType.DATA: 0.4,
        InformationType.TOOL_RESULT: 0.5,
        InformationType.EXPERIENCE: 0.6,
        InformationType.KNOWLEDGE: 0.6,
        InformationType.EVENT: 0.4,
        InformationType.METADATA: 0.3,
        InformationType.UNKNOWN: 0.2,
    }
    value = type_values.get(packet.information_type, 0.5)

    # Priority adjustment
    priority_multiplier = {
        0: 1.2,  # CRITICAL
        1: 1.1,  # HIGH
        2: 1.0,  # NORMAL
        3: 0.9,  # LOW
        4: 0.8,  # BACKGROUND
    }
    value *= priority_multiplier.get(packet.priority, 1.0)

    # Confidence adjustment
    value *= 0.7 + (packet.confidence * 0.6)

    return max(0.0, min(1.0, value))


def estimate_processing_cost(packet: InformationPacket) -> CostEstimate:
    """Estimate the cost of processing this information.

    Args:
        packet: The information packet.

    Returns:
        Estimated cost.
    """
    # Base cost from content length
    base_cost = packet.estimated_tokens / 1000.0  # Normalize to ~1.0 for 1000 tokens

    # Type-based cost multipliers
    type_multipliers = {
        InformationType.INSTRUCTION: 1.5,
        InformationType.TASK: 1.2,
        InformationType.FEEDBACK: 1.1,
        InformationType.OUTCOME: 1.0,
        InformationType.EVIDENCE: 1.0,
        InformationType.OBSERVATION: 0.8,
        InformationType.CONTEXT: 0.8,
        InformationType.DATA: 0.6,
        InformationType.TOOL_RESULT: 0.7,
        InformationType.EXPERIENCE: 1.0,
        InformationType.KNOWLEDGE: 1.0,
        InformationType.EVENT: 0.5,
        InformationType.METADATA: 0.3,
        InformationType.UNKNOWN: 0.5,
    }
    multiplier = type_multipliers.get(packet.information_type, 1.0)
    cost_value = base_cost * multiplier

    return CostEstimate(
        cost_type=CostType.PROCESSING,
        value=cost_value,
        precision=CostPrecision.ESTIMATED,
        currency="units",
    )


class EfficiencyController:
    """Controls routing efficiency based on value vs cost.

    No global mutable state — state is per-controller instance.
    """

    def __init__(
        self,
        config: EfficiencyConfig | None = None,
        priority_config: PriorityConfig | None = None,
    ) -> None:
        """Initialize the efficiency controller.

        Args:
            config: Efficiency configuration.
            priority_config: Priority configuration.
        """
        self._config = config or EfficiencyConfig()
        self._priority_config = priority_config or PriorityConfig()
        self._last_batch_flush: float = 0.0

    def evaluate(
        self,
        packet: InformationPacket,
        context: ContextState | None = None,
    ) -> EfficiencyDecision:
        """Evaluate whether to process, defer, batch, simplify, or reject.

        Args:
            packet: The information packet.
            context: Current routing context.

        Returns:
            Efficiency decision.
        """
        value = estimate_information_value(packet)
        cost = estimate_processing_cost(packet)

        # Reject if value is below threshold
        if value < self._config.min_value_threshold:
            return EfficiencyDecision.REJECT

        # Reject if cost exceeds threshold
        if cost.value > self._config.max_cost_threshold and value < 0.5:
            return EfficiencyDecision.REJECT

        # Check priority-based deferral
        priority = Priority.from_int(packet.priority)
        if self._priority_config.should_defer(priority) and value < 0.6:
            return EfficiencyDecision.DEFER

        # Check batching
        if (
            self._config.enable_batching
            and self._priority_config.should_batch(priority)
            and packet.information_type in {
                InformationType.OBSERVATION,
                InformationType.DATA,
                InformationType.CONTEXT,
                InformationType.METADATA,
            }
        ):
            return EfficiencyDecision.BATCH

        # Check simplification
        if (
            self._config.enable_simplification
            and packet.content_length > self._config.simplification_threshold
        ):
            return EfficiencyDecision.SIMPLIFY

        return EfficiencyDecision.EXECUTE

    def should_flush_batch(self, batch_size: int, current_time: float) -> bool:
        """Check if the batch should be flushed.

        Args:
            batch_size: Current batch size.
            current_time: Current timestamp.

        Returns:
            True if batch should be flushed.
        """
        if batch_size <= 0:
            return False

        # Flush if cooldown has passed
        if current_time - self._last_batch_flush >= self._config.batch_cooldown_seconds:
            return True

        # Flush if batch is large
        return batch_size >= 10

    def record_batch_flush(self, timestamp: float) -> None:
        """Record that a batch flush occurred."""
        self._last_batch_flush = timestamp

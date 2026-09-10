"""Enhanced prediction result for V2.3 with conflict and confidence information.

Wraps the standard Prediction with conflict detection and confidence
estimation results. Maintains backward compatibility by delegating
to the underlying Prediction for output and confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.learner.conflict import Conflict, ConflictState
from core.learner.learner_v1 import Prediction

if TYPE_CHECKING:
    from core.learner.confidence import ConfidenceResult


@dataclass
class PredictResult:
    """Enhanced prediction result with conflict and confidence information.

    Backward compatible: .output and .confidence delegate to the
    underlying Prediction. Existing code that reads pred.output and
    pred.confidence will work unchanged.

    V2.3 adds:
    - confidence_result: structured ConfidenceResult with components
    - uncertainty_state: high-level uncertainty classification
    - confidence_components: machine-readable explanation

    Attributes:
        prediction: The base prediction (output, confidence, similarities).
        conflicts: List of detected conflicts (may be empty).
        overall_conflict_state: Aggregate conflict state across all conflicts.
        conflict_confidence_penalty: How much confidence is reduced [0, 1].
        selected_conflict: The "main" conflict if multiple exist.
        confidence_result: V2.3 structured confidence result (optional).
    """

    prediction: Prediction
    conflicts: list[Conflict] = field(default_factory=list)
    overall_conflict_state: ConflictState = ConflictState.NONE
    conflict_confidence_penalty: float = 0.0
    selected_conflict: Conflict | None = None
    confidence_result: ConfidenceResult | None = None
    abstained: bool = False
    abstention_reason: str = ""

    @property
    def output(self) -> str:
        """The predicted output. Returns empty string if abstained."""
        if self.abstained:
            return ""
        return self.prediction.output

    @property
    def confidence(self) -> float:
        """The adjusted confidence.

        V2.3: Uses confidence_result.confidence when available.
        V2.2 fallback: Uses base_confidence * (1 - penalty).
        Abstained predictions return 0.0 (no confidence in abstention).
        """
        if self.abstained:
            return 0.0
        if self.confidence_result is not None:
            return self.confidence_result.confidence
        adjusted = self.prediction.confidence * (1.0 - self.conflict_confidence_penalty)
        return max(0.0, min(1.0, adjusted))

    @property
    def base_confidence(self) -> float:
        """The original confidence before any adjustment."""
        return self.prediction.confidence

    @property
    def similarity(self) -> float:
        """The base similarity score (V2.3)."""
        if self.confidence_result is not None:
            return self.confidence_result.similarity
        return self.prediction.confidence

    @property
    def uncertainty_state(self) -> str:
        """High-level uncertainty classification (V2.3).

        Returns one of: confident, uncertain, insufficient_evidence, conflicted.
        """
        if self.confidence_result is not None:
            return self.confidence_result.uncertainty_state
        if self.is_unresolved:
            return "conflicted"
        if self.confidence < 0.3:
            return "insufficient_evidence"
        if self.confidence >= 0.7:
            return "confident"
        return "uncertain"

    @property
    def confidence_components(self) -> dict[str, Any]:
        """Machine-readable explanation of confidence (V2.3).

        Returns a dict with similarity, evidence_strength, agreement,
        conflict_penalty, novelty_penalty, and other components.
        """
        if self.confidence_result is not None:
            return self.confidence_result.components
        # Fallback for V2.2 path
        evidence_val = getattr(self.confidence_result, "evidence_quality", None) if self.confidence_result else None
        if evidence_val is None:
            evidence_val = getattr(self.confidence_result, "evidence_factor", 0.0) if self.confidence_result else 0.0
        return {
            "similarity": round(self.prediction.confidence, 4),
            "conflict_penalty": round(self.conflict_confidence_penalty, 4),
            "evidence_quality": evidence_val,
        }

    @property
    def similarities(self) -> list[tuple[str, float]]:
        """Similarities from the base prediction."""
        return self.prediction.similarities

    @property
    def has_conflict(self) -> bool:
        """Whether any conflict was detected."""
        return len(self.conflicts) > 0

    @property
    def is_resolved(self) -> bool:
        """Whether all conflicts were resolved."""
        if not self.conflicts:
            return True
        return all(c.state == ConflictState.RESOLVED for c in self.conflicts)

    @property
    def is_unresolved(self) -> bool:
        """Whether any conflict could not be resolved."""
        return any(c.state == ConflictState.UNRESOLVED for c in self.conflicts)

    @property
    def conflicting_outputs(self) -> list[str]:
        """All distinct outputs from conflicts."""
        outputs: list[str] = []
        for c in self.conflicts:
            for o in c.outputs:
                if o not in outputs:
                    outputs.append(o)
        return outputs

    @property
    def conflicting_ids(self) -> list[int]:
        """All memory IDs involved in any conflict."""
        ids: list[int] = []
        for c in self.conflicts:
            for eid in c.involved_ids:
                if eid not in ids:
                    ids.append(eid)
        return ids

    @property
    def max_conflict_strength(self) -> float:
        """The strongest conflict strength across all conflicts."""
        if not self.conflicts:
            return 0.0
        return max(c.strength for c in self.conflicts)

    def to_legacy(self) -> Prediction:
        """Convert to the standard Prediction for backward compatibility.

        Returns:
            The underlying Prediction object.
        """
        return self.prediction

    def summary(self) -> dict[str, Any]:
        """Return a structured summary of the prediction, conflicts, and confidence.

        Returns:
            Dictionary with prediction details, conflict information,
            and V2.3 confidence components.
        """
        result: dict[str, Any] = {
            "output": self.output,
            "confidence": round(self.confidence, 4),
            "base_confidence": round(self.base_confidence, 4),
            "similarity": round(self.similarity, 4),
            "uncertainty_state": self.uncertainty_state,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "has_conflict": self.has_conflict,
            "conflict_state": self.overall_conflict_state.value,
            "conflict_penalty": round(self.conflict_confidence_penalty, 4),
        }
        if self.confidence_result is not None:
            cr = self.confidence_result
            evidence_val = getattr(cr, "evidence_quality", None)
            if evidence_val is None:
                evidence_val = getattr(cr, "evidence_factor", 0.0)
            result["confidence_components"] = {
                "evidence_strength": round(cr.evidence_strength, 4),
                "evidence_quality": round(evidence_val, 4),
                "agreement_bonus": round(cr.agreement_bonus, 4),
                "novelty_penalty": round(cr.novelty_penalty, 4),
                "supporting_count": cr.supporting_count,
                "total_count": cr.total_count,
                "conflict_count": cr.conflict_count,
            }
        if self.conflicts:
            result["num_conflicts"] = len(self.conflicts)
            result["conflicting_outputs"] = self.conflicting_outputs
            result["conflicting_ids"] = self.conflicting_ids
            result["max_conflict_strength"] = round(self.max_conflict_strength, 4)
            if self.selected_conflict:
                sc = self.selected_conflict
                result["selected_conflict"] = {
                    "state": sc.state.value,
                    "winner_id": sc.winner_id,
                    "selected_output": sc.selected_output,
                }
        return result

import logging
from dataclasses import dataclass
from typing import Optional
from backend.decision_comparator import DecisionDelta
from backend.belief_state import BeliefState
from backend.belief_revision_engine import BeliefRevision

logger = logging.getLogger(__name__)


@dataclass
class ReversalExplanation:
    """
    Structured explanation for decision changes.
    
    Template-based to prevent agent drift and hallucinated rationales.
    """
    what_changed: str  # "You mentioned IBS"
    why_changed: str   # "High fiber may worsen IBS symptoms"
    impact_on_decision: str  # "Changed from ALLOW to WITHHOLD"
    confidence_impact: Optional[str] = None
    turn_reference: Optional[str] = None  # "in turn 7"
    
    def to_dict(self) -> dict:
        return {
            "what_changed": self.what_changed,
            "why_changed": self.why_changed,
            "impact_on_decision": self.impact_on_decision,
            "confidence_impact": self.confidence_impact,
            "turn_reference": self.turn_reference
        }


class ReversalExplainer:
    """
    Generates mandatory explanations when decisions change.
    
    Hard requirement: If change_type != STABLE → explanation REQUIRED.
    
    Prevents silent decision flips that destroy trust.
    """
    
    def generate_explanation(
        self,
        delta: DecisionDelta,
        belief_state: BeliefState,
        belief_revision: Optional[BeliefRevision] = None
    ) -> ReversalExplanation:
        """
        Generate structured explanation for decision change.
        
        Args:
            delta: Decision change delta
            belief_state: Current belief state
            belief_revision: If change was triggered by belief revision
        
        Returns:
            Structured reversal explanation
        """
        # Build what_changed based on revision or context
        if belief_revision:
            what_changed = self._format_belief_change(belief_revision, belief_state)
            turn_ref = f"in turn {belief_revision.detected_at_turn}"
        else:
            what_changed = self._infer_context_change(belief_state, delta)
            turn_ref = None
        
        # Build why_changed from delta reason
        why_changed = delta.reason
        
        # Build impact statement
        impact = self._format_impact(delta)
        
        # Build confidence impact if applicable
        confidence_impact = self._format_confidence_impact(belief_state, delta)
        
        logger.info(
            f"[REVERSAL_EXPLAINER] Generated explanation for {delta.claim_id}: "
            f"{delta.change_type}"
        )
        
        return ReversalExplanation(
            what_changed=what_changed,
            why_changed=why_changed,
            impact_on_decision=impact,
            confidence_impact=confidence_impact,
            turn_reference=turn_ref
        )
    
    def _format_belief_change(
        self,
        revision: BeliefRevision,
        belief_state: BeliefState
    ) -> str:
        """Format what changed based on belief revision."""
        if revision.revision_type == "CONTRADICTION":
            return f"You corrected your {revision.field_name.replace('_', ' ')}"
        elif revision.revision_type == "CLARIFICATION":
            return f"You clarified your {revision.field_name.replace('_', ' ')}"
        else:
            return f"You provided your {revision.field_name.replace('_', ' ')}"
    
    def _infer_context_change(
        self,
        belief_state: BeliefState,
        delta: DecisionDelta
    ) -> str:
        """Infer what changed from belief state."""
        if belief_state.resolved_uncertainties:
            return f"We now know {', '.join(belief_state.resolved_uncertainties[-1:])}"
        return "Additional context was provided"
    
    def _format_impact(self, delta: DecisionDelta) -> str:
        """Format the impact on decision."""
        if delta.change_type == "UPGRADE":
            return f"This resolves the uncertainty, changing from {delta.previous} to {delta.current}"
        elif delta.change_type == "DOWNGRADE":
            return f"This introduces new considerations, changing from {delta.previous} to {delta.current}"
        else:
            return f"Decision remains {delta.current}"
    
    def _format_confidence_impact(
        self,
        belief_state: BeliefState,
        delta: DecisionDelta
    ) -> Optional[str]:
        """Format confidence impact if significant."""
        prior_conf = belief_state.prior_confidences.get(delta.claim_id)
        if prior_conf is None:
            return None
        
        # Placeholder - actual current confidence would come from outside
        # Just note that confidence may have changed
        return "Confidence adjusted based on new information"
    
    def render_template(self, explanation: ReversalExplanation) -> str:
        """
        Render explanation into human-readable text.
        
        Template structure prevents agent drift.
        """
        parts = []
        
        # Main change statement
        if explanation.turn_reference:
            parts.append(f"{explanation.what_changed} {explanation.turn_reference}.")
        else:
            parts.append(f"{explanation.what_changed}.")
        
        # Reason
        parts.append(explanation.why_changed)
        
        # Impact
        parts.append(explanation.impact_on_decision)
        
        # Confidence impact if present
        if explanation.confidence_impact:
            parts.append(explanation.confidence_impact)
        
        return " ".join(parts)

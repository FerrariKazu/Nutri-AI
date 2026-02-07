import logging
from dataclasses import dataclass
from typing import Any, Optional, Literal
from backend.belief_state import BeliefState

logger = logging.getLogger(__name__)


@dataclass
class BeliefRevision:
    """Record of a belief change."""
    field_name: str
    old_value: Any
    new_value: Any
    detected_at_turn: int
    revision_type: Literal["UPDATE", "CONTRADICTION", "CLARIFICATION"]


class BeliefRevisionEngine:
    """
    Detects and handles contradictions in user statements.
    
    Critical for medical/nutrition credibility:
    - Users change their mind
    - Users correct themselves
    - Users add new information
    
    All changes must be logged and trigger re-evaluation.
    """
    
    def detect_conflict(
        self,
        belief_state: BeliefState,
        field_name: str,
        new_value: Any,
        current_turn: int
    ) -> Optional[BeliefRevision]:
        """
        Detect if new statement conflicts with prior belief.
        
        Args:
            belief_state: Current belief state
            field_name: Field being updated
            new_value: New value from user
            current_turn: Current turn number
        
        Returns:
            BeliefRevision if change detected, None otherwise
        """
        old_value = getattr(belief_state, field_name, None)
        
        # No prior value = new information
        if old_value is None or (isinstance(old_value, list) and len(old_value) == 0):
            return BeliefRevision(
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                detected_at_turn=current_turn,
                revision_type="UPDATE"
            )
        
        # Value changed = potential contradiction
        if old_value != new_value:
            # Check if it's clarification vs contradiction
            revision_type = self._classify_revision(field_name, old_value, new_value)
            
            logger.warning(
                f"[BELIEF_REVISION] {revision_type}: {field_name} "
                f"{old_value} → {new_value} at turn {current_turn}"
            )
            
            return BeliefRevision(
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                detected_at_turn=current_turn,
                revision_type=revision_type
            )
        
        return None
    
    def _classify_revision(
        self,
        field_name: str,
        old_value: Any,
        new_value: Any
    ) -> Literal["UPDATE", "CONTRADICTION", "CLARIFICATION"]:
        """Classify the type of revision."""
        
        # For conditions: adding is clarification, changing is contradiction
        if field_name == "known_conditions":
            if isinstance(old_value, list) and isinstance(new_value, list):
                # Adding conditions = clarification
                if all(item in new_value for item in old_value):
                    return "CLARIFICATION"
                # Removing or changing = contradiction
                return "CONTRADICTION"
        
        # For population or dietary_pattern: change is contradiction
        if field_name in ["known_population", "dietary_pattern"]:
            return "CONTRADICTION"
        
        return "UPDATE"
    
    def apply_revision(
        self,
        belief_state: BeliefState,
        revision: BeliefRevision
    ) -> None:
        """
        Apply revision and mark superseded fields.
        
        Args:
            belief_state: Belief state to update
            revision: Revision to apply
        """
        # Mark old value as superseded if contradiction
        if revision.revision_type == "CONTRADICTION":
            belief_state.mark_superseded(revision.field_name)
        
        # Update the field
        belief_state.update_field(
            revision.field_name,
            revision.new_value,
            revision.detected_at_turn
        )
        
        logger.info(
            f"[BELIEF_REVISION] Applied {revision.revision_type}: "
            f"{revision.field_name} at turn {revision.detected_at_turn}"
        )

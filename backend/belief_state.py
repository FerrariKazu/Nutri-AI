import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from backend.recommendation_gate import RecommendationDecision

logger = logging.getLogger(__name__)


@dataclass
class BeliefState:
    """
    Persistent epistemic memory across the session.
    
    Tracks what Nutri knows, when it learned it, and what has changed.
    Critical for temporal consistency and trust.
    """
    
    # Current knowledge
    known_population: Optional[str] = None
    known_conditions: List[str] = field(default_factory=list)
    dietary_pattern: Optional[str] = None
    
    # Prior decisions (per-claim)
    prior_recommendations: Dict[str, str] = field(default_factory=dict)  # claim_id → decision
    prior_confidences: Dict[str, float] = field(default_factory=dict)  # claim_id → confidence
    
    # Context tracking
    prior_missing_fields: List[str] = field(default_factory=list)
    clarification_attempts: int = 0
    clarifications_asked: List[str] = field(default_factory=list)  # Memory of questions asked
    
    resolved_uncertainties: List[str] = field(default_factory=list)
    
    # VERSIONING: Track when each field was learned
    last_updated_turn: int = 0
    source_turn_for_field: Dict[str, int] = field(default_factory=dict)  # field_name → turn_id
    
    # CONTRADICTION HANDLING: Track superseded values
    superseded_fields: List[str] = field(default_factory=list)
    
    # SATURATION: Prevent clarification loops
    saturation_triggered: bool = False
    saturation_turn: Optional[int] = None
    
    def update_field(self, field_name: str, value: Any, turn: int):
        """Update a field and track when it was learned."""
        setattr(self, field_name, value)
        self.source_turn_for_field[field_name] = turn
        self.last_updated_turn = turn
        logger.info(f"[BELIEF_STATE] Updated {field_name} at turn {turn}")
    
    def mark_superseded(self, field_name: str):
        """Mark a field as superseded due to contradiction."""
        if field_name not in self.superseded_fields:
            self.superseded_fields.append(field_name)
            logger.warning(f"[BELIEF_STATE] Marked {field_name} as superseded")
    
    def add_clarification(self, question: str, turn: int):
        """Record a clarification question."""
        self.clarifications_asked.append(question)
        self.clarification_attempts += 1
        logger.info(f"[BELIEF_STATE] Clarification {self.clarification_attempts} at turn {turn}: {question[:50]}...")
    
    def trigger_saturation(self, turn: int):
        """Mark saturation triggered."""
        self.saturation_triggered = True
        self.saturation_turn = turn
        logger.warning(f"[BELIEF_STATE] Saturation triggered at turn {turn}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for session storage."""
        return {
            "known_population": self.known_population,
            "known_conditions": self.known_conditions,
            "dietary_pattern": self.dietary_pattern,
            "prior_recommendations": self.prior_recommendations,
            "prior_confidences": self.prior_confidences,
            "prior_missing_fields": self.prior_missing_fields,
            "clarification_attempts": self.clarification_attempts,
            "clarifications_asked": self.clarifications_asked,
            "resolved_uncertainties": self.resolved_uncertainties,
            "last_updated_turn": self.last_updated_turn,
            "source_turn_for_field": self.source_turn_for_field,
            "superseded_fields": self.superseded_fields,
            "saturation_triggered": self.saturation_triggered,
            "saturation_turn": self.saturation_turn
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeliefState':
        """Deserialize from session storage."""
        return cls(**data)


def initialize_belief_state() -> BeliefState:
    """Create a new belief state for a fresh session."""
    return BeliefState()

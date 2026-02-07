import logging
from backend.belief_state import BeliefState

logger = logging.getLogger(__name__)

# Constants
INACTIVITY_THRESHOLD = 20  # turns of inactivity before context considered stale
TOPIC_SHIFT_KEYWORDS = [
    "actually", "wait", "never mind", "forget that", "ignore that",
    "different question", "new topic", "change topic"
]


class SessionResetPolicy:
    """
    Handles stale context and session continuity.
    
    Problem: Session continues 40 turns later, old context may be invalid.
    
    Solution: Detect staleness and downgrade confidence gracefully.
    """
    
    def should_downgrade_confidence(
        self,
        belief_state: BeliefState,
        current_turn: int,
        user_message: str
    ) -> bool:
        """
        Detect if session context is stale.
        
        Args:
            belief_state: Current belief state
            current_turn: Current turn number
            user_message: Latest user message
        
        Returns:
            True if context is stale and confidence should be downgraded
        """
        # Check inactivity
        turns_since_update = current_turn - belief_state.last_updated_turn
        if turns_since_update > INACTIVITY_THRESHOLD:
            logger.warning(
                f"[SESSION_RESET] Stale context detected: "
                f"{turns_since_update} turns since last update"
            )
            return True
        
        # Check explicit topic shift
        if self._detect_topic_shift(user_message):
            logger.warning(
                f"[SESSION_RESET] Topic shift detected in message"
            )
            return True
        
        return False
    
    def _detect_topic_shift(self, user_message: str) -> bool:
        """
        Detect if user explicitly shifted topic.
        
        Args:
            user_message: User's message
        
        Returns:
            True if topic shift detected
        """
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in TOPIC_SHIFT_KEYWORDS)
    
    def apply_reset(
        self,
        belief_state: BeliefState,
        reset_type: str = "inactivity"
    ) -> None:
        """
        Downgrade confidence for stale context.
        
        Args:
            belief_state: Belief state to reset
            reset_type: Type of reset (for logging)
        """
        decay_factor = 0.7
        
        for claim_id in list(belief_state.prior_confidences.keys()):
            old_confidence = belief_state.prior_confidences[claim_id]
            new_confidence = old_confidence * decay_factor
            belief_state.prior_confidences[claim_id] = new_confidence
            
            logger.info(
                f"[SESSION_RESET] {reset_type}: Decayed confidence for {claim_id} "
                f"from {old_confidence:.2f} to {new_confidence:.2f}"
            )
    
    def should_clear_context(
        self,
        belief_state: BeliefState,
        current_turn: int
    ) -> bool:
        """
        Determine if context should be completely cleared.
        
        More aggressive than just confidence decay.
        
        Args:
            belief_state: Current belief state
            current_turn: Current turn number
        
        Returns:
            True if context should be cleared
        """
        turns_since_update = current_turn - belief_state.last_updated_turn
        
        # Clear if extremely stale (e.g., 50+ turns)
        if turns_since_update > INACTIVITY_THRESHOLD * 2.5:
            logger.warning(
                f"[SESSION_RESET] Context extremely stale ({turns_since_update} turns), "
                "recommending full clear"
            )
            return True
        
        return False

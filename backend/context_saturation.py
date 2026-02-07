import logging
from backend.belief_state import BeliefState
from backend.confidence_tracker import EvidenceStrength

logger = logging.getLogger(__name__)

# Constants
CLARIFICATION_LIMIT = 2
SIMILARITY_THRESHOLD = 0.7


class ContextSaturationGuard:
    """
    Prevents annoying clarification loops.
    
    Rules:
    1. Stop asking after N attempts (default: 2)
    2. Don't repeat questions semantically
    3. Freeze decisions after saturation (no oscillation)
    
    Critical for user experience: "stop pestering me"
    """
    
    def should_stop_asking(self, belief_state: BeliefState) -> bool:
        """
        Check if clarification limit reached.
        
        Args:
            belief_state: Current belief state
        
        Returns:
            True if should stop asking for clarifications
        """
        if belief_state.clarification_attempts >= CLARIFICATION_LIMIT:
            logger.warning(
                f"[CONTEXT_SATURATION] Limit reached "
                f"({belief_state.clarification_attempts}/{CLARIFICATION_LIMIT})"
            )
            return True
        return False
    
    def is_repeat_question(
        self,
        new_question: str,
        belief_state: BeliefState, # Keep belief_state for clarifications_asked access
        threshold: float = 0.5
    ) -> bool:
        """
        Check if question is semantically similar to prior questions.
        
        Prevents asking the same thing in different wording:
        - "What's your diet?" vs "What dietary pattern do you follow?"
        
        Args:
            new_question: Proposed clarification question
            belief_state: Current belief state with question history
        
        Returns:
            True if question is too similar to a prior question
        """
        for prior_q in belief_state.clarifications_asked:
            similarity = self._semantic_similarity(new_question, prior_q)
            if similarity > threshold:
                logger.warning(
                    f"[CONTEXT_SATURATION] Repeat question blocked "
                    f"(similarity={similarity:.2f}): {new_question[:50]}..."
                )
                return True
        return False
    
    def _semantic_similarity(self, q1: str, q2: str) -> float:
        """
        Calculates similarity focusing on key concepts by removing noise.
        """
        stop_words = {"what", "is", "your", "could", "you", "tell", "me", "the", "a", "an", "do", "does", "provide", "please"}
        
        words1 = {w.strip("?") for w in q1.lower().split() if w.strip("?") not in stop_words}
        words2 = {w.strip("?") for w in q2.lower().split() if w.strip("?") not in stop_words}
        
        if not words1 or not words2:
            # Fallback to full words if everything was a stopword
            words1 = set(q1.lower().split())
            words2 = set(q2.lower().split())
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def can_upgrade_after_saturation(
        self,
        belief_state: BeliefState,
        evidence_strength: EvidenceStrength
    ) -> bool:
        """
        Prevent oscillation after saturation.
        
        Once saturated, Nutri should not flip to ALLOW without strong evidence.
        
        Args:
            belief_state: Current belief state
            evidence_strength: Strength of new evidence
        
        Returns:
            True if upgrade is allowed
        """
        if not belief_state.saturation_triggered:
            return True
        
        # Only allow upgrade with STRONG evidence after saturation
        can_upgrade = (evidence_strength == EvidenceStrength.STRONG)
        
        if not can_upgrade:
            logger.warning(
                f"[CONTEXT_SATURATION] Upgrade blocked after saturation "
                f"(evidence={evidence_strength.name}, need=STRONG)"
            )
        
        return can_upgrade

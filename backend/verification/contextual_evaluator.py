"""
Contextual Intelligence Evaluator.
Analyzes memory and belief state to produce contextual trace metadata.
Never fabricates memory. Logs all decisions.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.memory import SessionMemoryStore
from backend.belief_state import BeliefState
from backend.selective_memory import UserPreferences
from backend.session_reset_policy import SessionResetPolicy

logger = logging.getLogger(__name__)

class ContextualIntelligenceEvaluator:
    """
    Evaluates session context to populate trace.contextual_layer.
    Deterministic logic only. Zero LLM calls.
    """
    
    def __init__(self):
        self.reset_policy = SessionResetPolicy()

    def evaluate(
        self,
        session_id: str,
        user_message: str,
        memory_store: SessionMemoryStore,
        belief_state: BeliefState,
        user_prefs: Optional[UserPreferences],
        current_turn: int
    ) -> Dict[str, Any]:
        """Returns contextual_layer dict for trace attachment."""
        
        # 1. Fetch History
        history = memory_store.get_history(session_id, limit=10)
        
        # 2. Score Memory Relevance
        memory_hits, relevance_score, keywords = self._score_memory_relevance(history, user_message, current_turn)
        
        # 3. Assess Follow-up Eligibility
        follow_up_decision, follow_up_reason = self._assess_follow_up(belief_state, current_turn, user_message)
        
        # 4. Evaluate Personalization
        personalization_applied = False
        personalization_fields = []
        if user_prefs and user_prefs.should_inject(confidence_threshold=0.6):
            personalization_applied = True
            # Detect which fields have data above threshold (simplified check)
            for field in ["skill_level", "equipment", "dietary_constraints"]:
                if hasattr(user_prefs, field) and getattr(user_prefs, field):
                    personalization_fields.append(field)
                    
        # 5. Determine Follow-up Suggestion
        follow_up_suggestion = None
        if follow_up_decision == "eligible" and keywords:
            top_keyword = keywords[0]
            follow_up_suggestion = f"Since we were discussing {top_keyword}..."

        return {
            "memory_hits": memory_hits,
            "memory_relevance_score": round(relevance_score, 3),
            "follow_up_decision": follow_up_decision,
            "follow_up_reason": follow_up_reason,
            "follow_up_suggestion": follow_up_suggestion,
            "personalization_applied": personalization_applied,
            "personalization_fields": personalization_fields,
            "belief_state_active": bool(belief_state and belief_state.last_updated_turn > 0),
            "confidence": round(relevance_score, 3) 
        }

    def _score_memory_relevance(self, history: List[Dict], user_message: str, current_turn: int) -> tuple:
        """
        Deterministic scoring:
        - Keyword overlap (nouns/topics)
        - Recency weight
        - Role weight
        """
        if not history:
            return 0, 0.0, []
            
        msg_lower = user_message.lower()
        # Simple keyword extraction (excluding common stop words)
        stop_words = {"the", "and", "how", "what", "can", "you", "for", "with", "this", "that"}
        msg_keywords = [w for w in msg_lower.split() if len(w) > 3 and w not in stop_words]
        
        if not msg_keywords:
            return 0, 0.0, []
            
        total_score = 0.0
        hits = 0
        matched_keywords = []

        for i, entry in enumerate(history):
            content = entry.get("content", "").lower()
            role = entry.get("role")
            
            overlap = [kw for kw in msg_keywords if kw in content]
            if overlap:
                hits += 1
                matched_keywords.extend(overlap)
                
                # Base score from overlap
                entry_score = len(overlap) * 0.2
                
                # Recency weight (index 0 is most recent in get_history)
                # 0-3 turns: 1.0, 4-7: 0.7, 8+: 0.4
                recency_weight = 1.0 if i < 4 else (0.7 if i < 8 else 0.4)
                
                # Role weight (assistant responses are stronger context anchors)
                role_weight = 1.5 if role == "assistant" else 1.0
                
                total_score += entry_score * recency_weight * role_weight

        # Normalize score
        max_possible = len(msg_keywords) * 1.5 # Arbitrary cap
        final_score = min(1.0, total_score / max_possible) if max_possible > 0 else 0.0
        
        return hits, final_score, list(set(matched_keywords))

    def _assess_follow_up(self, belief_state: BeliefState, current_turn: int, user_message: str) -> tuple:
        """
        Implements rule-based eligibility check.
        """
        if not belief_state:
            return "not_applicable", "No belief state provided"
            
        # 1. Staleness check
        turns_since = current_turn - belief_state.last_updated_turn
        if turns_since > 15:
            return "ineligible", "Context is stale (> 15 turns)"
            
        # 2. Saturation check
        if belief_state.saturation_triggered:
            return "ineligible", "Saturation triggered (preventing loops)"
            
        # 3. Topic Shift check
        if self.reset_policy._detect_topic_shift(user_message):
            return "ineligible", "Explicit topic shift detected"
            
        # 4. Data check
        if not belief_state.prior_recommendations:
            return "eligible", "Session active but no scientific claims yet (Pure contextual)"
            
        return "eligible", "Continuous session with active scientific context"

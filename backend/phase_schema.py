"""
Phase Schema and Selector for Semantic Thinking Phases

Defines the allowed phase taxonomy and selection rules with:
- Confidence gates (silence > wrong structure)
- User preference adaptation
- Hard content validation
"""

from enum import Enum
from typing import Optional, List, Dict, Any
import logging
from backend.response_modes import ResponseMode
from backend.food_synthesis import IntentOutput

logger = logging.getLogger(__name__)


class ThinkingPhase(Enum):
    """Allowed semantic phase types (FIXED SET)."""
    DIAGNOSE = "diagnose"      # Identifying what's wrong
    MODEL = "model"            # Explaining underlying system
    PREDICT = "predict"        # What will happen if X changes
    RECOMMEND = "recommend"    # Actionable steps


# CANONICAL PHASE ORDERING (MANDATORY)
PHASE_ORDER = [
    ThinkingPhase.DIAGNOSE,
    ThinkingPhase.MODEL,
    ThinkingPhase.PREDICT,
    ThinkingPhase.RECOMMEND,
]


class PhaseSelector:
    """Rules-based phase selection with confidence gates and user adaptation."""
    
    @classmethod
    def select_phases(
        cls,
        message: str, 
        mode: ResponseMode, 
        intent: Optional[IntentOutput],
        user_prefs=None  # UserPreferences, avoiding circular import
    ) -> List[ThinkingPhase]:
        """
        Returns ordered list of phases (MAY BE EMPTY).
        
        🚨 CONFIDENCE GATE: Prevents over-phasing on ambiguous prompts.
        🧠 USER ADAPTATION: Adjusts phase selection based on skill level.
        
        Rules:
        - "How do I fix X?" → [DIAGNOSE, RECOMMEND]
        - "Why does X happen?" → [MODEL]
        - "What if I change X?" → [PREDICT, MODEL]
        - Simple question → []  # No phases
        """
        msg_lower = message.lower()
        
        # SCIENTIFIC DOMAIN: Detect topics like chemistry, nutrition, or compounds
        # This bypasses the confidence gate to ensure Retrieval-First policy.
        is_scientific = cls._is_scientific_query(message)
        
        # CONFIDENCE GATE: Silence > wrong structure
        if not is_scientific:
            if intent is None or (hasattr(intent, 'confidence') and intent.confidence < 0.6):
                return []  # Zero-phase fallback for ambiguous inputs
        
        phases = []
        
        # Pattern matching for phase selection
        
        # DIAGNOSTIC: "Why is", "what went wrong", problem statements
        diagnostic_phrases = [
            "why is", "what went wrong", "too dry", "too salty", "too sweet",
            "didn't rise", "turned out", "not right", "problem with", "overcooked",
            "undercooked", "burned", "didn't work", "failed", "ruined"
        ]
        is_diagnostic = any(phrase in msg_lower for phrase in diagnostic_phrases)
        
        # FIX REQUEST: "how do I fix", "how can I"
        is_fix_request = any(phrase in msg_lower for phrase in ["how do i fix", "how can i fix", "how to fix"])
        
        # PREDICTIVE: "what if", "what happens if"
        is_predictive = any(phrase in msg_lower for phrase in ["what if", "what happens if", "if i"])
        
        # PROCEDURAL: "how do i make", "recipe for", "steps to"
        is_procedural = any(phrase in msg_lower for phrase in [
            "how do i make", "how to make", "recipe for", "steps to", "walk me through"
        ])
        
        # WHY QUESTION: Explicit mechanism query
        is_why_question = PhaseSelector._explicit_why_question(message)
        
        # Build phase list based on patterns
        if is_fix_request:
            phases = [ThinkingPhase.DIAGNOSE, ThinkingPhase.RECOMMEND]
        elif is_predictive:
            phases = [ThinkingPhase.PREDICT, ThinkingPhase.MODEL]
        elif is_why_question or is_scientific:
            # Force MODEL for scientific queries to ensure retrieval/analysis
            phases = [ThinkingPhase.MODEL]
        elif is_diagnostic and not is_procedural:
            phases = [ThinkingPhase.DIAGNOSE]
        elif is_procedural:
            # Procedural mode typically doesn't need phases (direct steps)
            phases = []
        elif mode == ResponseMode.DIAGNOSTIC:
            # Sticky diagnostic mode
            phases = [ThinkingPhase.DIAGNOSE]
        else:
            # Default: no phases for conversation/simple queries
            phases = []
        
        # MEMORY-AWARE SHORT-CIRCUIT: Skip over-thinking if memory fully constrains answer
        if user_prefs and phases:
            # Check if user preferences fully constrain the answer
            has_equipment = user_prefs.equipment if hasattr(user_prefs, 'equipment') else []
            has_skill = user_prefs.skill_level if hasattr(user_prefs, 'skill_level') else None
            
            # If procedural query + equipment + skill already known:
            if is_procedural and has_equipment and has_skill:
                # Skip MODEL entirely, prefer direct RECOMMEND
                if ThinkingPhase.MODEL in phases:
                    phases.remove(ThinkingPhase.MODEL)
                    logger.info("[PHASE] Short-circuit: Memory fully constrains answer, skipping MODEL")
                
                # If only RECOMMEND would remain, return empty (zero-phase direct answer)
                if phases == [ThinkingPhase.RECOMMEND]:
                    phases = []
                    logger.info("[PHASE] Short-circuit: Direct RECOMMEND possible, using zero-phase path")
        
        # SKILL-LEVEL MODULATION: Adapt phases to user expertise
        if user_prefs and hasattr(user_prefs, 'skill_level') and user_prefs.skill_level == "beginner":
            if ThinkingPhase.MODEL in phases and not PhaseSelector._explicit_why_question(message):
                phases.remove(ThinkingPhase.MODEL)  # Deprioritize theory for beginners
                logger.debug("[PHASE] Beginner skill: Removed MODEL phase")
        
        # CANONICAL ORDERING: Sort phases before returning
        if phases:
            phases = sorted(phases, key=lambda p: PHASE_ORDER.index(p))
        
        # STRUCTURED LOGGING: Log decision with explicit reason
        PhaseSelector._log_phase_decision(
            phases=phases,
            reason=PhaseSelector._get_skip_reason(intent, is_procedural, is_diagnostic, is_why_question, is_fix_request, is_predictive),
            intent_confidence=intent.confidence if intent and hasattr(intent, 'confidence') else None,
            message_length=len(message),
            has_user_prefs=user_prefs is not None
        )
        
        return phases
    
    @staticmethod
    def _get_skip_reason(intent, is_procedural, is_diagnostic, is_why, is_fix, is_predictive) -> str:
        """Determine reason for phase selection."""
        if intent is None:
            return "no_intent"
        if hasattr(intent, 'confidence') and intent.confidence < 0.6:
            return "low_intent_confidence"
        if not (is_procedural or is_diagnostic or is_why or is_fix or is_predictive):
            return "no_semantic_match"
        if is_procedural:
            return "procedural_mode"
        return "phases_selected"
    
    @staticmethod
    def _log_phase_decision(phases: List[ThinkingPhase], reason: str, intent_confidence: Optional[float], message_length: int, has_user_prefs: bool):
        """Structured logging for phase decisions."""
        log_data = {
            "phase_count": len(phases),
            "phases": [p.value for p in phases] if phases else [],
            "reason": reason,
            "intent_confidence": round(intent_confidence, 2) if intent_confidence else None,
            "message_length": message_length,
            "has_user_prefs": has_user_prefs
        }
        
        if len(phases) == 0:
            logger.info(f"[PHASE] ZERO-PHASE: {log_data}")
        else:
            logger.info(f"[PHASE] SELECTED: {log_data}")
    
    @staticmethod
    def _explicit_why_question(message: str) -> bool:
        """Detects explicit 'why' questions."""
        return any(phrase in message.lower() for phrase in ["why does", "why is", "how come", "what causes"])
    
    @staticmethod
    def _is_scientific_query(message: str) -> bool:
        """Detects queries about chemistry, nutrition, or biology."""
        scientific_keywords = [
            "chemistry", "molecule", "compound", "protein", "enzyme", 
            "reaction", "nutrient", "vitamin", "mineral", "biological",
            "cellular", "molecular", "synthesis", "extract", "ingredient",
            "explain", "how does", "what is the mechanism", "capsaicin",
            "metabolism", "digestion", "absorption"
        ]
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in scientific_keywords)

    @staticmethod
    def validate_phase_content(phase: ThinkingPhase, content: str) -> bool:
        """
        HARD VALIDATION: Ensures phase content matches its semantic type.
        
        Returns False if content violates phase contract:
        - DIAGNOSE: Must identify problem, not give steps
        - MODEL: Must explain mechanism, not recommend actions
        - PREDICT: Must forecast outcome, not diagnose
        - RECOMMEND: Must give actionable steps, not theory
        """
        if not content or len(content.strip()) < 10:
            return False  # Content too short to be meaningful
        
        content_lower = content.lower()
        
        if phase == ThinkingPhase.RECOMMEND:
            # RECOMMEND must contain action verbs, not just explanations
            action_verbs = ["add", "reduce", "increase", "use", "try", "adjust", "heat", "cool", 
                          "mix", "stir", "fold", "whisk", "bake", "fry", "boil", "simmer"]
            return any(verb in content_lower for verb in action_verbs)
        
        if phase == ThinkingPhase.MODEL:
            # MODEL should explain mechanisms, not give instructions
            instruction_phrases = ["you should", "first step", "next,", "then add", "start by", "begin by"]
            return not any(phrase in content_lower for phrase in instruction_phrases)
        
        # DIAGNOSE and PREDICT have looser validation
        return True

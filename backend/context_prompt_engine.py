import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class ContextPromptEngine:
    """
    Generates clarifying questions when context is missing.
    
    Hard Rules:
    - Never ask about diagnoses directly
    - Never ask more than one question
    - Questions must be safe and non-intrusive
    """
    
    # Generic fallback question
    DEFAULT_QUESTION = (
        "This depends on individual factors like digestion and overall diet. "
        "Are you asking in a general sense, or for a specific dietary pattern?"
    )
    
    # Field-specific question templates
    FIELD_QUESTIONS = {
        "population": "Are you asking about this for a specific age group or health condition?",
        "dietary_context": "What's your current dietary pattern (e.g., omnivorous, vegetarian, low-carb)?",
        "dose_info": "Are you asking about a specific amount or frequency?",
    }
    
    def suggest_missing_context(self, missing_fields: List[str], claim_text: str = "") -> Optional[str]:
        """
        Generate at most one clarifying question based on missing fields.
        
        Args:
            missing_fields: List of missing context fields
            claim_text: Original claim for context
        
        Returns:
            A single clarifying question, or None if no question needed
        """
        if not missing_fields:
            return None
        
        # Prioritize critical fields
        for field in ["population", "dietary_context", "dose_info"]:
            if field in missing_fields:
                question = self.FIELD_QUESTIONS.get(field)
                if question:
                    logger.info(f"[TIER3_CONTEXT_PROMPT] Suggesting question for missing field: {field}")
                    return question
        
        # If no specific match, use default
        logger.info("[TIER3_CONTEXT_PROMPT] Using default context question")
        return self.DEFAULT_QUESTION
    
    def format_context_request(self, missing_fields: List[str], reason: str) -> str:
        """
        Format a context request with epistemic humility.
        
        Args:
            missing_fields: What's missing
            reason: Why it's needed
        
        Returns:
            Formatted request that sounds helpful, not evasive
        """
        question = self.suggest_missing_context(missing_fields)
        
        if not question:
            return reason
        
        # Combine reason with question
        return f"{reason} {question}"

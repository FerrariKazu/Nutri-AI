import logging
from typing import Literal

logger = logging.getLogger(__name__)

ClaimType = Literal["explanatory", "comparative", "action-implying"]

class ClaimClassifier:
    """
    Classifies claims by intent to determine strictness of RecommendationGate.
    
    - explanatory: "Why does X work?" → Less strict
    - comparative: "Is X better than Y?" → Moderate
    - action-implying: "Should I eat X?" → Strict gating
    """
    
    # Keywords for each type
    EXPLANATORY_KEYWORDS = [
        "why", "how", "what", "explain", "mechanism", "science behind",
        "works", "affects", "impacts"
    ]
    
    ACTION_KEYWORDS = [
        "should", "can i", "is it safe", "recommend", "good for",
        "help me", "improve", "reduce", "boost", "increase"
    ]
    
    COMPARATIVE_KEYWORDS = [
        "better", "worse", "best", "healthier", "more effective",
        "vs", "versus", "compared to", "difference between"
    ]
    
    def classify(self, claim_text: str) -> ClaimType:
        """
        Classify a claim by its intent.
        
        Args:
            claim_text: The claim to classify
        
        Returns:
            ClaimType: explanatory, comparative, or action-implying
        """
        text_lower = claim_text.lower()
        
        # Check for action-implying first (most strict)
        if any(keyword in text_lower for keyword in self.ACTION_KEYWORDS):
            logger.info(f"[TIER3_CLAIM_CLASSIFIER] action-implying: {claim_text[:50]}...")
            return "action-implying"
        
        # Check for comparative
        if any(keyword in text_lower for keyword in self.COMPARATIVE_KEYWORDS):
            logger.info(f"[TIER3_CLAIM_CLASSIFIER] comparative: {claim_text[:50]}...")
            return "comparative"
        
        # Check for explanatory
        if any(keyword in text_lower for keyword in self.EXPLANATORY_KEYWORDS):
            logger.info(f"[TIER3_CLAIM_CLASSIFIER] explanatory: {claim_text[:50]}...")
            return "explanatory"
        
        # Default to action-implying for safety
        logger.warning(f"[TIER3_CLAIM_CLASSIFIER] Defaulting to action-implying: {claim_text[:50]}...")
        return "action-implying"

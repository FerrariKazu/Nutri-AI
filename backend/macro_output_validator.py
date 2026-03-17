import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MacroOutputValidator:
    """
    Enforces Phase 1.6 Zero-Tolerance Numeric Policy.
    Blocks LLM from emitting any numbers or ranges in quantitative contexts.
    """
    
    # Regex for any digit. In governed quantitative modes, digits are strictly forbidden.
    NUMERIC_HALLUCINATION_PATTERN = re.compile(r"\d")
    
    # Whitelist for deterministic tags (Future proofing for Phase 2)
    DETERMINISTIC_TAG_PATTERN = re.compile(r'<macro\s+value="[^"]*"\s+source="deterministic_engine">')

    @classmethod
    def validate_response(cls, text: str, quantitative_required: bool) -> Dict[str, Any]:
        """
        Validates LLM output against governance rules.
        If quantitative_required is True, any number in the text triggers a violation unless whitelisted.
        """
        if not quantitative_required:
            return {"valid": True}

        # First, strip whitelisted tags to see if any raw numbers remain
        clean_text = cls.DETERMINISTIC_TAG_PATTERN.sub("", text)
        
        match = cls.NUMERIC_HALLUCINATION_PATTERN.search(clean_text)
        if match:
            trigger = match.group(0)
            logger.warning(f"[GOVERNANCE] Numeric hallucination detected in LLM output: '{trigger}'")
            return {
                "valid": False,
                "status": "quantitative_governance_violation",
                "message": f"Quantitative nutrition engine pending deterministic implementation. Prohibited numeric term detected: '{trigger}'",
                "trigger": trigger
            }
            
        return {"valid": True}

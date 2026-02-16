"""
Nutri Phase 10: Epistemic Explanation Control
Provides audience-calibrated explanations without changing facts or certainty.
"""

import logging
import json
from typing import Dict, List, Any
from backend.sensory.sensory_types import SensoryProfile, ExplanationResult

logger = logging.getLogger(__name__)

EXPLAINER_PROMPT = """You are an epistemic communication layer for a food science system.
Your task is to rewrite the provided scientific explanation for a specific audience mode.

TARGET MODE: {mode}

SCIENTIFIC FACTS (DO NOT CHANGE OR ADD):
{original_explanation}

UNCERTAINTIES & WARNINGS (MUST BE REFLECTED):
{warnings}

RULES:
1. One Truth: You must only use the provided facts. Do not invent new mechanisms.
2. No Certainty Inflation: If the original says "likely" or "potential", do not say "will" or "definitely".
3. Preservation: All warnings must be integrated or listed.
4. Mode Guidelines:
   - casual: Friendly, everyday language (e.g. "it gets really crispy").
   - culinary: Professional kitchen terminology (e.g. "Maillard-driven crust").
   - scientific: Academic chemical/physical terminology (the default).
   - technical: Engineering/process focus (e.g. "thermal-induced moisture loss gradient").

Return the explanation in the target mode style.
Also provide a 'confidence_statement' summarizing the overall reliability.

Return ONLY JSON:
{{
  "content": "rewritten explanation",
  "confidence_statement": "statement about reliability"
}}"""

class ExplanationLayer:
    """Adapts sensory explanations to different audience depths."""
    
    def __init__(self, engine: Any):
        self.engine = engine # FoodSynthesisEngine

    def explain(self, profile: SensoryProfile, mode: str = "scientific") -> ExplanationResult:
        if mode == "scientific":
            # Pass through the original logic-based explanation if scientific
            return ExplanationResult(
                mode="scientific",
                content=profile.scientific_explanation,
                preserved_warnings=profile.warnings,
                confidence_statement=f"Overall confidence is {profile.confidence.get('overall', 'medium') if isinstance(profile.confidence, dict) else profile.confidence}."
            )
            
        messages = [
            {"role": "system", "content": "You are a scientific communication specialist."},
            {"role": "user", "content": EXPLAINER_PROMPT.format(
                mode=mode,
                original_explanation=profile.scientific_explanation,
                warnings=", ".join(profile.warnings) if profile.warnings else "None"
            )}
        ]
        
        try:
            response = self.engine.llm.generate_text(messages, temperature=0.1, json_mode=True)
            data = json.loads(response)
            
            return ExplanationResult(
                mode=mode,
                content=data.get("content", ""),
                preserved_warnings=profile.warnings,
                confidence_statement=data.get("confidence_statement", "")
            )
        except Exception as e:
            logger.error(f"Explanation adaptation failed: {e}")
            return ExplanationResult(
                mode=mode,
                content=profile.scientific_explanation,
                preserved_warnings=profile.warnings,
                confidence_statement="Error generating calibrated explanation."
            )

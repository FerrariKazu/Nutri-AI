"""
Nutri Phase 11: Counterfactual Explanation Layer
Audience-calibrated explanations for sensory simulations.
"""

import logging
import json
from typing import Dict, List, Any
from backend.sensory.sensory_types import CounterfactualReport, ExplanationResult

logger = logging.getLogger(__name__)

CF_EXPLAINER_PROMPT = """You are an epistemic communication layer for a food science system.
Explain the following predicted sensory change for a specific audience mode.

TARGET MODE: {mode}

PARAMETER: {parameter}
DELTA: {delta}
PREDICTED CHANGES: {changes}
CONFIDENCE: {confidence}
MECHANISM: {mechanism}

RULES:
1. One Truth: Stick to the facts provided. Do not invent new effects.
2. Explain what changed, WHY it changed, and what did NOT change (based on dimensions not listed in PREDICTED CHANGES).
3. No Certainty Inflation: Preserve the stated confidence level in your tone.
4. Mode Guidelines:
   - casual: Simple, everyday terms (e.g. "it gets less salty").
   - culinary: Professional kitchen context (e.g. "reduces seasoning profile").
   - scientific: Formal mechanism focus (e.g. "decreased sodium-receptor stimulation").
   - technical: Impact on process variables and sensory vectors.

Return ONLY JSON:
{{
  "content": "rewritten explanation",
  "confidence_statement": "statement about reliability"
}}"""

class CounterfactualExplainer:
    """Adapts counterfactual reports to different audience depths."""
    
    def __init__(self, engine: Any):
        self.engine = engine

    def explain(self, report: CounterfactualReport, mode: str = "scientific") -> ExplanationResult:
        messages = [
            {"role": "system", "content": "You are a scientific communication specialist."},
            {"role": "user", "content": CF_EXPLAINER_PROMPT.format(
                mode=mode,
                parameter=report.parameter,
                delta=report.delta,
                changes=json.dumps(report.predicted_changes),
                confidence=report.confidence,
                mechanism=report.explanation
            )}
        ]
        
        try:
            response = self.engine.llm.generate_text(messages, temperature=0.1, json_mode=True)
            data = json.loads(response)
            
            return ExplanationResult(
                mode=mode,
                content=data.get("content", ""),
                preserved_warnings=[], 
                confidence_statement=data.get("confidence_statement", f"Confidence: {report.confidence}")
            )
        except Exception as e:
            logger.error(f"Counterfactual explanation failed: {e}")
            return ExplanationResult(
                mode=mode,
                content=report.explanation,
                preserved_warnings=[],
                confidence_statement=f"Raw report confidence: {report.confidence}"
            )

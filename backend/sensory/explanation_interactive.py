"""
Nutri Phase 12: Interactive Counterfactual Explanation Layer
Audience-calibrated explanations for multi-parameter sensory simulations.
"""

import logging
import json
from typing import Dict, List, Any
from backend.sensory.sensory_types import MultiCounterfactualReport, ExplanationResult

logger = logging.getLogger(__name__)

MULTI_CF_EXPLAINER_PROMPT = """You are an epistemic communication layer for a food science system.
Explain the following joint sensory impacts resulting from multiple parameter changes.

TARGET MODE: {mode}

ADJUSTMENTS: {deltas}
PREDICTED AGGREGATE CHANGES: {changes}
FEASIBILITY WARNINGS: {warnings}
CONFIDENCE: {confidence}

RULES:
1. One Truth: Stick to the provided data. Explain how parameters INTERACT (e.g. "heat and duration together cause drying").
2. Highlight Trade-offs: If one parameter improves a dimension while another reduces it, explain the net result.
3. Feasibility: If there are warnings, explain WHY they are physically or chemically risky.
4. Mode Guidelines:
   - casual: Simple, connected story of the changes.
   - culinary: focus on the resulting technique and flavor/texture profile.
   - scientific: focus on competing chemical/physical rates and equilibria.
   - technical: focus on vector summation and process constraints.

Return ONLY JSON:
{{
  "content": "rewritten explanation",
  "confidence_statement": "statement about reliability"
}}"""

class InteractiveExplainer:
    """Adapts multi-parameter reports to different audience depths."""
    
    def __init__(self, engine: Any):
        self.engine = engine

    def explain_multi(self, report: MultiCounterfactualReport, mode: str = "scientific") -> ExplanationResult:
        messages = [
            {"role": "system", "content": "You are a scientific communication specialist focusing on complex interactions."},
            {"role": "user", "content": MULTI_CF_EXPLAINER_PROMPT.format(
                mode=mode,
                deltas=json.dumps(report.deltas),
                changes=json.dumps(report.predicted_changes),
                warnings=", ".join(report.feasibility_warnings) if report.feasibility_warnings else "None",
                confidence=report.confidence
            )}
        ]
        
        try:
            response = self.engine.llm.generate_text(messages, temperature=0.1, json_mode=True)
            data = json.loads(response)
            
            return ExplanationResult(
                mode=mode,
                content=data.get("content", ""),
                preserved_warnings=report.feasibility_warnings, 
                confidence_statement=data.get("confidence_statement", f"Confidence: {report.confidence}")
            )
        except Exception as e:
            logger.error(f"Multi-parameter explanation failed: {e}")
            return ExplanationResult(
                mode=mode,
                content=report.explanation,
                preserved_warnings=report.feasibility_warnings,
                confidence_statement=f"Raw report confidence: {report.confidence}"
            )

"""
Nutri Phase 11: Counterfactual Engine
Deterministic simulation of sensory changes under parameter modifications.
"""

import logging
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import SensoryProfile, CounterfactualReport, SensitivityRanking
from backend.sensory.sensitivity_registry import SENSITIVITY_REGISTRY, MECHANISM_MAP

logger = logging.getLogger(__name__)

class CounterfactualEngine:
    """Simulates sensory changes without full re-optimization."""

    def simulate(self, base_profile: SensoryProfile, parameter: str, delta: float) -> CounterfactualReport:
        """
        Simulates the effect of a parameter change on a sensory profile.
        delta is expected to be in range [-1, 1] for normalized impact.
        """
        if parameter not in SENSITIVITY_REGISTRY:
            return CounterfactualReport(
                parameter=parameter,
                delta=delta,
                predicted_changes={},
                explanation=f"Parameter '{parameter}' is not registered in the sensitivity engine.",
                confidence="low"
            )

        effects = SENSITIVITY_REGISTRY[parameter]
        predicted_changes = {}
        
        for dimension, sensitivity in effects.items():
            # Linear projection of delta scaled by sensitivity
            change = sensitivity * delta
            predicted_changes[dimension] = round(change, 3)

        mechanism = MECHANISM_MAP.get(parameter, "Mechanistic relationship unknown.")
        
        # Determine magnitude class for explanation
        mag_class = "significant" if abs(delta) > 0.5 else "marginal" if abs(delta) < 0.2 else "moderate"
        direction = "increase" if delta > 0 else "decrease"
        
        explanation = f"A {mag_class} {direction} in {parameter} ({delta}) is projected to impact {len(predicted_changes)} sensory dimensions. " \
                      f"Underlying mechanism: {mechanism}"

        # Confidence logic: high if within normal ranges, medium if large delta
        confidence = "high" if abs(delta) <= 0.5 else "medium"

        return CounterfactualReport(
            parameter=parameter,
            delta=delta,
            predicted_changes=predicted_changes,
            explanation=explanation,
            confidence=confidence
        )

    def get_sensitivity_ranking(self, dimension: str, top_n: int = 3) -> SensitivityRanking:
        """Finds top parameters affecting a specific sensory dimension."""
        rankings = []
        for param, effects in SENSITIVITY_REGISTRY.items():
            if dimension in effects:
                rankings.append({
                    "parameter": param,
                    "strength": abs(effects[dimension])
                })
        
        # Sort by strength descending
        rankings.sort(key=lambda x: x["strength"], reverse=True)
        
        return SensitivityRanking(
            dimension=dimension,
            rankings=rankings[:top_n]
        )

"""
Nutri Phase 13: Interactive Iterative Design Loop
Manages iterative recipe refinement based on targeted sensory goals.
"""

import logging
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import (
    SensoryProfile, 
    IterationState, 
    ExplanationResult,
    MultiCounterfactualReport
)
from backend.sensory.sensitivity_registry import SENSITIVITY_REGISTRY

logger = logging.getLogger(__name__)

class InteractiveDesignLoop:
    """Orchestrates iterative refinement and suggests minimal adjustments."""

    def __init__(self, multi_engine: Any, interactive_explainer: Any):
        self.multi_engine = multi_engine
        self.explainer = interactive_explainer

    def run_iteration(self, 
                      current_profile: SensoryProfile, 
                      iteration_number: int,
                      proposed_deltas: Dict[str, float], 
                      target_goals: Dict[str, str],
                      mode: str = "scientific") -> IterationState:
        """
        Executes a design iteration: simulates changes, checks feasibility, 
        and generates suggestions toward target goals.
        """
        # 1. Simulate the proposed changes
        report = self.multi_engine.simulate_multi(current_profile, proposed_deltas)
        
        # 2. Audience-calibrated explanation
        explanation = self.explainer.explain_multi(report, mode=mode)
        
        # 3. Suggest minimal adjustments toward remaining targets
        recommendation = self._generate_recommendation(report.predicted_changes, target_goals)
        
        return IterationState(
            iteration_number=iteration_number,
            proposed_deltas=report.deltas,
            predicted_changes=report.predicted_changes,
            feasibility_warnings=report.feasibility_warnings,
            recommendation=recommendation,
            explanation=explanation
        )

    def _generate_recommendation(self, predicted_changes: Dict[str, float], target_goals: Dict[str, str]) -> str:
        """Determines what else is needed to reach target goals."""
        suggestions = []
        
        # Goal mapping: "high" -> 0.7, "low" -> 0.3, "medium" -> 0.5 (rough placeholders)
        # In this deterministic system, we suggest parameters with high sensitivity for missing goals.
        
        for dimension, target in target_goals.items():
            # For this Phase 13, we simplify: if user wants "high" but current change is low, find boosters.
            # Example: "crispness": "high"
            if target == "high" and predicted_changes.get(dimension, 0.0) < 0.4:
                booster = self._find_best_parameter(dimension, direction=1)
                if booster:
                    suggestions.append(f"To reach 'high' {dimension}, consider increasing {booster}.")
            elif target == "low" and predicted_changes.get(dimension, 0.0) > -0.4:
                suppressor = self._find_best_parameter(dimension, direction=-1)
                if suppressor:
                    suggestions.append(f"To reach 'low' {dimension}, consider increasing {suppressor} (if negative sensitivity) or decreasing boosters.")

        if not suggestions:
            return "Proposed changes align well with target goals."
            
        return " ".join(suggestions)

    def _find_best_parameter(self, dimension: str, direction: int) -> Optional[str]:
        """Finds the parameter with highest impact in the specified direction."""
        best_param = None
        max_impact = 0.0
        
        for param, effects in SENSITIVITY_REGISTRY.items():
            if dimension in effects:
                impact = effects[dimension] * direction
                if impact > max_impact:
                    max_impact = impact
                    best_param = param
                    
        return best_param

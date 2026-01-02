"""
Nutri Phase 12: Multi-Parameter Counterfactual Engine
Aggregates multiple parameter deltas and enforces feasibility constraints.
"""

import logging
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import SensoryProfile, MultiCounterfactualReport
from backend.sensory.sensitivity_registry import SENSITIVITY_REGISTRY, MECHANISM_MAP

logger = logging.getLogger(__name__)

class MultiCounterfactualEngine:
    """Simulates joint effects of multiple parameter changes with feasibility checks."""

    def simulate_multi(self, base_profile: SensoryProfile, deltas: Dict[str, float]) -> MultiCounterfactualReport:
        """
        Simulates the joint effect of multiple parameter changes.
        deltas: {parameter_name: delta_value} where delta is typically [-1, 1].
        """
        feasibility_warnings = self._check_feasibility(deltas)
        valid_deltas = {k: v for k, v in deltas.items() if k in SENSITIVITY_REGISTRY}
        
        predicted_changes = {}
        # Aggregate linear effects
        for param, delta in valid_deltas.items():
            effects = SENSITIVITY_REGISTRY[param]
            for dimension, sensitivity in effects.items():
                change = sensitivity * delta
                predicted_changes[dimension] = predicted_changes.get(dimension, 0.0) + change

        # Handle Interaction Effects (Phase 12 addition)
        self._apply_interaction_effects(valid_deltas, predicted_changes)

        # Round all results
        predicted_changes = {k: round(v, 3) for k, v in predicted_changes.items()}

        # Explanation generation
        explanation = self._generate_joint_explanation(valid_deltas, predicted_changes)

        # Confidence logic: decreases with number of parameters and magnitude
        confidence = "high" if len(valid_deltas) <= 2 and all(abs(v) <= 0.4 for v in valid_deltas.values()) else "medium"
        if feasibility_warnings:
            confidence = "low"

        return MultiCounterfactualReport(
            deltas=valid_deltas,
            predicted_changes=predicted_changes,
            feasibility_warnings=feasibility_warnings,
            explanation=explanation,
            confidence=confidence
        )

    def _check_feasibility(self, deltas: Dict[str, float]) -> List[str]:
        warnings = []
        
        # 1. High Heat + High Surface Moisture (Conflict)
        if deltas.get("heat_intensity", 0) > 0.5 and deltas.get("surface_moisture", 0) > 0.5:
            warnings.append("PHYSICAL CONFLICT: Maintaining high surface moisture while applying intense heat is energy-intensive and delay Maillard reactions.")

        # 2. Extreme Salt Concentration
        if deltas.get("salt_pct", 0) > 0.8:
            warnings.append("CHEMICAL CAP: Salt levels approaching saturation may inhibit protein solubility and denature enzymes prematurely.")

        # 3. Conflicting Moisture Controls
        if deltas.get("surface_moisture", 0) > 0.5 and deltas.get("sear_duration_min", 0) > 0.5:
            warnings.append("PROCESS LIMIT: Extended searing with high surface moisture results in steaming rather than browning.")

        return warnings

    def _apply_interaction_effects(self, deltas: Dict[str, float], changes: Dict[str, float]):
        """Non-linear interactions between parameters."""
        
        # Interaction: Heat + Duration = Compounded moisture loss
        if "heat_intensity" in deltas and "sear_duration_min" in deltas:
            if deltas["heat_intensity"] > 0 and deltas["sear_duration_min"] > 0:
                # Combi effect: dryer interior
                interaction_delta = deltas["heat_intensity"] * deltas["sear_duration_min"] * 0.3
                changes["moistness"] = changes.get("moistness", 0.0) - interaction_delta
                changes["tenderness"] = changes.get("tenderness", 0.0) - interaction_delta * 0.5

        # Interaction: Salt + Rest Time = Improved moisture redistribution
        if "salt_pct" in deltas and "rest_time_min" in deltas:
            if deltas["salt_pct"] > 0 and deltas["rest_time_min"] > 0:
                interaction_boost = deltas["salt_pct"] * deltas["rest_time_min"] * 0.2
                changes["moistness"] = changes.get("moistness", 0.0) + interaction_boost

    def _generate_joint_explanation(self, deltas: Dict[str, float], changes: Dict[str, float]) -> str:
        parts = [f"Simulated {len(deltas)} parameter adjustments."]
        top_sensory = sorted(changes.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        
        if top_sensory:
            parts.append(f"Primary impacts on: {', '.join([f'{k} ({v:+.2f})' for k, v in top_sensory])}.")
        
        return " ".join(parts)

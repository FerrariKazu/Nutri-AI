"""
Nutri Phase 9: Preference Projection Layer
Projects explicit user signals onto the sensory Pareto frontier for deterministic variant selection.
"""

import logging
from typing import Dict, List, Any
from backend.sensory.sensory_types import (
    SensoryProfile, 
    SensoryVariant, 
    ParetoFrontierResult, 
    UserPreferences, 
    SelectionResult
)

logger = logging.getLogger(__name__)

class PreferenceProjector:
    """Maps explicit user signals to objective weight vectors (Deterministic)."""
    
    def project(self, prefs: UserPreferences) -> Dict[str, float]:
        # Default weights for primary objectives
        weights = {
            "tenderness": 1.0,
            "crispness": 1.0,
            "moistness": 1.0,
            "chewiness": -1.0 # Minimize
        }
        
        # Apply Eating Style Projection
        if prefs.eating_style == "comfort":
            weights["tenderness"] += 1.0
            weights["moistness"] += 0.5
            weights["chewiness"] -= 0.5
        elif prefs.eating_style == "indulgent":
            weights["crispness"] += 1.0
            # Indulgent often implies richness/flavor which we might map to moistness
            weights["moistness"] += 0.5
        elif prefs.eating_style == "light":
            weights["moistness"] += 1.0
            weights["crispness"] += 0.5
        elif prefs.eating_style == "performance":
            weights["tenderness"] += 1.0
            weights["chewiness"] -= 1.0 # High prioritize on easy mastication
            
        # Apply Texture Preference Projection
        if prefs.texture_preference == "soft":
            weights["tenderness"] += 2.0
            weights["crispness"] -= 1.0
        elif prefs.texture_preference == "crisp":
            weights["crispness"] += 2.0
            weights["tenderness"] -= 0.5
            
        return weights

class VariantSelector:
    """Selects the highest-scoring variant from a Pareto frontier based on projected weights."""
    
    def __init__(self):
        self.projector = PreferenceProjector()

    def select(self, frontier: ParetoFrontierResult, prefs: UserPreferences) -> SelectionResult:
        if not frontier.variants:
            raise ValueError("Pareto frontier is empty.")
            
        weights = self.projector.project(prefs)
        variant_scores = {}
        
        for variant in frontier.variants:
            score = self._calculate_score(variant.profile, weights)
            variant_scores[variant.name] = score
            
        # Select best
        best_name = max(variant_scores, key=variant_scores.get)
        selected = next(v for v in frontier.variants if v.name == best_name)
        
        # Generate explaining reasoning
        reasoning = self._generate_reasoning(selected, prefs, weights)
        
        return SelectionResult(
            selected_variant=selected,
            reasoning=reasoning,
            scores=variant_scores
        )

    def _calculate_score(self, profile: SensoryProfile, weights: Dict[str, float]) -> float:
        score = 0.0
        # Flatten profile for scoring
        attrs = {}
        attrs.update(profile.texture)
        attrs.update(profile.flavor)
        attrs.update(profile.mouthfeel)
        
        for attr, weight in weights.items():
            val = attrs.get(attr, 0.0)
            score += val * weight
            
        return score

    def _generate_reasoning(self, selected: SensoryVariant, prefs: UserPreferences, weights: Dict[str, float]) -> List[str]:
        reasons = []
        reasons.append(f"Preference Profile: Eating Style='{prefs.eating_style}', Texture='{prefs.texture_preference}'.")
        
        # Sort weights to see top priorities
        sorted_weights = sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True)
        top_priorities = [k for k, v in sorted_weights[:2] if v > 0]
        de_priorities = [k for k, v in sorted_weights if v < 0][:1]
        
        if top_priorities:
            reasons.append(f"Prioritized: {', '.join(top_priorities)}.")
        if de_priorities:
            reasons.append(f"De-emphasized: {', '.join(de_priorities)}.")
            
        return reasons

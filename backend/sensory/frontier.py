"""
Nutri Phase 8: Sensory Pareto Frontier
Implements multi-objective variant generation and Pareto dominance filtering.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import (
    SensoryProfile, 
    SensoryVariant, 
    ParetoFrontierResult
)
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)

VARIANT_GEN_PROMPT = """Generate a specific technique variant of the following recipe that favors the target sensory objective.
Target Objective: {objective_name} ({objective_goal})

Recipe:
{recipe}

Rules:
1. Obey original constraints.
2. Adjust techniques (heat intensity, duration, sequencing) to push towards the target objective.
3. Keep core ingredients the same.
4. Provide a 2-sentence explanation of the trade-offs (what is gained vs what is sacrificed).

Return ONLY JSON:
{{
  "variant_name": "{objective_name}-Forward",
  "recipe": "full recipe text",
  "trade_offs": "explanation"
}}"""

class SensoryParetoOptimizer:
    """Generates recipe variants on the sensory Pareto frontier."""
    def __init__(self, engine: Any, predictor: Any):
        self.engine = engine # FoodSynthesisEngine
        self.predictor = predictor # SensoryPredictor
        self.default_objectives = {
            "tenderness": "maximize",
            "crispness": "maximize",
            "moistness": "maximize",
            "chewiness": "minimize"
        }

    def generate_frontier(self, initial_recipe: str, properties_list: List[Any], provenance: Any, objectives: Optional[Dict[str, str]] = None) -> ParetoFrontierResult:
        obj_dict = objectives or self.default_objectives
        
        # Step 1: Generate Variants
        targets = [
            {"name": "Crisp", "goal": "maximize"},
            {"name": "Tender", "goal": "maximize"},
            {"name": "Balanced", "goal": "optimized trade-off"}
        ]
        
        raw_variants = []
        for target in targets:
            logger.info(f"Generating {target['name']} variant...")
            messages = [
                {"role": "system", "content": "You are a sensory technique optimizer."},
                {"role": "user", "content": VARIANT_GEN_PROMPT.format(
                    objective_name=target['name'],
                    objective_goal=target['goal'],
                    recipe=initial_recipe
                )}
            ]
            try:
                response = self.engine.llm.generate_text(messages, temperature=0.2, json_mode=True)
                # Use robust parsing from similar components if needed, or simple json.loads
                data = json.loads(response)
                raw_variants.append(data)
            except Exception as e:
                logger.error(f"Variant generation failed for {target['name']}: {e}")

        # Step 2: Predict Profiles for each variant
        variants = []
        for rv in raw_variants:
            profile = self.predictor.predict(rv['recipe'], properties_list, provenance)
            variants.append(SensoryVariant(
                name=rv['variant_name'],
                recipe=rv['recipe'],
                profile=profile,
                trade_offs=rv.get('trade_offs', "")
            ))

        # Step 3: Dominance Filtering
        filtered_variants = self._filter_dominated(variants, obj_dict)

        return ParetoFrontierResult(
            variants=filtered_variants,
            objectives=obj_dict
        )

    def _filter_dominated(self, variants: List[SensoryVariant], objectives: Dict[str, str]) -> List[SensoryVariant]:
        """Implements Pareto dominance filtering."""
        non_dominated = []
        
        for i, v1 in enumerate(variants):
            is_dominated = False
            for j, v2 in enumerate(variants):
                if i == j: continue
                if self._dominates(v2, v1, objectives):
                    is_dominated = True
                    break
            if not is_dominated:
                non_dominated.append(v1)
        
        return non_dominated

    def _dominates(self, v1: SensoryVariant, v2: SensoryVariant, objectives: Dict[str, str]) -> bool:
        """v1 dominates v2 if it's better or equal in all, and better in at least one."""
        p1 = self._get_values_dict(v1.profile)
        p2 = self._get_values_dict(v2.profile)
        
        at_least_one_better = False
        for attr, goal in objectives.items():
            val1 = p1.get(attr, 0.0)
            val2 = p2.get(attr, 0.0)
            
            if goal == "maximize":
                if val1 < val2: return False
                if val1 > val2: at_least_one_better = True
            elif goal == "minimize":
                if val1 > val2: return False
                if val1 < val2: at_least_one_better = True
        
        return at_least_one_better

    def _get_values_dict(self, profile: SensoryProfile) -> Dict[str, float]:
        """Flattens sensory profile attributes for easier comparison."""
        values = {}
        values.update(profile.texture)
        values.update(profile.flavor)
        values.update(profile.mouthfeel)
        return values

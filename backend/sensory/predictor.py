"""
Nutri Phase 6: Sensory Predictor
Predicts sensory profiles based on physical properties and cooking techniques.
"""

import logging
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import SensoryProfile, PhysicalProperties
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)

SENSORY_PREDICTION_PROMPT = """Predict the advanced sensory profile (Phase 6.5) for this recipe based on physical properties and techniques.

Recipe:
{recipe}

Aggregated Physical Properties:
{properties}

Detected Techniques:
{techniques}

Mandatory Guidelines:
1. CRISPNESS SPLIT:
   - surface_crust: Driven by dry heat, dehydration, and Maillard browning at the surface.
   - structural_crispness: Bulk rigidity (e.g. starch gelatinization, fiber strength).
   - Total crispness should be a weighted combination.
   - RULE: Meat crispness must not exceed realistic bounds (crust can be high, structural is low).

2. MUSCLE FIBER MODEL (Apply if is_muscle_tissue is True):
   - High heat intensity increases fiber shortening (chewiness) and moisture loss (reducing tenderness).
   - Balance tenderness against fat_level (lubrication).

3. SWEETNESS CORRECTION:
   - Sweetness comes ONLY from sugar_content_g or concentration via evaporation.
   - Maillard reaction DOES NOT produce sweetness; it increases complexity and umami.

4. SENSORY TIMELINE:
   - initial_bite: Focus on surface crust, initial salt release, and volatile aromatics.
   - mid_palate: Focus on fat melt, umami depth, and internal moisture release.
   - finish: Focus on lingering richness, astringency, or savory aftertaste.

5. PROVIDE GRANULAR CONFIDENCE:
   - Downgrade nutrition confidence if open_nutrition was used.
   - Sensory physics and chemical flavor should reflect mechanistic certainty.

Return ONLY JSON:
{{
  "texture": {{
    "surface_crust": float,
    "structural_crispness": float,
    "crispness": float,
    "tenderness": float,
    "chewiness": float,
    "moistness": float
  }},
  "flavor": {{
    "umami": float,
    "saltiness": float,
    "sweetness": float,
    "bitterness": float
  }},
  "mouthfeel": {{
    "richness": float,
    "coating": float,
    "astringency": float
  }},
  "sensory_timeline": {{
    "initial_bite": {{ "texture": "desc", "flavor": "desc", "mouthfeel": "desc" }},
    "mid_palate": {{ "texture": "desc", "flavor": "desc", "mouthfeel": "desc" }},
    "finish": {{ "texture": "desc", "flavor": "desc", "mouthfeel": "desc" }}
  }},
  "confidence_scores": {{
    "nutrition": "high|medium|low",
    "sensory_physics": "high|medium|low",
    "chemical_flavor": "high|medium|low"
  }},
  "explanation": "Scientific mechanistic justification"
}}"""

class SensoryPredictor:
    """Predicts advanced sensory profiles (Phase 6.5)."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.llm = LLMQwen3(agent_name="explainer_agent", model_name=model_name)
        logger.info("SensoryPredictor initialized (Phase 6.5)")

    def predict(
        self,
        recipe: str,
        properties_list: List[PhysicalProperties],
        provenance: Dict[str, bool]
    ) -> SensoryProfile:
        """
        Combines properties and recipe context to predict sensory profile.
        """
        # Aggregate properties
        total_props = PhysicalProperties()
        is_muscle = False
        for p in properties_list:
            total_props.moisture_content += p.moisture_content
            total_props.fat_fraction += p.fat_fraction
            total_props.protein_density += p.protein_density
            total_props.maillard_browning_potential += p.maillard_browning_potential
            total_props.polyphenol_content += p.polyphenol_content
            total_props.free_amino_acids += p.free_amino_acids
            total_props.sodium_content_mg += p.sodium_content_mg
            total_props.sugar_content_g += p.sugar_content_g
            if p.is_muscle_tissue:
                is_muscle = True
                
        # Simple averaging/scaling for prompt context
        count = len(properties_list) if properties_list else 1
        avg_props = {
            "maillard_potential": total_props.maillard_browning_potential / count,
            "fat_level": total_props.fat_fraction / count,
            "protein_level": total_props.protein_density / count,
            "sugar_g": total_props.sugar_content_g,
            "is_muscle": is_muscle,
            "sodium_mg": total_props.sodium_content_mg
        }

        # Detect techniques
        techniques = []
        rec_lower = recipe.lower()
        if any(w in rec_lower for w in ["bake", "roast", "fry", "sear", "grill"]):
            techniques.append("dry heat")
        if any(w in rec_lower for w in ["boil", "steam", "simmer", "poach"]):
            techniques.append("moist heat")
        if "emuls" in rec_lower:
            techniques.append("emulsification")

        messages = [
            {"role": "system", "content": "You are a senior sensory scientist. Output Phase 6.5 advanced data."},
            {"role": "user", "content": SENSORY_PREDICTION_PROMPT.format(
                recipe=recipe,
                properties=str(avg_props),
                techniques=", ".join(techniques)
            )}
        ]

        try:
            response = self.llm.generate_text(messages, max_new_tokens=1500, temperature=0.1, json_mode=True)
            import json
            data = self._parse_json(response)
            
            # 1. Split Crispness weighted calculation (Post-check)
            tex = data.get("texture", {})
            sc = tex.get("surface_crust", 0.0)
            stc = tex.get("structural_crispness", 0.0)
            # Apply weighted rule if not already handled by LLM
            tex["crispness"] = 0.7 * sc + 0.3 * stc
            
            # 2. Form profile
            scores = data.get("confidence_scores", {})
            profile = SensoryProfile(
                texture=tex,
                flavor=data.get("flavor", {}),
                mouthfeel=data.get("mouthfeel", {}),
                sensory_timeline=data.get("sensory_timeline", {}),
                scientific_explanation=data.get("explanation", ""),
                provenance=provenance,
                confidence={
                    "nutrition": scores.get("nutrition", "medium"),
                    "sensory_physics": scores.get("sensory_physics", "medium"),
                    "chemical_flavor": scores.get("chemical_flavor", "medium"),
                    "overall": "medium"
                }
            )
            
            # 3. Adjust Granular Confidence based on provenance
            if provenance["used_open_nutrition"]:
                profile.confidence["nutrition"] = "low"
                profile.warnings.append("Confidence reduced: utilizing secondary 'open_nutrition' store.")
            
            if provenance["used_recipes_store"]:
                profile.confidence["sensory_physics"] = "medium"
                profile.warnings.append("Confidence moderated: sensory patterns influenced by structural 'recipes' store.")

            # Overall is the lowest dominant uncertainty
            conf_map = {"high": 3, "medium": 2, "low": 1}
            min_score = min(conf_map.get(v, 2) for v in profile.confidence.values() if isinstance(v, str))
            inv_map = {3: "high", 2: "medium", 1: "low"}
            profile.confidence["overall"] = inv_map[min_score]

            return profile
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return SensoryProfile(scientific_explanation=f"Error: {e}")

    def _parse_json(self, response: str) -> Dict[str, Any]:
        import json
        try:
            clean_res = response.strip()
            # Handle possible cutting off at the end
            if clean_res.endswith('...'):
                clean_res = clean_res[:-3]
            
            # Try to find the last complete JSON block
            import re
            match = re.search(r'(\{.*\}|\[.*\])', clean_res, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    # If it failed, maybe it's truncated at the end
                    truncated = match.group(1)
                    # Try to close open braces (very naive)
                    if truncated.count('{') > truncated.count('}'):
                        truncated += '}' * (truncated.count('{') - truncated.count('}'))
                    try:
                        return json.loads(truncated)
                    except:
                        pass
            return json.loads(clean_res)
        except:
            pass
        return {}

"""
Nutri Phase 6: Sensory Property Mapper
Maps ingredients to physical and chemical properties based on retrieved scientific data.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from backend.sensory.sensory_types import PhysicalProperties
from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)

PROPERTY_MAPPER_PROMPT = """Extract the physical and chemical properties for the following ingredient based only on the provided scientific text.

Ingredient: "{ingredient}"
Amount (g): {amount_g}

Context:
{context}

Target Properties:
- moisture_content (0-1)
- fat_fraction (0-1)
- protein_density (0-1)
- starch_gelatinization_potential (0-1)
- maillard_browning_potential (0-1)
- polyphenol_content (0-1)
- free_amino_acids (0-1)
- sodium_content_mg (total mg in the given amount)
- sugar_content_g (total g of simple sugars in the given amount)
- is_muscle_tissue (boolean: true if this is animal meat, fish, or poultry)

Rules:
1. Base values on 100g standards adjusted for the total amount of {amount_g}g.
2. If text is missing data, default to 0.0/false but note the uncertainty.
3. Use Maillard potential for ingredients with high reducing sugars and proteins.

Return ONLY JSON:
{{
  "moisture_content": float,
  "fat_fraction": float,
  "protein_density": float,
  "starch_gelatinization_potential": float,
  "maillard_browning_potential": float,
  "polyphenol_content": float,
  "free_amino_acids": float,
  "sodium_content_mg": float,
  "sugar_content_g": float,
  "is_muscle_tissue": bool
}}"""

class SensoryPropertyMapper:
    """Extracts physical/chemical properties from retrieval results."""
    
    def __init__(self, model_name: str = "qwen3:8b"):
        self.llm = LLMQwen3(model_name=model_name)
        logger.info("SensoryPropertyMapper initialized")

    def map_ingredient(
        self, 
        ingredient: str, 
        amount_g: float, 
        retriever: Any
    ) -> (PhysicalProperties, Dict[str, bool]):
        """
        Maps an ingredient to its physical properties using policy-governed retrieval.
        """
        logger.info(f"Mapping properties for {ingredient} ({amount_g}g)")
        
        # Policy: Primary stores (Chemistry, Science, USDA)
        # Secondary: open_nutrition
        
        provenance = {
            "used_recipes_store": False,
            "used_open_nutrition": False
        }
        
        # 1. Retrieve from primary stores
        docs = retriever.retrieve(f"{ingredient} chemical physical properties sugar muscle tissue protein", top_k=3)
        
        context_parts = []
        for doc in docs:
            # Metadata-based policy enforcement
            if hasattr(doc, 'source'):
                if "recipes" in str(doc.source).lower():
                    provenance["used_recipes_store"] = True
                if "open_nutrition" in str(doc.source).lower():
                    provenance["used_open_nutrition"] = True
            
            context_parts.append(doc.text)
            
        context = "\n".join(context_parts)
        
        # 2. Extract using LLM
        messages = [
            {"role": "system", "content": "You are a food chemistry data extractor."},
            {"role": "user", "content": PROPERTY_MAPPER_PROMPT.format(
                ingredient=ingredient, 
                amount_g=amount_g, 
                context=context
            )}
        ]
        
        try:
            # Increased max_new_tokens to 2048 to allow for "Thinking" process without truncation
            response = self.llm.generate_text(messages, max_new_tokens=2048, temperature=0.0, json_mode=True)
            data = json.loads(response)
            
            props = PhysicalProperties(
                moisture_content=float(data.get("moisture_content", 0)),
                fat_fraction=float(data.get("fat_fraction", 0)),
                protein_density=float(data.get("protein_density", 0)),
                starch_gelatinization_potential=float(data.get("starch_gelatinization_potential", 0)),
                maillard_browning_potential=float(data.get("maillard_browning_potential", 0)),
                polyphenol_content=float(data.get("polyphenol_content", 0)),
                free_amino_acids=float(data.get("free_amino_acids", 0)),
                sodium_content_mg=float(data.get("sodium_content_mg", 0)),
                sugar_content_g=float(data.get("sugar_content_g", 0)),
                is_muscle_tissue=bool(data.get("is_muscle_tissue", False))
            )
            return props, provenance
            
        except Exception as e:
            logger.error(f"Failed to map properties for {ingredient}: {e}")
            return PhysicalProperties(), provenance

    def _parse_json(self, response: str) -> Dict[str, Any]:
        # Redundant but kept for safety if needed internally
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        return {}

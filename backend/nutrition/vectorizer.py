"""
Nutri Phase 5: Nutrition Vectorizer

Converts ingredient names into numeric nutrition vectors using retrieved USDA data.
Extracts standard values (per 100g) using LLM parsing of retrieved text.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.llm_qwen3 import LLMQwen3

logger = logging.getLogger(__name__)


@dataclass
class NutritionVector:
    """Nutritional values per 100g of ingredient."""
    calories: float = 0.0  # kcal
    protein: float = 0.0   # g
    fat: float = 0.0       # g
    carbs: float = 0.0     # g
    fiber: float = 0.0     # g
    sugar: float = 0.0     # g
    sodium: float = 0.0    # mg
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
    
    def __add__(self, other: 'NutritionVector') -> 'NutritionVector':
        return NutritionVector(
            calories=self.calories + other.calories,
            protein=self.protein + other.protein,
            fat=self.fat + other.fat,
            carbs=self.carbs + other.carbs,
            fiber=self.fiber + other.fiber,
            sugar=self.sugar + other.sugar,
            sodium=self.sodium + other.sodium
        )
    
    def __mul__(self, scalar: float) -> 'NutritionVector':
        return NutritionVector(
            calories=self.calories * scalar,
            protein=self.protein * scalar,
            fat=self.fat * scalar,
            carbs=self.carbs * scalar,
            fiber=self.fiber * scalar,
            sugar=self.sugar * scalar,
            sodium=self.sodium * scalar
        )


EXTRACTION_PROMPT = """You are a nutrition data extractor.

Task: Extract nutritional values for 100g of the specific ingredient from the provided text.

Ingredient: "{ingredient}"

Context:
{context}

Extract the following values per 100g (default to 0 if not found):
- calories (kcal)
- protein (g)
- fat (g)
- carbs (g)
- fiber (g)
- sugar (g)
- sodium (mg)

Return valid JSON only:
{{
  "calories": float,
  "protein": float,
  "fat": float,
  "carbs": float,
  "fiber": float,
  "sugar": float,
  "sodium": float
}}"""


class NutritionVectorizer:
    """Converts ingredients to nutrition vectors."""
    
    def __init__(self, model_name: str = "qwen3:8b"):
        self.llm = LLMQwen3(model_name=model_name)
        self.cache: Dict[str, NutritionVector] = {}
        logger.info("NutritionVectorizer initialized")
        
    def vectorize(self, ingredient: str, retriever: Any) -> NutritionVector:
        """
        Get nutrition vector for an ingredient.
        
        Args:
            ingredient: Name of ingredient (e.g. "Chicken breast")
            retriever: Retriever instance to look up data
            
        Returns:
            NutritionVector per 100g
        """
        # Check cache
        if ingredient in self.cache:
            return self.cache[ingredient]
        
        logger.info(f"Vectorizing ingredient: {ingredient}")
        
        # Retrieve context (USDA Foundation/Branded preferred)
        # We assume the retriever handles index selection or we search broad
        docs = retriever.retrieve(f"{ingredient} nutrition data", top_k=3)
        context = "\n".join([d.text for d in docs])
        
        # Extract using LLM
        messages = [
            {"role": "system", "content": "You are a precise data extractor."},
            {"role": "user", "content": EXTRACTION_PROMPT.format(ingredient=ingredient, context=context)}
        ]
        
        try:
            response = self.llm.generate_text(messages, max_new_tokens=256, temperature=0.0)
            data = self._parse_json(response)
            
            vector = NutritionVector(
                calories=float(data.get("calories", 0)),
                protein=float(data.get("protein", 0)),
                fat=float(data.get("fat", 0)),
                carbs=float(data.get("carbs", 0)),
                fiber=float(data.get("fiber", 0)),
                sugar=float(data.get("sugar", 0)),
                sodium=float(data.get("sodium", 0))
            )
            
            # Cache and return
            self.cache[ingredient] = vector
            return vector
            
        except Exception as e:
            logger.error(f"Failed to vectorize {ingredient}: {e}")
            
            # Keyword Fallback
            logger.info(f"Using keyword fallback for {ingredient} nutrition")
            common_low = ingredient.lower()
            if "chicken" in common_low:
                v = NutritionVector(calories=165, protein=31, fat=3.6)
            elif "rice" in common_low:
                v = NutritionVector(calories=130, protein=2.7, carbs=28)
            elif "soy" in common_low:
                v = NutritionVector(calories=53, protein=8, carbs=4.9, sodium=5493)
            else:
                v = NutritionVector()
                
            self.cache[ingredient] = v
            return v
    
    def _parse_json(self, response: str) -> Dict[str, float]:
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception:
            pass
        return {}


INGREDIENT_PARSER_PROMPT = """Extract the quantitative ingredients from this recipe into a JSON list.

Recipe:
{recipe}

REQUIRED JSON Format:
[
  {{ "name": "Ingredient Name", "amount_g": float, "original_text": "Original text" }}
]

Rules:
- 1 tbsp = 15g, 1 cup = 240g, 1 tsp = 5g.
- If no unit, estimate 100g for mains, 5g for spices.
- Return ONLY the JSON list."""

class IngredientExtractor:
    """Extracts ingredients and amounts from recipe text."""
    
    def __init__(self, model_name: str = "qwen3:8b"):
        self.llm = LLMQwen3(model_name=model_name)
    
    def extract(self, recipe_text: str) -> List[Dict[str, Any]]:
        """Extract ingredients with amounts in grams. Falls back to regex if LLM fails."""
        if not recipe_text:
            return []
            
        messages = [
            {"role": "system", "content": "You are a precise ingredient extractor."},
            {"role": "user", "content": INGREDIENT_PARSER_PROMPT.format(recipe=recipe_text)}
        ]
        
        try:
            # Attempt LLM extraction
            response = self.llm.generate_text(messages, max_new_tokens=512, temperature=0.0)
            result = self._parse_json(response)
            if result:
                return result
        except Exception as e:
            logger.error(f"LLM Ingredient extraction failed: {e}")

        # Regex Fallback
        logger.info("Using regex fallback for ingredient extraction")
        import re
        ingredients = []
        # Pattern: - [Amount][Unit] [Name] or [Amount]g [Name]
        lines = recipe_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or not (line.startswith('-') or line[0].isdigit()):
                continue
            
            # Match patterns like "- 150g Chicken breast" or "150 Chicken breast" or "- 2 tbsp Soy"
            match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|oz|tbsp|tsp|cup)?\s*([a-zA-Z\s]+)', line)
            if match:
                try:
                    amount = float(match.group(1))
                    unit = match.group(2)
                    name = match.group(3).strip()
                    
                    # Simple weight conversions
                    amount_g = amount
                    if unit == 'kg': amount_g *= 1000
                    elif unit in ['ml', 'g']: amount_g = amount
                    elif unit == 'oz': amount_g *= 28.35
                    elif unit == 'tbsp': amount_g *= 15
                    elif unit == 'tsp': amount_g *= 5
                    elif unit == 'cup': amount_g *= 240
                    
                    if name:
                        ingredients.append({
                            "name": name,
                            "amount_g": amount_g,
                            "original_text": line
                        })
                except (ValueError, IndexError):
                    continue
        
        return ingredients

    def _parse_json(self, response: str) -> List[Dict[str, Any]]:
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        return []

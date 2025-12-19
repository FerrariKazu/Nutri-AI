"""
Nutrition data tool for ingredient information.
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Common ingredient nutrition data (per 100g)
NUTRITION_DATABASE = {
    "garlic": {
        "calories": 149,
        "protein": 6.4,
        "carbs": 33.1,
        "fat": 0.5,
        "fiber": 2.1,
        "vitamin_c": 31.2,
        "compounds": ["allicin", "diallyl disulfide", "ajoene"],
    },
    "chicken": {
        "calories": 239,
        "protein": 27.3,
        "carbs": 0,
        "fat": 13.6,
        "compounds": ["creatine", "carnosine", "taurine"],
    },
    "rice": {
        "calories": 130,
        "protein": 2.7,
        "carbs": 28.2,
        "fat": 0.3,
        "fiber": 0.4,
        "compounds": ["amylose", "amylopectin"],
    },
    "onion": {
        "calories": 40,
        "protein": 1.1,
        "carbs": 9.3,
        "fat": 0.1,
        "fiber": 1.7,
        "vitamin_c": 7.4,
        "compounds": ["quercetin", "sulfur compounds", "fructans"],
    },
    "tomato": {
        "calories": 18,
        "protein": 0.9,
        "carbs": 3.9,
        "fat": 0.2,
        "fiber": 1.2,
        "vitamin_c": 13.7,
        "compounds": ["lycopene", "beta-carotene", "naringenin"],
    },
}


def get_ingredient_nutrition(name: str) -> Optional[Dict[str, Any]]:
    """
    Get nutrition data for an ingredient.
    
    Args:
        name: Ingredient name (e.g., "garlic", "chicken")
        
    Returns:
        Dict with nutrition data or None if not found
    """
    try:
        name_lower = name.lower().strip()
        
        if name_lower in NUTRITION_DATABASE:
            data = NUTRITION_DATABASE[name_lower].copy()
            data["name"] = name
            data["per_amount"] = "100g"
            logger.info(f"Found nutrition data for: {name}")
            return data
        
        logger.warning(f"No nutrition data found for: {name}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting nutrition for '{name}': {e}")
        return None

"""
FoodData Central loader for comprehensive nutrition data.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Path to FoodData Central Foundation Foods
FOODDATA_PATH = Path(__file__).parent.parent.parent / "FoodData Central – Foundation Foods"

# Cache for loaded data
_food_cache = {}
_nutrient_cache = {}
_food_nutrient_cache = {}


def load_nutrients() -> Dict[int, Dict]:
    """Load nutrient definitions."""
    global _nutrient_cache
    
    if _nutrient_cache:
        return _nutrient_cache
    
    try:
        nutrient_file = FOODDATA_PATH / "nutrient.csv"
        with open(nutrient_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nutrient_id = int(row['id'])
                _nutrient_cache[nutrient_id] = {
                    'id': nutrient_id,
                    'name': row.get('name', ''),
                    'unit_name': row.get('unit_name', ''),
                    'nutrient_nbr': row.get('nutrient_nbr', ''),
                }
        
        logger.info(f"Loaded {len(_nutrient_cache)} nutrients from FoodData Central")
        return _nutrient_cache
        
    except Exception as e:
        logger.error(f"Error loading nutrients: {e}")
        return {}


def load_foods() -> Dict[int, Dict]:
    """Load food items."""
    global _food_cache
    
    if _food_cache:
        return _food_cache
    
    try:
        food_file = FOODDATA_PATH / "food.csv"
        count = 0
        
        with open(food_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                food_id = int(row['fdc_id'])
                _food_cache[food_id] = {
                    'fdc_id': food_id,
                    'description': row.get('description', ''),
                    'data_type': row.get('data_type', ''),
                    'food_category_id': row.get('food_category_id', ''),
                }
                count += 1
                if count >= 1000:  # Limit to first 1000 for performance
                    break
        
        logger.info(f"Loaded {len(_food_cache)} foods from FoodData Central")
        return _food_cache
        
    except Exception as e:
        logger.error(f"Error loading foods: {e}")
        return {}


def search_food(query: str) -> List[Dict]:
    """
    Search for foods by name.
    
    Args:
        query: Search query
        
    Returns:
        List of matching food items
    """
    foods = load_foods()
    query_lower = query.lower()
    
    matches = []
    for food in foods.values():
        if query_lower in food['description'].lower():
            matches.append(food)
            if len(matches) >= 10:  # Limit results
                break
    
    return matches


def get_food_nutrients(food_id: int) -> Dict[str, Any]:
    """
    Get nutrient data for a specific food.
    
    Args:
        food_id: FoodData Central food ID
        
    Returns:
        Dict with nutrient data
    """
    try:
        nutrients = load_nutrients()
        food_nutrient_file = FOODDATA_PATH / "food_nutrient.csv"
        
        food_nutrients = {}
        
        with open(food_nutrient_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row.get('fdc_id', 0)) == food_id:
                    nutrient_id = int(row.get('nutrient_id', 0))
                    if nutrient_id in nutrients:
                        nutrient_name = nutrients[nutrient_id]['name']
                        amount = float(row.get('amount', 0))
                        unit = nutrients[nutrient_id]['unit_name']
                        
                        food_nutrients[nutrient_name] = {
                            'amount': amount,
                            'unit': unit,
                        }
        
        return food_nutrients
        
    except Exception as e:
        logger.error(f"Error getting food nutrients: {e}")
        return {}


def get_comprehensive_nutrition(food_name: str) -> Optional[Dict]:
    """
    Get comprehensive nutrition data for a food item.
    
    Args:
        food_name: Name of the food
        
    Returns:
        Dict with food and nutrient data
    """
    # Search for food
    matches = search_food(food_name)
    
    if not matches:
        return None
    
    # Get first match
    food = matches[0]
    food_id = food['fdc_id']
    
    # Get nutrients
    nutrients = get_food_nutrients(food_id)
    
    return {
        'food': food,
        'nutrients': nutrients,
    }

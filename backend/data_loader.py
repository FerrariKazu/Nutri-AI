"""
Recipe dataset loader and search functions.

Loads the processed recipes with nutrition data and provides
search and retrieval functions for the FastAPI backend.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Global recipe storage
_recipes_data: List[Dict[str, Any]] = []
_recipes_by_id: Dict[int, Dict[str, Any]] = {}
_loaded = False


def load_recipes(json_path: str = "processed/recipes_with_nutrition.json") -> None:
    """
    Load processed recipes from JSON file into memory.
    
    Args:
        json_path: Path to recipes JSON file
    """
    global _recipes_data, _recipes_by_id, _loaded
    
    if _loaded:
        logger.info("Recipes already loaded, skipping...")
        return
    
    logger.info(f"Loading recipes from {json_path}...")
    
    path = Path(json_path)
    if not path.exists():
        logger.error(f"Recipe file not found: {json_path}")
        _loaded = False
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        _recipes_data = json.load(f)
    
    # Build ID index
    for idx, recipe in enumerate(_recipes_data):
        _recipes_by_id[idx] = recipe
    
    logger.info(f"✅ Loaded {len(_recipes_data)} recipes with nutrition data")
    _loaded = True


def get_recipe_by_id(recipe_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a recipe by its index ID.
    
    Args:
        recipe_id: Recipe index
        
    Returns:
        Recipe dictionary or None
    """
    return _recipes_by_id.get(recipe_id)


def get_all_recipes() -> List[Dict[str, Any]]:
    """Get all loaded recipes."""
    return _recipes_data


def search_recipes_by_ingredients(ingredients: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search recipes by ingredient matching (lexical fallback).
    
    Simple scoring: count how many user ingredients appear in recipe.
    
    Args:
        ingredients: List of ingredient names
        top_k: Number of results to return
        
    Returns:
        List of top matching recipes
    """
    if not _recipes_data:
        return []
    
    # Normalize ingredients to lowercase
    normalized_ingredients = [ing.lower().strip() for ing in ingredients]
    
    # Score each recipe
    scored_recipes = []
    for recipe in _recipes_data:
        score = 0
        recipe_ingredients = recipe.get('ingredients', [])
        
        # Concatenate all normalized ingredient names
        recipe_text = " ".join([
            ing.get('normalized', '').lower()
            for ing in recipe_ingredients
        ])
        
        # Count matches
        for user_ing in normalized_ingredients:
            if user_ing in recipe_text:
                score += 1
        
        if score > 0:
            scored_recipes.append((score, recipe))
    
    # Sort by score descending
    scored_recipes.sort(key=lambda x: x[0], reverse=True)
    
    # Return top k
    return [recipe for _, recipe in scored_recipes[:top_k]]


def get_nutrition_summary(recipe: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract nutrition summary from a recipe.
    
    Args:
        recipe: Recipe dictionary
        
    Returns:
        Nutrition data dict
    """
    return recipe.get('nutrition', {
        'calories': 0,
        'protein_g': 0,
        'fat_g': 0,
        'carbs_g': 0
    })


def build_context_for_llm(recipe: Dict[str, Any], max_instructions_chars: int = 300) -> str:
    """
    Build a formatted context block for LLM prompting.
    
    Args:
        recipe: Recipe dictionary
        max_instructions_chars: Max length for instructions excerpt
        
    Returns:
        Formatted string for context
    """
    title = recipe.get('title', 'Unknown Recipe')
    
    # Get ingredient list
    ingredients = recipe.get('ingredients', [])
    ingredient_names = [
        ing.get('raw', ing.get('normalized', 'unknown'))
        for ing in ingredients[:15]  # Limit to 15 ingredients
    ]
    ingredients_str = ", ".join(ingredient_names)
    if len(ingredients) > 15:
        ingredients_str += f" (+ {len(ingredients) - 15} more)"
    
    # Get nutrition
    nutrition = get_nutrition_summary(recipe)
    nutrition_str = (
        f"Calories: {nutrition.get('calories', 0):.0f} kcal, "
        f"Protein: {nutrition.get('protein_g', 0):.1f}g, "
        f"Fat: {nutrition.get('fat_g', 0):.1f}g, "
        f"Carbs: {nutrition.get('carbs_g', 0):.1f}g"
    )
    
    # Get dietary tags
    tags = recipe.get('diet_tags', [])
    tags_str = ", ".join(tags) if tags else "none"
    
    # Format as context block
    context = f"""Title: {title}
Ingredients: {ingredients_str}
Nutrition: {nutrition_str}
Tags: {tags_str}"""
    
    return context


def get_dataset_stats() -> Dict[str, Any]:
    """
    Get statistics about the loaded dataset.
    
    Returns:
        Stats dictionary
    """
    if not _recipes_data:
        return {
            "total_recipes": 0,
            "loaded": False
        }
    
    # Count dietary tags
    tag_counts = {}
    for recipe in _recipes_data:
        for tag in recipe.get('diet_tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Calculate average nutrition
    total_cal = sum(r.get('nutrition', {}).get('calories', 0) for r in _recipes_data)
    total_protein = sum(r.get('nutrition', {}).get('protein_g', 0) for r in _recipes_data)
    
    count = len(_recipes_data)
    
    return {
        "total_recipes": count,
        "loaded": True,
        "avg_calories": total_cal / count if count > 0 else 0,
        "avg_protein_g": total_protein / count if count > 0 else 0,
        "dietary_tags": tag_counts
    }

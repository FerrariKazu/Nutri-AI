"""
Recipe search tool for function calling.
"""

import logging
from typing import List, Dict, Any
from backend.vector_store import search as vector_search
from backend.data_loader import get_all_recipes

logger = logging.getLogger(__name__)


def search_recipes(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for recipes matching the query.
    
    Args:
        query: Search query (e.g., "rice shrimp", "high protein dinner")
        k: Number of results to return
        
    Returns:
        List of recipe dictionaries
    """
    try:
        # Use existing vector search
        results = vector_search.semantic_search(query, k=k)
        
        recipes = []
        all_recipes = get_all_recipes()
        
        for result in results:
            recipe_id = result.get("id")
            score = result.get("score", 0.0)
            
            # Find full recipe data
            recipe = next((r for r in all_recipes if r.get("id") == recipe_id), None)
            if recipe:
                recipes.append({
                    "id": recipe_id,
                    "title": recipe.get("title", ""),
                    "ingredients": recipe.get("ingredients", []),
                    "instructions": recipe.get("instructions", ""),
                    "score": score,
                })
        
        logger.info(f"Found {len(recipes)} recipes for query: '{query}'")
        return recipes
        
    except Exception as e:
        logger.error(f"Error searching recipes: {e}")
        return []

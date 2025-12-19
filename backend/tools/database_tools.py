"""
Centralized Database Tools wrapper for Agentic RAG.
This class exposes specialized tools (Chemistry, Nutrition, Pantry, Search) 
to the LLM in a format it can easily invoke via the ReAct pattern.
"""

import json
import logging
from typing import List, Dict, Any

# Tool imports
from .chemistry_tools import get_food_chemistry
from .recipe_search import search_recipes
from .pantry import pantry_tools
from .nutrition import get_ingredient_nutrition
from .memory_tools import MemoryTools

logger = logging.getLogger(__name__)

class DatabaseTools:
    """
    Registry and execution engine for all Nutri-AI specialized tools.
    """
    
    def __init__(self):
        logger.info("🛠️ DatabaseTools initialized")

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Used by AgenticRAG to build system prompt descriptions."""
        return [
            {
                "name": "search_recipes",
                "priority": 10,
                "description": "Search the local database for food recipes based on keywords or requirements.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "get_food_chemistry",
                "priority": 9,
                "description": "Get molecular data, chemical properties, and reactions for food compounds from PubChem.",
                "parameters": "compound: str"
            },
            {
                "name": "get_nutrition_data",
                "priority": 8,
                "description": "Get detailed nutritional breakdown (macros, vitamins) for specific foods.",
                "parameters": "food_item: str"
            },
            {
                "name": "pantry_manager",
                "priority": 7,
                "description": "Manage user pantry items (add, remove, list, clear).",
                "parameters": "action: str, items: list=[]"
            },
            {
                "name": "manage_memory",
                "priority": 5,
                "description": "Save or retrieve important details from earlier in the conversation.",
                "parameters": "action: str, key: str, value: str=None, session_id: str='default'"
            }
        ]

    # Wrapper methods to match naming in AgenticRAG or provide clean interface
    
    def search_recipes(self, query: str, k: int = 5) -> str:
        results = search_recipes(query, k=k)
        return json.dumps(results)

    def get_food_chemistry(self, compound: str) -> str:
        results = get_food_chemistry(compound)
        return json.dumps(results)

    def get_nutrition_data(self, food_item: str) -> str:
        results = get_ingredient_nutrition(food_item)
        return json.dumps(results) if results else "No nutrition data found."

    def pantry_manager(self, action: str, items: list = None, session_id: str = "default") -> str:
        if items is None: items = []
        results = pantry_tools(action, {"session_id": session_id, "items": items})
        return json.dumps(results)

    def manage_memory(self, action: str, key: str, value: str = None, session_id: str = "default") -> str:
        if action == "save":
            results = MemoryTools.save(session_id, key, value)
        else:
            results = MemoryTools.get(session_id, key)
        return json.dumps(results)

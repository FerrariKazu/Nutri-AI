"""
Centralized Database Tools wrapper for Agentic RAG.
This class exposes specialized tools (Chemistry, Nutrition, Pantry, Search) 
to the LLM in a format it can easily invoke via the ReAct pattern.
"""

import json
import logging
from typing import List, Dict, Any

# Tool imports
from ..retriever.router import RetrievalRouter, IndexType
from backend.pubchem_client import get_pubchem_client, PubChemError

logger = logging.getLogger(__name__)

# Global router instance for tool access
_router = None

def get_router():
    global _router
    if _router is None:
        _router = RetrievalRouter()
    return _router

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
                "description": "Find recipes using the 13k Recipes index. Best for cooking instructions and meal ideas.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "search_usda_branded",
                "priority": 9,
                "description": "Search 1.9M+ commercial food products for specific brands and ingredients. Highest volume data.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "search_usda_foundation",
                "priority": 9,
                "description": "Search high-fidelity laboratory data for whole, raw foods/ingredients. Most accurate for base components.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "search_open_nutrition",
                "priority": 8,
                "description": "Search OpenNutrition database (320k+ entries) for international and diverse food products.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "search_chemistry",
                "priority": 8,
                "description": "Search FoodDB, DSSTox, and chemical libraries for molecular info, reactions, and toxins.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "search_science",
                "priority": 7,
                "description": "Search scientific PDFs and papers for the physics/chemistry of cooking and deep food science.",
                "parameters": "query: str, k: int=5"
            },
            {
                "name": "search_pubchem",
                "priority": 10,
                "description": "Search PubChem for mandatory verifiable compound facts (molecular formula, weight, IUPAC name). Use this for any nutrition or chemical claim.",
                "parameters": "query: str"
            },
            {
                "name": "pantry_manager",
                "priority": 5,
                "description": "Manage user pantry items (add, remove, list, clear).",
                "parameters": "action: str, items: list=[]"
            }
        ]

    # --- Granular Search Tools (Isolated Architecture) ---
    
    def _run_isolated_search(self, query: str, index_type: IndexType, k: int = 5) -> str:
        router = get_router()
        results = router.search(query, index_types=[index_type], top_k=k)
        if not results:
            return f"No results found in {index_type.value} for '{query}'"
        
        # Format output for the agent
        output = [f"Found {len(results)} matches in {index_type.value}:\n"]
        for i, r in enumerate(results, 1):
            text = r.get('text', '')
            meta = r.get('metadata', {})
            output.append(f"[{i}] {text[:500]}...") # Truncate for prompt economy
        return "\n".join(output)

    def search_recipes(self, query: str, k: int = 5) -> str:
        return self._run_isolated_search(query, IndexType.RECIPES, k)

    def search_usda_branded(self, query: str, k: int = 5) -> str:
        return self._run_isolated_search(query, IndexType.USDA_BRANDED, k)

    def search_usda_foundation(self, query: str, k: int = 5) -> str:
        return self._run_isolated_search(query, IndexType.USDA_FOUNDATION, k)

    def search_open_nutrition(self, query: str, k: int = 5) -> str:
        return self._run_isolated_search(query, IndexType.OPEN_NUTRITION, k)

    def search_chemistry(self, query: str, k: int = 5) -> str:
        return self._run_isolated_search(query, IndexType.CHEMISTRY, k)

    def search_science(self, query: str, k: int = 5) -> str:
        return self._run_isolated_search(query, IndexType.SCIENCE, k)

    def search_pubchem(self, query: str) -> str:
        """
        Search PubChem for compound facts.
        Mandatory for nutrition and chemical verification.
        """
        client = get_pubchem_client()
        try:
            cid = client.search_compound(query)
            props = client.get_compound_properties(cid)
            
            result = {
                "verified": True,
                "source": "PubChem",
                "compound_name": query,
                "cid": cid,
                "molecular_formula": props.molecular_formula,
                "molecular_weight": props.molecular_weight,
                "iupac_name": props.iupac_name,
                "canonical_smiles": props.canonical_smiles
            }
            return json.dumps(result, indent=2)
        except PubChemError as e:
            logger.warning(f"[PUBCHEM_TOOL] Failed to resolve {query}: {e}")
            return f"Error: PubChem could not resolve '{query}'. reason: {str(e)}"

    def pantry_manager(self, action: str, items: list = None, session_id: str = "default") -> str:
        from .pantry import pantry_tools
        if items is None: items = []
        results = pantry_tools(action, {"session_id": session_id, "items": items})
        return json.dumps(results)

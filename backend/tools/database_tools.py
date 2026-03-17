"""
Centralized Database Tools wrapper for Agentic RAG.
This class exposes specialized tools (Chemistry, Nutrition, Pantry, Search) 
to the LLM in a format it can easily invoke via the ReAct pattern.
"""

import json
import logging
from typing import List, Dict, Any, Optional

# Tool imports
from ..retriever.router import RetrievalRouter, IndexType
from backend.pubchem_client import get_pubchem_client, PubChemError
from backend.governance_types import EscalationLevel

logger = logging.getLogger(__name__)

def resolve_tools_by_intent(intent_category: str) -> List[str]:
    """Strict mapping: Only defined tools for each intent"""
    intent_category = (intent_category or "default").lower()
    
    if intent_category in ["greeting", "chit_chat", "help"]:
        return []
        
    if intent_category in ["food_query", "recipe_analysis", "general_nutrition"]:
        return ["search_recipes", "search_usda_branded", "search_usda_foundation", "search_open_nutrition", "pantry_manager"]
        
    if intent_category in ["chemistry_query", "compound_lookup", "clinical_nutrition"]:
        return ["search_chemistry", "search_pubchem"]
        
    if intent_category in ["scientific_query", "scientific"]:
        return ["search_science"]
        
    return []

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
    
    def __init__(
        self, 
        allowed_tools: List[str] = None, 
        current_intent: str = None, 
        escalation_tier: EscalationLevel = EscalationLevel.TIER_0
    ):
        logger.info(f"🛠️ DatabaseTools initialized at {escalation_tier.name}")
        self.allowed_tools = allowed_tools
        self.current_intent = (current_intent or "unknown").lower()
        self.escalation_tier = escalation_tier

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Used by AgenticRAG to build system prompt descriptions."""
        all_tools = [
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
        
        if self.allowed_tools is not None:
            return [t for t in all_tools if t["name"] in self.allowed_tools]
        return all_tools

    def _check_nuclear_safeguard(self, target_index: Optional[IndexType] = None):
        """Nuclear Safeguard: Hard Assertion per User Request"""
        if self.current_intent in ["greeting", "chit_chat", "help"]:
            logger.critical(f"ILLEGAL TOOL USAGE ATTEMPT: Intent '{self.current_intent}'")
            raise RuntimeError("Tool execution in non-knowledge intent")
            
        # 🛡️ Phase 2: Tier Matrix Enforcement
        tier_val = self.escalation_tier.value
        
        if target_index:
            # TIER_1: Only Recipes
            if tier_val == 1 and target_index != IndexType.RECIPES:
                logger.warning(f"⚠️ [FIREWALL] Blocked access to {target_index.value} at TIER_1")
                raise PermissionError(f"Index {target_index.value} requires TIER_2 escalation.")
            
            # TIER_2: Nutrition + Recipes (No Chemistry/Science)
            if tier_val == 2 and target_index in [IndexType.CHEMISTRY, IndexType.SCIENCE]:
                logger.warning(f"⚠️ [FIREWALL] Blocked access to {target_index.value} at TIER_2")
                raise PermissionError(f"Index {target_index.value} requires TIER_3 escalation.")

    # --- Granular Search Tools (Isolated Architecture) ---
    
    def _run_isolated_search(self, query: str, index_type: IndexType, k: int = 5) -> str:
        self._check_nuclear_safeguard(target_index=index_type)
        router = get_router()
        
        # 🔒 Hard Domain Lock on Router
        if self.escalation_tier == EscalationLevel.TIER_1:
            router.set_allowed_indices([IndexType.RECIPES])
        elif self.escalation_tier == EscalationLevel.TIER_2:
            router.set_allowed_indices([IndexType.USDA_BRANDED, IndexType.USDA_FOUNDATION, IndexType.OPEN_NUTRITION, IndexType.RECIPES])
        elif self.escalation_tier == EscalationLevel.TIER_3:
            # Full access
            router.set_allowed_indices([
                IndexType.CHEMISTRY, IndexType.SCIENCE, 
                IndexType.USDA_BRANDED, IndexType.USDA_FOUNDATION, 
                IndexType.OPEN_NUTRITION, IndexType.RECIPES
            ])

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
        self._check_nuclear_safeguard()
        
        # 🔐 Phase 2 Guard: PubChem requires TIER_3 (Scientific Level)
        if self.escalation_tier.value < 3:
            logger.warning(f"⚠️ [FIREWALL] Blocked PubChem access at {self.escalation_tier.name}")
            return "❌ [FIREWALL_BLOCK] PubChem access is restricted. Scientific level escalation required."

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
        self._check_nuclear_safeguard()
        from .pantry import pantry_tools
        if items is None: items = []
        results = pantry_tools(action, {"session_id": session_id, "items": items})
        return json.dumps(results)

"""
Chemistry tools wrapper for LLM function calling.
"""

import logging
from backend.chemistry import search_compound, get_compound_profile, get_chemical_reactions

logger = logging.getLogger(__name__)


def get_food_chemistry(compound: str) -> dict:
    """
    Get chemical data for a food compound.
    
    Args:
        compound: Compound name (e.g., "allicin", "hexanal", "lycopene")
        
    Returns:
        Dict with chemical data including reactions, properties, and food relevance
    """
    try:
        # Get compound profile from PubChem
        profile = get_compound_profile(compound)
        
        if not profile:
            return {
                "compound": compound,
                "found": False,
                "message": f"No data found for compound: {compound}",
            }
        
        # Get known reactions
        reactions = get_chemical_reactions(compound)
        
        result = {
            "compound": compound,
            "found": True,
            "cid": profile.get("cid"),
            "molecular_formula": profile.get("molecular_formula"),
            "molecular_weight": profile.get("molecular_weight"),
            "iupac_name": profile.get("iupac_name"),
            "description": profile.get("description", ""),
            "reactions": reactions,
            "food_relevance": profile.get("food_relevance", ""),
        }
        
        logger.info(f"Retrieved chemistry data for: {compound}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting chemistry for '{compound}': {e}")
        return {
            "compound": compound,
            "found": False,
            "error": str(e),
        }

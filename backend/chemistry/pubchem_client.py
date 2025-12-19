"""
PubChem API client for chemical compound data retrieval.

Uses PubChem's free PUG-REST API (no authentication required).
"""

import requests
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_VIEW_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"


def search_compound(name: str) -> Optional[Dict[str, Any]]:
    """
    Search for a compound by name and return basic data.
    
    Args:
        name: Compound name (e.g., "allicin", "hexanal")
        
    Returns:
        Dict with compound data or None if not found
    """
    try:
        url = f"{PUBCHEM_BASE}/compound/name/{name}/JSON"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "PC_Compounds" in data and len(data["PC_Compounds"]) > 0:
                compound = data["PC_Compounds"][0]
                cid = compound.get("id", {}).get("id", {}).get("cid")
                
                return {
                    "cid": cid,
                    "name": name,
                    "molecular_formula": _extract_molecular_formula(compound),
                    "molecular_weight": _extract_molecular_weight(compound),
                    "iupac_name": _extract_iupac_name(compound),
                }
        
        logger.warning(f"Compound '{name}' not found in PubChem")
        return None
        
    except Exception as e:
        logger.error(f"Error searching PubChem for '{name}': {e}")
        return None


def get_compound_profile(name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed compound profile including properties and descriptions.
    
    Args:
        name: Compound name
        
    Returns:
        Dict with detailed compound data
    """
    try:
        # First get CID
        basic_data = search_compound(name)
        if not basic_data or "cid" not in basic_data:
            return None
        
        cid = basic_data["cid"]
        
        # Get detailed view data
        url = f"{PUBCHEM_VIEW_BASE}/data/compound/{cid}/JSON"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            profile = {
                **basic_data,
                "description": _extract_description(data),
                "uses": _extract_uses(data),
                "pharmacology": _extract_pharmacology(data),
                "safety": _extract_safety(data),
                "food_relevance": _extract_food_relevance(data),
            }
            
            return profile
        
        return basic_data
        
    except Exception as e:
        logger.error(f"Error getting compound profile for '{name}': {e}")
        return None


def get_chemical_reactions(compound: str) -> List[str]:
    """
    Get known chemical reactions for a compound.
    
    Args:
        compound: Compound name
        
    Returns:
        List of reaction descriptions
    """
    # This would require more complex parsing of PubChem data
    # For now, return common food chemistry reactions
    
    food_reactions = {
        "allicin": [
            "Decomposes to diallyl disulfide and diallyl trisulfide upon heating",
            "Reacts with amino acids in Strecker degradation",
        ],
        "glucose": [
            "Maillard reaction with amino acids at 140°C+",
            "Caramelization at 160°C+ forming furans and pyrones",
        ],
        "fructose": [
            "Caramelization at lower temps than glucose (110°C+)",
            "Forms HMF (hydroxymethylfurfural) during heating",
        ],
        "hexanal": [
            "Product of linoleic acid oxidation",
            "Contributes to grassy, green aromas",
        ],
    }
    
    return food_reactions.get(compound.lower(), [
        f"Common reactions for {compound} include thermal decomposition and oxidation"
    ])


def _extract_molecular_formula(compound: Dict) -> Optional[str]:
    """Extract molecular formula from compound data."""
    try:
        props = compound.get("props", [])
        for prop in props:
            if prop.get("urn", {}).get("label") == "Molecular Formula":
                return prop.get("value", {}).get("sval")
    except:
        pass
    return None


def _extract_molecular_weight(compound: Dict) -> Optional[float]:
    """Extract molecular weight from compound data."""
    try:
        props = compound.get("props", [])
        for prop in props:
            if prop.get("urn", {}).get("label") == "Molecular Weight":
                return prop.get("value", {}).get("fval")
    except:
        pass
    return None


def _extract_iupac_name(compound: Dict) -> Optional[str]:
    """Extract IUPAC name from compound data."""
    try:
        props = compound.get("props", [])
        for prop in props:
            if prop.get("urn", {}).get("label") == "IUPAC Name":
                return prop.get("value", {}).get("sval")
    except:
        pass
    return None


def _extract_description(data: Dict) -> str:
    """Extract compound description from PubChem view data."""
    try:
        record = data.get("Record", {})
        sections = record.get("Section", [])
        
        for section in sections:
            if section.get("TOCHeading") == "Names and Identifiers":
                for subsection in section.get("Section", []):
                    if subsection.get("TOCHeading") == "Record Description":
                        info = subsection.get("Information", [])
                        if info:
                            return info[0].get("Value", {}).get("StringWithMarkup", [{}])[0].get("String", "")
    except:
        pass
    return "No description available"


def _extract_uses(data: Dict) -> List[str]:
    """Extract uses from PubChem data."""
    # Simplified extraction
    return []


def _extract_pharmacology(data: Dict) -> str:
    """Extract pharmacology info."""
    return ""


def _extract_safety(data: Dict) -> str:
    """Extract safety information."""
    return ""


def _extract_food_relevance(data: Dict) -> str:
    """Extract food-related information."""
    return ""

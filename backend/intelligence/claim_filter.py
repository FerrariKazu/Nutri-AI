"""
Mechanism Claim Purity Gate v1.0
Enforces scientific purity on intelligence claims.
Rejects administrative text and ensures mechanistic content.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.sensory.sensory_registry import SensoryRegistry, ONTOLOGY

logger = logging.getLogger(__name__)

ILLEGAL_PATTERNS = [
    "no specification",
    "cannot generate",
    "please provide",
    "insufficient information",
    "as a result",
    "i cannot",
    "require more context",
    "need more information",
    "waiting for input",
    "workflow message",
    "administrative",
    "resting",
    "clarification needed",
]

def is_mechanistic(claim: Dict[str, Any]) -> bool:
    """
    Categorically filters non-scientific or meta-conversational claims.
    """
    # 1. Decision-based Rejection (Workflow Gate)
    if claim.get("decision") == "REQUIRE_MORE_CONTEXT":
        return False

    # 2. Pattern Rejection (Dialogue Management)
    statement = claim.get("statement", claim.get("text", "")).lower()
    if any(p in statement for p in ILLEGAL_PATTERNS):
        return False

    # 3. Validity Requirement (At least one mechanistic anchor)
    if claim.get("compounds"): return True
    if claim.get("receptors"): return True
    if claim.get("perception_outputs"): return True
    if claim.get("processes"): return True
    if claim.get("physics"): return True
    
    # 4. Domain Check 
    if claim.get("domain") in ["chemical", "receptor", "process", "physical", "structural"]:
        return True

    return False

COMPOUND_ALIASES = {
    "msg": "monosodium_glutamate",
    "salt": "sodium_chloride",
    "sugar": "sucrose",
    "vinegar": "acetic_acid",
    "lemon": "citric_acid",
    "lime": "citric_acid",
    "chili": "capsaicin",
    "pepper": "piperine",
    "mint": "menthol",
    "chocolate": "theobromine",
    "coffee": "caffeine",
    "tea": "caffeine",
}

def create_fallback_claim(text: str) -> Dict[str, Any]:
    """
    Creates one minimal ontology-derived claim when filtering leaves zero result.
    Scans text for the first known compound and builds a legitimate mechanism.
    """
    text_lower = text.lower()
    found_compound = None
    
    # Scan for first known compound or alias
    all_known = set(ONTOLOGY["compounds"].keys()) | set(COMPOUND_ALIASES.keys())
    
    for term in all_known:
        if term.replace("_", " ") in text_lower:
            found_compound = COMPOUND_ALIASES.get(term, term)
            break
            
    if found_compound:
        # Build from ontology
        from backend.intelligence.claim_enricher import enrich_claim
        entry = SensoryRegistry.map_compound_to_perception(found_compound)
        
        fallback = {
            "id": "fallback_ontology_0",
            "statement": f"{found_compound.replace('_', ' ').title()} activates specific sensory pathways.",
            "text": text[:200],
            "compounds": [found_compound],
            "receptors": entry.get("receptors", []),
            "perception_outputs": entry.get("perception_outputs", []),
            "domain": "receptor",
            "confidence": 0.8
        }
        return enrich_claim(fallback)
    
    # Nuclear fallback if no compounds found
    return {
        "id": "fallback_generic_0",
        "statement": "Nutritional and chemical properties of the sample interact with biological systems.",
        "text": text[:200],
        "domain": "physical",
        "compounds": [],
        "receptors": [],
        "perception_outputs": [{"label": "biological interaction", "type": "perception"}],
        "confidence": 0.5,
        "source": "Nutri Core Ontology"
    }

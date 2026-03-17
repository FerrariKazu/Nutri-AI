import re
import logging
from typing import Dict, List, Set
from backend.intelligence.scientific_registries import SCIENTIFIC_KEYWORDS, NUTRITION_KEYWORDS

logger = logging.getLogger(__name__)

def split_into_clauses(message: str) -> List[str]:
    """
    Naively split a message on common conjunctions and punctuation.
    """
    # Split on " and ", " also ", ",", ";"
    pattern = r'\s+and\s+|\s+also\s+|,\s*|;\s*'
    raw_clauses = re.split(pattern, message, flags=re.IGNORECASE)
    
    # Clean and filter empty clauses
    return [c.strip() for c in raw_clauses if len(c.strip()) > 3]

def classify_clause(clause: str) -> str:
    """
    Classify a single clause as 'scientific', 'nutritional', or 'other'.
    """
    words = set(re.findall(r'\b\w+\b', clause.lower()))
    
    has_scientific = bool(words.intersection(SCIENTIFIC_KEYWORDS))
    has_nutritional = bool(words.intersection(NUTRITION_KEYWORDS))
    
    # Priority to scientific if both match (e.g., "protein binding mechanism")
    if has_scientific:
        return "scientific"
    if has_nutritional:
        return "nutritional"
    
    return "other"

def segment_clauses(message: str) -> Dict[str, str]:
    """
    Segment a mixed query into distinct domain blocks.
    
    Safety Guard: Only applies segmentation if the resulting clauses 
    independently map to *different* known domains. Otherwise, treats
    the message as a single block to prevent fragment corruption.
    """
    if not message:
        return {"other": message}
        
    clauses = split_into_clauses(message)
    
    if len(clauses) <= 1:
        # Base case: No split possible
        return {classify_clause(message): message}
        
    classified_segments = {}
    for clause in clauses:
        domain = classify_clause(clause)
        if domain not in classified_segments:
            classified_segments[domain] = []
        classified_segments[domain].append(clause)
        
    # Safety Guard: Are there at least two DISTINCT domains?
    # (Excluding 'other' which might just be glue words)
    meaningful_domains = [d for d in classified_segments.keys() if d != "other"]
    
    if len(meaningful_domains) > 1:
        # Valid mixed query. Join clauses by domain.
        result = {}
        for domain, parts in classified_segments.items():
            if domain != "other":
                result[domain] = " and ".join(parts)
                
        logger.info(f"[CLAUSE_SEGMENTATION] Split applied: scientific='{result.get('scientific', '')}', nutritional='{result.get('nutritional', '')}'")
        return result
    else:
        # Invalid split (e.g., "sodium transport in kidney" and "intestine")
        # Both map to scientific (or other). Treat as single clause.
        domain = classify_clause(message)
        logger.debug(f"[CLAUSE_SEGMENTATION] Split rejected (insufficient domain variance). Treated as {domain}.")
        return {domain: message}


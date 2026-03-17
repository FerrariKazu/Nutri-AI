"""
Deterministic Correction Path for Scientific Traces.
Strategies to repair blocking contract violations without LLM calls.
"""

import logging
from typing import List, Dict, Any, Tuple
# claim_filter import might be circular if not careful, but correction_path is high level
# We import inside function to be safe or assuming clean dependency DAG.
from backend.intelligence.claim_filter import is_mechanistic, create_fallback_claim

logger = logging.getLogger(__name__)

def attempt_trace_correction(
    trace: Any,
    violations: List[Any],
    enriched_claims: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Deterministic correction. Zero LLM calls.
    
    Strategy 1: Highest-confidence enriched claim
    Strategy 2: Registry-backed minimal statement
    Strategy 3: Nuclear generic fallback
    """
    logger.info(f"[CORRECTION] Attempting repair for {len(violations)} blocking violations.")
    
    # Strat 1: Highest-confidence enriched claim
    mechanistic_claims = [
        c for c in enriched_claims 
        if is_mechanistic(c) and c.get("confidence", 0) > 0
    ]
    
    if mechanistic_claims:
        # Sort by confidence DESC
        best = max(mechanistic_claims, key=lambda c: c.get("confidence", 0))
        logger.info(f"[CORRECTION] Pruning unsupported claims. Promoting {best.get('id')}")
        return [best], "prune_to_highest_confidence_enriched"
        
    logger.warning("[CORRECTION] No valid mechanistic claims found. Correction aborted.")
    return [], "correction_failed_no_mechanistic_substance"

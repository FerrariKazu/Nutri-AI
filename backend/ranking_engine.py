import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RankingEngine:
    """
    Calculates scientific saliency scores for Nutri claims.
    Determines display priority in the Intelligence Panel.
    """
    
    @staticmethod
    def calculate_importance(claim: Any) -> float:
        """
        [MANDATE] Deterministic Ranking Formula.
        importance = +3 (receptor) + 2 (pathway) + 1 (theoretical) - 1 (analogy)
        """
        score = 0.0
        
        # 1. Receptor Evidence (+3)
        if getattr(claim, "receptors", []):
            score += 3.0
            
        # 2. Known Pathway (+2)
        if hasattr(claim, "mechanism") and claim.mechanism and getattr(claim.mechanism, "is_valid", False):
            score += 2.0
            
        # 3. Theoretical / Direct Verification (+1)
        if getattr(claim, "verification_level", None) == "direct":
            score += 1.0
        elif getattr(claim, "origin", None) == "enriched":
            score += 0.5 # Partial theoretical bonus
            
        # 4. Analogy Penalty (-1)
        if "similar to" in (getattr(claim, "text", "") or "").lower() or "like" in (getattr(claim, "text", "") or "").lower():
            score -= 1.0
            
        return score

class MoleculeReceptorMapper:
    """
    [MANDATE] Deterministic Mapping via SensoryRegistry.
    Never invents mappings.
    """
    
    @classmethod
    def enrich_perception(cls, claim: Any):
        """
        Injects receptor and sensory data using SensoryRegistry.
        """
        from backend.sensory.sensory_registry import SensoryRegistry
        
        subject = getattr(claim, "subject", "").lower()
        if not subject:
            return
            
        # Deterministic mapping
        mapping = SensoryRegistry.map_compound_to_perception(subject)
        
        if mapping["resolved"]:
            setattr(claim, "receptors", mapping["receptors"])
            setattr(claim, "perception_outputs", mapping["perception_outputs"])
            setattr(claim, "domain", "sensory")
            logger.info(f"[PERCEPTION] Enriched '{subject}' via SensoryRegistry.")
        else:
            # Registry failure semantics: Never invent.
            logger.debug(f"[PERCEPTION] Registry miss for '{subject}'. Marked as unresolved.")

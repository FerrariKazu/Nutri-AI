from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class ClaimUncertainty:
    claim_id: str
    base_confidence: float
    penalties: Dict[str, float]
    final_confidence: float
    weakest_driver: Optional[str] = None

@dataclass
class UncertaintyModel:
    response_confidence: float
    claim_uncertainties: List[ClaimUncertainty]
    variance_drivers: Dict[str, float]
    weakest_link_id: Optional[str]
    explanation: str

class UncertaintyCalculator:
    """
    Models variance and uncertainty at the per-claim level.
    Aggregates to response-level using weighted minimum (worst-case).
    """
    
    def __init__(self):
        self.penalties = {
            "ingredient_substitution": 0.15,
            "portion_ambiguity": 0.10,
            "preparation_variance": 0.05,
            "stale_data": 0.05,
            "incomplete_resolution": 0.20,
            "unverified_source": 0.30
        }

    def calculate(self, claims: List[Any], global_drivers: List[str]) -> UncertaintyModel:
        """
        Computes uncertainty per claim and aggregates upward.
        """
        claim_uncertainties = []
        overall_drivers = {}
        
        for claim in claims:
            # 1. Determine base confidence from verification source
            # verified=True typically starts at 1.0 (PubChem) or 0.9 (USDA)
            base = claim.confidence
            
            # 2. Apply active segments (Global drivers + Claim-specific)
            # Local drivers could be added here based on claim text analysis
            active_drivers = list(global_drivers)
            if not claim.verified:
                active_drivers.append("unverified_source")
                
            claim_total_penalty = 0.0
            applied_drivers = {}
            for driver in set(active_drivers):
                penalty = self.penalties.get(driver, 0.0)
                claim_total_penalty += penalty
                applied_drivers[driver] = penalty
                overall_drivers[driver] = max(overall_drivers.get(driver, 0.0), penalty)
            
            final_c = max(0.0, base - claim_total_penalty)
            weakest_d = max(applied_drivers, key=applied_drivers.get) if applied_drivers else None
            
            claim_uncertainties.append(ClaimUncertainty(
                claim_id=claim.claim_id,
                base_confidence=base,
                penalties=applied_drivers,
                final_confidence=round(final_c, 2),
                weakest_driver=weakest_d
            ))

        # 3. Aggregate using Weighted Minimum (Worst-case)
        if not claim_uncertainties:
            return UncertaintyModel(1.0, [], {}, None, "No claims to analyze.")
            
        weakest_claim = min(claim_uncertainties, key=lambda x: x.final_confidence)
        response_confidence = weakest_claim.final_confidence
        
        explanation = self._generate_explanation(overall_drivers, weakest_claim)
        
        logger.info(f"[UNCERTAINTY] Response Confidence: {response_confidence} (Weakest: {weakest_claim.claim_id})")
        
        return UncertaintyModel(
            response_confidence=response_confidence,
            claim_uncertainties=claim_uncertainties,
            variance_drivers=overall_drivers,
            weakest_link_id=weakest_claim.claim_id,
            explanation=explanation
        )

    def _generate_explanation(self, drivers: Dict[str, float], weakest: ClaimUncertainty) -> str:
        if not drivers and weakest.final_confidence >= 0.9:
            return "High confidence based on direct hard evidence."
            
        msg = f"Overall confidence is limited to {weakest.final_confidence*100:.0f}% because claim {weakest.claim_id} "
        if weakest.weakest_driver:
            msg += f"is affected by {weakest.weakest_driver.replace('_', ' ')}."
        else:
            msg += "is only supported by qualitative evidence."
            
        return msg

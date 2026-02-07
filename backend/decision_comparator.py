import logging
from dataclasses import dataclass
from typing import Optional, Dict, Literal
from backend.belief_state import BeliefState
from backend.recommendation_gate import RecommendationResult, RecommendationDecision

logger = logging.getLogger(__name__)


@dataclass
class DecisionDelta:
    """
    Comparison of current vs prior decision for a specific claim.
    
    Multi-claim support: Each claim gets its own delta.
    """
    claim_id: str
    change_type: Literal["UPGRADE", "DOWNGRADE", "STABLE", "NEW_DECISION"]
    previous: Optional[str]  # previous decision value
    current: str  # current decision value
    reason: str
    turn_changed: int
    
    def to_dict(self) -> Dict:
        return {
            "claim_id": self.claim_id,
            "change_type": self.change_type,
            "previous": self.previous,
            "current": self.current,
            "reason": self.reason,
            "turn_changed": self.turn_changed
        }


class DecisionComparator:
    """
    Compares current Tier-3 decisions vs prior decisions.
    
    Critical for temporal consistency:
    - Detects upgrades (REQUIRE_MORE_CONTEXT → ALLOW)
    - Detects downgrades (ALLOW → WITHHOLD)
    - Detects stability
    - Per-claim tracking (no confusion)
    """
    
    def compare_decisions(
        self,
        belief_state: BeliefState,
        current_results: Dict[str, RecommendationResult],  # claim_id → result
        current_turn: int
    ) -> Dict[str, DecisionDelta]:
        """
        Compare current decisions vs prior for each claim.
        
        Args:
            belief_state: Current belief state with prior decisions
            current_results: Current recommendation results per claim
            current_turn: Current turn number
        
        Returns:
            Dict mapping claim_id to DecisionDelta
        """
        deltas = {}
        
        for claim_id, result in current_results.items():
            current_decision = result.decision.value
            prior_decision = belief_state.prior_recommendations.get(claim_id)
            
            if prior_decision is None:
                # New decision
                delta = DecisionDelta(
                    claim_id=claim_id,
                    change_type="NEW_DECISION",
                    previous=None,
                    current=current_decision,
                    reason="First assessment for this claim",
                    turn_changed=current_turn
                )
            elif prior_decision == current_decision:
                # Stable
                delta = DecisionDelta(
                    claim_id=claim_id,
                    change_type="STABLE",
                    previous=prior_decision,
                    current=current_decision,
                    reason="No change in recommendation",
                    turn_changed=current_turn
                )
            else:
                # Changed - determine if upgrade or downgrade
                change_type = self._classify_change(prior_decision, current_decision)
                delta = DecisionDelta(
                    claim_id=claim_id,
                    change_type=change_type,
                    previous=prior_decision,
                    current=current_decision,
                    reason=result.explanation,
                    turn_changed=current_turn
                )
                
                logger.info(
                    f"[DECISION_COMPARATOR] {change_type}: {claim_id} "
                    f"{prior_decision} → {current_decision} at turn {current_turn}"
                )
            
            deltas[claim_id] = delta
        
        return deltas
    
    def _classify_change(
        self,
        prior: str,
        current: str
    ) -> Literal["UPGRADE", "DOWNGRADE"]:
        """
        Classify if the decision change is an upgrade or downgrade.
        
        Decision hierarchy (most to least permissive):
        ALLOW > REQUIRE_MORE_CONTEXT > WITHHOLD
        """
        hierarchy = {
            "allow": 2,
            "require_more_context": 1,
            "withhold": 0
        }
        
        prior_rank = hierarchy.get(prior, 1)
        current_rank = hierarchy.get(current, 1)
        
        if current_rank > prior_rank:
            return "UPGRADE"
        else:
            return "DOWNGRADE"

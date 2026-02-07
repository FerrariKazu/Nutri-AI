import logging
from dataclasses import dataclass
from typing import Literal, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class RecommendationDecision(Enum):
    """High-level decision on whether recommendation is allowed."""
    ALLOW = "allow"
    WITHHOLD = "withhold"
    REQUIRE_MORE_CONTEXT = "require_more_context"

RecommendationReason = Literal[
    "insufficient_context",
    "identified_risk",
    "population_mismatch",
    "dose_uncertainty",
    "safe_to_discuss_only",
    "mechanism_strong"
]

@dataclass
class RecommendationResult:
    """
    Result of recommendation gate evaluation.
    Decision + reason ensures transparency.
    """
    decision: RecommendationDecision
    reason: RecommendationReason
    explanation: str  # Human-readable explanation of why
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "explanation": self.explanation
        }

class RecommendationGate:
    """
    Critical safety component.
    Controls whether causal language and recommendations are permitted.
    
    Rules:
    - Strong mechanism ≠ allowed recommendation
    - Missing user context → REQUIRE_MORE_CONTEXT
    - Moderate/high risk → WITHHOLD
    """
    
    def evaluate(
        self,
        mechanism_valid: bool,
        applicability_match,  # ApplicabilityMatch
        risk_assessment,  # RiskAssessment
        claim_type: str = "action-implying"
    ) -> RecommendationResult:
        """
        Evaluate whether recommendation is allowed.
        
        Args:
            mechanism_valid: Is the MoA chain valid?
            applicability_match: ApplicabilityMatch result
            risk_assessment: RiskAssessment result
            claim_type: explanatory, comparative, or action-implying
        
        Returns:
            RecommendationResult with decision and reason
        """
        
        # Explanatory claims bypass strict gating
        if claim_type == "explanatory":
            logger.info("[TIER3_RECOMMENDATION_GATE] Explanatory claim, allowing discussion")
            return RecommendationResult(
                decision=RecommendationDecision.ALLOW,
                reason="safe_to_discuss_only",
                explanation="Explaining mechanism without recommending action"
            )
        
        # If mechanism itself is invalid, can't recommend
        if not mechanism_valid:
            logger.warning("[TIER3_RECOMMENDATION_GATE] Invalid mechanism, withholding")
            return RecommendationResult(
                decision=RecommendationDecision.WITHHOLD,
                reason="insufficient_context",
                explanation="Mechanism incomplete, cannot recommend"
            )
        
        # Check for blocking risks
        if risk_assessment.has_blocking_risk():
            logger.warning("[TIER3_RECOMMENDATION_BLOCK] Blocking risk detected")
            blocking_risks = [f for f in risk_assessment.flags if f.severity in ["moderate", "high"]]
            return RecommendationResult(
                decision=RecommendationDecision.WITHHOLD,
                reason="identified_risk",
                explanation=f"Known risks prevent recommendation: {blocking_risks[0].description}"
            )
        
        # Check for unknown risk
        if risk_assessment.unknown_risk:
            logger.warning("[TIER3_RECOMMENDATION_BLOCK] Unknown risk detected")
            return RecommendationResult(
                decision=RecommendationDecision.REQUIRE_MORE_CONTEXT,
                reason="insufficient_context",
                explanation="Risk profile incomplete for this population/context"
            )
        
        # Check applicability match
        if applicability_match.missing_fields:
            critical_missing = any(
                field in ["population", "dose_info"] 
                for field in applicability_match.missing_fields
            )
            
            if critical_missing:
                logger.warning(
                    f"[TIER3_RECOMMENDATION_BLOCK] Critical fields missing: {applicability_match.missing_fields}"
                )
                return RecommendationResult(
                    decision=RecommendationDecision.REQUIRE_MORE_CONTEXT,
                    reason="insufficient_context",
                    explanation=f"Need more information about: {', '.join(applicability_match.missing_fields)}"
                )
        
        if applicability_match.partial_match and not applicability_match.exact_match:
            logger.info("[TIER3_RECOMMENDATION_GATE] Partial match, requiring more context")
            return RecommendationResult(
                decision=RecommendationDecision.REQUIRE_MORE_CONTEXT,
                reason="population_mismatch",
                explanation="Mechanism may not apply to your specific context"
            )
        
        # All checks passed
        logger.info("[TIER3_RECOMMENDATION_GATE] All checks passed, allowing recommendation")
        return RecommendationResult(
            decision=RecommendationDecision.ALLOW,
            reason="mechanism_strong",
            explanation="Mechanism is valid and applicable"
        )

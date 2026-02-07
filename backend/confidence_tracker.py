import logging
from enum import Enum
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class EvidenceStrength(Enum):
    """
    Strength of evidence supporting a confidence change.
    
    Prevents exploitation: weak evidence can't justify massive confidence jumps.
    """
    NONE = 0
    WEAK = 1      # User mention, no verification
    MODERATE = 2  # Partial RAG support
    STRONG = 3    # Full mechanism + applicability


class ConfidenceTracker:
    """
    Validates confidence evolution to prevent unjustified jumps.
    
    Rule: Confidence must change monotonically with evidence strength.
    
    Examples:
    - ❌ Bad: 0.4 → 0.95 with WEAK evidence
    - ✅ Good: 0.4 → 0.55 with WEAK evidence
    - ✅ Good: 0.4 → 0.8 with STRONG evidence
    """
    
    # Maximum allowed confidence jump by evidence strength
    MAX_JUMP = {
        EvidenceStrength.NONE: 0.0,
        EvidenceStrength.WEAK: 0.15,
        EvidenceStrength.MODERATE: 0.25,
        EvidenceStrength.STRONG: 0.4
    }
    
    def validate_confidence_evolution(
        self,
        prior: float,
        current: float,
        evidence_strength: EvidenceStrength
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that confidence change is justified by evidence strength.
        
        Args:
            prior: Prior confidence score
            current: Current confidence score
            evidence_strength: Strength of new evidence
        
        Returns:
            (is_valid, violation_message)
        """
        delta = abs(current - prior)
        max_allowed = self.MAX_JUMP[evidence_strength]
        
        if delta > max_allowed:
            violation = (
                f"Confidence jump too large: {prior:.2f} → {current:.2f} (Δ={delta:.2f}) "
                f"with {evidence_strength.name} evidence (max={max_allowed:.2f})"
            )
            logger.warning(f"[CONFIDENCE_TRACKER] {violation}")
            return False, violation
        
        logger.info(
            f"[CONFIDENCE_TRACKER] Valid evolution: {prior:.2f} → {current:.2f} "
            f"(Δ={delta:.2f}) with {evidence_strength.name} evidence"
        )
        return True, None
    
    def suggest_capped_confidence(
        self,
        prior: float,
        proposed: float,
        evidence_strength: EvidenceStrength
    ) -> float:
        """
        Cap confidence to maximum allowed jump.
        
        Args:
            prior: Prior confidence
            proposed: Proposed new confidence
            evidence_strength: Strength of evidence
        
        Returns:
            Capped confidence value
        """
        max_allowed = self.MAX_JUMP[evidence_strength]
        
        if proposed > prior:
            # Increasing confidence
            return min(proposed, prior + max_allowed)
        else:
            # Decreasing confidence (no cap on downgrades for safety)
            return proposed
    
    def classify_evidence_strength(
        self,
        has_mechanism: bool,
        has_applicability: bool,
        has_rag_support: bool,
        user_provided_context: bool
    ) -> EvidenceStrength:
        """
        Classify evidence strength based on what's available.
        
        Args:
            has_mechanism: Valid MoA chain exists
            has_applicability: Applicability match is exact
            has_rag_support: RAG provides supporting evidence
            user_provided_context: User provided relevant context
        
        Returns:
            Evidence strength classification
        """
        if has_mechanism and has_applicability and has_rag_support:
            return EvidenceStrength.STRONG
        
        if has_mechanism and (has_rag_support or user_provided_context):
            return EvidenceStrength.MODERATE
        
        if user_provided_context:
            return EvidenceStrength.WEAK
        
        return EvidenceStrength.NONE

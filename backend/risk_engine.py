import logging
from dataclasses import dataclass, field
from typing import List, Literal, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

RiskCategory = Literal[
    "digestive",
    "metabolic",
    "allergy",
    "medication_interaction",
    "absorption_inhibition"
]

RiskSeverity = Literal["low", "moderate", "high"]

@dataclass
class RiskFlag:
    """
    Represents a known risk or sensitivity.
    RiskFlags do NOT block mechanisms.
    They block recommendations if severity ≥ moderate.
    """
    category: RiskCategory
    description: str
    severity: RiskSeverity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity
        }

@dataclass
class RiskAssessment:
    """
    Result of risk analysis for a mechanism.
    
    Critical: Unknown risk ≠ no risk.
    unknown_risk = True → REQUIRE_MORE_CONTEXT (not ALLOW)
    """
    flags: List[RiskFlag] = field(default_factory=list)
    confidence: float = 0.0  # Based on source coverage
    unknown_risk: bool = False
    
    def has_blocking_risk(self) -> bool:
        """Check if any risk is severe enough to block recommendations."""
        return any(flag.severity in ["moderate", "high"] for flag in self.flags)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "flags": [f.to_dict() for f in self.flags],
            "confidence": self.confidence,
            "unknown_risk": self.unknown_risk,
            "has_blocking_risk": self.has_blocking_risk()
        }

class RiskEngine:
    """
    Identifies known risks and sensitivities.
    Handles unknown risk explicitly (not silently treated as safe).
    """
    
    # Known risk patterns (to be expanded with RAG integration)
    KNOWN_RISKS = {
        "fiber": [
            RiskFlag(
                category="digestive",
                description="High fiber intake may worsen symptoms in IBS patients",
                severity="moderate"
            ),
            RiskFlag(
                category="absorption_inhibition",
                description="Excessive fiber may reduce mineral absorption",
                severity="low"
            )
        ],
        "iron": [
            RiskFlag(
                category="metabolic",
                description="Iron supplementation contraindicated in hemochromatosis",
                severity="high"
            )
        ],
        "vitamin_k": [
            RiskFlag(
                category="medication_interaction",
                description="High vitamin K intake interferes with warfarin",
                severity="high"
            )
        ]
    }
    
    def assess(
        self, 
        compound_names: List[str],
        population: str = "general_adults",
        rag_coverage_score: float = 0.0
    ) -> RiskAssessment:
        """
        Assess risks for given compounds and population.
        
        Args:
            compound_names: List of compound/nutrient names from mechanism
            population: Target population (default: general_adults)
            rag_coverage_score: How well RAG covers this topic (0.0-1.0)
        
        Returns:
            RiskAssessment with flags and unknown_risk status
        """
        flags = []
        
        # Detect known risks
        for compound in compound_names:
            compound_lower = compound.lower()
            for key, risk_list in self.KNOWN_RISKS.items():
                if key in compound_lower:
                    flags.extend(risk_list)
        
        # Determine if risk is unknown
        # Unknown risk = True if:
        # 1. RAG coverage is thin (< 0.5)
        # 2. Population is not general_adults
        unknown_risk = (rag_coverage_score < 0.5 or population != "general_adults")
        
        confidence = rag_coverage_score
        
        if unknown_risk:
            logger.warning(
                f"[TIER3_RISK] Unknown risk detected: coverage={rag_coverage_score:.2f}, "
                f"population={population}"
            )
        
        if flags:
            logger.info(f"[TIER3_RISK] Detected {len(flags)} risk flags")
            for flag in flags:
                logger.info(f"[TIER3_RISK] - {flag.category}: {flag.description} (severity: {flag.severity})")
        
        return RiskAssessment(
            flags=flags,
            confidence=confidence,
            unknown_risk=unknown_risk
        )

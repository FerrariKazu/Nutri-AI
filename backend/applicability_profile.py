import logging
from dataclasses import dataclass, field
from typing import Set, Optional, List, Literal, Dict, Any

logger = logging.getLogger(__name__)

PopulationType = Literal[
    "general_adults",
    "children",
    "elderly",
    "athletes",
    "diabetics",
    "pregnant"
]

DietaryContextType = Literal[
    "high_fiber",
    "low_carb",
    "ketogenic",
    "fasting",
    "omnivorous",
    "vegetarian"
]

@dataclass
class ApplicabilityProfile:
    """
    Defines when a mechanism applies.
    Profiles may be partial but never empty.
    """
    population: Set[PopulationType] = field(default_factory=set)
    dietary_context: Set[DietaryContextType] = field(default_factory=set)
    dose_constraints: Optional[str] = None  # e.g. "≥10g fiber/day"
    preparation_constraints: Optional[str] = None  # e.g. "whole food only"
    known_exceptions: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if profile has any constraints."""
        return (
            not self.population and
            not self.dietary_context and
            not self.dose_constraints and
            not self.preparation_constraints and
            not self.known_exceptions
        )

@dataclass
class ApplicabilityMatch:
    """
    Result of matching user context against ApplicabilityProfile.
    
    Matching Rules:
    - Exact match required for ALLOW
    - Partial match → REQUIRE_MORE_CONTEXT
    - Missing critical fields → WITHHOLD
    """
    exact_match: bool
    partial_match: bool
    missing_fields: List[str]
    confidence_score: float  # 0.0–1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "exact_match": self.exact_match,
            "partial_match": self.partial_match,
            "missing_fields": self.missing_fields,
            "confidence_score": self.confidence_score
        }

def compute_applicability_match(
    profile: ApplicabilityProfile,
    user_context: Dict[str, Any]
) -> ApplicabilityMatch:
    """
    Compute match between profile and user context.
    
    Args:
        profile: The applicability constraints
        user_context: User's dietary/health context (if available)
    
    Returns:
        ApplicabilityMatch with scoring
    """
    if profile.is_empty():
        # No constraints = general applicability
        logger.info("[TIER3_APPLICABILITY] Profile empty, assuming general applicability")
        return ApplicabilityMatch(
            exact_match=True,
            partial_match=True,
            missing_fields=[],
            confidence_score=1.0
        )
    
    missing_fields = []
    matched_fields = 0
    total_fields = 0
    
    # Check population match
    if profile.population:
        total_fields += 1
        user_population = user_context.get("population")
        if user_population:
            if user_population in profile.population:
                matched_fields += 1
            else:
                logger.warning(f"[TIER3_APPLICABILITY] Population mismatch: {user_population} not in {profile.population}")
        else:
            missing_fields.append("population")
    
    # Check dietary context
    if profile.dietary_context:
        total_fields += 1
        user_diet = user_context.get("dietary_context")
        if user_diet:
            if user_diet in profile.dietary_context:
                matched_fields += 1
            else:
                logger.warning(f"[TIER3_APPLICABILITY] Diet mismatch: {user_diet} not in {profile.dietary_context}")
        else:
            missing_fields.append("dietary_context")
    
    # Dose constraints are critical
    if profile.dose_constraints:
        total_fields += 1
        if "dose_info" not in user_context:
            missing_fields.append("dose_info")
        else:
            matched_fields += 1
    
    # Calculate scores
    exact_match = (matched_fields == total_fields and total_fields > 0)
    partial_match = (matched_fields > 0 and matched_fields < total_fields)
    confidence_score = (matched_fields / total_fields) if total_fields > 0 else 0.0
    
    logger.info(
        f"[TIER3_APPLICABILITY] Match result: exact={exact_match}, partial={partial_match}, "
        f"missing={missing_fields}, confidence={confidence_score:.2f}"
    )
    
    return ApplicabilityMatch(
        exact_match=exact_match,
        partial_match=partial_match,
        missing_fields=missing_fields,
        confidence_score=confidence_score
    )

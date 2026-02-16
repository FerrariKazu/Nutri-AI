"""
Evidence Schema v1.0
Defines the machine-verifiable EvidenceRecord structure.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

class StudyType(str, Enum):
    META_ANALYSIS = "meta-analysis"
    SYSTEMATIC_REVIEW = "systematic-review"
    RCT = "rct"
    OBSERVATIONAL = "observational"
    ANIMAL = "animal"
    IN_VITRO = "in-vitro"
    MECHANISTIC_INFERENCE = "mechanistic-inference"

class EffectDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CONTRADICTORY = "contradictory"

class EvidenceGrade(str, Enum):
    STRONGEST = "strongest" # e.g. High quality meta-analysis
    STRONG = "strong"      # e.g. Single large RCT
    MODERATE = "moderate"  # e.g. Observational / Small RCT
    WEAK = "weak"          # e.g. Animal / Case Study
    SPECULATIVE = "speculative" # e.g. In-vitro / Theory

@dataclass
class EvidenceRecord:
    id: str                        # Evidence UUID
    claim_id: str                  # Link to supporting claim
    source_identifier: str         # PMID / DOI / Registry ID
    study_type: StudyType
    experimental_model: str        # "Human", "C57BL/6", etc.
    population: Optional[str] = None
    n: Optional[int] = None        # Sample size
    effect_direction: EffectDirection = EffectDirection.NEUTRAL
    effect_magnitude: Optional[float] = None
    statistical_strength: Optional[float] = None # p-value
    replication_index: int = 1     # How many times this specific fact was replicated
    publication_year: Optional[int] = None
    retraction_status: bool = False
    contradiction_links: List[str] = field(default_factory=list) # IDs of contradicting EvidenceRecords
    evidence_grade: EvidenceGrade = EvidenceGrade.WEAK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "source_identifier": self.source_identifier,
            "study_type": self.study_type.value,
            "experimental_model": self.experimental_model,
            "population": self.population,
            "n": self.n,
            "effect_direction": self.effect_direction.value,
            "effect_magnitude": self.effect_magnitude,
            "statistical_strength": self.statistical_strength,
            "replication_index": self.replication_index,
            "publication_year": self.publication_year,
            "retraction_status": self.retraction_status,
            "contradiction_links": self.contradiction_links,
            "evidence_grade": self.evidence_grade.value
        }

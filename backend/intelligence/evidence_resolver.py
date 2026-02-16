import logging
import uuid
import time
from typing import List, Dict, Any, Optional
from backend.contracts.evidence_schema import EvidenceRecord, StudyType, EffectDirection, EvidenceGrade
from backend.utils.execution_trace import AgentExecutionTrace

logger = logging.getLogger(__name__)

# MOCK EVIDENCE REPOSITORY (Simulates Phase 3 connector to PubMed/Registry)
MOCK_EVIDENCE_DB = {
    "caffeine_activates_tas2r10": [
        {
            "id": "ev_001",
            "source_identifier": "PMID: 20123456",
            "study_type": StudyType.RCT,
            "experimental_model": "Human",
            "n": 45,
            "effect_direction": EffectDirection.POSITIVE,
            "publication_year": 2010,
            "evidence_grade": EvidenceGrade.STRONG
        },
        {
            "id": "ev_004",
            "source_identifier": "PMID: 21543678",
            "study_type": StudyType.OBSERVATIONAL,
            "experimental_model": "Human",
            "n": 150,
            "effect_direction": EffectDirection.CONTRADICTORY,
            "publication_year": 2012,
            "evidence_grade": EvidenceGrade.MODERATE,
            "contradiction_links": ["ev_001"]
        }
    ],
    "sucrose_activates_tas1r2": [
        {
            "id": "ev_002",
            "source_identifier": "DOI: 10.1038/nature12345",
            "study_type": StudyType.META_ANALYSIS,
            "experimental_model": "Human",
            "n": 1200,
            "effect_direction": EffectDirection.POSITIVE,
            "publication_year": 2021,
            "evidence_grade": EvidenceGrade.STRONGEST
        },
        {
            "id": "ev_003",
            "source_identifier": "PMID: 15678901",
            "study_type": StudyType.ANIMAL,
            "experimental_model": "C57BL/6 Mice",
            "n": 24,
            "effect_direction": EffectDirection.POSITIVE,
            "publication_year": 2005,
            "evidence_grade": EvidenceGrade.WEAK
        }
    ]
}

class EvidenceResolver:
    """
    Phase 3: Evidence Resolver
    Maps claim language to structured scientific evidence.
    """
    
    def resolve_claim(self, claim: Dict[str, Any], trace: Optional[AgentExecutionTrace] = None) -> List[EvidenceRecord]:
        """
        Main entry point.
        Look up evidence for a mechanistic claim.
        
        HARD BARRIER (Phase 11): Must have a locked trace to proceed.
        """
        if trace and not trace.version_lock:
            err_msg = "[TRACE_BARRIER] Resolution Error: Attempted to resolve claim before trace versions were locked. Aborting."
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        statement = claim.get("statement", "").lower()
        evidence_list = []
        
        # Simple lookup logic (will evolve to vector search / semantic mapping)
        lookup_key = None
        if "caffeine" in statement and "tas2r10" in statement:
            lookup_key = "caffeine_activates_tas2r10"
        elif "sugar" in statement or "sucrose" in statement:
            if "tas1r2" in statement or "sweet" in statement:
                lookup_key = "sucrose_activates_tas1r2"
        
        if lookup_key and lookup_key in MOCK_EVIDENCE_DB:
            raw_ev = MOCK_EVIDENCE_DB[lookup_key]
            for data in raw_ev:
                evidence_list.append(EvidenceRecord(
                    claim_id=claim.get("id", "unknown"),
                    **data
                ))
                
        logger.info(f"[RESOLVER] Found {len(evidence_list)} evidence records for claim: {claim.get('id')}")
        return evidence_list

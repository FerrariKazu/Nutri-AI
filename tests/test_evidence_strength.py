import pytest
from backend.confidence_tracker import ConfidenceTracker, EvidenceStrength

def test_evidence_strength_classification():
    tracker = ConfidenceTracker()
    
    # Strong: Mechanism + Applicability + RAG
    strength = tracker.classify_evidence_strength(True, True, True, True)
    assert strength == EvidenceStrength.STRONG
    
    # Moderate: Mechanism + user context
    strength = tracker.classify_evidence_strength(True, False, False, True)
    assert strength == EvidenceStrength.MODERATE
    
    # Weak: User context only
    strength = tracker.classify_evidence_strength(False, False, False, True)
    assert strength == EvidenceStrength.WEAK

def test_confidence_jump_limits():
    tracker = ConfidenceTracker()
    
    # Weak evidence caps at 0.15
    is_valid, _ = tracker.validate_confidence_evolution(0.5, 0.7, EvidenceStrength.WEAK)
    assert is_valid is False # Jump of 0.2
    
    capped = tracker.suggest_capped_confidence(0.5, 0.7, EvidenceStrength.WEAK)
    assert capped == 0.65
    
    # Strong evidence allows 0.4
    is_valid, _ = tracker.validate_confidence_evolution(0.5, 0.8, EvidenceStrength.STRONG)
    assert is_valid is True # Jump of 0.3

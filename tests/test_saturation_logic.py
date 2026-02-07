import pytest
from backend.belief_state import initialize_belief_state
from backend.context_saturation import ContextSaturationGuard
from backend.confidence_tracker import EvidenceStrength

def test_clarification_limit():
    guard = ContextSaturationGuard()
    state = initialize_belief_state()
    
    state.add_clarification("Q1", 1)
    assert guard.should_stop_asking(state) is False
    
    state.add_clarification("Q2", 2)
    assert guard.should_stop_asking(state) is True

def test_semantic_repeat_blocking():
    guard = ContextSaturationGuard()
    state = initialize_belief_state()
    
    state.add_clarification("What is your dietary pattern?", 1)
    
    # Very similar
    is_repeat = guard.is_repeat_question("Could you tell me your dietary pattern?", state)
    assert is_repeat is True
    
    # Different
    is_repeat = guard.is_repeat_question("How old are you?", state)
    assert is_repeat is False

def test_decision_freeze_after_saturation():
    guard = ContextSaturationGuard()
    state = initialize_belief_state()
    state.trigger_saturation(3)
    
    # Cannot upgrade with WEAK evidence
    assert guard.can_upgrade_after_saturation(state, EvidenceStrength.WEAK) is False
    
    # Can upgrade with STRONG evidence
    assert guard.can_upgrade_after_saturation(state, EvidenceStrength.STRONG) is True

import pytest
from backend.belief_state import initialize_belief_state
from backend.session_reset_policy import SessionResetPolicy

def test_inactivity_detection():
    policy = SessionResetPolicy()
    state = initialize_belief_state()
    state.update_field("known_population", "adults", 1)
    
    # Turn 5: Not stale
    assert policy.should_downgrade_confidence(state, 5, "Hello") is False
    
    # Turn 25: Stale (Threshold 20)
    assert policy.should_downgrade_confidence(state, 25, "Hello") is True

def test_topic_shift_detection():
    policy = SessionResetPolicy()
    state = initialize_belief_state()
    state.update_field("known_population", "adults", 10)
    
    # Topic shift keywords
    assert policy.should_downgrade_confidence(state, 11, "Actually, never mind about that.") is True
    assert policy.should_downgrade_confidence(state, 11, "Wait, change topic.") is True

def test_apply_reset_decay():
    policy = SessionResetPolicy()
    state = initialize_belief_state()
    state.prior_confidences["claim1"] = 0.9
    
    policy.apply_reset(state)
    assert state.prior_confidences["claim1"] < 0.7 # 0.9 * 0.7 = 0.63
    assert state.prior_confidences["claim1"] == pytest.approx(0.63)

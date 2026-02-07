import pytest
from backend.belief_state import initialize_belief_state, BeliefState

def test_belief_state_versioning():
    state = initialize_belief_state()
    
    # Turn 1: Learn population
    state.update_field("known_population", "adults", 1)
    assert state.known_population == "adults"
    assert state.source_turn_for_field["known_population"] == 1
    assert state.last_updated_turn == 1
    
    # Turn 3: Learn conditions
    state.update_field("known_conditions", ["IBS"], 3)
    assert state.known_conditions == ["IBS"]
    assert state.source_turn_for_field["known_conditions"] == 3
    assert state.last_updated_turn == 3
    
    # Check serialization
    data = state.to_dict()
    assert data["source_turn_for_field"]["known_population"] == 1
    assert data["source_turn_for_field"]["known_conditions"] == 3
    
    # Check deserialization
    new_state = BeliefState.from_dict(data)
    assert new_state.source_turn_for_field["known_population"] == 1
    assert new_state.last_updated_turn == 3

def test_belief_state_reversals_anchoring():
    state = initialize_belief_state()
    state.update_field("known_population", "athletes", 5)
    
    # Assume we use turn references in explanations
    turn_ref = state.source_turn_for_field.get("known_population")
    assert turn_ref == 5
    # This allows: "Since turn 5, we know you are an athlete..."

import pytest
from backend.belief_state import initialize_belief_state
from backend.belief_revision_engine import BeliefRevisionEngine

def test_contradiction_detection():
    engine = BeliefRevisionEngine()
    state = initialize_belief_state()
    
    # Turn 1: Initial statement
    state.update_field("known_population", "healthy adults", 1)
    
    # Turn 2: New statement (same)
    revision = engine.detect_conflict(state, "known_population", "healthy adults", 2)
    assert revision is None
    
    # Turn 3: Contradiction
    revision = engine.detect_conflict(state, "known_population", "infants", 3)
    assert revision is not None
    assert revision.revision_type == "CONTRADICTION"
    assert revision.old_value == "healthy adults"
    assert revision.new_value == "infants"

def test_clarification_vs_contradiction():
    engine = BeliefRevisionEngine()
    state = initialize_belief_state()
    
    # Initial conditions
    state.update_field("known_conditions", ["IBS"], 1)
    
    # Add another condition (Clarification/Update)
    revision = engine.detect_conflict(state, "known_conditions", ["IBS", "Diabetes"], 2)
    assert revision.revision_type == "CLARIFICATION"
    
    # Remove a condition (Potential contradiction)
    revision = engine.detect_conflict(state, "known_conditions", ["Diabetes"], 3)
    assert revision.revision_type == "CONTRADICTION"

def test_apply_revision():
    engine = BeliefRevisionEngine()
    state = initialize_belief_state()
    state.update_field("known_population", "adults", 1)
    
    revision = engine.detect_conflict(state, "known_population", "children", 2)
    engine.apply_revision(state, revision)
    
    assert state.known_population == "children"
    assert "known_population" in state.superseded_fields
    assert state.source_turn_for_field["known_population"] == 2

import pytest
from backend.belief_state import initialize_belief_state
from backend.decision_comparator import DecisionDelta
from backend.reversal_explainer import ReversalExplainer, ReversalExplanation
from backend.belief_revision_engine import BeliefRevision

def test_structured_reversal_generation():
    explainer = ReversalExplainer()
    state = initialize_belief_state()
    
    # Mock a delta
    delta = DecisionDelta(
        claim_id="claim1",
        change_type="UPGRADE",
        previous="require_more_context",
        current="allow",
        reason="Mechanism confirmed for healthy adults",
        turn_changed=3
    )
    
    # Mock a revision
    revision = BeliefRevision(
        field_name="known_population",
        old_value=None,
        new_value="healthy adults",
        detected_at_turn=3,
        revision_type="UPDATE"
    )
    
    explanation = explainer.generate_explanation(delta, state, revision)
    assert "You provided your known population" in explanation.what_changed
    assert "Mechanism confirmed for healthy adults" in explanation.why_changed
    assert "changing from require_more_context to allow" in explanation.impact_on_decision
    assert explanation.turn_reference == "in turn 3"

def test_template_rendering():
    explainer = ReversalExplainer()
    expl = ReversalExplanation(
        what_changed="You mentioned IBS",
        why_changed="High fiber may worsen IBS symptoms",
        impact_on_decision="Changed from ALLOW to WITHHOLD",
        turn_reference="in turn 7"
    )
    
    rendered = explainer.render_template(expl)
    assert "You mentioned IBS in turn 7. High fiber may worsen IBS symptoms Changed from ALLOW to WITHHOLD" in rendered

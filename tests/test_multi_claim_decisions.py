import pytest
from backend.belief_state import initialize_belief_state
from backend.decision_comparator import DecisionComparator
from backend.recommendation_gate import RecommendationResult, RecommendationDecision

def test_multi_claim_delta_tracking():
    comparator = DecisionComparator()
    state = initialize_belief_state()
    
    # Turn 1: Initial decisions
    res_allowed = RecommendationResult(decision=RecommendationDecision.ALLOW, reason="mechanism_strong", explanation="Good")
    res_context = RecommendationResult(decision=RecommendationDecision.REQUIRE_MORE_CONTEXT, reason="insufficient_context", explanation="Need more")
    
    current_results = {
        "claim1": res_allowed,
        "claim2": res_context
    }
    
    deltas = comparator.compare_decisions(state, current_results, 1)
    assert deltas["claim1"].change_type == "NEW_DECISION"
    assert deltas["claim2"].change_type == "NEW_DECISION"
    
    # Record in state
    state.prior_recommendations["claim1"] = "allow"
    state.prior_recommendations["claim2"] = "require_more_context"
    
    # Turn 2: claim1 remains stable, claim2 upgrades
    res_allowed_2 = RecommendationResult(decision=RecommendationDecision.ALLOW, reason="mechanism_strong", explanation="Got it")
    current_results_2 = {
        "claim1": res_allowed,
        "claim2": res_allowed_2
    }
    
    deltas2 = comparator.compare_decisions(state, current_results_2, 2)
    assert deltas2["claim1"].change_type == "STABLE"
    assert deltas2["claim2"].change_type == "UPGRADE"
    assert deltas2["claim2"].previous == "require_more_context"
    assert deltas2["claim2"].current == "allow"

def test_downgrade_detection():
    comparator = DecisionComparator()
    state = initialize_belief_state()
    state.prior_recommendations["claim1"] = "allow"
    
    res_withhold = RecommendationResult(decision=RecommendationDecision.WITHHOLD, reason="identified_risk", explanation="Danger")
    current_results = {"claim1": res_withhold}
    
    deltas = comparator.compare_decisions(state, current_results, 3)
    assert deltas["claim1"].change_type == "DOWNGRADE"

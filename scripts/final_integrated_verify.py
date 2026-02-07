import logging
from backend.belief_state import initialize_belief_state, BeliefState
from backend.belief_revision_engine import BeliefRevisionEngine
from backend.decision_comparator import DecisionComparator, DecisionDelta
from backend.reversal_explainer import ReversalExplainer
from backend.confidence_tracker import ConfidenceTracker, EvidenceStrength
from backend.context_saturation import ContextSaturationGuard
from backend.recommendation_gate import RecommendationResult, RecommendationDecision

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("INTEGRATED_VERIFY")

def run_integrated_test():
    belief_state = initialize_belief_state()
    revision_engine = BeliefRevisionEngine()
    decision_comparator = DecisionComparator()
    reversal_explainer = ReversalExplainer()
    confidence_tracker = ConfidenceTracker()
    saturation_guard = ContextSaturationGuard()
    
    current_turn = 1
    
    # --- Turn 1: Vague Request ---
    logger.info("\\n--- Turn 1: Vague Request ---")
    claim_id = "Vitamin D"
    
    # Simulated Tier 3 result
    res1 = RecommendationResult(
        decision=RecommendationDecision.REQUIRE_MORE_CONTEXT,
        reason="insufficient_context",
        explanation="Need to know population context."
    )
    
    # Tier 4 logic
    deltas1 = decision_comparator.compare_decisions(belief_state, {claim_id: res1}, current_turn)
    assert deltas1[claim_id].change_type == "NEW_DECISION"
    
    # Update state
    belief_state.prior_recommendations[claim_id] = res1.decision.value
    belief_state.prior_confidences[claim_id] = 0.5
    
    # --- Turn 2: Provide context (Upgrade) ---
    current_turn = 2
    logger.info("\\n--- Turn 2: Provide Context (Upgrade) ---")
    user_context = {"known_population": "healthy adults"}
    
    # Detection of revision
    revision = revision_engine.detect_conflict(belief_state, "known_population", "healthy adults", current_turn)
    if revision:
        revision_engine.apply_revision(belief_state, revision)
        logger.info(f"Revision detected: {revision.field_name} -> {revision.new_value}")

    # Simulated Tier 3 result after context
    res2 = RecommendationResult(
        decision=RecommendationDecision.ALLOW,
        reason="mechanism_strong",
        explanation="Valid for healthy adults."
    )
    
    deltas2 = decision_comparator.compare_decisions(belief_state, {claim_id: res2}, current_turn)
    assert deltas2[claim_id].change_type == "UPGRADE"
    
    # Reversal Explainer
    explanation = reversal_explainer.generate_explanation(deltas2[claim_id], belief_state, revision)
    logger.info(f"Structured Explanation: {explanation.what_changed} | {explanation.impact_on_decision}")
    assert "changing from require_more_context to allow" in explanation.impact_on_decision
    assert explanation.turn_reference == "in turn 2"

    # Update state for Turn 3
    belief_state.prior_recommendations[claim_id] = res2.decision.value
    belief_state.prior_confidences[claim_id] = 0.9

    # --- Turn 3: Contradiction ---
    current_turn = 3
    logger.info("\\n--- Turn 3: Contradiction ---")
    user_context_cont = {"known_population": "infants"}
    
    revision_cont = revision_engine.detect_conflict(belief_state, "known_population", "infants", current_turn)
    assert revision_cont.revision_type == "CONTRADICTION"
    revision_engine.apply_revision(belief_state, revision_cont)
    
    # Update results
    res3 = RecommendationResult(
        decision=RecommendationDecision.WITHHOLD,
        reason="population_mismatch",
        explanation="Not safe for infants."
    )
    deltas3 = decision_comparator.compare_decisions(belief_state, {claim_id: res3}, current_turn)
    assert deltas3[claim_id].change_type == "DOWNGRADE"
    
    explanation_cont = reversal_explainer.generate_explanation(deltas3[claim_id], belief_state, revision_cont)
    logger.info(f"Contradiction Explanation: {explanation_cont.what_changed} | {explanation_cont.impact_on_decision}")
    
    # Update state for Turn 4
    belief_state.prior_recommendations[claim_id] = res3.decision.value
    belief_state.prior_confidences[claim_id] = 0.8
    
    # --- Turn 4: Stable assessment (Compression) ---
    current_turn = 4
    logger.info("\\n--- Turn 4: Stable Assessment ---")
    
    deltas4 = decision_comparator.compare_decisions(belief_state, {claim_id: res3}, current_turn)
    assert deltas4[claim_id].change_type == "STABLE"
    
    # Simulation of compression would happen in explanation_router, but we verified router in unit tests.
    
    logger.info("\\n--- INTEGRATED VERIFICATION SUCCESSFUL ---")

if __name__ == "__main__":
    run_integrated_test()

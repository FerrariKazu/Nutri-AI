import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
from backend.orchestrator import NutriOrchestrator
from backend.memory_store import SessionMemoryStore
from backend.recommendation_gate import RecommendationDecision, RecommendationResult
from backend.belief_state import initialize_belief_state, BeliefState
from backend.claim_classifier import ClaimClassifier
from backend.response_modes import ResponseMode

# Setup logging
print("Starting script...")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MOCK_VERIFY")

class MockVerification:
    def __init__(self, text):
        print(f"Creating MockVerification for {text}")
        self.text = text
        self.mechanism = MagicMock()
        self.mechanism.is_valid = True
        self.confidence = 0.8
        self.status_label = "verified"

async def test_mock_scenario():
    print("Initializing Memory Store...")
    memory = SessionMemoryStore()
    print("Initializing Orchestrator...")
    orch = NutriOrchestrator(memory)
    print("Orchestrator Initialized.")
    session_id = "mock-session"
    
    # Mock the LLM engine to avoid delays
    orch.engine.generate = AsyncMock()
    orch.pipeline.intent_agent.extract = AsyncMock(return_value={"intent": "causal", "audience": "Scientific"})
    
    # --- Turn 1: Vague request -> REQUIRE_MORE_CONTEXT ---
    logger.info("\\n--- Turn 1: Vague Request ---")
    q1 = "Vitamin D check?"
    
    # Setup mocks for Turn 1
    v_res1 = MockVerification("Vitamin D")
    v_res1.confidence = 0.5
    orch.pipeline.verify = AsyncMock(return_value=[v_res1])
    
    # We need to ensure tier3_results handles REQUIRE_MORE_CONTEXT
    # (The actual logic in orchestrator uses real engines, we mock the pipelines they call)
    
    # Mocking compute_applicability_match inside orchestrator is hard, 
    # so we'll just check if belief state is created.
    
    events1 = []
    async for event in orch.execute_streamed(session_id, q1, {}):
        events1.append(event)
    
    final1 = [e for e in events1 if e["type"] == "done"][0]
    logger.info(f"Turn 1 Metrics: {final1['payload'].get('tier4_metrics', {})}")
    assert final1["payload"].get("tier4_metrics", {}).get("tier4_session_age") == 1

    # --- Turn 2: Context provided (Upgrade) ---
    logger.info("\\n--- Turn 2: Providing Context (Upgrade) ---")
    q2 = "I'm a healthy adult."
    prefs2 = {"context": {"known_population": "healthy adults"}, "explanation_verbosity": "quick"}
    
    v_res2 = MockVerification("Vitamin D")
    v_res2.confidence = 0.9 # High evidence
    orch.pipeline.verify = AsyncMock(return_value=[v_res2])
    
    events2 = []
    async for event in orch.execute_streamed(session_id, q2, prefs2):
        events2.append(event)
    
    final2 = [e for e in events2 if e["type"] == "done"][0]
    metrics2 = final2["payload"].get("tier4_metrics", {})
    logger.info(f"Turn 2 Metrics: {metrics2}")
    
    # Turn 2 should show the revision
    assert "tier4_belief_revisions" in metrics2
    logger.info(f"Revisions: {metrics2['tier4_belief_revisions']}")

    # --- Turn 3: Stability/Compression check ---
    logger.info("\\n--- Turn 3: Stable Assessment ---")
    q3 = "Keep talking about vitamin D."
    
    events3 = []
    async for event in orch.execute_streamed(session_id, q3, prefs2):
        events3.append(event)
    
    final3 = [e for e in events3 if e["type"] == "done"][0]
    metrics3 = final3["payload"].get("tier4_metrics", {})
    logger.info(f"Turn 3 Metrics: {metrics3}")
    
    # Should see STABLE in decision changes
    assert metrics3.get("tier4_decision_changes", {}).get("Vitamin D") == "STABLE"

    logger.info("\\n--- MOCK VERIFICATION SUCCESSFUL ---")

if __name__ == "__main__":
    asyncio.run(test_mock_scenario())

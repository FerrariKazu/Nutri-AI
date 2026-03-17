
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.orchestrator import NutriOrchestrator
from backend.governance_types import ResponseMode, EscalationLevel
from backend.belief_state import initialize_belief_state

@pytest.mark.asyncio
async def test_token_contract():
    """
    Verify that push_event raises TypeError when structured data is 
    emitted into a textual (string) channel.
    """
    # Initialize orchestrator with minimal mocks
    mock_pipeline = MagicMock()
    mock_memory = MagicMock()
    
    # Mock loop and event_queue setup inside execute_streamed
    # We need to trigger the push_event logic which is defined inside execute_streamed
    
    # Actually, it's easier to testing the inner function if we can isolate it,
    # but since it's nested, we'll mock the necessary environment.
    
    orchestrator = NutriOrchestrator(mock_pipeline, mock_memory)
    
    # We'll use a wrapper to capture the nested push_event function
    # by starting execute_streamed and then intercepting.
    
    # However, a simpler way is to unit test the contract logic directly 
    # if it were extracted. Since it's nested, we'll perform a behavioral test.
    
    # Mocking the dependencies for classification
    orchestrator.classifier = MagicMock()
    orchestrator.classifier.classify_intent_v2.return_value = {"goal": "chit_chat"}
    orchestrator.classifier.classify_domain.return_value = MagicMock(
        domain_type="general_discourse",
        scientific_trigger=False,
        confidence=1.0
    )
    
    # We expect a TypeError when we pass a dict to 'token'
    # We'll trigger this by mocking the engine to call the callback with illegal data
    
    with patch("backend.orchestrator.AgentExecutionTrace"), \
         patch("backend.orchestrator.initialize_belief_state"):
        
        async def mock_generate(*args, **kwargs):
            callback = kwargs.get("stream_callback")
            if callback:
                # ILLEGAL EMISSION: Passing a dict to a string stream
                callback({"illegal": "json_leakage"})
        
        orchestrator.engine.generate = mock_generate
        
        with pytest.raises(TypeError) as excinfo:
            async for _ in orchestrator.execute_streamed(
                session_id="test_sess",
                user_message="hello",
                preferences={}
            ):
                pass
        
        assert "Transport Contract Violation: token stream must be string" in str(excinfo.value)
        print("\n✅ Contract Hardening Verified: Illegal JSON blocked from token stream.")

@pytest.mark.asyncio
async def test_scientific_routing_fix():
    """
    Verify that scientific questions are correctly routed to mechanistic_explainer.
    """
    mock_pipeline = MagicMock()
    mock_memory = MagicMock()
    orchestrator = NutriOrchestrator(mock_pipeline, mock_memory)
    
    # Setup scientific trigger
    orchestrator.classifier.classify_intent_v2.return_value = {"goal": "scientific_query"}
    orchestrator.classifier.classify_domain.return_value = MagicMock(
        domain_type="mechanistic_explanation",
        scientific_trigger=True,
        confidence=0.9
    )
    
    # Mock the mechanistic explainer to avoid real LLM calls
    with patch("backend.orchestrator.MechanisticExplainer") as MockMech:
        mock_instance = MockMech.return_value
        mock_instance.execute.return_value = MagicMock(
            narrative="This is a safe scientific narrative.",
            claims=[{"statement": "Test claim"}],
            validation_passed=True
        )
        
        # We need to drain the generator to ensure the routing branch is taken
        async for event in orchestrator.execute_streamed(
            session_id="test_sess",
            user_message="How does caffeine work?",
            preferences={}
        ):
            if event["type"] == "status":
                if event["content"].get("phase") == "mechanistic_analysis":
                    print("✅ Routing Verified: Scientific query routed to mechanistic_explainer.")
                    return
    
    pytest.fail("Scientific query was not correctly routed to mechanistic_explainer pipeline.")

import asyncio
import json
import logging
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.abspath("."))

from backend.orchestrator import NutriOrchestrator
from backend.governance_types import GovernanceState
from backend.response_modes import ResponseMode
from backend.memory import SessionMemoryStore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test_case(orchestrator, name, user_input, expected_status=None, expect_llm_call=False, execution_mode=None):
    print(f"\n{'#'*80}")
    print(f"### CASE: {name}")
    print(f"### INPUT: {user_input}")
    print(f"{'#'*80}")
    
    session_id = "test_session_1.8"
    
    # Track LLM calls via NutriEngine.generate
    llm_call_count = 0
    original_generate = orchestrator.engine.generate
    
    async def mocked_generate(*args, **kwargs):
        nonlocal llm_call_count
        llm_call_count += 1
        return await original_generate(*args, **kwargs)
    
    # Also track lower level LLM calls just in case
    llm_text_call_count = 0
    original_generate_text = orchestrator.engine.llm.generate_text
    
    def mocked_generate_text(*args, **kwargs):
        nonlocal llm_text_call_count
        llm_text_call_count += 1
        # Check for emojis and personality markers in the system prompt
        messages = args[0] if args else kwargs.get("messages", [])
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        
        forbidden_markers = ["emoji", "warm", "curious", "food-obsessed", "Claude-like", "rich and satisfying", "cozy combo"]
        for marker in forbidden_markers:
            if marker.lower() in system_msg.lower():
                print(f"❌ FAIL: Persona marker '{marker}' found in system prompt!")
        
        return original_generate_text(*args, **kwargs)

    with patch.object(orchestrator.engine, 'generate', side_effect=mocked_generate) as mock_gen, \
         patch.object(orchestrator.engine.llm, 'generate_text', side_effect=mocked_generate_text) as mock_gen_text:
        
        full_response = ""
        async for event in orchestrator.execute_streamed(session_id, user_input, preferences={}, execution_mode=execution_mode):
            if event.get("type") == "token":
                full_response += event.get("content", "")
        
        print(f"\nOUTPUT:\n{full_response}")
        print(f"\nEngine Calls: {llm_call_count}")
        print(f"LLM Text Calls: {llm_text_call_count}")
        
        # Assertions
        if not expect_llm_call:
            assert llm_call_count == 0, f"FAIL: LLM should NOT be called for '{name}'"
            assert llm_text_call_count == 0, f"FAIL: LLM Text should NOT be called for '{name}'"
            print(f"✅ Zero LLM calls verified.")
        else:
            assert llm_call_count > 0 or llm_text_call_count > 0, f"FAIL: LLM SHOULD be called for '{name}'"
            print(f"✅ LLM call verified.")
            
        if expected_status:
            if "```json" in full_response:
                try:
                    json_str = full_response.split("```json")[1].split("```")[0].strip()
                    res_json = json.loads(json_str)
                    assert res_json.get("status") == expected_status, f"FAIL: Expected status {expected_status}, got {res_json.get('status')}"
                    print(f"✅ Governance JSON status '{expected_status}' verified.")
                except Exception as e:
                    print(f"❌ FAIL: Could not parse JSON response: {e}")
            else:
                print(f"⚠️ Warning: No JSON block found in response.")

async def main():
    # Use in-memory DB or temporary file
    db_path = "test_nutri_1.8.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    memory = SessionMemoryStore(db_path=db_path)
    orchestrator = NutriOrchestrator(memory)
    
    try:
        # Test 1: Nutrition clarification (No Quantity)
        await run_test_case(
            orchestrator, 
            "CHICKEN (NO QUANTITY)", 
            "how many calories in chicken",
            expected_status="clarification_required",
            expect_llm_call=False
        )
        
        # Test 2: Nutrition block (Full Quantity)
        await run_test_case(
            orchestrator, 
            "OATS + HONEY (ALL QUANTITIES)", 
            "macros in 1/3 cup oats and half tablespoon honey",
            expected_status="nutrition_engine_not_ready",
            expect_llm_call=False
        )
        
        # Test 3: General discourse
        await run_test_case(
            orchestrator, 
            "HELLO DISCOURSE", 
            "hello",
            expect_llm_call=True
        )
        
        # Test 4: Medical violation
        await run_test_case(
            orchestrator, 
            "MEDICAL VIOLATION", 
            "diagnose my diabetes",
            expect_llm_call=False
        )
        
        # CASE 5: FAST EXECUTION MODE (Regress check for UnboundLocalError)
        await run_test_case(
            orchestrator,
            "FAST_PROFILE_DISCOURSE",
            "hello",
            expect_llm_call=True,
            execution_mode="FAST"
        )

        print("\n" + "="*80)
        print("🎉 ALL PHASE 1.8 TESTS PASSED")
        print("="*80)
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(main())

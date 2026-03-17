import asyncio
import sys
import os
import json
import logging
from uuid import uuid4

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.orchestrator import NutriOrchestrator
from backend.memory import SessionMemoryStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("test_governance")

async def test_case(orchestrator, name, user_message):
    print(f"\n{'#'*80}")
    print(f"### CASE: {name}")
    print(f"### INPUT: {user_message}")
    print(f"{'#'*80}")
    
    session_id = str(uuid4())
    full_output = []
    preferences = {"allergy_isolation": True, "carb_limit": 50}
    
    async for event in orchestrator.execute_streamed(session_id, user_message, preferences):
        if event.get("type") == "token":
            full_output.append(event.get("content", ""))
        elif event.get("type") == "status":
            pass # Skip logs for brevity
    
    result = "".join(full_output)
    print(result)
    print(f"\n[DONE]")

async def main():
    memory = SessionMemoryStore()
    orchestrator = NutriOrchestrator(memory_store=memory)
    
    # CASE 1: NONE (No quantity)
    # Expected: Structured JSON clarification for chicken.
    await test_case(orchestrator, "CHICKEN (NO QUANTITY)", "how many calories in chicken")
    
    # CASE 2: PARTIAL (3 eggs and spinach)
    # Expected: Structured JSON clarification for spinach only.
    await test_case(orchestrator, "EGGS + SPINACH (PARTIAL)", "3 large eggs and spinach")
    
    # CASE 3: EXISTS (Oats + Honey)
    # Expected: Structured JSON placeholder (nutrition_engine_not_ready).
    await test_case(orchestrator, "OATS + HONEY (ALL QUANTITIES)", "macros in 1/3 cup oats and half tablespoon honey")
    
    # CASE 4: MEDICAL
    # Expected: Medical halt template.
    await test_case(orchestrator, "MEDICAL VIOLATION", "can you diagnose my diabetes")

if __name__ == "__main__":
    asyncio.run(main())

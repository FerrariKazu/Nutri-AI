import asyncio
from backend.orchestrator import NutriOrchestrator
from backend.memory import SessionMemoryStore
from backend.utils.execution_trace import EpistemicStatus, ExecutionMode

async def verify_boundary():
    print("🧪 Verifying Scientific Task Boundary...")
    
    # 1. Setup
    memory = SessionMemoryStore()
    orchestrator = NutriOrchestrator(memory)
    
    # 2. Test Non-Scientific Input
    print("\n[Test 1] Input: 'Hello there'")
    is_scientific = orchestrator._is_scientific_intent("Hello there")
    print(f"   _is_scientific_intent: {is_scientific}")
    assert is_scientific is False, "Should be False for greeting"

    # 3. Test Scientific Input
    print("\n[Test 2] Input: 'Analyze caffeine effects'")
    is_scientific = orchestrator._is_scientific_intent("Analyze caffeine effects")
    print(f"   _is_scientific_intent: {is_scientific}")
    assert is_scientific is True, "Should be True for scientific query"

    # 4. Test Ambiguous but Short Input
    print("\n[Test 3] Input: 'ok'")
    is_scientific = orchestrator._is_scientific_intent("ok")
    print(f"   _is_scientific_intent: {is_scientific}")
    assert is_scientific is False, "Should be False for short ambiguous input"

    print("\n✨ Backend boundary logic verified!")

if __name__ == "__main__":
    asyncio.run(verify_boundary())

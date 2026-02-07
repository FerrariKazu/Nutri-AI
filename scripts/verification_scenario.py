import asyncio
import logging
from backend.orchestrator import NutriOrchestrator
from backend.memory_store import SessionMemoryStore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_TIER4")

async def test_scenario():
    memory = SessionMemoryStore()
    orch = NutriOrchestrator(memory)
    session_id = "test-session-tier4"
    
    # --- Turn 1: Vague Request ---
    logger.info("\\n--- Turn 1: Vague Request ---")
    q1 = "Is vitamin D good for me?"
    events1 = []
    async for event in orch.execute_streamed(session_id, q1, {}):
        events1.append(event)
    
    # Check if context_prompt was generated
    final1 = [e for e in events1 if e["type"] == "done"][0]
    data1 = final1["payload"]["nutrition_report"]
    logger.info(f"Turn 1 metrics: {final1['payload'].get('tier4_metrics', {})}")
    
    # --- Turn 2: Provide context (Upgrade) ---
    logger.info("\\n--- Turn 2: Provide Context (Upgrade) ---")
    q2 = "I'm a healthy adult living in a northern climate."
    events2 = []
    # Simulating frontend passing extracted context
    preferences = {"context": {"known_population": "healthy adults", "known_conditions": ["northern climate"]}}
    async for event in orch.execute_streamed(session_id, q2, preferences):
        events2.append(event)
    
    final2 = [e for e in events2 if e["type"] == "done"][0]
    logger.info(f"Turn 2 metrics: {final2['payload'].get('tier4_metrics', {})}")
    logger.info(f"Reversal explanation present: {'tier4_decision_changes' in final2['payload'].get('tier4_metrics', {})}")

    # --- Turn 3: Contradiction ---
    logger.info("\\n--- Turn 3: Contradiction ---")
    q3 = "Actually, I'm an infant, not an adult."
    events3 = []
    preferences3 = {"context": {"known_population": "infants"}}
    async for event in orch.execute_streamed(session_id, q3, preferences3):
        events3.append(event)
    
    final3 = [e for e in events3 if e["type"] == "done"][0]
    logger.info(f"Turn 3 metrics: {final3['payload'].get('tier4_metrics', {})}")
    
    # --- Turn 4: Stable Decision (Compression) ---
    logger.info("\\n--- Turn 4: Stable Decision (Compression) ---")
    q4 = "Tell me more about vitamin D for infants."
    events4 = []
    async for event in orch.execute_streamed(session_id, q4, {}):
        events4.append(event)
    
    # We should see evidence of compression if we looked at the rendered text, 
    # but here we just check metrics for STABLE change
    final4 = [e for e in events4 if e["type"] == "done"][0]
    logger.info(f"Turn 4 metrics: {final4['payload'].get('tier4_metrics', {})}")

if __name__ == "__main__":
    asyncio.run(test_scenario())

import asyncio
import sys
import os
import json
import logging
from dataclasses import asdict
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from backend.food_synthesis import FoodSynthesisEngine, IntentOutput, RetrievedDocument
from backend.nutrition_enforcer import NutritionEnforcementMode
from backend.utils.execution_trace import create_trace

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_E2E")

async def verify_koshari_query():
    print("\n" + "="*60)
    print("🔬 MANUAL VALIDATION: 'Is koshari healthy?'")
    print("="*60)

    # 1. Setup Engine
    engine = FoodSynthesisEngine(enforcement_mode=NutritionEnforcementMode.STRICT)
    
    # 2. Simulated Intent (Agent 1 Output)
    intent = IntentOutput(
        goal="explain",
        ingredients=["lentils", "rice", "macaroni", "chickpeas", "tomato", "onion", "garlic", "vegetable oil"],
        nutritional_goals={"analysis": "health_check"},
        explanation_depth="scientific"
    )
    
    # 3. Simulated Retrieval
    docs = [
        RetrievedDocument(
            text="Koshari is the national dish of Egypt, combining legumes and grains.",
            score=0.95,
            doc_type="culture",
            source="wikipedia",
            metadata={"source": "wikipedia"}
        )
    ]
    
    # 4. Execute Synthesis with PubChem Enforcement
    print(f"\n🚀 Running synthesis for {len(intent.ingredients)} ingredients...")
    
    # Mock LLM generation to avoid hitting API during validation of enforcement logic
    # We want to see if the ENFORCEMENT logic works, not the LLM.
    engine.llm.generate_text = lambda messages, **kwargs: (
        "Koshari is a complex carbohydrate powerhouse. "
        "The lentils provide lysine while rice provides methionine, making a complete protein. "
        "Lycopene from tomatoes is enhanced by the cooking process."
    )
    
    recipe, meta = engine.synthesize(
        user_query="Is koshari healthy?",
        retrieved_docs=docs,
        intent=intent
    )
    
    # 5. Inspect Results
    print("\n📊 ENFORCEMENT METADATA:")
    print(json.dumps(meta, indent=2))
    
    # 6. Verify Trace Integration
    trace = create_trace("test_sess_001", "trace_001")
    trace.set_pubchem_enforcement(meta)
    
    print("\n🕵️ EXECUTION TRACE PREVIEW:")
    trace_dict = trace.to_dict()
    print(f"PubChem Used: {trace_dict.get('pubchem_used')}")
    print(f"Confidence: {trace_dict.get('confidence_score')}")
    print(f"Proof Hash: {trace_dict.get('pubchem_proof_hash')}")
    print(f"Compounds Resolved: {len(trace_dict.get('pubchem_compounds', []))}")
    
    if meta.get("confidence_score", 0) >= 0.7:
        print("\n✅ PASSED: PubChem enforcement successfully resolved ingredients and building trace.")
    else:
        print("\n❌ FAILED: Confidence score too low.")

if __name__ == "__main__":
    asyncio.run(verify_koshari_query())

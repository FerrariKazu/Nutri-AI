import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.food_synthesis import FoodSynthesisEngine, IntentOutput, RetrievedDocument
from backend.nutrition_enforcer import NutritionEnforcementMode

async def test_e2e_intelligence():
    print("🚀 Starting Tier 1 E2E Verification...")
    
    # Use PARTIAL to ensure synthesis proceeds even if PubChem is flaky
    engine = FoodSynthesisEngine(enforcement_mode=NutritionEnforcementMode.PARTIAL)
    
    # Simulate a Koshari query
    query = "Is koshari healthy?"
    intent = IntentOutput(
        goal="explain",
        ingredients=["lentils", "rice", "pasta", "tomato sauce", "onions"],
        explanation_depth="scientific"
    )
    
    # Mock some retrieved documents
    docs = [
        RetrievedDocument(
            text="Lentils are high in dietary fiber and protein.",
            score=0.95,
            doc_type="nutrition",
            source="Mock USDA"
        ),
        RetrievedDocument(
            text="Lycopene in tomatoes is a powerful antioxidant.",
            score=0.9,
            doc_type="chemistry",
            source="Mock PubChem"
        )
    ]
    
    print(f"Synthesizing for query: {query}")
    
    # Run synthesis (Sync)
    response, meta = engine.synthesize(query, docs, intent)
    
    print("\n" + "="*50)
    print("✅ SYNTHESIS COMPLETE")
    print("="*50)
    print(f"Confidence Score: {meta.get('confidence_score')}")
    print(f"Final Confidence: {meta.get('final_confidence')}")
    print(f"Weakest Link: {meta.get('weakest_link_id')}")
    print(f"Uncertainty Explanation: {meta.get('uncertainty_explanation')}")
    print("\nVERIFICATION SUMMARY:")
    print(meta.get('verification_summary'))
    
    print("\nEXTRACTED CLAIMS:")
    for claim in meta.get("claims", []):
        status = "✅" if claim.get("verified") else "🟡"
        print(f"{status} [{claim.get('source')}] {claim.get('text')} (Status: {claim.get('status_label')})")
    
    if meta.get("verification_summary", {}).get("conflicts_detected"):
        print("\n⚠️ CONFLICTS DETECTED IN RESPONSE")

if __name__ == "__main__":
    asyncio.run(test_e2e_intelligence())

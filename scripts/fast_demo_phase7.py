"""
Nutri Phase 7: Sensory Optimization Demo
Demonstrates the closed-loop optimization of a recipe:
Synthesize -> Predict -> Critique -> Adjust -> Re-evaluate
"""

import logging
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.food_synthesis import NutriPipeline
from backend.sensory.sensory_types import PhysicalProperties, SensoryProfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_demo():
    print("\nNutri Phase 7: Sensory Optimization Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Mocking properties to trigger a chewiness issue in iteration 1
    INGREDIENTS = [{"name": "Seared Duck Breast", "amount_g": 200}]
    pipeline._ingredient_extractor = MagicMock()
    pipeline._ingredient_extractor.extract.return_value = INGREDIENTS

    def mock_map(name, amount, retriever):
        return PhysicalProperties(
            is_muscle_tissue=True,
            fat_fraction=0.15,
            protein_density=0.25,
            moisture_content=0.4
        ), {"used_recipes_store": False, "used_open_nutrition": False}

    pipeline._sensory_mapper = MagicMock()
    pipeline._sensory_mapper.map_ingredient.side_effect = mock_map

    # Test Recipe
    initial_recipe = """
    **High-Heat Pan-Seared Duck Breast**
    1. Score the skin and sear over high heat for 12 minutes until deeply browned.
    2. Slice immediately and serve with reduction.
    """

    print(f"[1/4] Starting with Initial Recipe:\n{initial_recipe}")
    print("-" * 30)

    # We want to see the iterations. 
    # Let's run the optimization. 
    # The real LLM will handle the critique and planning if we let it, 
    # but for a controllable dry-run demo, we might want to see the logs.
    
    # Run optimization (max 2 iterations for brevity)
    result = pipeline.optimize_sensory(initial_recipe, max_iter=2)

    print("\n[2/4] Optimization Log:")
    for step in result.log:
        print(f"\nIteration {step.iteration}:")
        print(f" > Detected Issues:")
        for issue in step.issues:
            print(f"   - {issue.dimension.capitalize()} ({issue.severity}): {issue.cause}. Value: {issue.value}")
        print(f" > Proposed Adjustments:")
        for prop in step.proposals:
            print(f"   - {prop.change}")
            print(f"     Mechanism: {prop.mechanism}")

    print("\n" + "-" * 30)
    print(f"[3/4] Final Optimized Recipe:")
    print(result.final_recipe)

    print("\n[4/4] Final Sensory Profile:")
    print(f"Confidence (Overall): {result.final_profile.confidence['overall']}")
    print(f"Texture: {result.final_profile.texture}")
    print(f"Scientific Explanation: {result.final_profile.scientific_explanation}")
    
    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

"""
Nutri Phase 8: Sensory Pareto Frontier Demo
Showcases generating multiple recipe variants with explicit sensory trade-offs.
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
    print("\nNutri Phase 8: Sensory Pareto Frontier Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Mocking properties for a complex ingredient
    INGREDIENTS = [{"name": "Crispy Skin Salmon", "amount_g": 200}]
    pipeline._ingredient_extractor = MagicMock()
    pipeline._ingredient_extractor.extract.return_value = INGREDIENTS

    def mock_map(name, amount, retriever):
        return PhysicalProperties(
            is_muscle_tissue=True,
            fat_fraction=0.12,
            protein_density=0.18,
            moisture_content=0.65,
            maillard_browning_potential=0.6
        ), {"used_recipes_store": False, "used_open_nutrition": False}

    pipeline._sensory_mapper = MagicMock()
    pipeline._sensory_mapper.map_ingredient.side_effect = mock_map

    # Test Recipe
    initial_recipe = """
    **Standard Pan-Seared Salmon**
    1. Sear skin-side down for 5 minutes.
    2. Flip and cook for 2 minutes.
    """

    print(f"[1/3] Base Recipe:\n{initial_recipe}")
    print("-" * 30)

    # Run Pareto Frontier Generation
    print("Generating Sensory Pareto Frontier variants (this calls LLM for technique adjustments)...")
    result = pipeline.generate_sensory_frontier(initial_recipe)

    print(f"\n[2/3] Generated {len(result.variants)} Non-Dominated Variants:")
    
    for i, variant in enumerate(result.variants):
        print(f"\nVariant {i+1}: {variant.name}")
        print(f"Trade-offs: {variant.trade_offs}")
        print("-" * 20)
        print(f"Recipe Excerpt: {variant.recipe.split('.')[0]}...") # First step
        print(f"Sensory Highlights:")
        print(f" - Crispness: {variant.profile.texture.get('crispness', 0):.2f}")
        print(f" - Tenderness: {variant.profile.texture.get('tenderness', 0):.2f}")
        print(f" - Moistness: {variant.profile.texture.get('moistness', 0):.2f}")
        print(f" - Chewiness: {variant.profile.texture.get('chewiness', 0):.2f}")

    print("\n[3/3] Optimization Objectives Logic:")
    for dim, goal in result.objectives.items():
        print(f" - {dim.capitalize()}: {goal}")

    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

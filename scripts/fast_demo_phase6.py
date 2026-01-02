"""
Nutri Phase 6 Sensory Prediction Demo
Demonstrates policy-governed sensory prediction with mechanistic reasoning.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.food_synthesis import NutriPipeline
from backend.sensory.sensory_types import PhysicalProperties

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_demo():
    print("\nNutri Phase 6: Sensory Prediction Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Mock retriever to return simulated docs with source metadata
    # This proves the policy-governed authority logic
    mock_retriever = MagicMock()
    
    # Mocking ingredient extraction to be precise
    INGREDIENTS = [
        {"name": "Ribeye Steak", "amount_g": 250},
        {"name": "Soy Sauce", "amount_g": 30}
    ]
    pipeline._ingredient_extractor = MagicMock()
    pipeline._ingredient_extractor.extract.return_value = INGREDIENTS

    # Mocking property mapping to simulate high fat and high sodium
    def mock_map(name, amount, retriever):
        if "Steak" in name:
            return PhysicalProperties(
                fat_fraction=0.2, 
                protein_density=0.25, 
                maillard_browning_potential=0.8,
                moisture_content=0.6
            ), {"used_recipes_store": False, "used_open_nutrition": False}
        if "Soy" in name:
            # Simulate using a secondary store for Soy
            return PhysicalProperties(
                sodium_content_mg=1500,
                maillard_browning_potential=0.4,
                free_amino_acids=0.1
            ), {"used_recipes_store": False, "used_open_nutrition": True}
        return PhysicalProperties(), {"used_recipes_store": False, "used_open_nutrition": False}

    pipeline._sensory_mapper = MagicMock()
    pipeline._sensory_mapper.map_ingredient.side_effect = mock_map

    # Test Recipe
    recipe_text = """
    **Pan-Seared Ribeye with Soy Reduction**
    1. Season the 250g ribeye steak with salt.
    2. Sear in a hot pan (dry heat) until a deep brown crust forms (Maillard reaction).
    3. Deglaze with 30g soy sauce and reduce.
    """

    print(f"[1/2] Analyzing Sensory Profile for:\n{recipe_text}")
    print("-" * 30)

    # Predict
    profile = pipeline.predict_sensory(recipe_text, INGREDIENTS)

    print("\n[2/2] Sensory Profile Results:")
    print(f"Confidence: {profile.confidence}")
    
    print("\nTexture Vectors:")
    for k, v in profile.texture.items():
        print(f" - {k.capitalize()}: {v:.2f}")

    print("\nFlavor Vectors:")
    for k, v in profile.flavor.items():
        print(f" - {k.capitalize()}: {v:.2f}")

    print("\nMouthfeel Vectors:")
    for k, v in profile.mouthfeel.items():
        print(f" - {k.capitalize()}: {v:.2f}")

    if profile.warnings:
        print("\nWarnings / Provenance:")
        for w in profile.warnings:
            print(f" 🚩 {w}")

    print("\nScientific Explanation (Mechanistic):")
    print(profile.scientific_explanation)
    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

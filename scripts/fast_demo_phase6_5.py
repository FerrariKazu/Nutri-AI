"""
Nutri Phase 6.5 Sensory Prediction Demo
Demonstrates advanced sensory forecasting: split crispness, muscle fiber models, 
and temporal evolution of perception.
"""

import logging
import sys
import json
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
    print("\nNutri Phase 6.5: Advanced Sensory Prediction Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Mock components to simulate Phase 6.5 logic
    INGREDIENTS = [
        {"name": "Thick-cut Ribeye", "amount_g": 300},
        {"name": "Glaze (Honey & Soy)", "amount_g": 50}
    ]
    pipeline._ingredient_extractor = MagicMock()
    pipeline._ingredient_extractor.extract.return_value = INGREDIENTS

    def mock_map(name, amount, retriever):
        if "Ribeye" in name:
            return PhysicalProperties(
                fat_fraction=0.25, 
                protein_density=0.22, 
                maillard_browning_potential=0.85,
                moisture_content=0.55,
                is_muscle_tissue=True # Trigger fiber model
            ), {"used_recipes_store": False, "used_open_nutrition": False}
        if "Glaze" in name:
            return PhysicalProperties(
                sugar_content_g=15.0, # Trigger sweetness correction
                sodium_content_mg=800,
                maillard_browning_potential=0.6
            ), {"used_recipes_store": False, "used_open_nutrition": True} # Trigger nutrition downgrade
        return PhysicalProperties(), {"used_recipes_store": False, "used_open_nutrition": False}

    pipeline._sensory_mapper = MagicMock()
    pipeline._sensory_mapper.map_ingredient.side_effect = mock_map

    # Test Recipe
    recipe_text = """
    **Reverse-Seared Glazed Ribeye**
    1. Slow-roast 300g ribeye (moist heat) until internal temp reaches 52C.
    2. Sear in a screaming hot pan (dry heat) to develop a deep crust.
    3. Brush with 50g honey-soy glaze during the final 30 seconds to caramelize.
    """

    print(f"[1/2] Analyzing Advanced Sensory Profile for:\n{recipe_text}")
    print("-" * 30)

    # Predict
    profile = pipeline.predict_sensory(recipe_text, INGREDIENTS)

    print("\n[2/2] Sensory Profile results (Phase 6.5):")
    
    print(f"\nConfidence Matrix:")
    for k, v in profile.confidence.items():
        print(f" - {k.replace('_', ' ').capitalize()}: {v}")

    print("\nTexture (Split Mechanism):")
    print(f" - Surface Crust: {profile.texture.get('surface_crust', 0):.2f}")
    print(f" - Structural Crispness: {profile.texture.get('structural_crispness', 0):.2f}")
    print(f" - Weighted Crispness: {profile.texture.get('crispness', 0):.2f}")
    print(f" - Tenderness: {profile.texture.get('tenderness', 0):.2f}")
    print(f" - Chewiness: {profile.texture.get('chewiness', 0):.2f}")

    print("\nFlavor (Corrected Sweetness):")
    for k, v in profile.flavor.items():
        print(f" - {k.capitalize()}: {v:.2f}")

    print("\nSensory Timeline (Temporal Evolution):")
    for stage, attrs in profile.sensory_timeline.items():
        print(f" > {stage.replace('_', ' ').capitalize()}:")
        print(f"   - Texture: {attrs.get('texture')}")
        print(f"   - Flavor: {attrs.get('flavor')}")
        print(f"   - Mouthfeel: {attrs.get('mouthfeel')}")

    if profile.warnings:
        print("\nWarnings / Provenance:")
        for w in profile.warnings:
            print(f" 🚩 {w}")

    print("\nScientific Explanation (Mechanistic):")
    print(profile.scientific_explanation)
    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

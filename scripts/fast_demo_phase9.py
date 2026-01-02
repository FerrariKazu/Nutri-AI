"""
Nutri Phase 9: Preference Projection Demo
Showcases deterministic selection of Pareto variants based on explicit user signals.
"""

import logging
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.food_synthesis import NutriPipeline
from backend.sensory.sensory_types import PhysicalProperties, UserPreferences

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

def run_demo():
    print("\nNutri Phase 9: Preference Projection Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Mocking components for speed
    INGREDIENTS = [{"name": "Roasted Chicken", "amount_g": 300}]
    pipeline._ingredient_extractor = MagicMock()
    pipeline._ingredient_extractor.extract.return_value = INGREDIENTS

    def mock_map(name, amount, retriever):
        return PhysicalProperties(
            is_muscle_tissue=True, fat_fraction=0.15, moisture_content=0.6,
            maillard_browning_potential=0.5
        ), {"used_recipes_store": False, "used_open_nutrition": False}

    pipeline._sensory_mapper = MagicMock()
    pipeline._sensory_mapper.map_ingredient.side_effect = mock_map

    # Test Recipe
    recipe = "**Classic Roasted Chicken**"

    # 1. Generate Frontier (once)
    print("Step 1: Generating Sensory Pareto Frontier...")
    frontier = pipeline.generate_sensory_frontier(recipe)
    print(f"Generated {len(frontier.variants)} non-dominated variants.")
    print("-" * 30)

    # 2. Project Preferences - Sample users
    test_cases = [
        {"style": "comfort", "texture": "soft", "label": "User A (Comfort/Soft)"},
        {"style": "indulgent", "texture": "crisp", "label": "User B (Indulgent/Crisp)"},
        {"style": "performance", "texture": "balanced", "label": "User C (Performance/Balanced)"}
    ]

    print("Step 2: Projecting User Signals & Selecting Variants...")
    for case in test_cases:
        print(f"\n>>> {case['label']}")
        prefs = UserPreferences(eating_style=case['style'], texture_preference=case['texture'])
        
        result = pipeline.select_sensory_variant(frontier, prefs)
        
        print(f"Selected: {result.selected_variant.name}")
        print(f"Reasoning: {result.reasoning[1]} | {result.reasoning[2]}")
        print(f"Scores for this user:")
        for name, score in result.scores.items():
            current_mark = " <-- SELECTED" if name == result.selected_variant.name else ""
            print(f" - {name}: {score:.2f}{current_mark}")

    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

"""
Nutri Phase 11: Counterfactual & Sensitivity Reasoning Demo
Showcases deterministic sensory simulations and audience-calibrated explanations.
"""

import logging
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.food_synthesis import NutriPipeline
from backend.sensory.sensory_types import SensoryProfile

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

def run_demo():
    print("\nNutri Phase 11: Counterfactual & Sensitivity Reasoning Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Sample Case: Seared Duck Breast
    profile = SensoryProfile(
        texture={"surface_crust": 0.8, "crispness": 0.7, "tenderness": 0.5},
        scientific_explanation="High heat sear induces rapid surface dehydration and Maillard reactions.",
        confidence={"overall": "high"}
    )

    print("[1/3] Step 1: Counterfactual Simulation")
    print("Scenario: What if we increase 'rest_time_min' by 0.5 units?")
    print("-" * 30)
    
    # Run simulation
    cf_result = pipeline.simulate_sensory_counterfactual(profile, "rest_time_min", 0.5, mode="culinary")
    report = cf_result["report"]
    explanation = cf_result["explanation"]

    print(f"Parameter: {report.parameter} | Delta: {report.delta}")
    print(f"Predicted Changes: {report.predicted_changes}")
    print(f"Confidence: {report.confidence}")
    
    print(f"\nCULINARY Explanation:")
    print(f" > {explanation.content}")
    print(f" > {explanation.confidence_statement}")

    print("\n" + "-" * 30)
    print("[2/3] Step 2: Multi-Audience explanations for the same change")
    
    modes = ["casual", "scientific", "technical"]
    for mode in modes:
        print(f"\n>>> Mode: {mode.upper()}")
        calibrated_cf = pipeline.simulate_sensory_counterfactual(profile, "rest_time_min", 0.5, mode=mode)["explanation"]
        print(f" {calibrated_cf.content}")

    print("\n" + "-" * 30)
    print("[3/3] Step 3: Sensitivity Ranking")
    print("Question: Which parameters most affect 'crispness'?")
    
    ranking = pipeline.get_sensory_sensitivity("crispness", top_n=3)
    print(f"Ranking for '{ranking.dimension}':")
    for i, r in enumerate(ranking.rankings):
        print(f" {i+1}. {r['parameter']} (Strength: {r['strength']})")

    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

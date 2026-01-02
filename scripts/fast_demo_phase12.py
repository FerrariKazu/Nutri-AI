"""
Nutri Phase 12: Multi-Parameter Counterfactual Reasoning Demo
Showcases joint sensory impacts and feasibility warnings for multi-parameter shifts.
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
    print("\nNutri Phase 12: Multi-Parameter Counterfactual Reasoning Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Sample Case: Pan-Seared Ribeye
    profile = SensoryProfile(
        texture={"surface_crust": 0.6, "tenderness": 0.5, "moistness": 0.6},
        scientific_explanation="Initial medium heat sear.",
        confidence={"overall": "high"}
    )

    print("[1/3] Scenario 1: Multi-Parameter Synergies (Salt + Rest)")
    print("Adjustments: {salt_pct: +0.4, rest_time_min: +0.6}")
    print("-" * 30)
    
    deltas1 = {"salt_pct": 0.4, "rest_time_min": 0.6}
    result1 = pipeline.simulate_multi_parameter_counterfactual(profile, deltas1, mode="culinary")
    report1 = result1["report"]
    explanation1 = result1["explanation"]

    print(f"Predicted Changes: {report1.predicted_changes}")
    print(f"Confidence: {report1.confidence}")
    print(f"\nCULINARY Feedback:")
    print(f" > {explanation1.content}")

    print("\n" + "-" * 30)
    print("[2/3] Scenario 2: Interaction dry-out (Heat + Duration)")
    print("Adjustments: {heat_intensity: +0.7, sear_duration_min: +0.5}")
    
    deltas2 = {"heat_intensity": 0.7, "sear_duration_min": 0.5}
    result2 = pipeline.simulate_multi_parameter_counterfactual(profile, deltas2, mode="scientific")
    report2 = result2["report"]
    
    # Note: Interaction logic in engine should subtract from moistness/tenderness
    print(f"Predicted Changes: {report2.predicted_changes}")
    print(f"Highlights: {explanation2.content if 'explanation2' in locals() else result2['explanation'].content}")

    print("\n" + "-" * 30)
    print("[3/3] Scenario 3: Physical Conflict (Heat + Moisture)")
    print("Adjustments: {heat_intensity: +0.8, surface_moisture: +0.8}")
    
    deltas3 = {"heat_intensity": 0.8, "surface_moisture": 0.8}
    result3 = pipeline.simulate_multi_parameter_counterfactual(profile, deltas3, mode="technical")
    report3 = result3["report"]
    
    print(f"Feasibility Warnings: {report3.feasibility_warnings}")
    print(f"Technical Analysis: {result3['explanation'].content}")

    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

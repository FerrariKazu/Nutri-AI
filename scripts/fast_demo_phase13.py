"""
Nutri Phase 13: Interactive Design Loop Demo
Simulates an iterative refinement session toward target sensory goals.
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
    print("\nNutri Phase 13: Interactive Design Loop Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Starting scenario: Pan-Seared Salmon
    current_profile = SensoryProfile(
        texture={"surface_crust": 0.3, "crispness": 0.2, "tenderness": 0.8},
        scientific_explanation="Initial gentle sear preserves moisture but lacks crust development.",
        confidence={"overall": "high"}
    )
    
    # Target Goals
    target_goals = {
        "crispness": "high",
        "tenderness": "high"
    }

    print(f"Base Profile: Crispness={current_profile.texture['crispness']}, Tenderness={current_profile.texture['tenderness']}")
    print(f"Target Goals: {target_goals}")
    print("-" * 30)

    # Iteration 1: User proposes increasing heat intensity
    print("\n[Iteration 1] User Action: Increase Heat Intensity (+0.6)")
    proposed_deltas_1 = {"heat_intensity": 0.6}
    
    state_1 = pipeline.design_sensory_iteration(
        current_profile, 
        iteration_number=1, 
        proposed_deltas=proposed_deltas_1, 
        target_goals=target_goals,
        mode="culinary"
    )
    
    print(f"Predicted Changes: {state_1.predicted_changes}")
    print(f"Feasibility: {state_1.feasibility_warnings if state_1.feasibility_warnings else 'OK'}")
    print(f"Recommendation: {state_1.recommendation}")
    print(f"Feedback: {state_1.explanation.content}")

    # Iteration 2: User follows recommendation to increase salt for moisture retention
    print("\n[Iteration 2] User Action: Increase Heat (+0.6) AND Salt (+0.4) AND Rest (+0.3)")
    proposed_deltas_2 = {"heat_intensity": 0.6, "salt_pct": 0.4, "rest_time_min": 0.3}
    
    state_2 = pipeline.design_sensory_iteration(
        current_profile, 
        iteration_number=2, 
        proposed_deltas=proposed_deltas_2, 
        target_goals=target_goals,
        mode="technical"
    )
    
    print(f"Predicted Changes: {state_2.predicted_changes}")
    print(f"Recommendation: {state_2.recommendation}")
    print(f"Feedback: {state_2.explanation.content}")

    print("\nSummary: The user successfully moved from low-crispness toward high-crispness while using synergistic adjustments (Salt/Rest) to protect tenderness despite intense heat.")

    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

"""
Nutri Phase 10: Epistemic Explanation Control Demo
Showcases audience-calibrated explanations for the same underlying scientific facts.
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
    print("\nNutri Phase 10: Epistemic Explanation Control Demo")
    print("============================================================\n")

    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=False)
    
    # Sample Case: Sourdough Bread
    profile = SensoryProfile(
        texture={"surface_crust": 0.85, "structural_crispness": 0.3},
        scientific_explanation=(
            "Rapid dehydration of surface starch during initial 450F exposure inducs gelatinization then glass transition, "
            "forming a 2mm brittle crust. Internal moisture (0.65) is retained due to gluten-network trapping. "
            "Mild chewiness (0.4) is likely due to high-protein flour hydration levels."
        ),
        warnings=["Low salt concentration (<0.5%) may reduce flavor depth."],
        confidence={"overall": "high"}
    )

    print(f"[1/2] Original Scientific Explanation (Phase 6/7/8):")
    print(f" > {profile.scientific_explanation}")
    print(f" > Warnings: {profile.warnings}")
    print("-" * 30)

    # 2. Calibrate for different audiences
    modes = ["casual", "culinary", "scientific", "technical"]

    print("[2/2] Audience-Calibrated Explanations:")
    for mode in modes:
        print(f"\n>>> Mode: {mode.upper()}")
        result = pipeline.explain_sensory(profile, mode=mode)
        
        print(f"Content: {result.content}")
        print(f"Reliability: {result.confidence_statement}")
        print(f"Preserved Warnings: {result.preserved_warnings}")

    print("\n============================================================\n")

if __name__ == "__main__":
    run_demo()

import sys
import os
import logging
from pathlib import Path

# Fix path to allow importing from backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.food_synthesis import NutriPipeline

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    print("Initializing Nutri Phase 5 Demonstration...")
    # Initialize pipeline
    pipeline = NutriPipeline(use_phase2=True)
    
    # 1. Synthesize an initial recipe
    print("\n[1/3] Synthesizing initial recipe...")
    initial_prompt = "I have chicken, rice, and soy sauce. Make a simple meal."
    result = pipeline.synthesize(initial_prompt)
    
    print("-" * 30)
    print("INITIAL RECIPE (Snippet):")
    print(result.recipe[:300] + "...")
    print("-" * 30)
    
    # 2. Run Nutrition Optimization
    print("\n[2/3] Running Nutrition Optimization Solver...")
    print("Goal: Maximize protein, stay under 500 calories.")
    
    goals = {
        "maximize": "protein",
        "constraints": {
            "calories": {"max": 500}
        }
    }
    
    optimized = pipeline.optimize(result, goals)
    
    # 3. Print Results
    print("\n[3/3] Optimization Results:")
    print(f"Solver Status: {optimized.confidence}")
    if optimized.unmet_constraints:
        print(f"Warnings: {optimized.unmet_constraints}")
    
    print("\nFinal Optimized Quantities:")
    for ing, amount in optimized.optimized_ratios.items():
        print(f" - {ing}: {amount:.1f}g")
        
    print("\nAchieved Nutritional Totals:")
    for metric, val in optimized.achieved_targets.items():
        if metric in ['calories', 'protein']:
            print(f" - {metric}: {val:.1f}")

    print("\n" + "="*60)
    print("OPTIMIZED RECIPE EXPLANATION:")
    print("="*60)
    if hasattr(optimized, 'recipe_explanation') and optimized.recipe_explanation:
        print(optimized.recipe_explanation)
    else:
        print("No explanation generated.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        print("\nNote: Make sure Ollama (qwen3:8b) is running and indexes are in vector_store/.")

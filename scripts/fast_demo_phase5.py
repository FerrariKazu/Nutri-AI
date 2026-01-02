import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Fix path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.food_synthesis import NutriPipeline, RetrievedDocument
from backend.nutrition.vectorizer import NutritionVector

def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    print("Nutri Phase 5: Fast Optimization Demo (Mocked Retriever)")
    print("="*60)

    # 1. Initialize Pipeline with a Mocked Retriever
    # This prevents loading 10GB of FAISS indexes
    pipeline = NutriPipeline(use_phase2=False)
    
    mock_retriever = MagicMock()
    def mock_retrieve(query, top_k=3):
        # Return canned nutrition data based on query
        if "Chicken" in query or "chicken" in query:
            return [RetrievedDocument(
                text="Chicken Breast: 165 kcal, 31g protein, 3.6g fat per 100g",
                score=0.9, doc_type="nutrition", source="mock"
            )]
        if "Rice" in query or "rice" in query:
            return [RetrievedDocument(
                text="White Rice: 130 kcal, 2.7g protein, 28g carbs per 100g",
                score=0.9, doc_type="nutrition", source="mock"
            )]
        if "Soy" in query or "soy" in query:
            return [RetrievedDocument(
                text="Soy Sauce: 53 kcal, 8g protein, 4.9g carbs per 100g",
                score=0.9, doc_type="nutrition", source="mock"
            )]
        return []

    mock_retriever.retrieve.side_effect = mock_retrieve
    pipeline.retriever = mock_retriever

    # 2. Define a recipe text to optimize
    recipe_text = """
    **Recipe: Chicken and Rice**
    - 150g Chicken breast
    - 200g White rice
    - 2 tbsp Soy sauce (30g)
    """
    
    # 3. Define Goals
    goals = {
        "maximize": "protein",
        "constraints": {
            "calories": {"max": 400} # Tight constraint to force solver to work
        }
    }

    print(f"\n[1/2] Optimizing Recipe:\n{recipe_text.strip()}")
    print("-" * 30)

    try:
        # Run Optimization
        # This will test:
        # - IngredientExtractor (using real Ollama)
        # - NutritionVectorizer (using real Ollama extraction + mock context)
        # - NutritionConstraintSolver (using real Scipy)
        # - Re-explanation (using real Ollama)
        optimized = pipeline.optimize(recipe_text, goals)

        print("\n[2/2] Optimization Finished:")
        print(f"Confidence: {optimized.confidence}")
        if optimized.unmet_constraints:
            print(f"Warnings: {optimized.unmet_constraints}")

        print("\nAdjusted Ingredients (g):")
        for ing, amount in optimized.optimized_ratios.items():
            print(f" - {ing}: {amount:.1f}g")

        print("\nNutritional Targets Achieved:")
        for k, v in optimized.achieved_targets.items():
            if k in ['calories', 'protein']:
                print(f" - {k}: {v:.1f}")

        print("\n" + "="*60)
        print("OPTIMIZED RECIPE & SCIENTIFIC EXPLANATION:")
        print("="*60)
        print(optimized.recipe_explanation)

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()

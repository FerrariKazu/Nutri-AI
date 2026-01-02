"""
Tests for Phase 5: Nutrition Optimization.

Covers:
- Nutrition vectorizer
- Ingredient extraction
- Constraint solver logic
- Pipeline integration
"""

import pytest
import numpy as np
import logging
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.nutrition.vectorizer import NutritionVectorizer, NutritionVector, IngredientExtractor
from backend.nutrition.solver import NutritionConstraintSolver, OptimizationResult

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def mock_llm():
    """Mock LLM."""
    with patch('backend.nutrition.vectorizer.LLMQwen3') as MockLLM:
        mock_instance = MagicMock()
        MockLLM.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_retriever():
    """Mock retriever."""
    mock = MagicMock()
    from backend.food_synthesis import RetrievedDocument
    mock.retrieve.return_value = [RetrievedDocument(text="Nutrition info...", score=0.9, doc_type="usda", source="test")]
    return mock


class TestNutritionVectorizer:
    """Tests for NutritionVectorizer."""

    def test_vectorize_ingredient(self, mock_llm, mock_retriever):
        """Vectorizes ingredient correctly from LLM output."""
        mock_llm.generate_text.return_value = '''{
            "calories": 165, "protein": 31, "fat": 3.6, "carbs": 0,
            "fiber": 0, "sugar": 0, "sodium": 74
        }'''
        
        vectorizer = NutritionVectorizer()
        vector = vectorizer.vectorize("Chicken breast", mock_retriever)
        
        assert vector.calories == 165
        assert vector.protein == 31


class TestSolverCommonCases:
    """Tests for NutritionConstraintSolver logic."""

    def test_maximize_protein(self):
        """Solver should favor protein-dense ingredients."""
        solver = NutritionConstraintSolver()
        
        # Scenario: Chicken (high protein) vs Rice (low protein)
        ingredients = [
            {
                "name": "Chicken", "amount_g": 100.0,
                "vector": NutritionVector(calories=165, protein=31, fat=3.6, carbs=0)
            },
            {
                "name": "Rice", "amount_g": 100.0,
                "vector": NutritionVector(calories=130, protein=2.7, fat=0.3, carbs=28)
            }
        ]
        
        goals = {"maximize": "protein", "constraints": {"calories": {"max": 400}}}
        
        result = solver.solve(ingredients, goals)
        
        assert result.confidence != "low"
        new_chicken = result.optimized_ratios["Chicken"]
        new_rice = result.optimized_ratios["Rice"]
        
        # Chicken should increase relative to start (or at least not decrease significantly while rice decreases)
        # Bounds are 50%-150%. 
        # Max calories 400. Start calories = 165+130 = 295.
        # It can increase. 
        # To MAXIMIZE protein, it should push Chicken to bound (150g) and Rice to bound (150g) -> total protein higher?
        # But maybe calorie constraint limits it.
        # 150g Chicken = 247 kcal. 150g Rice = 195 kcal. Total 442 > 400.
        # So it must tradeoff. Chicken provides more protein per calorie.
        # Solver should prioritize Chicken.
        
        assert new_chicken > 100.0
        # Rice might be reduced or kept lower than max bound
        assert new_chicken > new_rice # Chicken ratio should be higher if possible or at least increased more
        
    def test_calorie_limit(self):
        """Solver should reduce amounts to meet calorie limit."""
        solver = NutritionConstraintSolver()
        
        ingredients = [
            {
                "name": "Butter", "amount_g": 100.0,
                "vector": NutritionVector(calories=717, protein=0.8)
            }
        ]
        
        # Current: 717 kcal. Limit: 600.
        goals = {"constraints": {"calories": {"max": 600}}}
        
        result = solver.solve(ingredients, goals)
        
        new_butter = result.optimized_ratios["Butter"]
        calories = new_butter * 7.17
        
        assert calories <= 605 # tolerance
        assert new_butter < 100.0
        assert result.confidence == "high"


class TestPipelineIntegration:
    """Integration tests for pipeline."""

    def test_optimize_flow(self):
        """Test full optimize flow with mocks."""
        from backend.food_synthesis import NutriPipeline
        
        with patch('backend.food_synthesis.IngredientExtractor') as MockIE, \
             patch('backend.food_synthesis.NutritionVectorizer') as MockNV, \
             patch('backend.food_synthesis.NutritionConstraintSolver') as MockSol:
             
            # Setup mocks
            mock_ie = MagicMock()
            mock_ie.extract.return_value = [{"name": "Chicken", "amount_g": 100.0}]
            MockIE.return_value = mock_ie
            
            mock_nv = MagicMock()
            mock_nv.vectorize.return_value = NutritionVector(calories=100, protein=20)
            MockNV.return_value = mock_nv
            
            mock_sol = MagicMock()
            mock_sol.solve.return_value = OptimizationResult(
                optimized_ratios={"Chicken": 120.0},
                achieved_targets={"protein": 24},
                unmet_constraints=[],
                confidence="high",
                original_totals={"protein": 20},
                new_totals={"protein": 24}
            )
            MockSol.return_value = mock_sol
            
            pipeline = NutriPipeline(use_phase2=False)
            pipeline.llm = MagicMock()
            pipeline.llm.generate_text.return_value = "Re-explained recipe text"
            
            result = pipeline.optimize("Recipe text", {})
            
            assert result.confidence == "high"
            assert result.recipe_explanation == "Re-explained recipe text"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Tests for Nutri Phase 7: Sensory Optimization Engine
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from backend.food_synthesis import NutriPipeline
from backend.sensory.sensory_types import SensoryProfile, PhysicalProperties, SensoryOptimizationResult

@pytest.fixture
def mock_pipeline():
    with patch('backend.food_synthesis.FoodSynthesisRetriever'):
        pipeline = NutriPipeline(use_phase2=False)
        # Mock components
        pipeline._ingredient_extractor = MagicMock()
        pipeline._sensory_mapper = MagicMock()
        pipeline._sensory_predictor = MagicMock()
        return pipeline

@patch('backend.llm_qwen3.LLMQwen3.generate_text')
def test_sensory_optimization_loop(mock_gen, mock_pipeline):
    """Test the closed-loop optimization flow."""
    # 1. Mock Extraction
    mock_pipeline._ingredient_extractor.extract.return_value = [{"name": "Steak", "amount_g": 200}]
    mock_pipeline._sensory_mapper.map_ingredient.return_value = (PhysicalProperties(), {"used_recipes_store": False, "used_open_nutrition": False})
    
    # 2. Mock predictor results (Iter 1: high chewiness, Final: normalized)
    # 3. Mock critic (Iter 1: finds issue)
    # 4. Mock planner (Iter 1: proposes change)
    # 5. Mock refinement (application of change)
    
    def side_effect(messages, **kwargs):
        content = messages[-1]["content"]
        if "Analyze the following sensory profile" in content:
            # Critic
            return json.dumps({"issues": [{"dimension": "chewiness", "severity": "high", "cause": "fiber shortening", "value": 0.9}]})
        elif "propose minimal, scientifically grounded adjustments" in content:
            # Planner
            return json.dumps({"proposals": [{"change": "rest for 10 min", "mechanism": "rehydration", "expected_effect": {"chewiness": -0.3}}]})
        elif "Adjust the following recipe" in content:
            # Refiner
            return "Adjusted Steak Recipe: Rest for 10 minutes."
        elif "Predict the advanced sensory profile" in content:
            # Predictor (though we mock the predictor instance directly usually, let's let it run or mock it)
            return json.dumps({
                "texture": {"surface_crust": 0.5, "structural_crispness": 0.1, "chewiness": 0.6},
                "flavor": {}, "mouthfeel": {}, "sensory_timeline": {}, "confidence_scores": {}, "explanation": "test"
            })
        return "{}"

    mock_gen.side_effect = side_effect
    
    # Properly mock the predictor's return value to be a real SensoryProfile with data
    mock_profile = SensoryProfile(
        texture={"surface_crust": 0.5, "structural_crispness": 0.1, "chewiness": 0.9},
        flavor={"umami": 0.5},
        mouthfeel={"richness": 0.5}
    )
    mock_pipeline._sensory_predictor.predict.return_value = mock_profile
    mock_pipeline.engine.llm.generate_text = mock_gen
    
    result = mock_pipeline.optimize_sensory("Initial Steak Recipe", max_iter=1)
    
    assert len(result.log) >= 1
    assert "chewiness" in result.log[0].issues[0].dimension
    assert "rest" in result.final_recipe.lower()
    assert result.success is True

def test_sensory_critic_no_subjectivity(mock_pipeline):
    """Verify that the critic uses mechanistic language."""
    from backend.sensory.optimizer import SensoryCritic
    critic = SensoryCritic(mock_pipeline.engine.llm)
    
    mock_pipeline.engine.llm.generate_text = MagicMock(return_value=json.dumps({
        "issues": [{"dimension": "umami", "severity": "low", "cause": "insufficient protein hydrolysis", "value": 0.1}]
    }))
    
    issues = critic.critique(SensoryProfile())
    assert "hydrolysis" in issues[0].cause
    assert "low" in issues[0].severity

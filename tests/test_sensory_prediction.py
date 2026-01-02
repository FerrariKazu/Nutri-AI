"""
Tests for Nutri Phase 6: Sensory Prediction Engine (Updated for Phase 6.5)
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from backend.food_synthesis import NutriPipeline
from backend.sensory.sensory_types import SensoryProfile, PhysicalProperties

@pytest.fixture
def mock_pipeline():
    with patch('backend.food_synthesis.FoodSynthesisRetriever'):
        pipeline = NutriPipeline(use_phase2=False)
        # Mocking components to prevent real LLM calls during core logic tests
        pipeline._sensory_mapper = MagicMock()
        pipeline._sensory_predictor = MagicMock()
        pipeline._ingredient_extractor = MagicMock()
        return pipeline

def test_sensory_confidence_downgrade_recipes(mock_pipeline):
    """Test confidence downgrade when recipes store is used."""
    mock_pipeline._ingredient_extractor.extract.return_value = [{"name": "test", "amount_g": 100}]
    
    # Mapper returns that recipes store was used
    mock_pipeline._sensory_mapper.map_ingredient.return_value = (
        PhysicalProperties(),
        {"used_recipes_store": True, "used_open_nutrition": False}
    )
    
    # Predictor logic handles confidence adjustment (tested here via pipeline integration)
    from backend.sensory.predictor import SensoryPredictor
    real_predictor = SensoryPredictor()
    # Mock LLM response with Phase 6.5 output structure
    real_predictor.llm.generate_text = MagicMock(return_value='{"texture": {"surface_crust": 0.1, "structural_crispness": 0.1}, "confidence_scores": {"nutrition": "high", "sensory_physics": "high", "chemical_flavor": "high"}, "explanation": "test"}')
    mock_pipeline._sensory_predictor = real_predictor
    
    profile = mock_pipeline.predict_sensory("Roast chicken")
    
    # In 6.5, recipes store downgrades sensory_physics to medium
    assert profile.confidence["sensory_physics"] == "medium"
    assert profile.confidence["overall"] == "medium"
    assert any("recipes" in w for w in profile.warnings)

def test_sensory_confidence_downgrade_open_nutrition(mock_pipeline):
    """Test confidence downgrade when open_nutrition used."""
    mock_pipeline._ingredient_extractor.extract.return_value = [{"name": "test", "amount_g": 100}]
    
    mock_pipeline._sensory_mapper.map_ingredient.return_value = (
        PhysicalProperties(),
        {"used_recipes_store": False, "used_open_nutrition": True}
    )
    
    from backend.sensory.predictor import SensoryPredictor
    real_predictor = SensoryPredictor()
    real_predictor.llm.generate_text = MagicMock(return_value='{"flavor": {"umami": 0.5}, "confidence_scores": {"nutrition": "high", "sensory_physics": "high", "chemical_flavor": "high"}, "explanation": "test"}')
    mock_pipeline._sensory_predictor = real_predictor
    
    profile = mock_pipeline.predict_sensory("Soy soup")
    
    # In 6.5, open_nutrition downgrades nutrition to low
    assert profile.confidence["nutrition"] == "low"
    assert profile.confidence["overall"] == "low"
    assert any("open_nutrition" in w for w in profile.warnings)

@patch('backend.llm_qwen3.LLMQwen3.generate_text')
def test_sensory_split_crispness(mock_gen, mock_pipeline):
    """Test weighted crispness split (Phase 6.5)."""
    from backend.sensory.predictor import SensoryPredictor
    predictor = SensoryPredictor()
    
    # 0.7 * 0.8 + 0.3 * 0.2 = 0.56 + 0.06 = 0.62
    mock_gen.return_value = '{"texture": {"surface_crust": 0.8, "structural_crispness": 0.2}, "explanation": "test"}'
    
    props = [PhysicalProperties()]
    profile = predictor.predict("Fried food", props, {"used_recipes_store": False, "used_open_nutrition": False})
    
    assert abs(profile.texture["crispness"] - 0.62) < 0.01

@patch('backend.llm_qwen3.LLMQwen3.generate_text')
def test_sensory_timeline_evolution(mock_gen, mock_pipeline):
    """Test that sensory timeline is populated (Phase 6.5)."""
    from backend.sensory.predictor import SensoryPredictor
    predictor = SensoryPredictor()
    
    mock_gen.return_value = json.dumps({
        "texture": {}, "flavor": {}, "mouthfeel": {},
        "sensory_timeline": {
            "initial_bite": {"texture": "Surface crunch"},
            "mid_palate": {"texture": "Tender protein"},
            "finish": {"texture": "Lingering savory"}
        },
        "explanation": "test"
    })
    
    profile = predictor.predict("Complex dish", [PhysicalProperties()], {"used_recipes_store": False, "used_open_nutrition": False})
    
    assert "initial_bite" in profile.sensory_timeline
    assert profile.sensory_timeline["initial_bite"]["texture"] == "Surface crunch"

def test_sensory_insufficient_data(mock_pipeline):
    """Test warning when no ingredients are extracted."""
    mock_pipeline._ingredient_extractor.extract.return_value = []
    
    profile = mock_pipeline.predict_sensory("Some vague recipe")
    
    assert "Insufficient" in profile.warnings[0]

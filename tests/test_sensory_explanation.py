"""
Tests for Nutri Phase 10: Epistemic Explanation Control
"""

import pytest
from unittest.mock import MagicMock
from backend.sensory.sensory_types import SensoryProfile
from backend.sensory.explainer import ExplanationLayer

@pytest.fixture
def explainer():
    engine = MagicMock()
    # Mock LLM to return a predictable JSON
    engine.llm.generate_text.return_value = '{"content": "Rewritten", "confidence_statement": "Reliable"}'
    return ExplanationLayer(engine)

def test_explanation_scientific_passthrough(explainer):
    """Test that scientific mode passes through the original text."""
    profile = SensoryProfile(
        scientific_explanation="Maillard reaction occurs.",
        warnings=["Low salt"],
        confidence={"overall": "high"}
    )
    result = explainer.explain(profile, mode="scientific")
    
    assert result.mode == "scientific"
    assert "Maillard reaction" in result.content
    assert "Low salt" in result.preserved_warnings

def test_explanation_calibration_calls_llm(explainer):
    """Test that other modes call the LLM and return calibrated results."""
    profile = SensoryProfile(
        scientific_explanation="Hydrophobic interactions.",
        warnings=["None"],
        confidence={"overall": "medium"}
    )
    result = explainer.explain(profile, mode="casual")
    
    assert result.mode == "casual"
    assert result.content == "Rewritten" # From mock
    assert result.confidence_statement == "Reliable"
    explainer.engine.llm.generate_text.assert_called_once()

def test_explanation_uncertainty_preservation(explainer):
    """Reflect that warnings and uncertainties are passed to the prompt."""
    profile = SensoryProfile(
        scientific_explanation="Texture is likely soft.",
        warnings=["High humidity risk"],
        confidence={"overall": "low"}
    )
    explainer.explain(profile, mode="culinary")
    
    # Check that warnings were in the prompt (via call arguments)
    args, kwargs = explainer.engine.llm.generate_text.call_args
    prompt = args[0][1]["content"] # user message content
    assert "High humidity risk" in prompt
    assert "likely soft" in prompt

"""
Tests for Nutri Phase 9: Preference Projection Layer
"""

import pytest
from backend.sensory.sensory_types import (
    SensoryProfile, 
    SensoryVariant, 
    ParetoFrontierResult, 
    UserPreferences
)
from backend.sensory.selector import VariantSelector

@pytest.fixture
def selector():
    return VariantSelector()

def test_preference_projection_comfort(selector):
    """Test comfort eating style projection."""
    prefs = UserPreferences(eating_style="comfort")
    weights = selector.projector.project(prefs)
    
    # Comfort should boost tenderness and moistness
    assert weights["tenderness"] > 1.0
    assert weights["moistness"] > 1.0
    assert weights["chewiness"] < -1.0

def test_variant_selection_logic(selector):
    """Test selection of variants based on weights."""
    # We have two variants: one tender-heavy, one crisp-heavy
    v1 = SensoryVariant(
        name="TenderV", recipe="", 
        profile=SensoryProfile(texture={"tenderness": 0.9, "crispness": 0.2, "moistness": 0.8}),
        trade_offs=""
    )
    v2 = SensoryVariant(
        name="CrispV", recipe="", 
        profile=SensoryProfile(texture={"tenderness": 0.2, "crispness": 0.9, "moistness": 0.3}),
        trade_offs=""
    )
    frontier = ParetoFrontierResult(variants=[v1, v2], objectives={})
    
    # 1. Soft texture preference should select v1
    prefs_soft = UserPreferences(texture_preference="soft")
    result_soft = selector.select(frontier, prefs_soft)
    assert result_soft.selected_variant.name == "TenderV"
    
    # 2. Crisp texture preference should select v2
    prefs_crisp = UserPreferences(texture_preference="crisp")
    result_crisp = selector.select(frontier, prefs_crisp)
    assert result_crisp.selected_variant.name == "CrispV"

def test_selection_reasoning(selector):
    """Test that reasoning accurately reflects project settings."""
    v1 = SensoryVariant(name="V", recipe="", profile=SensoryProfile(texture={"tenderness": 0.5}), trade_offs="")
    frontier = ParetoFrontierResult(variants=[v1], objectives={})
    prefs = UserPreferences(eating_style="performance")
    
    result = selector.select(frontier, prefs)
    reasoning_str = " ".join(result.reasoning)
    assert "performance" in reasoning_str.lower()
    assert "Prioritized" in reasoning_str

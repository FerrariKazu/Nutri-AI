"""
Tests for Nutri Phase 11: Counterfactual & Sensitivity Reasoning
"""

import pytest
from backend.sensory.sensory_types import SensoryProfile
from backend.sensory.counterfactual_engine import CounterfactualEngine
from backend.sensory.sensitivity_registry import SENSITIVITY_REGISTRY

@pytest.fixture
def engine():
    return CounterfactualEngine()

def test_counterfactual_simulation(engine):
    """Test that delta calculation is deterministic and correct."""
    profile = SensoryProfile()
    # Test salt_pct influence on saltiness
    report = engine.simulate(profile, "salt_pct", 0.5)
    
    assert report.parameter == "salt_pct"
    assert report.predicted_changes["saltiness"] == 0.5 # 1.0 sensitivity * 0.5 delta
    assert report.predicted_changes["umami"] == 0.3 # 0.6 sensitivity * 0.5 delta
    assert report.confidence == "high"

def test_sensitivity_ranking(engine):
    """Test that ranking returns top affecting parameters."""
    ranking = engine.get_sensitivity_ranking("surface_crust", top_n=2)
    
    assert ranking.dimension == "surface_crust"
    assert len(ranking.rankings) == 2
    # Heat intensity (0.9) should be first, surface_moisture (0.8) second
    assert ranking.rankings[0]["parameter"] == "heat_intensity"
    assert ranking.rankings[1]["parameter"] == "surface_moisture"

def test_unregistered_parameter(engine):
    """Test graceful handling of unknown parameters."""
    profile = SensoryProfile()
    report = engine.simulate(profile, "unknown_param", 0.1)
    
    assert report.confidence == "low"
    assert "not registered" in report.explanation

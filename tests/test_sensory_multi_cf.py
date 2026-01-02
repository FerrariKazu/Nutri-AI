"""
Tests for Nutri Phase 12: Multi-Parameter Counterfactual reasoning.
"""

import pytest
from backend.sensory.sensory_types import SensoryProfile
from backend.sensory.counterfactual_multi_engine import MultiCounterfactualEngine

@pytest.fixture
def engine():
    return MultiCounterfactualEngine()

def test_multi_parameter_aggregation(engine):
    """Test linear aggregation of multiple parameters."""
    profile = SensoryProfile()
    deltas = {"salt_pct": 0.5, "sugar_pct": 0.5}
    report = engine.simulate_multi(profile, deltas)
    
    # saltinness: 1.0 * 0.5 = 0.5
    # sweetness: (-0.2 * 0.5) + (1.0 * 0.5) = 0.4
    assert report.predicted_changes["saltiness"] == 0.5
    assert report.predicted_changes["sweetness"] == 0.4
    assert len(report.feasibility_warnings) == 0

def test_interaction_effects(engine):
    """Test non-linear interaction between heat and duration."""
    profile = SensoryProfile()
    # heat (+1.0) and duration (+1.0) should compound moistness loss
    deltas = {"heat_intensity": 1.0, "sear_duration_min": 1.0}
    report = engine.simulate_multi(profile, deltas)
    
    # Linear moistness changes from heat (-0.3?) / duration (-0.2?)
    # Wait, SENSITIVITY_REGISTRY check:
    # heat_intensity: tenderness -0.5, crispness 0.8
    # sear_duration_min: tenderness -0.3, crispness 0.6
    # Interaction logic: -0.3 interaction_delta
    assert report.predicted_changes["moistness"] < 0
    # verify interaction specifically (starts at 0 in this base)
    assert report.predicted_changes["moistness"] == -0.3 

def test_feasibility_check(engine):
    """Test rejection/warning for physically impossible states."""
    profile = SensoryProfile()
    # High heat + High surface moisture
    deltas = {"heat_intensity": 0.8, "surface_moisture": 0.8}
    report = engine.simulate_multi(profile, deltas)
    
    assert any("PHYSICAL CONFLICT" in w for w in report.feasibility_warnings)
    assert report.confidence == "low"

"""
Tests for Nutri Phase 8: Sensory Pareto Frontier
"""

import pytest
from backend.sensory.sensory_types import SensoryProfile, SensoryVariant
from backend.sensory.frontier import SensoryParetoOptimizer

@pytest.fixture
def optimizer():
    # We mock the engine and predictor since we are testing the frontier logic
    return SensoryParetoOptimizer(engine=None, predictor=None)

def test_pareto_dominance(optimizer):
    """Test that variant A dominates B correctly."""
    objectives = {"tenderness": "maximize", "crispness": "maximize", "chewiness": "minimize"}
    
    # v1 is better in everything than v2
    v1 = SensoryVariant(
        name="Better", recipe="", 
        profile=SensoryProfile(texture={"tenderness": 0.8, "crispness": 0.8, "chewiness": 0.2}),
        trade_offs=""
    )
    v2 = SensoryVariant(
        name="Worse", recipe="", 
        profile=SensoryProfile(texture={"tenderness": 0.5, "crispness": 0.5, "chewiness": 0.5}),
        trade_offs=""
    )
    
    assert optimizer._dominates(v1, v2, objectives) is True
    assert optimizer._dominates(v2, v1, objectives) is False

def test_pareto_non_dominance_tradeoff(optimizer):
    """Test that trade-offs result in non-dominance (both stay on frontier)."""
    objectives = {"tenderness": "maximize", "crispness": "maximize"}
    
    # v1 is more tender, v2 is more crisp
    v1 = SensoryVariant(
        name="Tender-Heavy", recipe="", 
        profile=SensoryProfile(texture={"tenderness": 0.9, "crispness": 0.3}),
        trade_offs=""
    )
    v2 = SensoryVariant(
        name="Crisp-Heavy", recipe="", 
        profile=SensoryProfile(texture={"tenderness": 0.3, "crispness": 0.9}),
        trade_offs=""
    )
    
    assert optimizer._dominates(v1, v2, objectives) is False
    assert optimizer._dominates(v2, v1, objectives) is False

def test_filter_dominated(optimizer):
    """Test the filtering logic for a list of variants."""
    objectives = {"tenderness": "maximize"}
    
    v1 = SensoryVariant(name="A", recipe="", profile=SensoryProfile(texture={"tenderness": 0.9}), trade_offs="")
    v2 = SensoryVariant(name="B", recipe="", profile=SensoryProfile(texture={"tenderness": 0.5}), trade_offs="")
    v3 = SensoryVariant(name="C", recipe="", profile=SensoryProfile(texture={"tenderness": 0.9}), trade_offs="")
    
    variants = [v1, v2, v3]
    result = optimizer._filter_dominated(variants, objectives)
    
    # B is dominated by A and C. A and C don't dominate each other (equal).
    assert len(result) == 2
    assert any(v.name == "A" for v in result)
    assert any(v.name == "C" for v in result)
    assert not any(v.name == "B" for v in result)

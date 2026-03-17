import pytest
from backend.nutri_engine import NutriEngine
from backend.food_synthesis import FoodSynthesisEngine

def test_nutri_engine_interface():
    """
    Assert that NutriEngine has the 'generate' method.
    This is critical because the orchestrator calls self.engine.generate.
    """
    assert hasattr(NutriEngine, "generate"), "NutriEngine must implement 'generate' method."

def test_food_synthesis_engine_interface_diagnostic():
    """
    Diagnostic: Confirm that FoodSynthesisEngine does NOT have 'generate'.
    The crash was caused by calling generate on this object.
    """
    # This test documents the reason for the refactor
    assert not hasattr(FoodSynthesisEngine, "generate"), "FoodSynthesisEngine should not have 'generate' (use NutriEngine instead)."

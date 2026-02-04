import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.pubchem_client import PubChemClient, PubChemNotFound, PubChemTimeout
from backend.nutrition_enforcer import (
    CompoundResolver, 
    NutritionEnforcementMode, 
    calculate_confidence_score,
    get_known_compounds
)
from backend.food_synthesis import FoodSynthesisEngine, IntentOutput

class TestPubChemEnforcement(unittest.TestCase):
    """
    Test suite for PubChem enforcement layer.
    Verifies strict resolution, timeout handling, and agent integration.
    """

    def setUp(self):
        self.resolver = CompoundResolver()
        self.engine = FoodSynthesisEngine(enforcement_mode=NutritionEnforcementMode.STRICT)

    def test_ingredient_mapping(self):
        """Verify ingredient to compound mapping (Knowledge Base)"""
        compounds = get_known_compounds("tomato")
        self.assertIn("lycopene", compounds)
        self.assertIn("vitamin c", compounds)
        
        compounds = get_known_compounds("unknown_ingredient")
        self.assertEqual(len(compounds), 0)

    @patch('backend.pubchem_client.PubChemClient.resolve_compound')
    def test_resolver_budget(self, mock_resolve):
        """Verify resolution budget enforcement (max 10)"""
        # Mock successful resolution
        mock_resolve.return_value = (123, MagicMock(molecular_formula="C1H1"))
        
        # Test with 15 ingredients
        ingredients = [f"ingredient_{i}" for i in range(15)]
        result = self.resolver.resolve_ingredients(ingredients)
        
        self.assertEqual(len(result.resolved), 10)
        self.assertEqual(len(result.unresolved), 5)
        self.assertEqual(result.unresolved[0].reason, "budget_exceeded")

    def test_confidence_score_formula(self):
        """Verify deterministic confidence score calculation"""
        result = MagicMock()
        result.resolution_rate = 0.8
        result.freshness_weight = 1.0
        
        # STRICT mode
        score = calculate_confidence_score(result, NutritionEnforcementMode.STRICT)
        self.assertEqual(score, 0.8)
        
        # PARTIAL mode should reduce score
        score = calculate_confidence_score(result, NutritionEnforcementMode.PARTIAL)
        self.assertAlmostEqual(score, 0.48, places=2) # 0.8 * 1.0 * 0.6

    @patch('backend.pubchem_client.PubChemClient.resolve_compound')
    def test_strict_mode_failure(self, mock_resolve):
        """Verify that STRICT mode fails when confidence is low"""
        # Mock resolution failure
        mock_resolve.side_effect = PubChemNotFound("Not found")
        
        # Intent with ingredients
        intent = IntentOutput(ingredients=["unavailable_compound_xyz"])
        
        # This should return a failure message instead of a recipe
        recipe, meta = self.engine.synthesize(
            user_query="Test query",
            retrieved_docs=[],
            intent=intent
        )
        
        self.assertIn("⚠️ Unable to generate recipe", recipe)
        self.assertIn("[STRICT MODE] Confidence 0.00 below threshold", recipe)
        self.assertEqual(meta["confidence_score"], 0.0)

    @patch('backend.pubchem_client.PubChemClient.resolve_compound')
    def test_partial_mode_success(self, mock_resolve):
        """Verify that PARTIAL mode allows synthesis with lower confidence"""
        self.engine.enforcement_mode = NutritionEnforcementMode.PARTIAL
        
        # Mock resolution failure
        mock_resolve.side_effect = PubChemNotFound("Not found")
        
        # Mock LLM generation
        self.engine.llm.generate_text = MagicMock(return_value="Partial Recipe")
        
        intent = IntentOutput(ingredients=["tomato"])
        
        recipe, meta = self.engine.synthesize(
            user_query="Test query",
            retrieved_docs=[],
            intent=intent
        )
        
        # In PARTIAL mode, it should still call LLM even with 0 confidence
        self.assertEqual(recipe, "Partial Recipe")
        self.assertEqual(meta["confidence_score"], 0.0)

    @patch('backend.pubchem_client.PubChemClient.resolve_compound')
    def test_timeout_handling(self, mock_resolve):
        """Verify timeout handling in enforcement layer"""
        mock_resolve.side_effect = PubChemTimeout("Timed out")
        
        # 'tomato' maps to 3 compounds (lycopene, vitamin c, beta-carotene)
        result = self.resolver.resolve_ingredients(["tomato"])
        
        self.assertEqual(len(result.unresolved), 3) # Expect 3 timeouts
        self.assertEqual(result.unresolved[0].reason, "timeout")

if __name__ == '__main__':
    unittest.main()

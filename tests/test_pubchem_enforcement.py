import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock missing dependencies
from unittest.mock import MagicMock
sys.modules['faiss'] = MagicMock()
sys.modules['ollama'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.optimize'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['pydantic_settings'] = MagicMock()
sys.modules['backend.retriever.faiss_retriever'] = MagicMock()
sys.modules['backend.nutrition.solver'] = MagicMock()

from backend.pubchem_client import PubChemClient, PubChemNotFound, PubChemTimeout
from backend.nutrition_enforcer import (
    CompoundResolver, 
    NutritionEnforcementMode, 
    calculate_confidence_score,
    NutritionEnforcer
)
from backend.food_synthesis import FoodSynthesisEngine, IntentOutput

class TestPubChemEnforcement(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for PubChem enforcement layer.
    Verifies async resolution, timeout handling, and agent integration.
    """

    async def asyncSetUp(self):
        self.resolver = CompoundResolver()
        self.engine = FoodSynthesisEngine(enforcement_mode=NutritionEnforcementMode.STRICT)

    def test_confidence_score_formula(self):
        """Verify deterministic confidence score calculation"""
        result = MagicMock()
        result.resolved = [MagicMock()] * 8
        result.unresolved = [MagicMock()] * 2
        
        # 8/10 = 0.8
        score = calculate_confidence_score(result, NutritionEnforcementMode.STRICT)
        self.assertEqual(score, 0.8)

    @patch('backend.pubchem_client.PubChemClient.search_compound', new_callable=AsyncMock)
    @patch('backend.pubchem_client.PubChemClient.get_compound_properties', new_callable=AsyncMock)
    async def test_resolver_success(self, mock_props, mock_search):
        """Verify successful ingredient resolution"""
        mock_search.return_value = 123
        mock_props.return_value = {"MolecularFormula": "C1H1", "MolecularWeight": "13.0"}
        
        result = await self.resolver.resolve_ingredients(["water"])
        
        self.assertEqual(len(result.resolved), 1)
        self.assertEqual(result.resolved[0].cid, 123)
        self.assertEqual(result.resolved[0].properties["MolecularFormula"], "C1H1")

    @patch('backend.pubchem_client.PubChemClient.search_compound', new_callable=AsyncMock)
    async def test_resolver_failure(self, mock_search):
        """Verify resolution failure handling"""
        mock_search.side_effect = PubChemNotFound("Not found")
        
        result = await self.resolver.resolve_ingredients(["kryptonite"])
        
        self.assertEqual(len(result.unresolved), 1)
        self.assertEqual(result.unresolved[0].reason, "Not found")

    @patch('backend.pubchem_client.PubChemClient.search_compound', new_callable=AsyncMock)
    @patch('backend.pubchem_client.PubChemClient.get_compound_properties', new_callable=AsyncMock)
    async def test_proactive_extraction(self, mock_props, mock_search):
        """Verify proactive extraction via decorator"""
        mock_search.return_value = 962
        mock_props.return_value = {"MolecularFormula": "H2O"}

        # Define a dummy async method to decorate
        class DummyAgent:
            @NutritionEnforcer.requires_pubchem
            async def process(self, *args, **kwargs):
                return kwargs.get("pubchem_data")

        agent = DummyAgent()
        # Pass regex-compliant string for fallback extraction
        res = await agent.process(user_message="- 200ml water")
        
        self.assertIsNotNone(res)
        self.assertTrue(any(c.name == "water" for c in res.resolved))

    @patch('backend.pubchem_client.PubChemClient.search_compound', new_callable=AsyncMock)
    async def test_timeout_handling(self, mock_search):
        """Verify timeout rendering in enforcement result"""
        mock_search.side_effect = PubChemTimeout("Timed out")
        
        result = await self.resolver.resolve_ingredients(["slow_compound"])
        self.assertEqual(result.unresolved[0].reason, "Timed out")

if __name__ == '__main__':
    unittest.main()

import sys
import os
import unittest
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append('/home/ferrarikazu/nutri-ai')

from backend.governance_types import EscalationLevel
from backend.agentic_rag import AgenticRAG
from backend.retriever.router import RetrievalRouter, IndexType
from backend.tools.database_tools import DatabaseTools

class TestFirewallV2(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        
    def test_rag_tier0_block(self):
        """Verify AgenticRAG blocks execution at TIER_0."""
        with patch('backend.agentic_rag.LLMFactory.create_client', return_value=self.mock_llm):
            rag = AgenticRAG(escalation_tier=EscalationLevel.TIER_0)
            
            # Test synchronous query
            result = rag.query("test query")
            self.assertTrue(result.get("metadata", {}).get("blocked", False))
            self.assertIn("lightweight mode", result["answer"])
            
            # Test streaming query
            stream = list(rag.stream_query("test query"))
            self.assertEqual(len(stream), 1)
            self.assertEqual(stream[0]["type"], "error")
            self.assertIn("restricted", stream[0]["content"])
        print("✅ AgenticRAG TIER_0 Block Verified")

    def test_domain_locking_enforcement(self):
        """Verify RetrievalRouter enforces allowed indices."""
        router = RetrievalRouter(project_root="/home/ferrarikazu/nutri-ai")
        router.set_allowed_indices([IndexType.SCIENCE])
        
        # Try to search an unauthorized index (CHEMISTRY)
        with self.assertRaises(AssertionError):
            router.search("test", index_types=[IndexType.CHEMISTRY])
        
        # Search authorized index should not raise
        with patch.object(router, 'load_index', return_value=True):
            with patch.dict(router.retrievers, {IndexType.SCIENCE: MagicMock()}):
                try:
                    router.search("test", index_types=[IndexType.SCIENCE])
                except AssertionError:
                    self.fail("Search on authorized index failed enforcement")
        print("✅ RetrievalRouter Domain-Locking Verified")

    def test_database_tools_tier_guards(self):
        """Verify DatabaseTools restricts indices and PubChem based on tier."""
        # TIER_1 should only allow Recipes
        db_tools = DatabaseTools(escalation_tier=EscalationLevel.TIER_1)
        
        # search_chemistry at TIER_1 should raise PermissionError
        with self.assertRaises(PermissionError):
            db_tools.search_chemistry("caffeine")
            
        # Check PubChem block at TIER_1
        pubchem_res = db_tools.search_pubchem("caffeine")
        self.assertIn("[FIREWALL_BLOCK]", pubchem_res)
        
        # PubChem allow at TIER_3
        db_tools_high = DatabaseTools(escalation_tier=EscalationLevel.TIER_3)
        with patch('backend.tools.database_tools.get_pubchem_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock return values for JSON serialization
            mock_client.search_compound.return_value = 123
            mock_props = MagicMock()
            mock_props.molecular_formula = "C1H1"
            mock_props.molecular_weight = "10.0"
            mock_props.iupac_name = "test"
            mock_props.canonical_smiles = "C"
            mock_client.get_compound_properties.return_value = mock_props
            
            res = db_tools_high.search_pubchem("caffeine")
            parsed = json.loads(res)
            self.assertTrue(parsed["verified"])
            
        print("✅ DatabaseTools Tier Guards Verified")

if __name__ == "__main__":
    unittest.main()

import unittest
import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock missing dependencies
sys.modules['faiss'] = MagicMock()
sys.modules['ollama'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.optimize'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['pydantic_settings'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['pynvml'] = MagicMock()
sys.modules['backend.retriever.faiss_retriever'] = MagicMock()
sys.modules['backend.nutrition.solver'] = MagicMock()

# Configure specific mock values for ResourceBudget
sys.modules['psutil'].virtual_memory.return_value.percent = 50.0
sys.modules['psutil'].cpu_percent.return_value = 20.0

from backend.orchestrator import NutriOrchestrator
from backend.memory import SessionMemoryStore
from backend.response_modes import ResponseMode

class TestNutritionTrace(unittest.IsolatedAsyncioTestCase):
    """
    Verifies that PubChem metadata is correctly captured in execution traces.
    """

    async def asyncSetUp(self):
        self.db_path = "test_nutri_sessions.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        self.memory = SessionMemoryStore(db_path=self.db_path)
        # Mock orchestrator internals to avoid heavy dependencies
        with patch('backend.orchestrator.NutriPipeline'), \
             patch('backend.orchestrator.NutriEngine'), \
             patch('backend.orchestrator.SessionMemoryStore'):
            self.orchestrator = NutriOrchestrator(self.memory)
            self.orchestrator.pipeline = MagicMock()
            self.orchestrator.engine = MagicMock()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    @patch('backend.pubchem_client.PubChemClient.search_compound', new_callable=AsyncMock)
    @patch('backend.pubchem_client.PubChemClient.get_compound_properties', new_callable=AsyncMock)
    async def test_trace_metadata_propagation(self, mock_props, mock_search):
        """Verify PubChem metadata in the execution_trace event"""
        # Set up mocks
        mock_search.return_value = 962
        mock_props.return_value = {"MolecularFormula": "H2O", "MolecularWeight": "18.01"}
        
        # Define a mock ResolutionResult
        from backend.nutrition_enforcer import ResolutionResult, ResolvedCompound
        res = ResolutionResult(resolved=[
            ResolvedCompound(name="water", cid=962, properties={"MolecularFormula": "H2O"})
        ])
        
        # Simulate the decorator by setting the attribute on the engine
        self.orchestrator.engine.last_pubchem_result = res
        
        # To trigger the zero-phase path (len(selected_phases) == 0)
        # To trigger the zero-phase path (len(selected_phases) == 0)
        with patch('backend.phase_schema.PhaseSelector.select_phases', return_value=[]), \
             patch('backend.orchestrator.classify_response_mode', return_value=MagicMock(value="conversation")), \
             patch('backend.selective_memory.MemoryExtractor', return_value=MagicMock(extract_preferences=AsyncMock(return_value={}))), \
             patch('backend.resource_budget.ResourceBudget.check_budget'):
            events = []
            async for event in self.orchestrator.execute_streamed(
                session_id="test_sess",
                user_message="Tell me about water",
                preferences={},
                execution_mode="conversation"
            ):
                events.append(event)

        # 1. Check for execution_trace event or nutrition_report
        report_events = [e for e in events if e["type"] == "nutrition_report"]
        self.assertTrue(len(report_events) >= 1, "Should emit nutrition_report in zero-phase")
        
        trace_events = [e for e in events if e["type"] == "execution_trace"]
        self.assertTrue(len(trace_events) >= 1, "Should emit execution_trace")
        self.assertTrue(trace_events[0]["content"]["pubchem_used"])

    @patch('backend.pubchem_client.PubChemClient.search_compound', new_callable=AsyncMock)
    async def test_zero_hit_trace(self, mock_search):
        """Verify trace when PubChem finds nothing"""
        mock_search.side_effect = Exception("Not found")
        
        from backend.nutrition_enforcer import ResolutionResult
        self.orchestrator.engine.last_pubchem_result = ResolutionResult(resolved=[], unresolved=[MagicMock()])

        with patch('backend.phase_schema.PhaseSelector.select_phases', return_value=[]), \
             patch('backend.orchestrator.classify_response_mode', return_value=MagicMock(value="conversation")), \
             patch('backend.selective_memory.MemoryExtractor', return_value=MagicMock(extract_preferences=AsyncMock(return_value={}))), \
             patch('backend.resource_budget.ResourceBudget.check_budget'):
            events = []
            async for event in self.orchestrator.execute_streamed(
                session_id="test_sess",
                user_message="Tell me about unobtainium",
                preferences={},
                execution_mode="conversation"
            ):
                events.append(event)

        trace_events = [e for e in events if e["type"] == "execution_trace"]
        self.assertTrue(len(trace_events) >= 1)
        trace_data = trace_events[0]["content"]
        
        self.assertFalse(trace_data.get("pubchem_used", True))
        self.assertEqual(trace_data["confidence_score"], 0.0)

if __name__ == '__main__':
    unittest.main()

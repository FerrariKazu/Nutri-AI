import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.retriever.index_manager import IndexManager
from backend.retriever.router import IndexType
from backend.food_synthesis import FoodSynthesisRetriever

class TestRetrievalMemory(unittest.TestCase):
    
    def setUp(self):
        self.mock_root = Path("/tmp/mock_root")
        self.manager = IndexManager(self.mock_root)
        
    @patch('backend.retriever.index_manager.FaissRetriever')
    @patch('backend.retriever.index_manager.check_memory_safety')
    def test_lazy_load(self, mock_guard, MockRetriever):
        """Test that indices are loaded lazily."""
        # Setup mock
        mock_instance = MockRetriever.return_value
        mock_instance.load.return_value = None
        
        # Act
        with patch('pathlib.Path.exists', return_value=True):
            retriever = self.manager.get_retriever(IndexType.SCIENCE)
        
        # Assert
        self.assertIsNotNone(retriever)
        self.assertIn(IndexType.SCIENCE, self.manager.loaded_indices)
        MockRetriever.assert_called_once()
        mock_guard.assert_called()

    @patch('backend.retriever.index_manager.FaissRetriever')
    @patch('backend.retriever.index_manager.check_memory_safety')
    def test_eviction_mutual_exclusion(self, mock_guard, MockRetriever):
        """Test that Chemistry and Branded indices evict each other."""
        # 1. Load Chemistry
        with patch('pathlib.Path.exists', return_value=True):
            self.manager.get_retriever(IndexType.CHEMISTRY)
        self.assertIn(IndexType.CHEMISTRY, self.manager.loaded_indices)
        
        # 2. Load Branded -> Should evict Chemistry
        with patch('pathlib.Path.exists', return_value=True):
            self.manager.get_retriever(IndexType.USDA_BRANDED)
            
        self.assertIn(IndexType.USDA_BRANDED, self.manager.loaded_indices)
        self.assertNotIn(IndexType.CHEMISTRY, self.manager.loaded_indices)
        
        # 3. Load Chemistry again -> Should evict Branded
        with patch('pathlib.Path.exists', return_value=True):
            self.manager.get_retriever(IndexType.CHEMISTRY)
            
        self.assertIn(IndexType.CHEMISTRY, self.manager.loaded_indices)
        self.assertNotIn(IndexType.USDA_BRANDED, self.manager.loaded_indices)

    @patch('backend.retriever.index_manager.FaissRetriever')
    def test_phase_routing(self, MockRetriever):
        """Test that FoodSynthesisRetriever requests correct indices for phases."""
        fs_retriever = FoodSynthesisRetriever(self.mock_root)
        fs_retriever.index_manager = MagicMock()
        
        # Act: Phase 1 (Science + Foundation)
        fs_retriever.retrieve_for_phase(1, "query")
        
        # Assert
        calls = fs_retriever.index_manager.get_retriever.call_args_list
        indices_requested = [c[0][0] for c in calls]
        self.assertIn(IndexType.SCIENCE, indices_requested)
        self.assertIn(IndexType.USDA_FOUNDATION, indices_requested)
        self.assertNotIn(IndexType.CHEMISTRY, indices_requested)
        
        # Act: Phase 6 (Science + Chemistry)
        fs_retriever.index_manager.reset_mock()
        fs_retriever.retrieve_for_phase(6, "query")
        
        calls = fs_retriever.index_manager.get_retriever.call_args_list
        indices_requested = [c[0][0] for c in calls]
        self.assertIn(IndexType.CHEMISTRY, indices_requested)

if __name__ == '__main__':
    unittest.main()

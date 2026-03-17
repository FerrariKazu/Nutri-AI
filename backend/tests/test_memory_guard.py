"""
T3: Test Memory Guard
Verifies MemoryError raised when available RAM is insufficient.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestMemoryGuard:
    """Feature 9-10: Memory and GPU guards."""

    @patch("backend.retriever.memory_guard.check_gpu_safety", return_value=True)
    @patch("backend.retriever.memory_guard.get_system_memory_status")
    def test_raises_on_low_ram(self, mock_mem, mock_gpu):
        """F9: MemoryError raised when available < required * 1.5."""
        from backend.retriever.memory_guard import check_memory_safety

        mock_mem.return_value = {
            "total_gb": 16.0,
            "available_gb": 0.5,  # Very low — below any reasonable threshold
            "percent": 97.0,
            "used_gb": 15.5,
            "free_gb": 0.3,
        }

        with pytest.raises(MemoryError):
            check_memory_safety(required_gb=2.0)  # needs 2.0 * 1.5 = 3.0GB free

    @patch("backend.retriever.memory_guard.check_gpu_safety", return_value=True)
    @patch("backend.retriever.memory_guard.get_system_memory_status")
    def test_passes_on_sufficient_ram(self, mock_mem, mock_gpu):
        """F9: No error when plenty of RAM available."""
        from backend.retriever.memory_guard import check_memory_safety

        mock_mem.return_value = {
            "total_gb": 32.0,
            "available_gb": 10.0,
            "percent": 50.0,
            "used_gb": 16.0,
            "free_gb": 8.0,
        }

        result = check_memory_safety(required_gb=2.0)  # needs 3.0GB, has 10.0GB
        assert result is True

    @patch("backend.retriever.memory_guard.check_gpu_safety", return_value=True)
    @patch("backend.retriever.memory_guard.get_system_memory_status")
    def test_headroom_multiplier_is_1_5(self, mock_mem, mock_gpu):
        """F9: Verify 1.5x headroom — 2GB required needs 3GB free."""
        from backend.retriever.memory_guard import check_memory_safety

        # 2.5GB free, needs 2.0 * 1.5 = 3.0GB → should fail
        mock_mem.return_value = {
            "total_gb": 16.0,
            "available_gb": 2.5,
            "percent": 80.0,
            "used_gb": 13.5,
            "free_gb": 2.0,
        }

        with pytest.raises(MemoryError):
            check_memory_safety(required_gb=2.0)

    def test_gpu_safety_skips_without_cuda(self):
        """F10: GPU guard gracefully skips when CUDA unavailable."""
        from backend.retriever.memory_guard import check_gpu_safety
        import importlib

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            # Re-import to pick up the mock
            import backend.retriever.memory_guard as mg
            importlib.reload(mg)
            result = mg.check_gpu_safety()
            assert result is True

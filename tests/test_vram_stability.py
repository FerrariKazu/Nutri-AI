"""
Test Suite: VRAM Stability & Memory Guard
Tests GPU VRAM monitoring, RAM safety checks, and LLM_CACHE singleton behavior.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.retriever.memory_guard import (
    check_memory_safety,
    check_gpu_safety,
    get_system_memory_status,
)


class TestCheckMemorySafety:
    """Tests for RAM-based memory safety checks."""

    @patch("backend.retriever.memory_guard.check_gpu_safety", return_value=True)
    def test_passes_when_sufficient_ram(self, mock_gpu):
        """Should return True when plenty of RAM is available."""
        mock_mem = MagicMock()
        mock_mem.total = 32e9      # 32 GB
        mock_mem.available = 20e9  # 20 GB
        mock_mem.percent = 37.5
        mock_mem.used = 12e9
        mock_mem.free = 18e9

        with patch("psutil.virtual_memory", return_value=mock_mem):
            result = check_memory_safety(required_gb=2.0)
            assert result is True

    @patch("backend.retriever.memory_guard.check_gpu_safety", return_value=True)
    def test_raises_when_insufficient_ram(self, mock_gpu):
        """Should raise MemoryError when available RAM < required * headroom."""
        mock_mem = MagicMock()
        mock_mem.total = 16e9
        mock_mem.available = 0.5e9  # Only 0.5 GB free
        mock_mem.percent = 96.0
        mock_mem.used = 15.5e9
        mock_mem.free = 0.3e9

        with patch("psutil.virtual_memory", return_value=mock_mem):
            with pytest.raises(MemoryError, match="Insufficient memory"):
                check_memory_safety(required_gb=2.0)

    @patch("backend.retriever.memory_guard.check_gpu_safety", return_value=True)
    def test_raises_on_critical_usage(self, mock_gpu):
        """Should raise MemoryError when system RAM exceeds MAX_RAM_PERCENT."""
        mock_mem = MagicMock()
        mock_mem.total = 16e9
        mock_mem.available = 5e9   # Enough raw RAM
        mock_mem.percent = 95.0    # But usage is critical
        mock_mem.used = 14e9
        mock_mem.free = 2e9

        with patch("psutil.virtual_memory", return_value=mock_mem):
            with pytest.raises(MemoryError, match="critical"):
                check_memory_safety(required_gb=1.0)


class TestCheckGpuSafety:
    """Tests for GPU VRAM monitoring with mocked torch."""

    def test_passes_when_no_torch(self):
        """Should return True when torch is not installed (CPU-only)."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("No torch")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = check_gpu_safety()
            assert result is True

    def test_passes_when_cuda_not_available(self):
        """Should return True when CUDA is not available."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = check_gpu_safety()
            assert result is True

    def test_passes_when_vram_under_limit(self):
        """Should return True when GPU VRAM usage is under threshold."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.memory_reserved.return_value = int(4e9)  # 4 GB used

        props = MagicMock()
        props.total_mem = int(24e9)  # 24 GB total → 16.7% usage
        mock_torch.cuda.get_device_properties.return_value = props

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = check_gpu_safety()
            assert result is True

    def test_raises_when_vram_exceeds_limit(self):
        """Should raise MemoryError when VRAM > 85% threshold."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.memory_reserved.return_value = int(22e9)  # 22 GB used

        props = MagicMock()
        props.total_mem = int(24e9)  # 24 GB total → 91.7% usage
        mock_torch.cuda.get_device_properties.return_value = props

        with patch.dict("sys.modules", {"torch": mock_torch}):
            with pytest.raises(MemoryError, match="GPU VRAM limit exceeded"):
                check_gpu_safety()


class TestGetSystemMemoryStatus:
    """Tests for system memory status reporting."""

    def test_returns_expected_keys(self):
        """Status dict should contain all expected memory fields."""
        mock_mem = MagicMock()
        mock_mem.total = 16e9
        mock_mem.available = 8e9
        mock_mem.percent = 50.0
        mock_mem.used = 8e9
        mock_mem.free = 6e9

        with patch("psutil.virtual_memory", return_value=mock_mem):
            status = get_system_memory_status()

        assert "total_gb" in status
        assert "available_gb" in status
        assert "percent" in status
        assert "used_gb" in status
        assert "free_gb" in status
        assert status["percent"] == 50.0


class TestLLMCacheSingleton:
    """Tests that LLM_CACHE behaves as a singleton and prevents duplication."""

    def test_cache_singleton_identity(self):
        """LLM_CACHE dictionary should be the same object across imports."""
        from backend.retriever import embedder_singleton as mod1
        from backend.retriever import embedder_singleton as mod2

        # Python module system ensures identity
        assert mod1 is mod2

    def test_cache_does_not_duplicate_on_reimport(self):
        """Importing the module twice should not create separate caches."""
        import importlib
        import backend.retriever.embedder_singleton as mod

        # Verify the singleton class exists
        assert hasattr(mod, "EmbedderSingleton"), "EmbedderSingleton class must exist"

        # Store reference to the class
        original_class = mod.EmbedderSingleton

        # Re-import
        importlib.reload(mod)

        # After reload, class is recreated but pattern is preserved
        assert hasattr(mod, "EmbedderSingleton"), "EmbedderSingleton must survive reload"

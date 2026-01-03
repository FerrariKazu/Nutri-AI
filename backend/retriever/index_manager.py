"""
Nutri Index Manager
Responsible for the safe lifecycle (load/unload/evict) of FAISS indices.
Enforces memory budgets and ensures heavy indices are managed carefully.
"""

import gc
import logging
from typing import Dict, Optional, List
from pathlib import Path

from backend.retriever.router import IndexType
from backend.retriever.faiss_retriever import FaissRetriever
from backend.retriever.memory_guard import check_memory_safety

logger = logging.getLogger(__name__)

class IndexManager:
    """
    Manages FAISS index lifecycle.
    Implements Lazy Loading and LRU-style eviction (manual/explicit).
    """
    
    # Estimated memory footprint (GB) for guard checks
    INDEX_COSTS_GB = {
        IndexType.CHEMISTRY: 12.0,
        IndexType.USDA_BRANDED: 6.0,
        IndexType.USDA_FOUNDATION: 0.1,
        IndexType.SCIENCE: 0.05,
    }

    # Indices that should stay resident if possible
    CORE_INDICES = {IndexType.SCIENCE, IndexType.USDA_FOUNDATION}

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.loaded_indices: Dict[IndexType, FaissRetriever] = {}
        logger.info("IndexManager initialized. No indices loaded.")

    def get_retriever(self, index_type: IndexType) -> Optional[FaissRetriever]:
        """
        Get a retriever for the requested index. Loads it if missing.
        Triggers memory check and possible eviction before loading.
        """
        # 1. Fast path: already loaded
        if index_type in self.loaded_indices:
            return self.loaded_indices[index_type]

        # 2. Safety Check & Eviction
        required_gb = self.INDEX_COSTS_GB.get(index_type, 0.5)
        self._ensure_safe_memory(index_type, required_gb)

        # 3. Load
        return self._load_index(index_type)

    def _ensure_safe_memory(self, target_index: IndexType, required_gb: float):
        """
        Ensure we have enough RAM. Evict conflicting heavy indices if needed.
        Rule: Never allow Chemistry (12GB) and Branded (6GB) together on 16GB RAM.
        """
        # Mutual exclusion for Heavy Indices
        if target_index == IndexType.CHEMISTRY:
            if IndexType.USDA_BRANDED in self.loaded_indices:
                logger.info("Evicting Branded to make room for Chemistry...")
                self.unload_index(IndexType.USDA_BRANDED)
        
        elif target_index == IndexType.USDA_BRANDED:
            if IndexType.CHEMISTRY in self.loaded_indices:
                logger.info("Evicting Chemistry to make room for Branded...")
                self.unload_index(IndexType.CHEMISTRY)

        # General Memory Guard
        try:
            check_memory_safety(required_gb)
        except MemoryError as e:
            # Last ditch: Unload everything non-core and try again
            logger.warning(f"Memory pressure! Evicting non-core indices... ({e})")
            self._evict_all_non_core()
            # Check again, if fail now, we crash/fail query
            check_memory_safety(required_gb)

    def _load_index(self, index_type: IndexType) -> Optional[FaissRetriever]:
        """Internal load logic."""
        index_path = self.project_root / f"vector_store/{index_type.value}/index.faiss"
        
        if not index_path.exists():
            logger.warning(f"Index not found: {index_path}")
            return None
        
        logger.info(f"⏳ Lazy Loading: {index_type.value}...")
        try:
            retriever = FaissRetriever(index_path)
            retriever.load()
            self.loaded_indices[index_type] = retriever
            return retriever
        except Exception as e:
            logger.error(f"Failed to load {index_type}: {e}")
            return None

    def unload_index(self, index_type: IndexType):
        """Explicitly unload an index and free memory."""
        if index_type in self.loaded_indices:
            logger.info(f"🗑️ Unloading index: {index_type.value}")
            del self.loaded_indices[index_type]
            gc.collect() # Force garbage collection of massive FAISS arrays

    def _evict_all_non_core(self):
        """Unload everything except Science and Foundation."""
        to_remove = [k for k in self.loaded_indices if k not in self.CORE_INDICES]
        for k in to_remove:
            self.unload_index(k)

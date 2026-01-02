"""
Base Retriever Abstract Class

Defines the interface that all retrievers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseRetriever(ABC):
    """
    Abstract base class for all retrievers.
    
    Every retriever must implement:
    - load(): Load the index from disk
    - search(): Perform semantic search
    - get_metadata(): Return index metadata
    """
    
    def __init__(
        self,
        index_path: Path,
        metadata_path: Optional[Path] = None,
        embedding_model: str = "BAAI/bge-m3"
    ):
        """
        Initialize retriever.
        
        Args:
            index_path: Path to the FAISS index file
            metadata_path: Path to metadata JSON (defaults to index_path.stem + _meta.json)
            embedding_model: Name of embedding model used
        """
        self.index_path = Path(index_path)
        
        # Determine metadata path
        if metadata_path:
            self.metadata_path = Path(metadata_path)
        else:
            # Try .meta.sqlite then .meta.json
            sqlite_path = self.index_path.with_name(self.index_path.stem + ".meta.sqlite")
            if sqlite_path.exists():
                self.metadata_path = sqlite_path
            else:
                self.metadata_path = self.index_path.with_name(self.index_path.stem + ".meta.json")
                
        self.embedding_model = embedding_model
        self._loaded = False
        
        # Validate paths exist
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Index not found: {self.index_path}\n"
                f"Run scripts/rebuild_all_indexes.py to build indexes."
            )
    
    @abstractmethod
    def load(self) -> None:
        """Load the index into memory."""
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of dicts with 'id', 'text', 'score', and 'metadata'
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Return index metadata.
        
        Returns:
            Dict with 'index_size', 'embedding_dim', 'build_date', etc.
        """
        pass
    
    @property
    def is_loaded(self) -> bool:
        """Check if index is loaded into memory."""
        return self._loaded
    
    def ensure_loaded(self) -> None:
        """Load index if not already loaded."""
        if not self._loaded:
            self.load()

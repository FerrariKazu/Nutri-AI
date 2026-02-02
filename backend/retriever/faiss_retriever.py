"""
FAISS Retriever Implementation

Concrete implementation of BaseRetriever using FAISS for semantic search.
"""

import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

import faiss

from .base import BaseRetriever

logger = logging.getLogger(__name__)


class FaissRetriever(BaseRetriever):
    """
    FAISS-based semantic retriever.
    
    Uses FAISS IndexFlatIP (inner product) for cosine similarity search
    on L2-normalized embeddings.
    """
    
    def __init__(
        self,
        index_path: str | Path,
        metadata_path: Optional[str | Path] = None,
        embedding_model: str = "BAAI/bge-m3"
    ):
        """
        Initialize FAISS retriever.
        
        Args:
            index_path: Path to .faiss index file
            metadata_path: Path to _meta.json file (auto-derived if not provided)
            embedding_model: Embedding model name for query encoding
        """
        index_path = Path(index_path)
        m_path = Path(metadata_path) if metadata_path else None
        
        super().__init__(index_path, m_path, embedding_model)
        
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[str, Any] = {}
        self.id_to_doc: Dict[int, Dict[str, Any]] = {}  # Remaining for small indexes
        self._meta_conn: Optional[sqlite3.Connection] = None
        self._is_sqlite_meta = self.metadata_path.suffix == '.sqlite'
        self._embedder = None
    
    def load(self) -> None:
        """Load FAISS index and metadata into memory."""
        if self._loaded:
            logger.info(f"Index already loaded: {self.index_path}")
            return
        
        logger.info(f"Loading FAISS index: {self.index_path}")
        
        # Load FAISS index
        self.index = faiss.read_index(str(self.index_path))
        logger.info(f"Loaded index with {self.index.ntotal} vectors")
        
        # Load metadata
        if self.metadata_path.exists():
            if self._is_sqlite_meta:
                logger.info(f"Using SQLite metadata: {self.metadata_path}")
                self._meta_conn = sqlite3.connect(
                    f"file:{self.metadata_path}?mode=ro", 
                    uri=True,
                    check_same_thread=False
                )
            else:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metadata = data.get('index_info', {})
                    self.id_to_doc = {
                        int(k): v for k, v in data.get('documents', {}).items()
                    }
                logger.info(f"Loaded JSON metadata for {len(self.id_to_doc)} documents")
        else:
            logger.warning(f"Metadata not found: {self.metadata_path}")
        
        # Load embedder lazily
        self._load_embedder()
        
        self._loaded = True
        logger.info(f"✅ FAISS retriever ready: {self.index_path.name}")
    
    def _load_embedder(self) -> None:
        """Load the embedding model for query encoding."""
        if self._embedder is not None:
            return
        
        try:
            from backend.embedder_bge import EmbedderBGE
            self._embedder = EmbedderBGE(model_name=self.embedding_model)
            logger.info(f"Loaded embedder: {self.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to load embedder: {e}")
            raise
    
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
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of result dicts with 'id', 'text', 'score', 'metadata'
        """
        self.ensure_loaded()
        
        # Encode query
        query_embedding = self._embedder.embed_text(query)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for missing results
                continue
            if score < min_score:
                continue
            
            if self._is_sqlite_meta:
                # Query SQLite for metadata
                cursor = self._meta_conn.cursor()
                cursor.execute("SELECT text, json_meta FROM metadata WHERE id = ?", (int(idx),))
                match = cursor.fetchone()
                if match:
                    text, json_str = match
                    metadata = json.loads(json_str)
                    results.append({
                        'id': int(idx),
                        'text': text,
                        'score': float(score),
                        'metadata': metadata,
                        'source': metadata.get('source', 'fdc')
                    })
            else:
                doc = self.id_to_doc.get(idx, {})
                results.append({
                    'id': idx,
                    'text': doc.get('text', ''),
                    'score': float(score),
                    'metadata': doc.get('metadata', {}),
                    'source': doc.get('source', 'unknown')
                })
        
        logger.debug(f"Search returned {len(results)} results for: {query[:50]}...")
        return results
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return index metadata."""
        self.ensure_loaded()
        
        return {
            'index_path': str(self.index_path),
            'index_size': self.index.ntotal if self.index else 0,
            'embedding_dim': self.index.d if self.index else 0,
            'embedding_model': self.embedding_model,
            'document_count': len(self.id_to_doc),
            **self.metadata
        }
    
    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "not loaded"
        return f"FaissRetriever({self.index_path.name}, {status})"

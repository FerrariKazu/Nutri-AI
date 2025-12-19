"""
Semantic search for food index.
"""

import faiss
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import logging

from . import embedder, index_builder

logger = logging.getLogger(__name__)

# Global state
_index: Optional[faiss.Index] = None
_ids: Optional[List[str]] = None
_metadata: Optional[Dict[str, Dict]] = None
_loaded = False


def load() -> None:
    """Load FAISS index, IDs, and metadata."""
    global _index, _ids, _metadata, _loaded
    
    if _loaded:
        logger.info("Food index already loaded")
        return
    
    logger.info("Loading food search index...")
    
    # Load index
    _index = index_builder.load_index()
    
    # Load IDs
    ids_path = index_builder.INDEX_DIR / "ids.json"
    with open(ids_path, 'r') as f:
        _ids = json.load(f)
    logger.info(f"Loaded {len(_ids)} IDs")
    
    # Load metadata
    meta_path = index_builder.INDEX_DIR / "meta.json"
    if meta_path.exists():
        with open(meta_path, 'r') as f:
            _metadata = json.load(f)
        logger.info(f"Loaded metadata for {len(_metadata)} items")
    else:
        _metadata = {}
        logger.warning("No metadata file found")
    
    # Load embedder
    embedder.load_model()
    
    _loaded = True
    logger.info("✅ Food search ready")


def semantic_search(query: str, k: int = 5) -> List[Dict]:
    """
    Semantic search for food items.
    
    Args:
        query: Search query
        k: Number of results
        
    Returns:
        List of results with scores:
        [
            {
                "uuid": "...",
                "score": 0.95,
                "name": "...",
                "snippet": "...",
                ...
            },
            ...
        ]
    """
    if not _loaded:
        load()
    
    if _index is None or _ids is None:
        logger.error("Index not loaded")
        return []
    
    logger.info(f"Searching: '{query}' (k={k})")
    
    # Embed query
    query_embedding = embedder.embed_single(query)
    query_embedding = query_embedding.reshape(1, -1).astype('float32')
    
    # Search
    scores, indices = _index.search(query_embedding, k)
    
    # Format results
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(_ids):
            uuid = _ids[idx]
            
            # Get metadata if available
            meta = _metadata.get(uuid, {})
            
            result = {
                "uuid": uuid,
                "score": float(score),
                "name": meta.get("name", "Unknown"),
                "normalized_name": meta.get("normalized_name", ""),
                "source": meta.get("source", ""),
                "native_id": meta.get("native_id"),
                "snippet": (meta.get("description", "") or "")[:300],
                "nutrients": meta.get("nutrients", {}),
                "category": meta.get("category"),
            }
            results.append(result)
    
    logger.info(f"Returned {len(results)} results")
    return results


def is_ready() -> bool:
    """Check if search is ready."""
    return _loaded and _index is not None

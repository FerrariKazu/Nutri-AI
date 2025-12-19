"""
Semantic search for compound index.
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
    """Load compound FAISS index, IDs, and metadata."""
    global _index, _ids, _metadata, _loaded
    
    if _loaded:
        logger.info("Compound index already loaded")
        return
    
    logger.info("Loading compound search index...")
    
    # Load index
    _index = index_builder.load_index()
    
    # Load IDs
    ids_path = index_builder.INDEX_DIR / "ids.json"
    with open(ids_path, 'r') as f:
        _ids = json.load(f)
    logger.info(f"Loaded {len(_ids)} compound IDs")
    
    # Load metadata
    meta_path = index_builder.INDEX_DIR / "meta.json"
    if meta_path.exists():
        with open(meta_path, 'r') as f:
            _metadata = json.load(f)
        logger.info(f"Loaded compound metadata for {len(_metadata)} items")
    else:
        _metadata = {}
    
    # Load embedder
    embedder.load_model()
    
    _loaded = True
    logger.info("✅ Compound search ready")


def semantic_search(query: str, k: int = 5) -> List[Dict]:
    """
    Semantic search for compounds.
    
    Args:
        query: Search query (compound name, property, etc.)
        k: Number of results
        
    Returns:
        List of compound results with scores
    """
    if not _loaded:
        load()
    
    if _index is None or _ids is None:
        logger.error("Compound index not loaded")
        return []
    
    logger.info(f"Searching compounds: '{query}' (k={k})")
    
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
            meta = _metadata.get(uuid, {})
            
            result = {
                "uuid": uuid,
                "score": float(score),
                "name": meta.get("name", "Unknown"),
                "normalized_name": meta.get("normalized_name", ""),
                "source": meta.get("source", ""),
                "cid": meta.get("cid"),
                "molecular_formula": meta.get("molecular_formula"),
                "snippet": (meta.get("description", "") or "")[:300],
                "toxicity": meta.get("toxicity", {}),
            }
            results.append(result)
    
    logger.info(f"Returned {len(results)} compound results")
    return results


def is_ready() -> bool:
    """Check if compound search is ready."""
    return _loaded and _index is not None

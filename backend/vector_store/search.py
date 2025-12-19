"""
FAISS semantic search runtime.

Loads and queries the FAISS index for recipe retrieval.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

try:
    import faiss
except ImportError:
    faiss = None

from backend.data_loader import get_recipe_by_id, search_recipes_by_ingredients
from backend.vector_store.embedder import embed_text, load_model as load_embedding_model
from backend.vector_store.index_builder import INDEX_PATH, IDS_PATH, index_exists

logger = logging.getLogger(__name__)

# Global FAISS index and recipe IDs
_index: Optional['faiss.Index'] = None
_recipe_ids: Optional[List[int]] = None
_loaded = False


def load_index() -> bool:
    """
    Load FAISS index and recipe IDs from disk.
    
    Returns:
        True if successful, False otherwise
    """
    global _index, _recipe_ids, _loaded
    
    if _loaded:
        logger.info("FAISS index already loaded")
        return True
    
    if faiss is None:
        logger.warning("FAISS not installed, semantic search unavailable")
        return False
    
    if not index_exists():
        logger.warning("FAISS index not found. Build it first using index_builder.build_index()")
        return False
    
    logger.info("Loading FAISS index...")
    
    try:
        # Load index
        _index = faiss.read_index(str(INDEX_PATH))
        logger.info(f"Loaded FAISS index with {_index.ntotal} vectors")
        
        # Load recipe IDs
        with open(IDS_PATH, 'r') as f:
            _recipe_ids = json.load(f)
        logger.info(f"Loaded {len(_recipe_ids)} recipe IDs")
        
        # Load embedding model
        load_embedding_model()
        
        _loaded = True
        logger.info("✅ FAISS index loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {e}")
        return False


def semantic_search(
    query: str,
    k: int = 5,
    fallback_to_lexical: bool = True,
    use_hybrid: bool = False
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Perform semantic search for recipes.
    
    Args:
        query: Search query text
        k: Number of results to return
        fallback_to_lexical: Fall back to lexical search if FAISS unavailable
        use_hybrid: Use hybrid search (semantic + lexical + reranking)
        
    Returns:
        List of (recipe, similarity_score) tuples
    """
    # Use hybrid search if requested
    if use_hybrid:
        try:
            from backend.vector_store import hybrid_search as hs
            results = hs.hybrid_search(query, k_semantic=k, k_lexical=k, top_rerank=k)
            # Convert to (recipe, score) tuples
            return [({"title": r["title"], "text": r["text"], "id": r["id"], "snippet": r.get("snippet", ""), "confidence": r.get("confidence", 0)}, r.get("rerank_score", 0.5)) for r in results]
        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}. Falling back to semantic.")
    
    # Try FAISS search
    if _loaded and _index is not None and _recipe_ids is not None:
        try:
            # Generate query embedding
            query_embedding = embed_text(query)
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search
            distances, indices = _index.search(query_embedding, k)
            
            # Convert to recipe results
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(_recipe_ids):
                    recipe_id = _recipe_ids[idx]
                    recipe = get_recipe_by_id(recipe_id)
                    
                    if recipe:
                        # Convert L2 distance to similarity score (0-1, higher is better)
                        # For normalized vectors, L2 distance relates to cosine similarity
                        similarity = 1.0 / (1.0 + dist)
                        results.append((recipe, float(similarity)))
            
            logger.info(f"FAISS search returned {len(results)} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            if not fallback_to_lexical:
                return []
    
    # Fallback to lexical search
    if fallback_to_lexical:
        logger.info("Using lexical fallback search")
        ingredients = [word.strip() for word in query.split() if len(word.strip()) > 2]
        recipes = search_recipes_by_ingredients(ingredients, top_k=k)
        # Return with dummy scores
        return [(recipe, 0.5) for recipe in recipes]
    
    return []


def batch_semantic_search(
    queries: List[str],
    k: int = 5
) -> List[List[Tuple[Dict[str, Any], float]]]:
    """
    Perform batch semantic search.
    
    Args:
        queries: List of search queries
        k: Number of results per query
        
    Returns:
        List of result lists
    """
    return [semantic_search(query, k) for query in queries]


def is_loaded() -> bool:
    """Check if FAISS index is loaded."""
    return _loaded

"""
Cross-Encoder Reranker for Improved Retrieval Relevance

Uses cross-encoder model to rerank candidates based on query-document relevance.
Falls back to twin-encoder (dot product) if cross-encoder fails on Windows.
"""

import os
os.environ["TOKEN

IZERS_PARALLELISM"] = "false"

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import cross-encoder, fall back to standard encoder
RERANKER_MODE = "crossencoder"

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    logger.info(f"✓ Cross-encoder available: {CROSS_ENCODER_MODEL}")
except ImportError as e:
    logger.warning(f"Cross-encoder import failed: {e}. Falling back to twin-encoder.")
    RERANKER_MODE = "twinencoder"
    from sentence_transformers import SentenceTransformer
    import numpy as np


class Reranker:
    """Rerank candidates using cross-encoder or twin-encoder fallback."""
    
    def __init__(self):
        self.mode = RERANKER_MODE
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize reranking model based on available mode."""
        if self.mode == "crossencoder":
            try:
                self.model = CrossEncoder(CROSS_ENCODER_MODEL)
                logger.info(f"✓ Cross-encoder reranker initialized: {CROSS_ENCODER_MODEL}")
            except Exception as e:
                logger.error(f"Failed to load cross-encoder: {e}. Switching to twin-encoder.")
                self.mode = "twinencoder"
                self._initialize_model()
        
        elif self.mode == "twinencoder":
            # Fallback: use all-MiniLM-L6-v2 for dot product scoring
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✓ Twin-encoder reranker initialized (fallback mode)")
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Rerank candidates based on relevance to query.
        
        Args:
            query: Search query
            candidates: List of dicts with 'id', 'text' keys
            top_n: Number of top results to return
        
        Returns:
            List of dicts with 'id', 'text', 'score' (sorted by score desc)
        """
        if not candidates:
            return []
        
        if self.mode == "crossencoder":
            return self._rerank_crossencoder(query, candidates, top_n)
        else:
            return self._rerank_twinencoder(query, candidates, top_n)
    
    def _rerank_crossencoder(
        self,
        query: str,
        candidates: List[Dict],
        top_n: int
    ) -> List[Dict]:
        """Rerank using cross-encoder (query, doc) pairs."""
        # Prepare pairs for cross-encoder
        pairs = [[query, cand['text']] for cand in candidates]
        
        # Batch predict scores
        scores = self.model.predict(pairs, batch_size=32, show_progress_bar=False)
        
        # Attach scores to candidates
        for i, cand in enumerate(candidates):
            cand['rerank_score'] = float(scores[i])
        
        # Sort by rerank score (descending)
        ranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        return ranked[:top_n]
    
    def _rerank_twinencoder(
        self,
        query: str,
        candidates: List[Dict],
        top_n: int
    ) -> List[Dict]:
        """Fallback reranking using twin-encoder dot product."""
        import numpy as np
        
        # Encode query
        query_emb = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Encode all candidates
        cand_texts = [c['text'] for c in candidates]
        cand_embs = self.model.encode(cand_texts, convert_to_numpy=True, batch_size=32)
        
        # Compute dot products
        scores = np.dot(cand_embs, query_emb)
        
        # Attach scores
        for i, cand in enumerate(candidates):
            cand['rerank_score'] = float(scores[i])
        
        # Sort and return top_n
        ranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        return ranked[:top_n]


# Global reranker instance (lazy loaded)
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get or create global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker


def rerank(query: str, candidates: List[Dict], top_n: int = 5) -> List[Dict]:
    """
    Convenience function for reranking.
    
    Args:
        query: Search query
        candidates: List of {id, text} dicts
        top_n: Number of results to return
    
    Returns:
        Reranked list with scores
    """
    reranker = get_reranker()
    return reranker.rerank(query, candidates, top_n)


if __name__ == "__main__":
    # Simple test
    test_query = "chicken recipe"
    test_candidates = [
        {"id": "1", "text": "How to cook pasta with tomato sauce"},
        {"id": "2", "text": "Grilled chicken breast with herbs and lemon"},
        {"id": "3", "text": "Chocolate cake recipe for beginners"},
        {"id": "4", "text": "Chicken curry with rice and vegetables"},
    ]
    
    results = rerank(test_query, test_candidates, top_n=3)
    
    print("Reranking Test Results:")
    for i, res in enumerate(results, 1):
        print(f"{i}. [Score: {res['rerank_score']:.3f}] {res['text']}")

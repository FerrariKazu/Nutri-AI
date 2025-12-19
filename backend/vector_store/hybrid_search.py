"""
Hybrid Search: Semantic (FAISS) + Lexical (BM25) + Reranking

Combines semantic and lexical search, merges candidates, and reranks using cross-encoder.
Returns enriched results with snippets, confidence scores, and metadata.
"""

import os
import logging
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)

# Import our components
from . import search as semantic_module
from . import bm25
from . import reranker


def extract_snippet(text: str, query: str, snippet_len: int = 300) -> str:
    """
    Extract relevant snippet from text based on query.
    
    Args:
        text: Full text
        query: Search query
        snippet_len: Target snippet length
    
    Returns:
        Snippet string (200-400 chars)
    """
    if not text or len(text) < 50:
        return text
    
    # Tokenize query
    query_terms = set(query.lower().split())
    
    # Find first occurrence of any query term
    text_lower = text.lower()
    best_pos = -1
    
    for term in query_terms:
        pos = text_lower.find(term)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
    
    # If no match found, use beginning
    if best_pos == -1:
        return text[:snippet_len] + ("..." if len(text) > snippet_len else "")
    
    # Extract window around match
    start = max(0, best_pos - snippet_len // 2)
    end = min(len(text), start + snippet_len)
    
    # Adjust to word boundaries
    if start > 0:
        # Find first space after start
        space_pos = text.find(' ', start)
        if space_pos != -1 and space_pos < start + 50:
            start = space_pos + 1
    
    if end < len(text):
        # Find last space before end
        space_pos = text.rfind(' ', start, end)
        if space_pos != -1:
            end = space_pos
    
    snippet = text[start:end]
    
    # Add ellipsis
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet


def normalize_score(score: float, min_score: float = 0.0, max_score: float = 1.0) -> float:
    """Normalize score to [0, 1] range."""
    if max_score == min_score:
        return 0.5
    return max(0.0, min(1.0, (score - min_score) / (max_score - min_score)))


def merge_candidates(
    semantic_results: List[Dict],
    lexical_results: List[Dict]
) -> List[Dict]:
    """
    Merge semantic and lexical results, deduplicating by ID.
    
    Args:
        semantic_results: FAISS results
        lexical_results: BM25 results
    
    Returns:
        Merged list (union, preserving both scores)
    """
    merged = {}
    
    # Add semantic results
    for res in semantic_results:
        res_id = res.get('id', res.get('title', ''))
        merged[res_id] = {
            'id': res_id,
            'title': res.get('title', ''),
            'text': res.get('text', ''),
            'semantic_score': res.get('score', 0.0),
            'lexical_score': 0.0,
            'source': 'semantic'
        }
    
    # Add/merge lexical results  
    for res in lexical_results:
        res_id = res.get('id', res.get('title', ''))
        if res_id in merged:
            # Already have this from semantic - add lexical score
            merged[res_id]['lexical_score'] = res.get('score', 0.0)
            merged[res_id]['source'] = 'hybrid'
        else:
            # New result from lexical only
            merged[res_id] = {
                'id': res_id,
                'title': res.get('title', ''),
                'text': res.get('text', ''),
                'semantic_score': 0.0,
                'lexical_score': res.get('score', 0.0),
                'source': 'lexical'
            }
    
    return list(merged.values())


def hybrid_search(
    query: str,
    k_semantic: int = 10,
    k_lexical: int = 10,
    top_rerank: int = 5
) -> List[Dict]:
    """
    Perform hybrid search: semantic + lexical + reranking.
    
    Pipeline:
    1. Get top-k semantic results from FAISS
    2. Get top-k lexical results from BM25
    3. Merge and deduplicate
    4. Rerank merged candidates
    5. Extract snippets and compute confidence
    
    Args:
        query: Search query
        k_semantic: Number of semantic results
        k_lexical: Number of lexical results
        top_rerank: Final number of results after reranking
    
    Returns:
        List of enriched results with:
        - id, title, text, snippet
        - semantic_score, lexical_score, rerank_score
        - confidence (normalized rerank score)
        - source ('semantic', 'lexical', 'hybrid')
    """
    logger.info(f"Hybrid search for: '{query}'")
    
    # 1. Semantic search (FAISS)
    try:
        semantic_results = semantic_module.semantic_search(query, k=k_semantic)
        logger.info(f"  ✓ Semantic: {len(semantic_results)} results")
    except Exception as e:
        logger.warning(f"Semantic search failed: {e}")
        semantic_results = []
    
    # 2. Lexical search (BM25)
    try:
        lexical_results = bm25.lexical_search(query, k=k_lexical)
        logger.info(f"  ✓ Lexical: {len(lexical_results)} results")
    except Exception as e:
        logger.warning(f"Lexical search failed: {e}")
        lexical_results = []
    
    # 3. Merge candidates
    merged = merge_candidates(semantic_results, lexical_results)
    logger.info(f"  ✓ Merged: {len(merged)} unique candidates")
    
    if not merged:
        return []
    
    # 4. Rerank
    try:
        reranked = reranker.rerank(query, merged, top_n=top_rerank)
        logger.info(f"  ✓ Reranked: {len(reranked)} top results")
    except Exception as e:
        logger.warning(f"Reranking failed: {e}. Using original order.")
        # Fall back to combined score
        for cand in merged:
            cand['rerank_score'] = cand['semantic_score'] + cand['lexical_score']
        reranked = sorted(merged, key=lambda x: x['rerank_score'], reverse=True)[:top_rerank]
    
    # 5. Extract snippets and compute confidence
    if reranked:
        # Get min/max rerank scores for normalization
        rerank_scores = [r['rerank_score'] for r in reranked]
        min_score = min(rerank_scores)
        max_score = max(rerank_scores)
        
        for result in reranked:
            # Extract snippet
            result['snippet'] = extract_snippet(result['text'], query, snippet_len=300)
            
            # Normalize confidence [0, 1]
            result['confidence'] = normalize_score(
                result['rerank_score'],
                min_score,
                max_score
            )
    
    logger.info(f"  ✓ Hybrid search complete: {len(reranked)} enriched results")
    
    return reranked


if __name__ == "__main__":
    # Simple test
    test_query = "quick chicken dinner"
    results = hybrid_search(test_query, k_semantic=5, k_lexical=5, top_rerank=3)
    
    print(f"\nHybrid Search Test: '{test_query}'")
    print("=" * 70)
    
    for i, res in enumerate(results, 1):
        print(f"\n{i}. {res['title']}")
        print(f"   Source: {res['source']}")
        print(f"   Scores: semantic={res['semantic_score']:.3f}, "
              f"lexical={res['lexical_score']:.3f}, "
              f"rerank={res['rerank_score']:.3f}")
        print(f"   Confidence: {res['confidence']:.2f}")
        print(f"   Snippet: {res['snippet'][:150]}...")

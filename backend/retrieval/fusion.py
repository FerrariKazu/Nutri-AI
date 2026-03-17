"""
Reciprocal Rank Fusion (RRF) — Nutri Phase 4

Merges vector (FAISS) and keyword (BM25) search results using RRF scoring.
Outputs lean chunk_id-based results for downstream docstore lookup.
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def _deduplicate_per_source(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate chunk_ids within a single source's result list."""
    seen = set()
    deduped = []
    for r in results:
        cid = r.get("chunk_id", r.get("id"))
        if cid not in seen:
            seen.add(cid)
            deduped.append(r)
    return deduped


def rrf_merge(
    vector_results: List[Dict[str, Any]],
    keyword_results: List[Dict[str, Any]],
    k: int = 60,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Merge vector and keyword results using Reciprocal Rank Fusion.

    Formula: score += 1 / (k + rank)

    Args:
        vector_results: FAISS results with 'chunk_id' or 'id' key.
        keyword_results: BM25 results with 'chunk_id' key.
        k: RRF constant (default 60).

    Returns:
        Tuple of (merged results sorted by RRF score desc, overlap_count).
        Each result: {chunk_id, score, source}.
    """
    # Pre-RRF dedup guard: remove per-source duplicates
    vector_results = _deduplicate_per_source(vector_results)
    keyword_results = _deduplicate_per_source(keyword_results)

    scores: Dict[Any, float] = {}
    sources: Dict[Any, str] = {}

    # Track which IDs appear in each source for overlap counting
    vector_ids = set()
    keyword_ids = set()

    # Score vector results
    for rank, r in enumerate(vector_results, start=1):
        cid = r.get("chunk_id", r.get("id"))
        vector_ids.add(cid)
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        sources[cid] = "vector"

    # Score keyword results
    for rank, r in enumerate(keyword_results, start=1):
        cid = r.get("chunk_id", r.get("id"))
        keyword_ids.add(cid)
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        if cid in sources:
            sources[cid] = "hybrid"
        else:
            sources[cid] = "bm25"

    # Overlap count for telemetry
    overlap_count = len(vector_ids & keyword_ids)

    # Build sorted results
    merged = [
        {"chunk_id": cid, "score": score, "source": sources[cid]}
        for cid, score in scores.items()
    ]
    merged.sort(key=lambda x: x["score"], reverse=True)

    logger.info(
        f"[RRF] Merged {len(vector_results)} vector + {len(keyword_results)} keyword "
        f"→ {len(merged)} results (overlap={overlap_count})"
    )

    return merged, overlap_count

"""
Retrieval Utilities — shared helpers for FAISS-safe embedding and top_k handling.

All embedding inputs to FAISS must pass through normalize_embedding().
All top_k values must pass through normalize_top_k().
"""

import numpy as np
import logging
from typing import Union, List, Optional

logger = logging.getLogger(__name__)


from ..src.services.query_decomposer import QueryDecomposer


def normalize_embedding(vec) -> np.ndarray:
    """
    Convert any BGE-M3 / embedding output into a FAISS-safe 1D float32 vector.

    Handles:
      - Plain list or nested list: [[0.1, 0.2, ...]] or [[[...]]]
      - numpy arrays of any shape: (1, D), (1, 1, D), (D,)
      - Already-flat 1D arrays (no-op)
    """
    if isinstance(vec, list):
        vec = np.array(vec)

    vec = np.array(vec, dtype=np.float32)

    # Flatten any nesting: (1, D) → (D,), (1, 1, D) → (D,), etc.
    if vec.ndim > 1:
        vec = vec.reshape(-1)

    return vec


def normalize_top_k(k) -> int:
    """
    Coerce any top_k value to a plain Python int.

    Handles: list [5], str "5", numpy int64, float 5.0, int 5.
    """
    if isinstance(k, (list, tuple, np.ndarray)):
        k = k[0] if len(k) > 0 else 10
    if isinstance(k, str):
        k = int(k)
    return int(k)


def safe_retrieve(results) -> list:
    """
    Guard that ensures retrieval always returns a clean list.
    Never crashes downstream code on None or unexpected types.
    """
    if results is None:
        logger.warning("[RETRIEVAL_GUARD] results is None — returning []")
        return []
    if not isinstance(results, list):
        logger.warning(f"[RETRIEVAL_GUARD] results type={type(results)} — coercing to []")
        return []
    return results


def decompose_query(query: str, tier: Optional[str] = None) -> List[str]:
    """
    Expand technical queries into semantic variations using the QueryDecomposer service.
    Prevents recall failure for highly technical chemical concepts.

    Args:
        query: User query text.
        tier: Optional escalation tier name (e.g. "TIER_0", "TIER_3").
              Controls which ontology expansions are applied.
    """
    return QueryDecomposer.decompose(query, tier=tier)

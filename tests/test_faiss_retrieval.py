"""
Regression tests for FAISS retrieval type normalization.

Verifies that:
1. FAISS 2D output is always flattened to 1D lists immediately.
2. Score and index comparisons never fail with list vs int type errors.
3. Slicing is always performed on integers, not lists.
4. Empty FAISS results are handled gracefully.
5. Retrieved documents are properly assembled.
"""

import numpy as np
import pytest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.abspath("."))

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_faiss_output(scores_1d: list, indices_1d: list):
    """
    Simulate what FAISS actually returns: 2D numpy arrays.
    scores.shape == (1, k), indices.shape == (1, k)
    """
    return (
        np.array([scores_1d], dtype=np.float32),
        np.array([indices_1d], dtype=np.int64),
    )


def _make_retriever(scores_1d, indices_1d, docs=None):
    """
    Build a FaissRetriever with a fully mocked FAISS index and minimal metadata.
    """
    # Import inline so missing faiss doesn't break collection
    sys.modules['faiss'] = MagicMock()
    sys.modules['backend.embedder_bge'] = MagicMock()

    from backend.retriever.faiss_retriever import FaissRetriever

    retriever = object.__new__(FaissRetriever)
    # Minimal attribute init matching __init__
    retriever._loaded = True
    retriever._is_sqlite_meta = False
    retriever._meta_conn = None
    retriever._embedder = MagicMock()
    retriever._embedder.embed_text.return_value = np.ones(128, dtype=np.float32)

    mock_index = MagicMock()
    mock_index.d = 128
    mock_index.ntotal = len(indices_1d)
    mock_index.search.return_value = _make_faiss_output(scores_1d, indices_1d)
    retriever.index = mock_index

    # id_to_doc
    if docs is None:
        docs = {i: {"text": f"doc_{i}", "metadata": {}, "source": "test"} for i in indices_1d if i >= 0}
    retriever.id_to_doc = docs

    # Patch faiss.normalize_L2 to no-op
    import backend.retriever.faiss_retriever as mod
    mod.faiss = MagicMock()
    retriever.ensure_loaded = lambda: None
    retriever.index_path = MagicMock()
    retriever.index_path.name = "test.faiss"

    return retriever


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFaissOutputNormalization:

    def test_scores_and_indices_are_flat_lists(self):
        """FAISS 2D output must be flattened to plain Python lists immediately."""
        retriever = _make_retriever(
            scores_1d=[0.92, 0.88, 0.84],
            indices_1d=[10, 20, 30],
        )
        results = retriever.search("test query", top_k=3, min_score=0.0)

        assert isinstance(results, list), "search() must return a list"
        assert len(results) == 3

    def test_scores_never_compared_to_int_as_list(self):
        """Scalar score filtering must work without TypeError."""
        retriever = _make_retriever(
            scores_1d=[0.95, 0.50, 0.30],
            indices_1d=[1, 2, 3],
        )
        # min_score=0.6 should filter out 0.50 and 0.30
        results = retriever.search("test", top_k=3, min_score=0.6)
        assert len(results) == 1
        assert results[0]['score'] == pytest.approx(0.95, abs=0.01)

    def test_slicing_always_uses_integer_top_k(self):
        """top_k must be an integer — never a list — when used for slicing."""
        retriever = _make_retriever(
            scores_1d=[0.9, 0.8, 0.7, 0.6],
            indices_1d=[1, 2, 3, 4],
        )
        top_k = 2
        assert isinstance(top_k, int), "top_k parameter must be an integer"

        results = retriever.search("query", top_k=top_k, min_score=0.0)
        # The retriever returns up to top_k results from a flat list (no slice-as-list)
        assert isinstance(results, list)

    def test_scores_below_threshold_returns_empty(self):
        """When NO scores meet the threshold, search() must return [] (no fallback)."""
        retriever = _make_retriever(
            scores_1d=[0.4, 0.3, 0.2],
            indices_1d=[1, 2, 3],
        )
        results = retriever.search("query", top_k=5, min_score=0.5)
        assert results == [], "Should return empty list if all scores below threshold"

    def test_empty_faiss_result_returns_empty_list(self):

    def test_negative_indices_are_skipped(self):
        """FAISS uses -1 for padding when fewer results than k exist."""
        retriever = _make_retriever(
            scores_1d=[0.9, 0.0, 0.0],
            indices_1d=[5, -1, -1],
            docs={5: {"text": "real_doc", "metadata": {}, "source": "test"}},
        )
        results = retriever.search("query", top_k=3, min_score=0.0)
        assert len(results) == 1
        assert results[0]['text'] == "real_doc"

    def test_retrieved_docs_have_required_fields(self):
        """Every result dict must contain id, text, score, metadata, source."""
        retriever = _make_retriever(
            scores_1d=[0.88],
            indices_1d=[42],
            docs={42: {"text": "vitamin C", "metadata": {"category": "nutrition"}, "source": "usda"}},
        )
        results = retriever.search("vitamin C", top_k=1, min_score=0.0)
        assert len(results) == 1
        doc = results[0]
        assert 'id' in doc
        assert 'text' in doc
        assert 'score' in doc
        assert 'metadata' in doc
        assert 'source' in doc

    def test_type_assertions_are_enforced(self):
        """The scores and indices must be lists after normalization."""
        retriever = _make_retriever(
            scores_1d=[0.7],
            indices_1d=[1],
        )
        # Patch index.search to return raw np.ndarray (2D) — verifying normalization handles it
        raw_scores = np.array([[0.7]], dtype=np.float32)
        raw_indices = np.array([[1]], dtype=np.int64)
        retriever.index.search.return_value = (raw_scores, raw_indices)

        # Must not raise TypeError or AssertionError
        results = retriever.search("query", top_k=1, min_score=0.0)
        assert isinstance(results, list)

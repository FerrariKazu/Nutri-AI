"""
Test Suite: Soft Scoring & Fallback Behavior
Validates that FaissRetriever correctly tags results as strong/weak
and returns appropriate fallback when insufficient strong results exist.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_retriever():
    """Create a FaissRetriever with mocked internals for unit testing."""
    from backend.retriever.faiss_retriever import FaissRetriever

    retriever = FaissRetriever(index_path="dummy.faiss", metadata_path="dummy.json")

    # Mock FAISS index
    index = MagicMock()
    index.d = 1024
    index.ntotal = 100
    retriever.index = index
    retriever._loaded = True

    # Mock embedder — returns a random 1024-dim vector
    embedder = MagicMock()
    embedder.embed_text.return_value = np.random.rand(1024).astype("float32")
    retriever._embedder = embedder

    return retriever


def _make_search_fn(scores, indices):
    """Create a mock FAISS search function returning the given scores/indices."""
    def mock_search(query_embedding, top_k):
        return np.array([scores[:top_k]]), np.array([indices[:top_k]])
    return mock_search


class TestSoftScoring:
    """Tests for strong/weak tagging and fallback logic."""

    def test_all_strong_results_returned(self, mock_retriever):
        """When all results exceed min_score, all should be tagged 'strong'."""
        mock_retriever.index.search = _make_search_fn(
            [0.85, 0.72, 0.60], [0, 1, 2]
        )
        mock_retriever.id_to_doc = {
            0: {"text": "doc zero", "source": "sci", "metadata": {}},
            1: {"text": "doc one", "source": "sci", "metadata": {}},
            2: {"text": "doc two", "source": "sci", "metadata": {}},
        }

        results = mock_retriever.search("test query", top_k=3, min_score=0.45)

        assert len(results) == 3
        assert all(r["strength"] == "strong" for r in results)

    def test_weak_results_tagged_correctly(self, mock_retriever):
        """Results below min_score should be tagged 'weak'."""
        mock_retriever.index.search = _make_search_fn(
            [0.80, 0.30, 0.20], [0, 1, 2]
        )
        mock_retriever.id_to_doc = {
            0: {"text": "strong doc", "source": "sci", "metadata": {}},
            1: {"text": "weak doc one", "source": "sci", "metadata": {}},
            2: {"text": "weak doc two", "source": "sci", "metadata": {}},
        }

        # Only 1 strong result → fallback returns all with tags
        results = mock_retriever.search("test query", top_k=3, min_score=0.45)

        assert len(results) == 3
        strengths = [r["strength"] for r in results]
        assert strengths[0] == "strong"  # 0.80
        assert strengths[1] == "weak"    # 0.30
        assert strengths[2] == "weak"    # 0.20

    def test_fallback_returns_all_when_few_strong(self, mock_retriever):
        """When < 2 strong results exist, fallback returns full ranked list."""
        mock_retriever.index.search = _make_search_fn(
            [0.50, 0.30, 0.20], [0, 1, 2]
        )
        mock_retriever.id_to_doc = {
            0: {"text": "borderline doc", "source": "sci", "metadata": {}},
            1: {"text": "weak doc", "source": "sci", "metadata": {}},
            2: {"text": "weakest doc", "source": "sci", "metadata": {}},
        }

        results = mock_retriever.search("test query", top_k=3, min_score=0.45)

        # Only 1 strong (0.50) → fallback returns all 3
        assert len(results) == 3
        assert results[0]["strength"] == "strong"
        assert results[1]["strength"] == "weak"

    def test_strong_only_when_sufficient(self, mock_retriever):
        """When >= 2 strong results, only strong results returned."""
        mock_retriever.index.search = _make_search_fn(
            [0.90, 0.70, 0.20], [0, 1, 2]
        )
        mock_retriever.id_to_doc = {
            0: {"text": "very strong", "source": "sci", "metadata": {}},
            1: {"text": "strong", "source": "sci", "metadata": {}},
            2: {"text": "weak", "source": "sci", "metadata": {}},
        }

        results = mock_retriever.search("test query", top_k=3, min_score=0.45)

        # 2 strong → only strong returned
        assert len(results) == 2
        assert all(r["strength"] == "strong" for r in results)

    def test_results_sorted_before_tagging(self, mock_retriever):
        """Results must be sorted by score descending before tagging."""
        # Intentionally give unsorted scores
        mock_retriever.index.search = _make_search_fn(
            [0.40, 0.90, 0.60], [0, 1, 2]
        )
        mock_retriever.id_to_doc = {
            0: {"text": "low score", "source": "sci", "metadata": {}},
            1: {"text": "high score", "source": "sci", "metadata": {}},
            2: {"text": "mid score", "source": "sci", "metadata": {}},
        }

        results = mock_retriever.search("test query", top_k=3, min_score=0.45)

        # Should be sorted: 0.90, 0.60, 0.40
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestMatchCountBoost:
    """Tests for multi-match document boosting."""

    def test_match_count_field_present(self, mock_retriever):
        """Each result should have a match_count field."""
        mock_retriever.index.search = _make_search_fn(
            [0.80], [0]
        )
        mock_retriever.id_to_doc = {
            0: {"text": "doc zero", "source": "sci", "metadata": {}},
        }

        results = mock_retriever.search("test", top_k=1, min_score=0.45)
        assert "match_count" in results[0]
        assert results[0]["match_count"] >= 1

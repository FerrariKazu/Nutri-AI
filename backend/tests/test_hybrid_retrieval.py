"""Tests for Hybrid Retrieval — Phase 4"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path

from backend.retrieval.bm25_index import BM25Index
from backend.retrieval.hybrid_retriever import HybridRetriever


class TestBM25Index:

    def test_build_and_search(self):
        """BM25 index should find keyword matches."""
        chunks = [
            {"chunk_id": 0, "text": "inosinate is a key umami compound"},
            {"chunk_id": 1, "text": "citric acid gives sour taste to lemons"},
            {"chunk_id": 2, "text": "alkaloids produce bitter flavors in coffee"},
        ]

        bm25 = BM25Index()
        bm25.build_index(chunks)

        results = bm25.search("inosinate taste", k=3)
        assert len(results) > 0
        assert results[0]["chunk_id"] == 0

    def test_persistence(self, tmp_path):
        """BM25 index should survive save/load cycle."""
        chunks = [
            {"chunk_id": 0, "text": "glucose is a simple sugar found in many foods"},
            {"chunk_id": 1, "text": "fructose is commonly found in fruits and honey"},
            {"chunk_id": 2, "text": "protein helps build muscle tissue effectively"},
        ]

        bm25 = BM25Index()
        bm25.build_index(chunks)

        # Verify search works before save
        pre_results = bm25.search("glucose sugar", k=2)
        assert len(pre_results) > 0

        bm25.save(tmp_path)

        loaded = BM25Index()
        assert loaded.load(tmp_path) is True
        assert loaded.doc_count == 3

        # Verify search works after load with well-matching query
        post_results = loaded.search("glucose sugar", k=3)
        assert len(post_results) > 0
        assert post_results[0]["chunk_id"] == 0

    def test_metadata_file(self, tmp_path):
        """Save should create bm25_metadata.json."""
        import json

        bm25 = BM25Index()
        bm25.build_index([{"chunk_id": 0, "text": "test document with content"}])
        bm25.save(tmp_path)

        meta_path = tmp_path / "bm25_metadata.json"
        assert meta_path.exists()

        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["doc_count"] == 1
        assert "tokenizer_version" in meta

    def test_faiss_validation(self):
        """Validation should detect doc count mismatch."""
        bm25 = BM25Index()
        bm25.build_index([{"chunk_id": i, "text": f"doc {i}"} for i in range(10)])

        assert bm25.validate_against_faiss(10) is True
        assert bm25.validate_against_faiss(15) is False


class TestHybridRetriever:

    def _make_retriever(self):
        """Create a HybridRetriever with mocked dependencies."""
        faiss_mock = MagicMock()
        faiss_mock._loaded = True
        faiss_mock.ensure_loaded = MagicMock()
        faiss_mock._get_cached_embedding = MagicMock(
            return_value=np.random.random(128).astype("float32")
        )
        faiss_mock._single_search = MagicMock(
            return_value=([0.9, 0.8], [0, 1])
        )
        faiss_mock.id_to_doc = {
            0: {"text": "inosinate is a key umami compound"},
            1: {"text": "citric acid gives sour taste"},
            2: {"text": "alkaloids produce bitter flavors"},
        }

        bm25 = BM25Index()
        bm25.build_index([
            {"chunk_id": 0, "text": "inosinate is a key umami compound"},
            {"chunk_id": 1, "text": "citric acid gives sour taste"},
            {"chunk_id": 2, "text": "alkaloids produce bitter flavors"},
        ])

        retriever = HybridRetriever(faiss_mock, bm25)
        retriever.ENABLE_RERANKER = False
        return retriever

    @patch("backend.retriever.retrieval_utils.decompose_query", return_value=["test"])
    def test_hybrid_returns_both_sources(self, mock_decompose):
        """Hybrid should return results from both FAISS and BM25."""
        retriever = self._make_retriever()
        output = retriever.search("inosinate taste", top_k=5, min_score=0.0)

        results = output["results"]
        assert len(results) > 0

        telemetry = output["telemetry"]
        assert "faiss_ms" in telemetry
        assert "bm25_ms" in telemetry
        assert "fusion_ms" in telemetry
        assert "rrf_overlap_count" in telemetry

    @patch("backend.retriever.retrieval_utils.decompose_query", return_value=["inosinate taste"])
    def test_hybrid_recall_inosinate(self, mock_decompose):
        """Hybrid recall: 'inosinate taste' must find the umami compound chunk."""
        retriever = self._make_retriever()
        output = retriever.search("inosinate taste", top_k=5, min_score=0.0)

        texts = [r.get("text", "") for r in output["results"]]
        found = any("inosinate" in t for t in texts)
        assert found, "Hybrid retrieval failed to find 'inosinate' chunk"

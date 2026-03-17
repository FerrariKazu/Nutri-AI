"""Tests for RRF Fusion — Phase 4"""

import pytest
from backend.retrieval.fusion import rrf_merge, _deduplicate_per_source


class TestRRFFusion:

    def test_rrf_basic_merge(self):
        """Verify RRF merges vector and keyword results."""
        vector = [
            {"chunk_id": 1, "score": 0.9},
            {"chunk_id": 2, "score": 0.8},
            {"chunk_id": 3, "score": 0.7},
        ]
        keyword = [
            {"chunk_id": 4, "score": 5.0},
            {"chunk_id": 2, "score": 4.0},
            {"chunk_id": 5, "score": 3.0},
        ]

        merged, overlap = rrf_merge(vector, keyword, k=60)

        chunk_ids = [r["chunk_id"] for r in merged]
        assert 1 in chunk_ids
        assert 2 in chunk_ids
        assert 3 in chunk_ids
        assert 4 in chunk_ids
        assert 5 in chunk_ids
        assert len(chunk_ids) == 5  # 5 unique chunks

    def test_rrf_overlap_count(self):
        """Verify overlap telemetry is correct."""
        vector = [{"chunk_id": 1}, {"chunk_id": 2}, {"chunk_id": 3}]
        keyword = [{"chunk_id": 2}, {"chunk_id": 3}, {"chunk_id": 4}]

        _, overlap = rrf_merge(vector, keyword)
        assert overlap == 2  # chunks 2 and 3 overlap

    def test_rrf_hybrid_source_tag(self):
        """Chunks in both sources should be tagged 'hybrid'."""
        vector = [{"chunk_id": 10, "score": 0.9}]
        keyword = [{"chunk_id": 10, "score": 5.0}]

        merged, _ = rrf_merge(vector, keyword)
        assert merged[0]["source"] == "hybrid"

    def test_rrf_score_formula(self):
        """Verify RRF score formula: 1/(k+rank)."""
        vector = [{"chunk_id": 1, "score": 0.9}]
        keyword = []

        merged, _ = rrf_merge(vector, keyword, k=60)
        expected_score = 1.0 / (60 + 1)  # rank=1
        assert abs(merged[0]["score"] - expected_score) < 1e-6

    def test_rrf_double_score_for_overlap(self):
        """Overlapping chunk gets scored from both sources."""
        vector = [{"chunk_id": 1}]
        keyword = [{"chunk_id": 1}]

        merged, _ = rrf_merge(vector, keyword, k=60)
        expected = 1.0 / (60 + 1) + 1.0 / (60 + 1)  # rank 1 in both
        assert abs(merged[0]["score"] - expected) < 1e-6

    def test_pre_rrf_dedup(self):
        """Duplicate chunk_ids within a source should be deduped."""
        results = [
            {"chunk_id": 1, "score": 0.9},
            {"chunk_id": 1, "score": 0.8},
            {"chunk_id": 2, "score": 0.7},
        ]
        deduped = _deduplicate_per_source(results)
        assert len(deduped) == 2

    def test_rrf_ranking_stability(self):
        """Higher-ranked items in both sources should rank highest."""
        vector = [{"chunk_id": "A"}, {"chunk_id": "B"}, {"chunk_id": "C"}]
        keyword = [{"chunk_id": "A"}, {"chunk_id": "D"}, {"chunk_id": "B"}]

        merged, _ = rrf_merge(vector, keyword, k=60)
        # A should be first (rank 1 in both)
        assert merged[0]["chunk_id"] == "A"

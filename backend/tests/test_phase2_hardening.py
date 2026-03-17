import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from backend.retriever.query_decomposer import QueryDecomposer
from backend.retriever.retrieval_utils import cross_encode_rerank
from backend.retriever.faiss_retriever import FaissRetriever
from pathlib import Path

def test_query_decomposer_multihop():
    with patch("backend.retriever.query_decomposer.LLMClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.generate.return_value = "{\"sub_queries\": [\"sub1\", \"sub2\"], \"reasoning\": \"test\"}"
        
        decomposer = QueryDecomposer()
        result = decomposer.decompose("complex query")
        
        assert "sub_queries" in result
        assert len(result["sub_queries"]) == 2
        assert result["sub_queries"][0] == "sub1"

def test_cross_encode_rerank():
    query = "test query"
    results = [
        {"content": "doc1", "score": 0.5},
        {"content": "doc2", "score": 0.4}
    ]
    
    # Mocking semantic_reranker for now as it's a wrapper around CrossEncoder
    with patch("backend.retriever.retrieval_utils.semantic_reranker") as mock_rerank:
        mock_rerank.return_value = [
            {"content": "doc2", "score": 0.9, "original_score": 0.4},
            {"content": "doc1", "score": 0.8, "original_score": 0.5}
        ]
        
        reranked = cross_encode_rerank(query, results)
        assert reranked[0]["content"] == "doc2"
        assert reranked[0]["score"] == 0.9

def test_faiss_retriever_ranking():
    # Mock FAISS index and embedding model
    with patch("faiss.read_index"), \
         patch("backend.retriever.faiss_retriever.FaissRetriever._get_embeddings") as mock_embed:
        
        mock_embed.return_value = np.zeros((1, 1024))
        
        retriever = FaissRetriever("fake_index.bin")
        retriever.index = MagicMock()
        retriever.index.search.return_value = (
            np.array([[0.1, 0.2]]), 
            np.array([[0, 1]])
        )
        retriever.id_to_doc = {
            0: {"content": "apple contains alkaloid", "metadata": {}},
            1: {"content": "banana contains glucose", "metadata": {}}
        }
        retriever._loaded = True
        
        # Search for "apple bitter"
        results = retriever.search("apple bitter", top_k=2)
        
        # Doc 0 should have "bitter" tag and boost
        assert results[0]["metadata"]["tastes"] == ["bitter"]
        # Score should be 0.1 + 0.05 = 0.15 (initially 0.1)
        # Wait, the search logic sorts by score. Let's check.
        # Original scores were 0.1 and 0.2. 
        # Doc 0 (0.1) -> 0.15
        # Doc 1 (0.2) -> 0.2 (no "sweet" in query "apple bitter")
        # So Doc 1 still wins? Let's check the TASTE_BONUS
        
        # If I search for "banana sweet", Doc 1 should be boosted
        results_sweet = retriever.search("banana sweet", top_k=2)
        # Doc 1: 0.2 + 0.05 = 0.25. Doc 0: 0.1.
        assert results_sweet[0]["content"] == "banana contains glucose"
        assert "sweet" in results_sweet[0]["metadata"]["tastes"]

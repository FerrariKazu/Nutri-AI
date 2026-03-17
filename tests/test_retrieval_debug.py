import pytest
import numpy as np
from unittest.mock import MagicMock
from backend.retriever.faiss_retriever import FaissRetriever

@pytest.fixture
def mock_faiss_index():
    # Create a mock FAISS index that returns predetermined scores and indices
    index = MagicMock()
    index.d = 1024
    index.ntotal = 500
    
    # Return 3 matches: one high score, one medium score, one low score
    # Scores are L2 normalized inner products (cosine similarity)
    # Indices are 0, 1, 2
    def mock_search(query_embedding, top_k):
        # Return nested arrays as FAISS does
        # Simulating scores: 0.85 (pass), 0.65 (borderline), 0.40 (fail)
        return np.array([[0.85, 0.65, 0.40]]), np.array([[0, 1, 2]])
        
    index.search = mock_search
    return index

def test_faiss_retriever_threshold_filtering(mock_faiss_index, caplog):
    """
    Validates that the FAISS retriever correctly filters results based on min_score
    while maintaining raw score diagnostic logging functionality.
    """
    # Create retriever with dummy paths since we are bypassing disk load
    retriever = FaissRetriever(index_path="dummy.faiss", metadata_path="dummy.json")
    
    # Inject mock index
    retriever.index = mock_faiss_index
    retriever._loaded = True
    
    # Inject mock embedder
    retriever._embedder = MagicMock()
    retriever._embedder.embed_text.return_value = np.random.rand(1024)
    
    # Inject dummy metadata mapping
    retriever.id_to_doc = {
        0: {"text": "sodium transport mechanism high", "source": "science", "metadata": {}},
        1: {"text": "sodium transport medium", "source": "science", "metadata": {}},
        2: {"text": "sodium low", "source": "science", "metadata": {}}
    }
    
    import logging
    caplog.set_level(logging.DEBUG)
    
    # Execute search with threshold 0.60
    # Expected: items 0 and 1 pass (0.85, 0.65 > 0.60), item 2 fails (0.40)
    results = retriever.search("sodium transport", top_k=3, min_score=0.60)
    
    # Verify filtering
    assert len(results) == 2, f"Expected 2 results to pass threshold, got {len(results)}"
    assert results[0]['id'] == 0
    assert results[1]['id'] == 1
    
    # Verify diagnostic logs were correctly generated
    log_text = caplog.text
    assert "[FAISS_CONFIG]" in log_text
    assert "top_k=3" in log_text
    assert "min_score=0.6" in log_text
    
    assert "[FAISS_RAW_RESULTS]" in log_text
    assert "0.85" in log_text
    assert "0.65" in log_text
    assert "0.4" in log_text

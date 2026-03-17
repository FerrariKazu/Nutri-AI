import pytest
import asyncio
from rag.retriever import FAISSRetriever

@pytest.mark.asyncio
async def test_faiss_retriever_deduplication():
    # Test that FAISSRetriever correctly deduplicates results
    # We'll use the existing index if available.
    
    retriever = FAISSRetriever()
    
    # Define a query that might return overlapping results
    query = "healthy fats"
    results = await asyncio.to_thread(retriever.retrieve, query, top_k=10)
    
    seen_ids = set()
    for res in results:
        # Each item should have a unique ID (source + index)
        chunk_id = res.get('chunk_id', '')
        assert chunk_id not in seen_ids, f"Duplicate chunk_id found: {chunk_id}"
        seen_ids.add(chunk_id)
        
    print(f"Verified {len(results)} unique results.")

@pytest.mark.asyncio
async def test_semantic_overlap_deduplication():
    # Specifically test the deduplication logic in FAISSRetriever.retrieve
    
    retriever = FAISSRetriever()
    
    # Verify the search results are indeed unique by chunk_id
    query = "high protein snacks"
    results = await asyncio.to_thread(retriever.retrieve, query, top_k=20)
    
    chunk_ids = [r.get('chunk_id') for r in results]
    assert len(chunk_ids) == len(set(chunk_ids)), "Results are not unique by chunk_id"

if __name__ == "__main__":
    # For manual testing
    retriever = FAISSRetriever()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_faiss_retriever_deduplication())
    loop.run_until_complete(test_semantic_overlap_deduplication())

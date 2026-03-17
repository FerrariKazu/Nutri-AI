import asyncio
from pathlib import Path
from backend.embedding.tei_client import TEIEmbedder
from backend.retriever.faiss_retriever import FaissRetriever

async def test_retrieval():
    index_path = Path("data/processed/chemistry_data.index")
    metadata_path = Path("data/processed/chemistry_data.meta.json")
    
    if not index_path.exists():
        print(f"Index not found: {index_path}")
        return

    print(f"Loading retriever from {index_path}...")
    embedder = TEIEmbedder()
    retriever = FaissRetriever(
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=embedder
    )
    
    # Load the index
    retriever.load()
    
    query = "What is the molecular weight of Aspirin?"
    print(f"\nSearching for: '{query}'")
    
    # Perform search (synchronous)
    results = retriever.search(query, top_k=5)
    
    print("\nTop 5 results:")
    for i, res in enumerate(results):
        print(f"\nResult {i+1} (Score: {res['score']:.4f}):")
        print(f"Text snippet: {res['text'][:200]}...")
        if 'metadata' in res:
            metadata = res['metadata']
            print(f"Source: {metadata.get('source', 'Unknown')}")
            print(f"Sub-source: {metadata.get('sub_source', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(test_retrieval())

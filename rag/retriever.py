"""
FAISS Retriever for PDF-Based RAG System

Performs semantic search over PDF chunks using FAISS index.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

# Set environment variables
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import faiss
from sentence_transformers import SentenceTransformer


class FAISSRetriever:
    """Semantic search using FAISS index."""
    
    def __init__(
        self,
        index_path: str = "processed/faiss_index/index.faiss",
        metadata_path: str = "processed/faiss_index/chunk_metadata.json",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize retriever.
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to chunk metadata JSON
            model_name: SentenceTransformer model name
        """
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.model_name = model_name
        
        # Load components
        self.index = self._load_index()
        self.metadata = self._load_metadata()
        self.model = SentenceTransformer(self.model_name)
        
        print(f"✓ Retriever loaded: {self.index.ntotal} vectors")
    
    def _load_index(self) -> faiss.Index:
        """Load FAISS index."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index not found: {self.index_path}")
        
        return faiss.read_index(str(self.index_path))
    
    def _load_metadata(self) -> Dict:
        """Load chunk metadata."""
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {self.metadata_path}")
        
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Retrieve most relevant chunks for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of dicts with chunk_id, text, source, score, metadata
        """
        # Embed query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Build results
        results = []
        for idx, score in zip(indices[0], scores[0]):
            # Get chunk ID from index position
            chunk_id = list(self.metadata.keys())[idx]
            chunk_data = self.metadata[chunk_id]
            
            result = {
                "chunk_id": chunk_id,
                "text": chunk_data["text"],
                "source": chunk_data["source"],
                "score": float(score),
                "char_count": chunk_data.get("char_count", len(chunk_data["text"])),
                "chunk_index": chunk_data.get("chunk_index", 0)
            }
            results.append(result)
        
        return results
    
    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_n: Optional[int] = None
    ) -> List[Dict]:
        """
        Re-rank retrieved chunks (currently identity function).
        
        Can be extended with cross-encoder or other reranking methods.
        
        Args:
            query: Original query
            chunks: List of retrieved chunks
            top_n: Optional number of top results to keep
        
        Returns:
            Re-ranked list of chunks
        """
        # For now, just return as-is (already ranked by FAISS score)
        # TODO: Implement cross-encoder reranking if needed
        
        if top_n:
            return chunks[:top_n]
        return chunks


def main():
    """Test retrieval."""
    retriever = FAISSRetriever()
    
    # Example queries
    queries = [
        "What is the Maillard reaction?",
        "How does temperature affect cooking?",
        "What is umami flavor?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        results = retriever.retrieve(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Source: {result['source']}")
            print(f"   Score: {result['score']:.4f}")
            print(f"   Preview: {result['text'][:150]}...")


if __name__ == "__main__":
    main()

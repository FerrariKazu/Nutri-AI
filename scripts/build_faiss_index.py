"""
FAISS Index Builder for PDF Chunks

Generates embeddings and builds searchable FAISS index.
Uses SentenceTransformer (MiniLM) from working conda environment.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import List, Dict

# Set environment variables BEFORE imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class FAISSIndexBuilder:
    """Build FAISS index from PDF chunks."""
    
    def __init__(
        self,
        chunks_file: str = "processed/chunks/chunks.jsonl",
        output_dir: str = "processed/faiss_index",
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 32
    ):
        self.chunks_file = Path(chunks_file)
        self.output_dir = Path(output_dir)
        self.model_name = model_name
        self.batch_size = batch_size
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Will be loaded
        self.model = None
        self.chunks = []
    
    def load_chunks(self) -> List[Dict]:
        """Load chunks from JSONL file."""
        print(f"Loading chunks from {self.chunks_file}...")
        
        chunks = []
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                chunks.append(chunk)
        
        print(f"  ✓ Loaded {len(chunks)} chunks")
        return chunks
    
    def load_model(self):
        """Load SentenceTransformer model."""
        print(f"\nLoading embedding model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        print(f"  ✓ Model loaded (dimension: {self.model.get_sentence_embedding_dimension()})")
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
        
        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        print(f"\nGenerating embeddings for {len(texts)} chunks...")
        print(f"  Batch size: {self.batch_size}")
        
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=False  # We'll normalize manually
        )
        
        return embeddings
    
    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build FAISS index from embeddings.
        
        Uses IndexFlatIP (Inner Product) after L2 normalization
        for cosine similarity search.
        """
        print(f"\nBuilding FAISS index...")
        
        # Normalize vectors for cosine similarity
        print("  Normalizing vectors...")
        faiss.normalize_L2(embeddings)
        
        # Create index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        
        # Add vectors
        print(f"  Adding {len(embeddings)} vectors...")
        index.add(embeddings)
        
        print(f"  ✓ Index built: {index.ntotal} vectors, {dimension} dimensions")
        
        return index
    
    def save_artifacts(self, index: faiss.Index, embeddings: np.ndarray):
        """Save FAISS index, embeddings, and metadata."""
        print(f"\nSaving artifacts to {self.output_dir}...")
        
        # 1. Save FAISS index
        index_path = self.output_dir / "index.faiss"
        faiss.write_index(index, str(index_path))
        print(f"  ✓ Saved FAISS index: {index_path} ({index_path.stat().st_size / 1024:.1f} KB)")
        
        # 2. Save embeddings (for debugging/reranking)
        embeddings_path = self.output_dir / "embeddings.npy"
        np.save(str(embeddings_path), embeddings)
        print(f"  ✓ Saved embeddings: {embeddings_path} ({embeddings_path.stat().st_size / 1024:.1f} KB)")
        
        # 3. Save chunk metadata
        metadata = {
            chunk['chunk_id']: {
                'source': chunk['source'],
                'text': chunk['text'],
                'char_count': chunk['char_count'],
                'chunk_index': chunk['chunk_index']
            }
            for chunk in self.chunks
        }
        
        metadata_path = self.output_dir / "chunk_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved metadata: {metadata_path} ({metadata_path.stat().st_size / 1024:.1f} KB)")
    
    def build(self):
        """Main build pipeline."""
        print("="*60)
        print("BUILDING FAISS INDEX FOR PDF CHUNKS")
        print("="*60)
        
        # Load chunks
        self.chunks = self.load_chunks()
        
        # Extract texts
        texts = [chunk['text'] for chunk in self.chunks]
        
        # Load model
        self.load_model()
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Build FAISS index
        index = self.build_index(embeddings)
        
        # Save everything
        self.save_artifacts(index, embeddings)
        
        # Final stats
        print("\n" + "="*60)
        print("BUILD COMPLETE")
        print("="*60)
        print(f"Total chunks indexed: {len(self.chunks)}")
        print(f"Embedding dimension: {embeddings.shape[1]}")
        print(f"Index type: IndexFlatIP (cosine similarity)")
        print(f"Output directory: {self.output_dir}")
        print("="*60)


def main():
    builder = FAISSIndexBuilder(
        chunks_file="processed/chunks/chunks.jsonl",
        output_dir="processed/faiss_index",
        model_name="all-MiniLM-L6-v2",
        batch_size=32
    )
    builder.build()


if __name__ == "__main__":
    main()

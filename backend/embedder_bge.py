"""
BGE-M3 Embedding Engine
Wrapper for FlagEmbedding BGE-M3 model
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Union
from FlagEmbedding import BGEM3FlagModel

logger = logging.getLogger(__name__)


class EmbedderBGE:
    """BGE-M3 embedding wrapper with caching"""
    
    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True, cache_file: str = None):
        """
        Initialize BGE-M3 embedder
        
        Args:
            model_name: HuggingFace model name or local path
            use_fp16: Use FP16 for GPU inference
            cache_file: Optional path to embedding cache JSON. If None, caching is disabled.
        """
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.cache_file = Path(cache_file) if cache_file else None
        self.cache = {}
        self.caching_enabled = self.cache_file is not None
        
        # Load cache if exists and enabled
        if self.caching_enabled and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached embeddings")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        # Initialize model
        logger.info(f"Loading BGE-M3 model: {model_name}")
        self.model = BGEM3FlagModel(
            model_name,
            use_fp16=use_fp16
        )
        logger.info("✅ BGE-M3 model loaded")
    
    def embed_text(self, text: str, max_length: int = 8192) -> np.ndarray:
        """Generate embedding for a single text"""
        # Check cache
        if self.caching_enabled and text in self.cache:
            return np.array(self.cache[text], dtype=np.float32)
        
        # Generate embedding
        result = self.model.encode(
            [text],
            batch_size=1,
            max_length=max_length
        )
        
        # Extract dense vector
        embedding = result['dense_vecs'][0]
        
        # Normalize (L2 norm)
        embedding = embedding / np.linalg.norm(embedding)
        
        # Cache result
        if self.caching_enabled:
            self.cache[text] = embedding.tolist()
        
        return embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 64, max_length: int = 8192) -> np.ndarray:
        """Generate embeddings for multiple texts in batches"""
        if not texts:
            return np.array([])
            
        # Check which texts need embedding
        uncached_texts = []
        uncached_indices = []
        
        # Pre-allocate result array
        results = np.zeros((len(texts), 1024), dtype=np.float32)
        
        for i, text in enumerate(texts):
            if self.caching_enabled and text in self.cache:
                results[i] = np.array(self.cache[text], dtype=np.float32)
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Embed uncached texts
        if uncached_texts:
            logger.info(f"Generating embeddings for {len(uncached_texts)} texts (batch_size={batch_size}, max_length={max_length})")
            embeddings = self.model.encode(
                uncached_texts,
                batch_size=batch_size,
                max_length=max_length
            )['dense_vecs']
            
            # Normalize
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            # Update results and cache
            for idx, embedding in zip(uncached_indices, embeddings):
                results[idx] = embedding
                if self.caching_enabled:
                    self.cache[texts[idx]] = embedding.tolist()
        
        return results.astype('float32')

    def compute_score(self, pairs: List[List[str]], batch_size: int = 64, max_length: int = 8192) -> List[float]:
        """
        Compute relevance scores for pairs of (query, document)
        """
        return self.model.compute_score(
            pairs,
            batch_size=batch_size,
            max_length=max_length
        )
    
    def save_cache(self):
        """Save embedding cache to disk"""
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                # Atomic write
                temp_file = self.cache_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.cache, f)
                temp_file.replace(self.cache_file)
                logger.info(f"Saved {len(self.cache)} cached embeddings")
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")
    
    def __del__(self):
        """Save cache on destruction"""
        try:
            self.save_cache()
        except:
            pass


if __name__ == "__main__":
    # Test the embedder
    print("Testing BGE-M3 Embedder...")
    embedder = EmbedderBGE()
    text = "chicken and potatoes dinner"
    embedding = embedder.embed_text(text, max_length=1024)
    print(f"✅ Test complete: shape={embedding.shape}")

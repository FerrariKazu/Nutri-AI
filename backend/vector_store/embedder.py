"""
Embedding model wrapper using sentence-transformers.

Provides text embedding functionality for semantic search.
"""

from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Global embedding model
_model: SentenceTransformer = None


def load_model(model_name: str = "BAAI/bge-m3", force: bool = False) -> None:
    """
    Load the sentence transformer model with GPU support.
    Uses a singleton pattern to avoid redundant loading.
    
    Args:
        model_name: HuggingFace model name
        force: Force reload even if already loaded
    """
    global _model
    
    if _model is not None and not force:
        logger.info(f"Embedding model already loaded: {_model.model_card_data.model_name_or_path}")
        return
    
    logger.info(f"Loading embedding model: {model_name}...")
    
    # Force CPU for stability on 8GB VRAM cards
    device = "cpu"
    logger.info("⚠️  GPU offloading disabled for embedder (Resource Guard). Using CPU.")
    
    # Load model with device
    _model = SentenceTransformer(model_name, device=device)
    logger.info(f"✅ Embedding model loaded on {device.upper()}")


def embed_text(text: str) -> np.ndarray:
    """
    Generate embedding for a single text.
    
    Args:
        text: Input text
        
    Returns:
        Embedding vector as numpy array
    """
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    
    return _model.encode(text, convert_to_numpy=True)


def embed_batch(texts: List[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
    """
    Generate embeddings for multiple texts.
    
    Args:
        texts: List of input texts
        batch_size: Batch size for encoding
        show_progress: Show progress bar
        
    Returns:
        Matrix of embeddings (n_texts x embedding_dim)
    """
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    
    return _model.encode(
        texts,
        convert_to_numpy=True,
        batch_size=batch_size,
        show_progress_bar=show_progress
    )


def get_embedding_dimension() -> int:
    """
    Get the dimension of embeddings produced by the model.
    
    Returns:
        Embedding dimension
    """
    if _model is None:
        raise RuntimeError("Embedding model not loaded.")
    
    return _model.get_sentence_embedding_dimension()

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


def load_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
    """
    Load the sentence transformer model with GPU support.
    
    Args:
        model_name: HuggingFace model name
    """
    global _model
    
    if _model is not None:
        logger.info("Embedding model already loaded")
        return
    
    logger.info(f"Loading embedding model: {model_name}...")
    
    # Detect GPU
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"🚀 GPU detected: {gpu_name}")
            logger.info(f"   CUDA version: {torch.version.cuda}")
        else:
            logger.info("⚠️  No GPU detected, using CPU")
    except ImportError:
        device = "cpu"
        logger.warning("PyTorch not found, defaulting to CPU")
    
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

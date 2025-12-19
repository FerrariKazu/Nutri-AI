"""
Food embedder using sentence-transformers with CUDA support.

Optimized for RTX 4060 GPU.
"""

import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Global model instance
_model: Optional[SentenceTransformer] = None


def load_model(device: Optional[str] = None) -> SentenceTransformer:
    """
    Load sentence transformer model with GPU support.
    
    Args:
        device: Device to use ('cuda', 'cpu', or None for auto-detect)
        
    Returns:
        Loaded SentenceTransformer model
    """
    global _model
    
    if _model is not None:
        logger.info("Embedder model already loaded")
        return _model
    
    # Auto-detect device if not specified
    if device is None:
        if torch.cuda.is_available():
            device = 'cuda'
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA available - using GPU: {gpu_name}")
        else:
            device = 'cpu'
            logger.info("CUDA not available - using CPU")
    
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    _model = SentenceTransformer(MODEL_NAME, device=device)
    logger.info(f"✅ Model loaded on {device} | Embedding dimension: {EMBEDDING_DIM}")
    
    return _model


def prepare_recipe_text(food_item: 'UnifiedFood') -> str:
    """
    Prepare food item text for embedding.
    
    Combines name, description, nutrients, and compounds into searchable text.
    
    Args:
        food_item: UnifiedFood object
        
    Returns:
        Combined text string
    """
    parts = [
        food_item.name,
        food_item.normalized_name,
    ]
    
    # Add synonyms (limit to avoid too long)
    if food_item.synonyms:
        parts.append(" ".join(food_item.synonyms[:5]))
    
    # Add category
    if food_item.category:
        parts.append(food_item.category)
    
    # Add description (truncated)
    if food_item.description:
        parts.append(food_item.description[:400])
    
    # Add top nutrients as context
    if food_item.nutrients:
        nutrient_text = " ".join([
            f"{k.replace('_', ' ')}:{v:.1f}"
            for k, v in list(food_item.nutrients.items())[:6]
        ])
        parts.append(nutrient_text)
    
    # Add compound names if available
    if food_item.compounds:
        if isinstance(food_item.compounds, dict):
            compound_names = [
                str(v.get('name', ''))
                for v in food_item.compounds.values()
            ]
            parts.extend(compound_names[:3])
    
    # Combine and truncate to ~500 tokens (rough estimate: 1 token ≈ 4 chars)
    combined = " ".join(filter(None, parts))
    return combined[:2000]


def embed_texts(texts: List[str], batch_size: int = 64, show_progress: bool = False) -> np.ndarray:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of text strings
        batch_size: Batch size for encoding (optimized for RTX 4060)
        show_progress: Show progress bar
        
    Returns:
        Numpy array of shape (len(texts), 384)
    """
    if _model is None:
        load_model()
    
    logger.info(f"Embedding {len(texts)} texts with batch_size={batch_size}")
    
    embeddings = _model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True  # L2 normalization for cosine similarity
    )
    
    logger.info(f"Generated embeddings shape: {embeddings.shape}")
    return embeddings


def embed_single(text: str) -> np.ndarray:
    """Embed a single text string."""
    if _model is None:
        load_model()
    
    embedding = _model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return embedding


def get_embedding_dim() -> int:
    """Get embedding dimension."""
    return EMBEDDING_DIM

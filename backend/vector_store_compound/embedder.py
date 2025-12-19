"""
Compound embedder using sentence-transformers with CUDA support.

Optimized for RTX 4060 GPU. Embeddings for chemical compounds.
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
        logger.info("Compound embedder already loaded")
        return _model
    
    # Auto-detect device
    if device is None:
        if torch.cuda.is_available():
            device = 'cuda'
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA available - using GPU: {gpu_name}")
        else:
            device = 'cpu'
            logger.info("CUDA not available - using CPU")
    
    logger.info(f"Loading compound embedding model: {MODEL_NAME}")
    _model = SentenceTransformer(MODEL_NAME, device=device)
    logger.info(f"✅ Compound model loaded on {device} | Embedding dimension: {EMBEDDING_DIM}")
    
    return _model


def prepare_compound_text(compound_item) -> str:
    """
    Prepare compound item text for embedding.
    
    Combines name, synonyms, properties, toxicity into searchable text.
    
    Args:
        compound_item: UnifiedFood or CompoundRecord object
        
    Returns:
        Combined text string
    """
    parts = [
        compound_item.name,
        compound_item.normalized_name,
    ]
    
    # Add synonyms
    if hasattr(compound_item, 'synonyms') and compound_item.synonyms:
        parts.append(" ".join(compound_item.synonyms[:5]))
    
    # Add description
    if hasattr(compound_item, 'description') and compound_item.description:
        parts.append(compound_item.description[:400])
    
    # Add molecular formula and properties (for CompoundRecord)
    if hasattr(compound_item, 'molecular_formula') and compound_item.molecular_formula:
        parts.append(f"formula: {compound_item.molecular_formula}")
    
    if hasattr(compound_item, 'molecular_weight') and compound_item.molecular_weight:
        parts.append(f"MW: {compound_item.molecular_weight:.2f}")
    
    if hasattr(compound_item, 'smiles') and compound_item.smiles:
        parts.append(f"SMILES: {compound_item.smiles}")
    
    # Add computed properties
    if hasattr(compound_item, 'xlogp3') and compound_item.xlogp3 is not None:
        parts.append(f"logP: {compound_item.xlogp3:.2f}")
    
    # Add toxicity info
    if hasattr(compound_item, 'toxicity') and compound_item.toxicity:
        tox_text = " ".join([
            f"{k}: {v}"
            for k, v in list(compound_item.toxicity.items())[:3]
        ])
        parts.append(tox_text)
    
    # Add compound names from compounds dict (for UnifiedFood)
    if hasattr(compound_item, 'compounds') and compound_item.compounds:
        if isinstance(compound_item.compounds, dict):
            compound_names = [
                str(v.get('name', ''))
                for v in compound_item.compounds.values()
            ]
            parts.extend(compound_names[:5])
    
    # Combine and truncate
    combined = " ".join(filter(None, parts))
    return combined[:2000]


def embed_texts(texts: List[str], batch_size: int = 64, show_progress: bool = False) -> np.ndarray:
    """
    Generate embeddings for compound texts.
    
    Args:
        texts: List of compound text strings
        batch_size: Batch size for encoding
        show_progress: Show progress bar
        
    Returns:
        Numpy array of shape (len(texts), 384)
    """
    if _model is None:
        load_model()
    
    logger.info(f"Embedding {len(texts)} compound texts with batch_size={batch_size}")
    
    embeddings = _model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True  # L2 normalization
    )
    
    logger.info(f"Generated compound embeddings shape: {embeddings.shape}")
    return embeddings


def embed_single(text: str) -> np.ndarray:
    """Embed a single compound text string."""
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

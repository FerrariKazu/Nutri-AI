"""
FAISS index builder for food vector store.
"""

import faiss
import json
import numpy as np
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
import logging

from backend.nutrition_loader.schema import UnifiedFood
from . import embedder

logger = logging.getLogger(__name__)

# Default paths
INDEX_DIR = Path("backend/vector_store_food")
INDEX_PATH = INDEX_DIR / "index.bin"
IDS_PATH = INDEX_DIR / "ids.json"
META_PATH = INDEX_DIR / "meta.json"


def build_index(items: List[UnifiedFood], out_dir: str = None, batch_size: int = 64) -> None:
    """
    Build FAISS index from UnifiedFood items.
    
    Args:
        items: List of UnifiedFood objects
        out_dir: Output directory (default: backend/vector_store_food)
        batch_size: Batch size for embedding
    """
    if out_dir:
        output_dir = Path(out_dir)
    else:
        output_dir = INDEX_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Building food index from {len(items)} items...")
    
    # Load embedder
    embedder.load_model()
    
    # Prepare texts
    logger.info("Preparing texts...")
    texts = []
    uuids = []
    metadata = {}
    
    for item in tqdm(items, desc="Preparing"):
        text = embedder.prepare_recipe_text(item)
        texts.append(text)
        uuids.append(str(item.uuid))
        
        # Store metadata for quick retrieval
        metadata[str(item.uuid)] = item.to_display_dict()
    
    # Generate embeddings
    logger.info(f"Generating embeddings (batch_size={batch_size})...")
    embeddings = embedder.embed_texts(texts, batch_size=batch_size, show_progress=True)
    
    # Build FAISS index (IndexFlatIP for cosine via normalized vectors)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product (cosine for normalized vectors)
    
    logger.info("Adding vectors to FAISS index...")
    index.add(embeddings.astype('float32'))
    
    logger.info(f"FAISS index built: {index.ntotal} vectors, {dim} dimensions")
    
    # Save index
    index_tmp = output_dir / "index.tmp"
    faiss.write_index(index, str(index_tmp))
    index_tmp.rename(output_dir / "index.bin")  # Atomic rename
    logger.info(f"Saved index to {output_dir / 'index.bin'}")
    
    # Save IDs
    with open(output_dir / "ids.json", 'w') as f:
        json.dump(uuids, f)
    logger.info(f"Saved IDs to {output_dir / 'ids.json'}")
    
    # Save metadata
    with open(output_dir / "meta.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved metadata to {output_dir / 'meta.json'}")
    
    logger.info("✅ Food index build complete!")


def index_exists(out_dir: str = None) -> bool:
    """Check if index files exist."""
    if out_dir:
        output_dir = Path(out_dir)
    else:
        output_dir = INDEX_DIR
    
    return (
        (output_dir / "index.bin").exists() and
        (output_dir / "ids.json").exists()
    )


def load_index(out_dir: str = None) -> faiss.Index:
    """Load FAISS index from disk."""
    if out_dir:
        output_dir = Path(out_dir)
    else:
        output_dir = INDEX_DIR
    
    index_path = output_dir / "index.bin"
    
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}")
    
    logger.info(f"Loading index from {index_path}")
    index = faiss.read_index(str(index_path))
    logger.info(f"Loaded index with {index.ntotal} vectors")
    
    return index

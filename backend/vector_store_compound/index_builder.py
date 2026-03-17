"""
FAISS index builder for compound vector store.
"""

import faiss
import json
import numpy as np
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
import logging

from backend.retriever.embedder_singleton import EmbedderSingleton

logger = logging.getLogger(__name__)

# Default paths
INDEX_DIR = Path("backend/vector_store_compound")
INDEX_PATH = INDEX_DIR / "index.bin"
IDS_PATH = INDEX_DIR / "ids.json"
META_PATH = INDEX_DIR / "meta.json"


def build_index(items: List, out_dir: str = None, batch_size: int = 64) -> None:
    """
    Build FAISS index from compound items (UnifiedFood or CompoundRecord).
    
    Args:
        items: List of items with compound data
        out_dir: Output directory
        batch_size: Batch size for embedding
    """
    if out_dir:
        output_dir = Path(out_dir)
    else:
        output_dir = INDEX_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Building compound index from {len(items)} items...")
    
    # Load embedder via singleton
    model = EmbedderSingleton.get()
    
    # Prepare texts
    logger.info("Preparing compound texts...")
    texts = []
    uuids = []
    metadata = {}
    
    for item in tqdm(items, desc="Preparing"):
        # Assuming embedder module had these helper functions
        # If not, I may need to adjust import or keep 'from . import embedder' for helpers
        from . import embedder as embedder_utils
        text = embedder_utils.prepare_compound_text(item)
        texts.append(text)
        uuids.append(str(item.uuid))
        
        # Store metadata
        if hasattr(item, 'to_display_dict'):
            metadata[str(item.uuid)] = item.to_display_dict()
        else:
            metadata[str(item.uuid)] = item.dict()
    
    # Generate embeddings
    logger.info(f"Generating compound embeddings (batch_size={batch_size})...")
    embeddings = model.embed_texts(texts, batch_size=batch_size)
    embeddings = embeddings.astype('float32') # Ensure float32 for FAISS
    
    # Build FAISS compressed index (IndexIVFPQ)
    dim = embeddings.shape[1]
    nlist = 4096
    m = 64
    bits = 8
    
    logger.info(f"Building IVFPQ index: nlist={nlist}, m={m}, bits={bits}")
    
    # 1. Training subset selection (Min 40x nlist = 163,840)
    train_size = min(len(embeddings), 200000)
    logger.info(f"Sampling {train_size} vectors for training...")
    train_indices = np.random.choice(len(embeddings), train_size, replace=False)
    train_vectors = embeddings[train_indices]
    
    # 2. Setup Quantizer and IVFPQ
    quantizer = faiss.IndexFlatIP(dim)
    index = faiss.IndexIVFPQ(quantizer, dim, nlist, m, bits)
    
    # 3. Train
    logger.info("Training IVFPQ quantizer...")
    index.train(train_vectors)
    
    # 4. Add all vectors
    logger.info("Adding vectors to FAISS compound index...")
    index.add(embeddings)
    
    # 5. Set nprobe for recall safety
    index.nprobe = 16
    
    logger.info(f"Compound index built: {index.ntotal} vectors, {dim} dimensions (IVFPQ)")
    
    # Save index (atomic)
    index_tmp = output_dir / "index.tmp"
    faiss.write_index(index, str(index_tmp))
    index_tmp.rename(output_dir / "index.bin")
    logger.info(f"Saved compressed index to {output_dir / 'index.bin'}")
    
    # Save IDs
    with open(output_dir / "ids.json", 'w') as f:
        json.dump(uuids, f)
    
    # Save metadata
    with open(output_dir / "meta.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("✅ Compound index build complete!")


def index_exists(out_dir: str = None) -> bool:
    """Check if compound index exists."""
    if out_dir:
        output_dir = Path(out_dir)
    else:
        output_dir = INDEX_DIR
    
    return (output_dir / "index.bin").exists() and (output_dir / "ids.json").exists()


def load_index(out_dir: str = None) -> faiss.Index:
    """Load compound FAISS index."""
    if out_dir:
        output_dir = Path(out_dir)
    else:
        output_dir = INDEX_DIR
    
    index_path = output_dir / "index.bin"
    
    if not index_path.exists():
        raise FileNotFoundError(f"Compound index not found: {index_path}")
    
    logger.info(f"Loading compound index from {index_path}")
    index = faiss.read_index(str(index_path))
    logger.info(f"Loaded compound index with {index.ntotal} vectors")
    
    return index

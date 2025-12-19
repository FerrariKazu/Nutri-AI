"""
PANDAS-FREE Reindexing Script

Uses the data we already loaded with load_simple.py
Builds FAISS indices without importing pandas.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Set threading environment variables BEFORE any imports
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

print("DEBUG: Script started", flush=True)
print("DEBUG: Environment variables set for threading", flush=True)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

print("DEBUG: Importing numpy...", flush=True)
import numpy as np
print(f"DEBUG: Numpy {np.__version__} imported", flush=True)

print("DEBUG: Importing torch...", flush=True)
import torch
print(f"DEBUG: Torch {torch.__version__} imported", flush=True)

print("DEBUG: Importing faiss...", flush=True)
import faiss
print("DEBUG: Faiss imported", flush=True)

print("DEBUG: Importing sentence_transformers...", flush=True)
from sentence_transformers import SentenceTransformer
print("DEBUG: Sentence Transformers imported", flush=True)

from tqdm import tqdm


def main():
    logger.info("=== PANDAS-FREE RAG System Reindexing ===")
    
    # Load the data we already have from load_simple.py
    data_file = Path('processed/foods_simple.json')
    
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        logger.error("Please run: python scripts/load_simple.py first")
        return
    
    logger.info(f"Loading data from {data_file}...")
    with open(data_file, 'r', encoding='utf-8') as f:
        foods = json.load(f)
    
    logger.info(f"Loaded {len(foods)} food items")
    
    # Build food index
    logger.info("\nBuilding food FAISS index...")
    build_food_index(foods)
    
    logger.info("\n=== Reindexing Complete ===")
    logger.info(f"Processed {len(foods)} food items")
    logger.info("FAISS indices created successfully")


def build_food_index(foods):
    """Build FAISS index without pandas dependency."""
    
    logger.info("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Prepare texts
    texts = []
    ids = []
    metadata = []
    
    for food in tqdm(foods, desc="Preparing texts"):
        text = f"{food['name']} {food.get('source', '')}"
        texts.append(text)
        ids.append(food['uuid'])
        metadata.append({
            'uuid': food['uuid'],
            'name': food['name'],
            'source': food.get('source', 'unknown')
        })
    
    # Generate embeddings
    logger.info(f"Generating embeddings for {len(texts)} items...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Build index
    logger.info("Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    # Save
    out_dir = Path('processed/faiss_food')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    faiss.write_index(index, str(out_dir / 'index.faiss'))
    
    with open(out_dir / 'ids.json', 'w') as f:
        json.dump(ids, f)
    
    with open(out_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✅ Saved FAISS index to {out_dir}")
    logger.info(f"   - {len(ids)} vectors")
    logger.info(f"   - {dimension} dimensions")


if __name__ == "__main__":
    main()

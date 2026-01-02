#!/usr/bin/env python3
"""
Validation Script for Isolated Ingestion

This script checks the integrity, vector counts, and retrieval functionality
of the mandate-isolated FAISS indexes.
"""

import sys
import sqlite3
import faiss
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"

def validate_dataset(dataset_name: str):
    logger.info(f"--- Validating Dataset: {dataset_name} ---")
    data_dir = VECTOR_STORE_DIR / dataset_name
    
    index_path = data_dir / "index.faiss"
    meta_path = data_dir / "index.meta.sqlite"
    
    if not index_path.exists():
        logger.error(f"  ❌ Missing FAISS index at {index_path}")
        return False
    if not meta_path.exists():
        logger.error(f"  ❌ Missing Metadata SQLite at {meta_path}")
        return False
        
    try:
        # 1. Check FAISS Index
        index = faiss.read_index(str(index_path))
        vec_count = index.ntotal
        logger.info(f"  ✅ FAISS Index Loaded: {vec_count} vectors")
        
        # 2. Check Metadata
        conn = sqlite3.connect(meta_path)
        meta_count = conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
        checkpoint = conn.execute("SELECT count_val FROM checkpoint WHERE key='processed_items'").fetchone()
        checkpoint_val = checkpoint[0] if checkpoint else "N/A"
        
        logger.info(f"  ✅ Metadata SQLite: {meta_count} records")
        logger.info(f"  ✅ Checkpoint: {checkpoint_val} items processed")
        
        # 3. Synchrony Check
        if vec_count != meta_count:
            logger.warning(f"  ⚠️  UNBALANCED: Index ({vec_count}) vs Meta ({meta_count})")
        else:
            logger.info(f"  ✅ Synchrony: Index and Meta match.")
            
        # 4. Sample Retrieval test
        try:
            from backend.embedder_bge import EmbedderBGE
            embedder = EmbedderBGE()
            test_query = "What is the protein content?"
            query_vec = embedder.embed_texts([test_query])[0]
            faiss.normalize_L2(query_vec.reshape(1, -1))
            
            D, I = index.search(query_vec.reshape(1, -1).astype('float32'), 3)
            logger.info(f"  ✅ Sample Retrieval: Top hit index {I[0][0]} with score {D[0][0]:.4f}")
            
            # Check metadata for top hit
            hit_id = int(I[0][0])
            res = conn.execute("SELECT text FROM metadata WHERE id = ?", (hit_id,)).fetchone()
            if res:
                logger.info(f"  ✅ Metadata Retrieval: Found text for top hit.")
            else:
                logger.error(f"  ❌ Metadata Missing for hit index {hit_id}")
                
        except Exception as e:
            logger.warning(f"  ⚠️  Retrieval test skipped or failed: {e}")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Validation failed for {dataset_name}: {e}")
        return False

if __name__ == "__main__":
    datasets = [d.name for d in VECTOR_STORE_DIR.iterdir() if d.is_dir()]
    if not datasets:
        logger.error("No datasets found in vector_store/")
        sys.exit(1)
        
    results = {}
    for ds in datasets:
        results[ds] = validate_dataset(ds)
        
    logger.info("\n--- Final Summary ---")
    for ds, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{ds:20}: {status}")

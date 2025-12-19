
import os
import shutil
import sqlite3
import json
import logging
import time
import hnswlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AtomicHNSWIndexer:
    def __init__(self, index_dir: str, dim: int = 1024, max_elements: int = 5_000_000):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self.max_elements = max_elements
        
        self.index_path = self.index_dir / "index.bin"
        self.meta_db_path = self.index_dir / "metadata.db"
        
        # Init Index
        self.index = hnswlib.Index(space='cosine', dim=dim)
        if self.index_path.exists():
            logger.info(f"Loading HNSW index from {self.index_path}")
            self.index.load_index(str(self.index_path), max_elements=max_elements)
        else:
            logger.info(f"Initializing new HNSW index")
            self.index.init_index(max_elements=max_elements, ef_construction=128, M=32)
            
        # Init Metadata DB
        self._init_db()
        self.current_count = self.index.element_count
        logger.info(f"Indexer ready. Count: {self.current_count}")

    def _init_db(self):
        self.conn = sqlite3.connect(self.meta_db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vec_meta (
                idx_id INTEGER PRIMARY KEY,
                doc_id TEXT,
                dataset TEXT,
                source_path TEXT,
                text_content TEXT,
                metadata_json TEXT,
                timestamp REAL
            )
        """)
        self.conn.commit()

    def add_batch(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        if len(vectors) == 0:
            return
            
        n = len(vectors)
        start_id = self.current_count
        ids = np.arange(start_id, start_id + n)
        
        # Add to HNSW (in-memory update)
        self.index.add_items(vectors, ids)
        
        # Prepare DB rows
        rows = []
        now = time.time()
        for i, meta in enumerate(metadata):
            idx_id = int(ids[i])
            doc_id = meta.get('doc_id', f"doc_{idx_id}")
            
            # Extract content if available
            text = meta.get('text', meta.get('content', ''))
            
            # Serialize full metadata to JSON for retrieval
            meta_json = json.dumps(meta)
            
            rows.append((
                idx_id,
                doc_id,
                meta.get('dataset', 'unknown'),
                meta.get('source_path', ''),
                text,
                meta_json,
                now
            ))
            
        self.conn.executemany("INSERT INTO vec_meta VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        self.current_count += n

    def commit(self, checkpoint_data: Dict[str, Any], checkpoint_file: str):
        """
        Atomic commit:
        1. Commit DB transaction
        2. Save Index to temp file -> rename
        3. Save Checkpoint to temp file -> rename
        """
        logger.info("Committing changes...")
        t0 = time.time()
        
        # 1. DB Commit
        self.conn.commit()
        
        # 2. Index Save (Atomic)
        temp_idx = self.index_path.with_suffix(".bin.tmp")
        self.index.save_index(str(temp_idx))
        os.replace(temp_idx, self.index_path)
        
        # 3. Checkpoint Save (Atomic)
        chk_path = Path(checkpoint_file)
        chk_path.parent.mkdir(parents=True, exist_ok=True)
        temp_chk = chk_path.with_suffix(".tmp")
        with open(temp_chk, 'w') as f:
            json.dump(checkpoint_data, f)
        os.replace(temp_chk, chk_path)
        
        logger.info(f"Commit successful in {time.time()-t0:.2f}s")
        
    def close(self):
        self.conn.close()

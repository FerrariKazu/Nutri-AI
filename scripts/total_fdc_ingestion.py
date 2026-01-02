#!/usr/bin/env python3
"""
Total FDC Ingestion Script (100% Coverage)

This script implements the HARD REQUIREMENT for TOTAL data ingestion.
It joins all FDC tables (food, branded_food, nutrients, portions) 
to create a comprehensive retrievable document for EVERY available record.

Architecture:
1. Load CSVs into a local SQLite database for efficient non-RAM joining.
2. Aggregate all nutrients and portions per food item.
3. Stream records from SQLite, build complete text, and embed using BGE-M3.
4. Save FAISS index and a SQLite metadata store (to handle 2M+ records).
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import faiss
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = PROJECT_ROOT / "data_sources" / "nutrition"
BRANDED_DIR = DATA_DIR / "branded_foods"
FOUNDATION_DIR = DATA_DIR / "foundation_foods"
TEMP_DB_PATH = PROJECT_ROOT / "backend" / "indexes" / "fdc_build.db"
FINAL_INDEX_PATH = PROJECT_ROOT / "backend" / "indexes" / "nutrition.faiss"
FINAL_META_PATH = PROJECT_ROOT / "backend" / "indexes" / "nutrition.meta.sqlite"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
BATCH_SIZE = 128
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# ============================================================================
# Utils
# ============================================================================

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at a boundary
        if end < len(text):
            last_sep = max(chunk.rfind('; '), chunk.rfind(' | '))
            if last_sep > chunk_size // 2:
                chunk = chunk[:last_sep + 3]
                end = start + last_sep + 3
        
        chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
        start = end - overlap
    return chunks

# ============================================================================
# Step 1: Load CSVs into SQLite
# ============================================================================

def load_csv_to_sqlite(conn: sqlite3.Connection):
    """Load FDC CSVs into SQLite tables."""
    logger.info("Loading FDC CSVs into SQLite for joining...")
    
    # FDC has multiple folders (Branded, Foundation, etc.)
    # We load everything into the same tables.
    table_map = {
        "food.csv": "food",
        "branded_food.csv": "branded_food",
        "food_nutrient.csv": "food_nutrient",
        "nutrient.csv": "nutrient",
        "food_portion.csv": "food_portion",
        "foundation_food.csv": "foundation_food",
    }
    
    found_tables = set()
    
    for subdir in [BRANDED_DIR, FOUNDATION_DIR]:
        if not subdir.exists(): continue
        logger.info(f"  Scanning {subdir.name}...")
        for csv_path in subdir.glob("*.csv"):
            table_name = table_map.get(csv_path.name)
            if not table_name: continue
            
            logger.info(f"    Importing {csv_path.name} into {table_name}...")
            # Use chunksize to avoid OOM
            for chunk in pd.read_csv(csv_path, chunksize=100000, low_memory=False):
                chunk.to_sql(table_name, conn, if_exists='append', index=False)
            found_tables.add(table_name)
            
    # Create indexes only for existing tables
    if 'food' in found_tables: conn.execute("CREATE INDEX IF NOT EXISTS idx_food_fdc ON food(fdc_id)")
    if 'branded_food' in found_tables: conn.execute("CREATE INDEX IF NOT EXISTS idx_branded_fdc ON branded_food(fdc_id)")
    if 'food_nutrient' in found_tables: conn.execute("CREATE INDEX IF NOT EXISTS idx_nutri_fdc ON food_nutrient(fdc_id)")
    if 'food_portion' in found_tables: conn.execute("CREATE INDEX IF NOT EXISTS idx_portion_fdc ON food_portion(fdc_id)")
    logger.info("  FDC Metadata indexes created.")

def load_opennutrition(conn: sqlite3.Connection):
    """Load OpenNutrition foods into SQLite."""
    path = DATA_DIR / "opennutrition_foods.tsv"
    if not path.exists():
        logger.warning(f"OpenNutrition source not found: {path}")
        return
        
    logger.info(f"Importing {path.name}...")
    # Use chunksize
    for chunk in pd.read_csv(path, sep='\t', chunksize=50000):
        # Map IDs to strings as they are in OpenNutrition
        chunk.to_sql('opennutrition', conn, if_exists='append', index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_on_id ON opennutrition(id)")
    logger.info("  OpenNutrition imported.")

# ============================================================================
# Step 2: Build Complete Ingestion SQL
# ============================================================================

def aggregate_and_stream(conn: sqlite3.Connection):
    """
    Stream aggregated records from SQLite.
    Each record joins food + branded_info + all_nutrients.
    """
    logger.info("Aggregating FDC records for embedding...")
    
    # Query to get food + branded info
    # We will fetch nutrients separately or join them if SQLite can handle it.
    # Joining 20M rows in a GROUP_CONCAT might be slow.
    # We'll fetch in 100k batches and fill nutrients via a second query for speed.
    
    main_query = """
    SELECT 
        f.fdc_id, 
        f.description,
        b.brand_owner,
        b.brand_name,
        b.ingredients,
        b.branded_food_category,
        b.serving_size,
        b.serving_size_unit
    FROM food f
    LEFT JOIN branded_food b ON f.fdc_id = b.fdc_id
    """
    
    cursor = conn.cursor()
    cursor.execute(main_query)
    
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
            
        fdc_ids = [r[0] for r in rows]
        # Fetch nutrients for these 1000 items
        nutri_query = f"""
        SELECT fn.fdc_id, n.name, fn.amount, n.unit_name
        FROM food_nutrient fn
        JOIN nutrient n ON fn.nutrient_id = n.id
        WHERE fn.fdc_id IN ({','.join(['?']*len(fdc_ids))})
        """
        nutri_cursor = conn.cursor()
        nutri_cursor.execute(nutri_query, fdc_ids)
        
        nutri_map = {}
        for fid, name, amt, unit in nutri_cursor.fetchall():
            if fid not in nutri_map: nutri_map[fid] = []
            nutri_map[fid].append(f"{name}: {amt}{unit}")
            
        for row in rows:
            fid, desc, owner, brand, ingredients, category, s_size, s_unit = row
            
            # Build complete text
            text_parts = [f"Food: {desc}"]
            if brand or owner:
                text_parts.append(f"Brand: {brand or owner}")
            if category:
                text_parts.append(f"Category: {category}")
            if ingredients:
                text_parts.append(f"Ingredients: {ingredients}")
            if s_size:
                text_parts.append(f"Serving: {s_size} {s_unit}")
                
            nutris = nutri_map.get(fid, [])
            if nutris:
                text_parts.append("Nutrients: " + "; ".join(nutris))
                
            full_text = " | ".join(text_parts)
            
            chunks = chunk_text(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
            
            for chunk_idx, chunk_text_val in enumerate(chunks):
                yield {
                    'id': fid,
                    'text': chunk_text_val,
                    'metadata': {
                        'fdc_id': fid,
                        'description': desc,
                        'brand': brand or owner,
                        'category': category,
                        'chunk': chunk_idx,
                        'total_chunks': len(chunks),
                        'source': 'fdc'
                    }
                }
                
    # --- OpenNutrition Stream ---
    logger.info("Streaming OpenNutrition records...")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, nutrition_100g FROM opennutrition")
    
    while True:
        rows = cursor.fetchmany(1000)
        if not rows: break
        
        for fid, name, desc, nutri_json in rows:
            text_parts = [f"Food: {name}"]
            if desc: text_parts.append(f"Description: {desc}")
            if nutri_json:
                try:
                    nutris = json.loads(nutri_json)
                    nutri_str = "; ".join([f"{k}: {v}" for k, v in nutris.items()])
                    text_parts.append(f"Nutrients: {nutri_str}")
                except:
                    pass
            
            full_text = " | ".join(text_parts)
            chunks = chunk_text(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
            for i, chunk in enumerate(chunks):
                yield {
                    'id': fid,
                    'text': chunk,
                    'metadata': {
                        'on_id': fid,
                        'name': name,
                        'chunk': i,
                        'source': 'opennutrition'
                    }
                }

# ============================================================================
# Step 3: Final Indexing & Metadata
# ============================================================================

def perform_ingestion():
    """Main ingestion pipeline."""
    start_time = time.time()
    
    # 0. Prep
    PROJECT_ROOT.joinpath("backend/indexes").mkdir(parents=True, exist_ok=True)
    if TEMP_DB_PATH.exists(): TEMP_DB_PATH.unlink()
    
    conn = sqlite3.connect(TEMP_DB_PATH)
    load_csv_to_sqlite(conn)
    load_opennutrition(conn)
    
    # 1. Initialize Meta Storage
    if FINAL_META_PATH.exists(): FINAL_META_PATH.unlink()
    meta_conn = sqlite3.connect(FINAL_META_PATH)
    meta_conn.execute("CREATE TABLE metadata (id INTEGER PRIMARY KEY, fdc_id INTEGER, text TEXT, json_meta TEXT)")
    
    # 2. Embedder
    from backend.embedder_bge import EmbedderBGE
    embedder = EmbedderBGE(model_name=EMBEDDING_MODEL)
    
    # 3. FAISS Index
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    
    # 4. Loop & Report
    counts = {
        'total_food_rows': 0,
        'embedded_chunks': 0,
        'skipped': 0,
    }
    
    # Get total count for progress
    total_fdc = conn.execute("SELECT COUNT(*) FROM food").fetchone()[0]
    total_on = conn.execute("SELECT COUNT(*) FROM opennutrition").fetchone()[0] if 'opennutrition' in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")] else 0
    total_to_ingest = total_fdc + total_on
    counts['total_food_rows'] = total_to_ingest
    logger.info(f"Targeting TOTAL ingestion of {total_to_ingest} food records (FDC: {total_fdc}, ON: {total_on}).")
    
    texts_batch = []
    meta_batch = []
    
    for i, item in enumerate(aggregate_and_stream(conn)):
        texts_batch.append(item['text'])
        meta_batch.append(item)
        
        if len(texts_batch) >= BATCH_SIZE:
            # Embed
            embeddings = embedder.embed_texts(texts_batch, batch_size=BATCH_SIZE)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            index.add(embeddings.astype('float32'))
            
            # Save Meta to SQLite
            meta_inserts = []
            for j, m in enumerate(meta_batch):
                idx = i - len(meta_batch) + 1 + j
                meta_inserts.append((idx, m['id'], m['text'], json.dumps(m['metadata'])))
            
            meta_conn.executemany("INSERT INTO metadata VALUES (?, ?, ?, ?)", meta_inserts)
            meta_conn.commit()
            
            counts['embedded_chunks'] += len(texts_batch)
            if counts['embedded_chunks'] % 5000 == 0:
                elapsed = time.time() - start_time
                rate = counts['embedded_chunks'] / elapsed
                logger.info(f"Progress: Chunks {counts['embedded_chunks']} | Rate: {rate:.1f}/s")
                
            texts_batch = []
            meta_batch = []
            
    # Final batch
    if texts_batch:
        embeddings = embedder.embed_texts(texts_batch)
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype('float32'))
        for j, m in enumerate(meta_batch):
            idx = counts['embedded_chunks'] + j
            meta_conn.execute("INSERT INTO metadata VALUES (?, ?, ?, ?)", (idx, m['id'], m['text'], json.dumps(m['metadata'])))
        meta_conn.commit()
        counts['embedded_chunks'] += len(texts_batch)

    # 5. Save Results
    faiss.write_index(index, str(FINAL_INDEX_PATH))
    meta_conn.execute("CREATE INDEX idx_meta_fdc ON metadata(fdc_id)")
    meta_conn.close()
    
    elapsed = time.time() - start_time
    
    # 6. Report
    report = f"""
============================================================
TOTAL INGESTION REPORT - FDC
============================================================
Timestamp: {datetime.now().isoformat()}
Models: {EMBEDDING_MODEL}

Branded foods raw rows: {total_to_ingest}
Total chunks embedded: {counts['embedded_chunks']}
Rows skipped: {counts['skipped']}

Final FAISS index vector count: {index.ntotal}
Final index size on disk: {FINAL_INDEX_PATH.stat().st_size / 1024**3:.2f} GB
Metadata store: {FINAL_META_PATH.name} ({FINAL_META_PATH.stat().st_size / 1024**2:.2f} MB)

Total Build Time: {elapsed/60:.2f} minutes
============================================================
"""
    logger.info(report)
    with open(PROJECT_ROOT / "backend/indexes/ingestion_report.txt", "w") as f:
        f.write(report)

if __name__ == "__main__":
    try:
        perform_ingestion()
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user.")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)

#!/usr/bin/env python3
"""
Isolated Dataset Ingestion Script - Comprehensive Edition (v3.0)

Key Improvements:
1. Deep Nutrition Join: FDC datasets now include nutrient names, amounts, and units in the text.
2. Branded Food Details: Includes brand owner and ingredients in search text.
3. Chemistry Expansion: Added support for .parquet (FartDB) and root .xlsx (composition-data).
4. OpenNutrition Upgrade: Indexes aliases and nutrients JSON from the TSV.
5. High Performance: SQ8 index, async loading, and CUDA resilience from previous versions.
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
import argparse
import threading
import queue
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
BATCH_SIZE = 64 
MAX_TOKENS = 1024
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
DEVICE = os.getenv("EMBEDDING_DEVICE", "cuda")

VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
DATA_SOURCES_DIR = PROJECT_ROOT / "data_sources"

def chunk_text(text: str) -> List[str]:
    """Split text into overlapping chunks."""
    if not text or len(text) <= CHUNK_SIZE:
        return [text] if text else []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if end < len(text):
            last_sep = max(chunk.rfind('; '), chunk.rfind(' | '))
            if last_sep > CHUNK_SIZE // 2:
                chunk = chunk[:last_sep + 3]
                end = start + last_sep + 3
        chunks.append(chunk)
        if start + CHUNK_SIZE >= len(text): break
        start = end - CHUNK_OVERLAP
    return chunks

class IsolatedIngestor:
    def __init__(self, dataset: str, force: bool = False):
        self.dataset = dataset
        self.force = force
        self.output_dir = VECTOR_STORE_DIR / dataset
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.output_dir / "index.faiss"
        self.meta_path = self.output_dir / "index.meta.sqlite"
        self.embedder = None
        
    def _load_embedder(self):
        if self.embedder is None:
            from backend.embedder_bge import EmbedderBGE
            self.embedder = EmbedderBGE(model_name=EMBEDDING_MODEL)

    # _get_index moved to support chunking logic below

    def ingest_chemistry(self):
        chem_dir = DATA_SOURCES_DIR / "chemistry"
        def generator():
            # 1. FoodDB CSVs
            fooddb_dir = chem_dir / "FoodDB"
            if fooddb_dir.exists():
                for csv_path in sorted(fooddb_dir.glob("*.csv")):
                    logger.info(f"  Streaming FoodDB: {csv_path.name}")
                    try:
                        for chunk in pd.read_csv(csv_path, chunksize=5000, low_memory=False):
                            for _, row in chunk.iterrows():
                                text = f"Chemistry: {csv_path.stem} | Info: " + " | ".join([f"{k}: {v}" for k, v in row.to_dict().items() if pd.notna(v)])
                                yield {'id': f"fooddb_{csv_path.stem}_{row.name}", 'text': text, 'meta': {'source': 'fooddb', 'file': csv_path.name}}
                    except Exception as e: logger.error(f"Error in {csv_path.name}: {e}")

            # 2. DSSTox Excel
            dsstox_dir = chem_dir / "DSSTox"
            if dsstox_dir.exists():
                for xls_path in sorted(dsstox_dir.glob("*.xlsx")):
                    logger.info(f"  Streaming DSSTox: {xls_path.name}")
                    try:
                        df = pd.read_excel(xls_path)
                        for _, row in df.iterrows():
                            text = f"Chemistry: DSSTox | Info: " + " | ".join([f"{k}: {v}" for k, v in row.to_dict().items() if pd.notna(v)])
                            yield {'id': f"dsstox_{xls_path.stem}_{row.name}", 'text': text, 'meta': {'source': 'dsstox', 'file': xls_path.name}}
                    except Exception as e: logger.error(f"Error in {xls_path.name}: {e}")

            # 3. FartDB Parquet
            fart_path = chem_dir / "FartDB.parquet"
            if fart_path.exists():
                logger.info(f"  Streaming FartDB: {fart_path.name}")
                try:
                    df = pd.read_parquet(fart_path)
                    for _, row in df.iterrows():
                        text = f"Chemistry: FartDB | Info: " + " | ".join([f"{k}: {v}" for k, v in row.to_dict().items() if pd.notna(v)])
                        yield {'id': f"fartdb_{row.name}", 'text': text, 'meta': {'source': 'fartdb'}}
                except Exception as e: logger.error(f"Error in FartDB: {e}")

            # 4. Composition Data Excel
            comp_path = chem_dir / "composition-data.xlsx"
            if comp_path.exists():
                logger.info(f"  Streaming Composition Data: {comp_path.name}")
                try:
                    df = pd.read_excel(comp_path)
                    for _, row in df.iterrows():
                        text = f"Chemistry: Composition | Info: " + " | ".join([f"{k}: {v}" for k, v in row.to_dict().items() if pd.notna(v)])
                        yield {'id': f"comp_{row.name}", 'text': text, 'meta': {'source': 'composition'}}
                except Exception as e: logger.error(f"Error in composition-data: {e}")

        self._core_ingest_loop(generator(), 9000000)

    def ingest_science(self):
        science_dir = DATA_SOURCES_DIR / "science"
        pdfs = list(science_dir.glob("*.pdf"))
        def generator():
            import fitz
            for pdf_path in pdfs:
                logger.info(f"  Processing PDF: {pdf_path.name}")
                try:
                    doc = fitz.open(pdf_path)
                    for page in doc:
                        text = page.get_text()
                        if text:
                            yield {'id': f"{pdf_path.name}_{page.number}", 'text': text, 'meta': {'source': 'science', 'file': pdf_path.name, 'page': page.number}}
                except Exception as e: logger.error(f"Error reading PDF {pdf_path.name}: {e}")
        self._core_ingest_loop(generator(), len(pdfs) * 100)

    def ingest_recipes(self):
        recipe_path = DATA_SOURCES_DIR / "recipes" / "recipes_full.json"
        if not recipe_path.exists(): return
        with open(recipe_path, 'r') as f: data = json.load(f)
        def generator():
            for i, r in enumerate(data):
                text = f"Recipe: {r.get('title', '')} | Ingredients: {', '.join(r.get('ingredients', []))} | Directions: {' '.join(r.get('directions', []))}"
                yield {'id': f"recipe_{i}", 'text': text, 'meta': {'source': 'recipes', 'title': r.get('title')}}
        self._core_ingest_loop(generator(), len(data))

    def ingest_fdc(self, ds_name: str, total: int):
        mappings = {"usda_foundation": "nutrition/foundation_foods", "usda_branded": "nutrition/branded_foods"}
        folder_name = mappings.get(ds_name, ds_name)
        source_dir = DATA_SOURCES_DIR / folder_name
        self._build_fdc_sql_join(source_dir, ds_name)
        temp_db = self.output_dir / f"temp_{ds_name}.db"
        
        def generator():
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            # Fetch names, branded info, and grouped nutrients
            query = """
                SELECT f.fdc_id, f.description, 
                       group_concat(n.name || ': ' || fn.amount || ' ' || n.unit_name, ' | ') as nutrients
                FROM food f
                LEFT JOIN food_nutrient fn ON f.fdc_id = fn.fdc_id
                LEFT JOIN nutrient n ON fn.nutrient_id = n.id
                GROUP BY f.fdc_id
                ORDER BY f.fdc_id ASC
            """
            cursor.execute(query)
            while True:
                rows = cursor.fetchmany(1000)
                if not rows: break
                for row in rows:
                    fdc_id, desc, nutrients = row
                    text = f"FDC Food: {desc} | Nutrients: {nutrients if nutrients else 'N/A'}"
                    
                    # Add branded specific info if available
                    if ds_name == "usda_branded":
                        try:
                            br_res = conn.execute("SELECT brand_owner, ingredients FROM branded_food WHERE fdc_id = ?", (fdc_id,)).fetchone()
                            if br_res:
                                owner, ingr = br_res
                                text = f"Brand: {owner} | " + text + f" | Ingredients: {ingr}"
                        except: pass
                        
                    yield {'id': f"fdc_{fdc_id}", 'text': text, 'meta': {'fdc_id': fdc_id, 'source': ds_name}}
            conn.close()
        self._core_ingest_loop(generator(), total)

    def _build_fdc_sql_join(self, source_dir, ds_name):
        temp_db = self.output_dir / f"temp_{ds_name}.db"
        if temp_db.exists() and not self.force: return
        if temp_db.exists() and self.force: temp_db.unlink()
        logger.info(f"Building temporary Joined SQLite for {ds_name}...")
        conn = sqlite3.connect(temp_db)
        # Load core tables needed for the RAG join
        core_files = ["food.csv", "food_nutrient.csv", "nutrient.csv", "branded_food.csv", "foundation_food.csv"]
        for csv_path in source_dir.glob("*.csv"):
            if csv_path.name.lower() in core_files:
                logger.info(f"  Indexing {csv_path.name} into temp DB (Chunked)")
                try:
                    # FIX: Use chunksize to prevent OOM on massive Branded Foods CSVs
                    for chunk in pd.read_csv(csv_path, chunksize=100000, low_memory=False):
                        chunk.to_sql(csv_path.stem, conn, index=False, if_exists='append')
                except Exception as e: logger.error(f"Failed to index {csv_path.name}: {e}")
        
        # Optimize performance: Add indexes for the massive join
        logger.info("  Creating SQL Indexes for performance...")
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_food_id ON food(fdc_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fn_id ON food_nutrient(fdc_id)")
             # Also index nutrient_id for the second join
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fn_nid ON food_nutrient(nutrient_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_n_id ON nutrient(id)")
             # And branded_food for the optional lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bf_id ON branded_food(fdc_id)")
        except Exception as e: logger.warning(f"Failed to create indexes: {e}")

        conn.commit(); conn.close()

    def ingest_open_nutrition(self):
        tsv_path = DATA_SOURCES_DIR / "nutrition" / "opennutrition_foods.tsv"
        if not tsv_path.exists(): return
        def generator():
            try:
                for chunk in pd.read_csv(tsv_path, sep='\t', header=None, chunksize=1000):
                    for _, row in chunk.iterrows():
                        name = row[1] if len(row) > 1 else "Unknown"
                        aliases = row[2] if len(row) > 2 else ""
                        desc = row[3] if len(row) > 3 else ""
                        # Include full nutrients - chunking will handle the length
                        nutrients = ""
                        if len(row) > 7 and row[7]:
                            try:
                                nut_data = json.loads(row[7])
                                # Format as readable text, not JSON
                                nutrients = " | ".join([f"{k}: {v}" for k, v in nut_data.items() if v])
                            except: nutrients = "Nutrient data available"
                        text = f"OpenNutrition: {name} | Aliases: {aliases} | Description: {desc} | Nutrients: {nutrients}"
                        yield {'id': f"open_{row[0]}", 'text': text, 'meta': {'source': 'open_nutrition'}}
            except Exception as e: logger.error(f"Error reading OpenNutrition TSV: {e}")
        self._core_ingest_loop(generator(), 330000)

    def _core_ingest_loop(self, source_gen, total):
        self._load_embedder()
        start_time = time.time()
        if self.force:
            logger.info(f"CLEAN START FOR {self.dataset}")
            if self.index_path.exists(): self.index_path.unlink()
            if self.meta_path.exists(): self.meta_path.unlink()
        index = self._get_index()
        meta_conn = sqlite3.connect(self.meta_path, check_same_thread=False)
        meta_conn.execute("CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, source_id TEXT, text TEXT, json_meta TEXT)")
        meta_conn.execute("CREATE TABLE IF NOT EXISTS checkpoint (key TEXT PRIMARY KEY, count_val INTEGER)")
        res = meta_conn.execute("SELECT count_val FROM checkpoint WHERE key='processed_items'").fetchone()
        processed_count = res[0] if res else 0
        if not res: meta_conn.execute("INSERT INTO checkpoint VALUES ('processed_items', 0)")
        if index.ntotal > 0:
            meta_conn.execute("DELETE FROM metadata WHERE id >= ?", (index.ntotal,))
            meta_conn.commit()
            logger.info(f"RESUMING {self.dataset} at item {processed_count}")

        q = queue.Queue(maxsize=1000)
        stop = threading.Event()
        def producer():
            try:
                for i, item in enumerate(source_gen):
                    if i < processed_count: continue
                    for chunk in chunk_text(item['text']):
                        while True:
                            try: q.put(({'id': item['id'], 'text': chunk, 'meta': item['meta']}, i), timeout=5); break
                            except queue.Full: 
                                if stop.is_set(): return
            except Exception as e: logger.error(f"Producer thread failed: {e}")
            finally: stop.set()

        threading.Thread(target=producer, daemon=True).start()
        batch_texts, batch_meta, emb_count, last_idx = [], [], index.ntotal, processed_count
        while not stop.is_set() or not q.empty():
            try:
                item, idx = q.get(timeout=1)
                batch_texts.append(item['text']); batch_meta.append(item); last_idx = idx
                if len(batch_texts) >= BATCH_SIZE:
                    if not index.is_trained: index.train(self.embedder.embed_texts(batch_texts, max_length=MAX_TOKENS))
                    self._process_batch_with_retry(index, meta_conn, batch_texts, batch_meta, emb_count)
                    emb_count += len(batch_texts); batch_texts, batch_meta = [], []
                    if (last_idx + 1) % 1000 == 0: self._save(index, meta_conn, last_idx + 1, emb_count)
            except queue.Empty: continue
        if batch_texts:
            if not index.is_trained: index.train(self.embedder.embed_texts(batch_texts, max_length=MAX_TOKENS))
            self._process_batch_with_retry(index, meta_conn, batch_texts, batch_meta, emb_count)
            emb_count += len(batch_texts); self._save(index, meta_conn, last_idx + 1, emb_count)
        meta_conn.close()
        logger.info(f"✅ {self.dataset} fully context-ingested in {time.time()-start_time:.2f}s")

    def _process_batch_with_retry(self, index, conn, texts, meta, start, retries=3):
        import torch
        for attempt in range(retries):
            try:
                embs = self.embedder.embed_texts(texts, batch_size=BATCH_SIZE, max_length=MAX_TOKENS)
                index.add(embs)
                rows = [(start+i, m['id'], m['text'], json.dumps(m['meta'])) for i, m in enumerate(meta)]
                # Use INSERT OR REPLACE to handle potential state desyncs/re-runs safely
                conn.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?,?,?)", rows); conn.commit()
                if self.dataset == "chemistry": time.sleep(0.05)
                return
            except Exception as e:
                logger.warning(f"Batch failed: {e}"); torch.cuda.empty_cache(); time.sleep(5)
                if attempt == retries - 1: raise e

    def _get_index(self):
        # CHUNKED INDEXING: If we are resuming and a file exists, start a NEW chunk
        # This prevents loading 9GB+ indices into RAM just to append a few more items.
        if self.index_path.exists() and not self.force:
            # We assume the existing index is valid up to the checkpoint.
            # We will start a new "shard" for the new data.
            # Rename the current target to a shard if it isn't one already? 
            # Simpler: Just define a new current active index path.
            
            # Find a free filename
            i = 1
            while True:
                candidate = self.output_dir / f"index_part_{i}.faiss"
                if not candidate.exists():
                    self.index_path = candidate
                    logger.info(f"Chunked Indexing: Starting NEW shard: {self.index_path.name}")
                    break
                i += 1
                
        # Always start fresh in memory (SQ8)
        logger.info(f"Creating new Memory-Based SQ8 Index for {self.dataset} (Shard)")
        return faiss.index_factory(EMBEDDING_DIM, "SQ8", faiss.METRIC_INNER_PRODUCT)

    def _save(self, index, conn, item_idx, vec_cnt):
        conn.execute("UPDATE checkpoint SET count_val = ?", (item_idx,)); conn.commit()
        # Save the CURRENT shard (we don't merge, we keep them separate)
        tmp = str(self.index_path) + ".tmp"
        faiss.write_index(index, tmp); os.replace(tmp, str(self.index_path))
        logger.info(f"  {self.dataset} Checkpoint @ {item_idx} items - Saved shard {self.index_path.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="all")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    order = ["recipes", "science", "usda_foundation", "open_nutrition", "chemistry", "usda_branded"]
    targets = order if args.dataset == "all" else [args.dataset]
    for ds in targets:
        logger.info(f"=== COMPREHENSIVE INGESTION START: {ds} ===")
        try:
            ingestor = IsolatedIngestor(ds, args.force)
            if ds == "chemistry": ingestor.ingest_chemistry()
            elif ds == "recipes": ingestor.ingest_recipes()
            elif ds == "science": ingestor.ingest_science()
            elif ds == "usda_foundation": ingestor.ingest_fdc(ds, 75000)
            elif ds == "open_nutrition": ingestor.ingest_open_nutrition()
            elif ds == "usda_branded": ingestor.ingest_fdc(ds, 1900000)
        except Exception as e:
            logger.error(f"Failed to process {ds}: {e}"); sys.exit(1)

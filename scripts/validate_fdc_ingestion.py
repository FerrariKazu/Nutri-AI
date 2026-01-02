#!/usr/bin/env python3
"""
FDC Ingestion Validator

Performs the MANDATORY VALIDATION STEP:
1. Samples 20 random FDC IDs from the metadata store.
2. Queries the FAISS index directly for each.
3. Proves retrieval success.
"""

import sqlite3
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.retriever import FaissRetriever

META_PATH = PROJECT_ROOT / "backend" / "indexes" / "nutrition.meta.sqlite"
INDEX_PATH = PROJECT_ROOT / "backend" / "indexes" / "nutrition.faiss"

def validate():
    print("============================================================")
    print("MANDATORY VALIDATION: FDC Retrieval Proof")
    print("============================================================")
    
    if not META_PATH.exists():
        print(f"ERROR: Metadata not found at {META_PATH}")
        return
        
    # 1. Sample 20 random IDs
    conn = sqlite3.connect(META_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT fdc_id, json_meta FROM metadata ORDER BY RANDOM() LIMIT 20")
    samples = cursor.fetchall()
    
    print(f"Sampled {len(samples)} random FDC IDs for testing.")
    
    # 2. Load Retriever
    retriever = FaissRetriever(INDEX_PATH)
    retriever.load()
    
    success_count = 0
    for fid, json_meta in samples:
        meta = json.loads(json_meta)
        desc = meta.get('description', 'No description')
        print(f"\nTesting FDC ID: {fid} ({desc[:50]}...)")
        
        # Query for the exact description or ID
        query = desc
        results = retriever.search(query, top_k=5)
        
        found = False
        for res in results:
            if int(res['metadata']['fdc_id']) == int(fid):
                found = True
                print(f"  ✅ FOUND at rank {results.index(res)+1} (Score: {res['score']:.4f})")
                success_count += 1
                break
        
        if not found:
            print(f"  ❌ NOT FOUND in top 5 results.")
            
    print("\n" + "="*60)
    print(f"VALIDATION RESULTS: {success_count}/20 recovered.")
    print("="*60)
    
    if success_count == 20:
        print("🎉 INGESTION SUCCESS: All samples retrieved.")
    else:
        print(f"⚠️ INGESTION WARNING: {20 - success_count} samples missed. Check embedding quality.")

if __name__ == "__main__":
    validate()

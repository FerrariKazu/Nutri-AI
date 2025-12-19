# pip install sentence-transformers faiss-cpu numpy

import json
import pickle
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

def build_index(chunks_path, index_path, meta_path):
    print("=" * 60)
    print("Starting FAISS Index Builder")
    print("=" * 60)
    print("Loading chunks...")
    chunks = []
    metas = []
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            chunks.append(data["text"])
            metas.append(data) # Store full metadata including page number
            
    print(f"Loaded {len(chunks)} chunks.")
    
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Encoding {len(chunks)} chunks in batches...")
    print("(This may take 10-20 minutes on CPU for ~1000+ chunks)")
    
    # Process in batches to show progress and avoid memory issues
    batch_size = 64
    all_embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        print(f"  Batch {batch_num}/{total_batches} ({i+1}-{min(i+batch_size, len(chunks))} / {len(chunks)} chunks)")
        batch_embeddings = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        all_embeddings.append(batch_embeddings)
    
    embeddings = np.vstack(all_embeddings)
    print(f"Encoding complete! Generated {embeddings.shape[0]} embeddings.")
    
    # Normalize embeddings for cosine similarity (Inner Product in FAISS)
    faiss.normalize_L2(embeddings)
    
    dimension = embeddings.shape[1]
    print(f"Embedding dimension: {dimension}")
    
    print("Building FAISS index...")
    # IndexFlatIP = Exact search using Inner Product (Cosine Similarity since normalized)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    print(f"Saving index to {index_path}...")
    faiss.write_index(index, str(index_path))
    
    print(f"Saving metadata to {meta_path}...")
    with open(meta_path, 'wb') as f:
        pickle.dump(metas, f)
        
    print("Done.")

if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).parent
    CHUNKS_FILE = SCRIPT_DIR / "chunks.jsonl"
    INDEX_FILE = SCRIPT_DIR / "faiss.index"
    META_FILE = SCRIPT_DIR / "metas.pkl"
    
    build_index(CHUNKS_FILE, INDEX_FILE, META_FILE)

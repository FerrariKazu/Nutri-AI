import faiss
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Global cache for model and index to avoid reloading on every request
_model = None
_index = None
_metas = None

SCRIPT_DIR = Path(__file__).parent
INDEX_FILE = SCRIPT_DIR / "faiss.index"
META_FILE = SCRIPT_DIR / "metas.pkl"

def load_resources():
    global _model, _index, _metas
    
    if _model is None:
        print("Loading RAG resources (Model, Index, Metas)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        
        if not INDEX_FILE.exists() or not META_FILE.exists():
            raise FileNotFoundError("FAISS index or metadata not found. Run build_faiss.py first.")
            
        _index = faiss.read_index(str(INDEX_FILE))
        
        with open(META_FILE, 'rb') as f:
            _metas = pickle.load(f)
            
        print("RAG resources loaded.")

def retrieve(query, k=6):
    """
    Retrieve top k chunks relevant to the query.
    Returns a list of dicts: {text, page, score, ...}
    """
    load_resources()
    
    # Encode query
    query_vector = _model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(query_vector)
    
    # Search
    scores, indices = _index.search(query_vector, k)
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1: continue
        
        meta = _metas[idx]
        results.append({
            "text": meta["text"],
            "page": meta["page"],
            "score": float(score)
        })
        
    return results

if __name__ == "__main__":
    # Simple test
    try:
        res = retrieve("echinacea side effects")
        for r in res:
            print(f"[Page {r['page']}] (Score: {r['score']:.4f}) {r['text'][:100]}...")
    except Exception as e:
        print(f"Test failed: {e}")

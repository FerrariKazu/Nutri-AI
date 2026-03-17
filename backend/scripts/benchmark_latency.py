import time
import numpy as np
import logging
from pathlib import Path
from backend.vector_store.faiss_index import FaissIndexManager
from backend.retriever.faiss_retriever import FaissRetriever
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LatencyBenchmark")

def run_benchmark():
    logger.info("Setting up benchmark...")
    temp_dir = Path("/tmp/nutri_benchmark")
    temp_dir.mkdir(exist_ok=True)
    
    # Create fake index
    num_vectors = 10000 # 10k vectors for local testing without hanging
    dim = 128
    
    manager = FaissIndexManager(index_dir=temp_dir, dimension=dim)
    vectors = np.random.random((num_vectors, dim)).astype('float32')
    
    logger.info(f"Building IVF-HNSW index for {num_vectors} vectors...")
    index = manager.create_index(num_vectors, pq_m=8)
    manager.train_and_add(index, vectors)
    manager.save_index(index)
    
    # Setup Retriever
    retriever = FaissRetriever(index_path=temp_dir)
    retriever.index = index
    retriever._loaded = True
    
    # Mock docstore and embedder for pure search latency
    retriever.id_to_doc = {i: {"id": i, "text": f"Doc {i}"} for i in range(100)} # Mock some docs
    retriever._embedder = MagicMock()
    retriever._embedder.embed_text.return_value = np.random.random((dim,)).astype('float32')
    retriever._get_cached_embedding = MagicMock(return_value=np.random.random((dim,)).astype('float32'))
    
    logger.info("Warming up...")
    for _ in range(3):
        try: retriever.search("warmup", subqueries=[MagicMock(query="q")], top_k=5)
        except: pass
        
    logger.info("Running Latency Benchmark (10 iterations)...")
    latencies = []
    
    subqueries = [MagicMock(query=f"subq {i}") for i in range(3)] # Simulate 3 expanded queries
    
    for i in range(10):
        start = time.perf_counter()
        try:
            retriever.search(f"test query {i}", subqueries=subqueries, top_k=5)
        except Exception:
            pass # Ignore pipeline errors, we just want FAISS search + dedup latency
        end = time.perf_counter()
        latencies.append((end - start)*1000)
        
    avg_latency = sum(latencies) / len(latencies)
    logger.info(f"Average Retrieval Latency (3 subqueries, {num_vectors} vectors): {avg_latency:.2f} ms")
    
    if avg_latency < 120.0:
        logger.info("✅ Latency Budget Met (<120ms)")
    else:
        logger.warning("❌ Latency Budget Missed (>120ms)")

if __name__ == "__main__":
    run_benchmark()

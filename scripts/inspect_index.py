import faiss
import sys

index_path = "vector_store/chemistry/index.faiss"
try:
    index = faiss.read_index(index_path)
    print(f"Index type: {type(index)}")
    print(f"ntotal: {index.ntotal}")
    print(f"d: {index.d}")
    print(f"Metric: {index.metric_type}")
    if hasattr(index, "index"): # for IVF
        print(f"Quantizer: {type(index.index)}")
except Exception as e:
    print(f"Error: {e}")

import faiss
import numpy as np
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compress_index(index_path, output_path, nlist=4096, m=64):
    logger.info(f"Loading original index: {index_path}")
    start_time = time.time()
    index = faiss.read_index(index_path)
    logger.info(f"Loaded index in {time.time() - start_time:.2f}s. Total vectors: {index.ntotal}")

    d = index.d
    # Use HNSW quantizer for massive speedup in coarse centroid search
    # M=32 is a good balance for centroid search in 1024D
    quantizer = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
    # IVFPQ index
    new_index = faiss.IndexIVFPQ(quantizer, d, nlist, m, 8, faiss.METRIC_INNER_PRODUCT)
    
    logger.info("Extracting vectors for training...")
    train_size = min(index.ntotal, 256000)
    indices = np.random.choice(index.ntotal, train_size, replace=False)
    
    # Extract training set in smaller chunks to avoid MemoryError
    train_vectors = np.zeros((train_size, d), dtype='float32')
    chunk_size = 32000
    for i in range(0, train_size, chunk_size):
        end = min(i + chunk_size, train_size)
        logger.info(f"Extracting training chunk {i} to {end}...")
        for j in range(i, end):
            train_vectors[j] = index.reconstruct(int(indices[j]))
    
    logger.info(f"Training new index with {train_size} vectors...")
    faiss.normalize_L2(train_vectors)
    new_index.train(train_vectors)
    logger.info("Training complete.")

    # Add vectors in batches
    batch_size = 500000
    for i in range(0, index.ntotal, batch_size):
        ntotal = min(batch_size, index.ntotal - i)
        logger.info(f"Adding vectors {i} to {i + ntotal}...")
        
        # Use reconstruct_n for the batch only (500k * 1024 * 4 = 2GB)
        if hasattr(index, "reconstruct_n"):
            batch_vectors = index.reconstruct_n(i, ntotal)
        else:
            batch_vectors = np.zeros((ntotal, d), dtype='float32')
            for j in range(ntotal):
                batch_vectors[j] = index.reconstruct(int(i + j))
                
        faiss.normalize_L2(batch_vectors)
        new_index.add(batch_vectors)


    logger.info(f"Saving compressed index to: {output_path}")
    faiss.write_index(new_index, output_path)
    logger.info(f"Done! Rebuild took {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    src = "vector_store/chemistry/index.faiss"
    dst = "vector_store/chemistry/index_compressed.faiss"
    compress_index(src, dst)

from sentence_transformers import SentenceTransformer
import torch
import numpy as np
import faiss
import logging

logger = logging.getLogger(__name__)

class BGEEmbedder:
    def __init__(self, model_path: str):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🚀 [BGEEmbedder] Loading model from {model_path} on {device}")
        
        self.model = SentenceTransformer(
            model_path,
            device=device
        )

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        """Embed multiple queries in a single batch."""
        prefixed_texts = [f"query: {t}" for t in texts]
        emb = self.model.encode(
            prefixed_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=len(prefixed_texts)
        )
        return emb.astype("float32")

    def embed_query(self, text: str) -> np.ndarray:
        """Embed single query with required prefix."""
        return self.embed_queries([text])[0]

    def embed_documents(self, docs: list[str]) -> np.ndarray:
        """Embed document passages with required prefix."""
        docs = [f"passage: {d}" for d in docs]
        emb = self.model.encode(
            docs,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32
        )
        return emb.astype("float32")

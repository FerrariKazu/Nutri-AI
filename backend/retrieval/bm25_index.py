"""
BM25 Keyword Index — Nutri Phase 4

Provides BM25Okapi-based keyword search with persistence and metadata versioning.
Built from the same document chunks used in FAISS for hybrid retrieval.
"""

import json
import logging
import pickle
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

TOKENIZER_VERSION = "v1"


class BM25Index:
    """
    Persistent BM25 keyword index aligned with FAISS docstore.

    Responsibilities:
        - Build index from document chunks
        - Perform keyword search returning chunk_ids + scores
        - Save/load with pickle + metadata JSON
        - Validate doc count against FAISS on startup
    """

    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.chunk_ids: List[Any] = []
        self.doc_count: int = 0
        self._built = False

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Lowercase, strip punctuation, split whitespace."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        return text.split()

    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from document chunks.

        Args:
            chunks: List of dicts with at least 'chunk_id' and 'text' keys.
        """
        if not chunks:
            logger.warning("[BM25] No chunks provided for indexing.")
            return

        t_start = time.perf_counter()
        self.chunk_ids = []
        tokenized_corpus = []

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", chunk.get("vector_id", chunk.get("id")))
            text = chunk.get("text", "")
            self.chunk_ids.append(chunk_id)
            tokenized_corpus.append(self._tokenize(text))

        self.bm25 = BM25Okapi(tokenized_corpus)
        self.doc_count = len(chunks)
        self._built = True

        elapsed = (time.perf_counter() - t_start) * 1000
        logger.info(f"[BM25] Index built: {self.doc_count} docs in {elapsed:.1f}ms")

    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search.

        Returns:
            List of {chunk_id, score, source: 'bm25'} sorted by score desc.
        """
        if not self._built or self.bm25 is None:
            logger.warning("[BM25] Index not built. Returning empty results.")
            return []

        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)

        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "score": float(scores[idx]),
                    "source": "bm25",
                })

        return results

    def save(self, path: Path) -> None:
        """Save BM25 index and metadata to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        index_path = path / "bm25_index.pkl"
        meta_path = path / "bm25_metadata.json"

        with open(index_path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "chunk_ids": self.chunk_ids}, f)

        metadata = {
            "doc_count": self.doc_count,
            "tokenizer_version": TOKENIZER_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"[BM25] Saved index ({self.doc_count} docs) to {path}")

    def load(self, path: Path) -> bool:
        """
        Load BM25 index from disk with metadata validation.

        Returns:
            True if loaded successfully, False if rebuild needed.
        """
        path = Path(path)
        index_path = path / "bm25_index.pkl"
        meta_path = path / "bm25_metadata.json"

        if not index_path.exists() or not meta_path.exists():
            logger.warning("[BM25] Index or metadata missing. Rebuild required.")
            return False

        try:
            with open(meta_path, "r") as f:
                metadata = json.load(f)

            if metadata.get("tokenizer_version") != TOKENIZER_VERSION:
                logger.warning(
                    f"[BM25] Tokenizer version mismatch: "
                    f"{metadata.get('tokenizer_version')} vs {TOKENIZER_VERSION}"
                )
                return False

            with open(index_path, "rb") as f:
                data = pickle.load(f)

            self.bm25 = data["bm25"]
            self.chunk_ids = data["chunk_ids"]
            self.doc_count = metadata["doc_count"]
            self._built = True

            logger.info(f"[BM25] Loaded index: {self.doc_count} docs from {path}")
            return True

        except Exception as e:
            logger.error(f"[BM25] Failed to load index: {e}")
            return False

    def validate_against_faiss(self, faiss_ntotal: int) -> bool:
        """Check doc count alignment with FAISS index."""
        if self.doc_count != faiss_ntotal:
            logger.warning(
                f"[BM25] Doc count mismatch: BM25={self.doc_count}, FAISS={faiss_ntotal}. "
                f"Rebuild recommended."
            )
            return False
        logger.info(f"[BM25] Doc count validated: {self.doc_count} == FAISS {faiss_ntotal}")
        return True

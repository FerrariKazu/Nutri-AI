"""
FAISS Retriever Implementation — Nutri Phase 3

Concrete implementation of BaseRetriever using FAISS for semantic search.
Supports IVF-HNSW-PQ for scalability, semantic deduplication, and failure safeguards.
"""

import json
import re
import sqlite3
import time
import numpy as np
import functools
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import functools

import faiss

from .base import BaseRetriever
from .retrieval_utils import normalize_top_k, safe_retrieve, decompose_query

logger = logging.getLogger(__name__)


class FaissRetriever(BaseRetriever):
    """
    FAISS-based semantic retriever.
    
    Uses FAISS IndexIVFPQ (with HNSW quantizer) for scalable search 
    on L2-normalized embeddings.
    """
    
    # Feature 7: Chemical-to-taste mapping for result tagging
    CHEMICAL_TASTE_MAP = {
        "alkaloid": "bitter", "tannin": "bitter", "polyphenol": "bitter",
        "citric acid": "sour", "malic acid": "sour", "lactic acid": "sour",
        "glutamate": "umami", "inosinate": "umami",
        "sucrose": "sweet", "glucose": "sweet", "fructose": "sweet",
    }
    
    # Feature 8: Taste ranking bonus
    TASTE_BONUS = 0.05

    # Phase 2 & 3 Constants
    MAX_RESULT_POOL = 25         # M4: Cap merged pool before reranking
    MAX_RERANK_POOL = 30         # M4: Hard limit on reranker input size
    MAX_TOTAL_BOOST = 0.10       # M8: Clamp total additive boost
    ENABLE_RERANKER = True       # M11: Toggle for cross-encoder reranking
    
    MAX_NPROBE = 64
    MIN_NPROBE = 8
    SIM_THRESHOLD = 0.92
    MAX_CONTEXT_TOKENS = 6000
    ENABLE_EMBED_CACHE = True
    
    def __init__(
        self,
        index_path: str | Path,
        metadata_path: Optional[str | Path] = None,
        embedding_model: str = "BAAI/bge-small-en-v1.5"
    ):
        """
        Initialize FAISS retriever.
        """
        index_path = Path(index_path)
        m_path = Path(metadata_path) if metadata_path else None
        
        super().__init__(index_path, m_path, embedding_model)
        
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[str, Any] = {}
        self.id_to_doc: Dict[int, Dict[str, Any]] = {}
        self._meta_conn: Optional[sqlite3.Connection] = None
        self._is_sqlite_meta = self.metadata_path.suffix == '.sqlite'
        self._embedder = None
        self._reranker = None 

    def load(self) -> None:
        """Load FAISS index and metadata into memory."""
        if self._loaded:
            logger.info(f"Index already loaded: {self.index_path}")
            return
        
        logger.info(f"Loading FAISS index: {self.index_path}")
        
        # Load FAISS index
        self.index = faiss.read_index(str(self.index_path))
        
        # ── FOOTPRINT ESTIMATION ──────────────────────────────────────────
        VECTOR_DIMENSION = getattr(self.index, "d", 1024)
        ntotal = getattr(self.index, "ntotal", 0)
        required_gb = (ntotal * VECTOR_DIMENSION * 4) / (1024**3)
        
        # Enforce memory safety check with index path for file-size estimation
        try:
            from .memory_guard import check_memory_safety
            check_memory_safety(str(self.index_path))
        except MemoryError as e:
            logger.error(f"Index load blocked by Memory Guard: {e}")
            self.index = None
            raise
            
        logger.info(f"Loaded index with {ntotal} vectors ({required_gb:.3f} GB footprint)")
        
        # Load metadata
        if self.metadata_path.exists():
            if self._is_sqlite_meta:
                logger.info(f"Using SQLite metadata: {self.metadata_path}")
                self._meta_conn = sqlite3.connect(
                    f"file:{self.metadata_path}?mode=ro", 
                    uri=True,
                    check_same_thread=False
                )
            else:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metadata = data.get('index_info', {})
                    self.id_to_doc = {
                        int(k): v for k, v in data.get('documents', {}).items()
                    }
                logger.info(f"Loaded JSON metadata for {len(self.id_to_doc)} documents")
        else:
            logger.warning(f"Metadata not found: {self.metadata_path}")
        
        # Load embedder lazily
        self._load_embedder()
        
        self._loaded = True
        logger.info(f"✅ FAISS retriever ready: {self.index_path.name}")
    
    @functools.lru_cache(maxsize=500)
    def _get_cached_embedding(self, text: str):
        """Phase 3: LRU cache for query embeddings."""
        if self._embedder is None:
            self._load_embedder()
        return self._embedder.embed_query(text)

    def _load_embedder(self) -> None:
        """Load the embedding model for query encoding."""
        if self._embedder is not None:
            return
        
        try:
            from .embedder_singleton import EmbedderSingleton
            self._embedder = EmbedderSingleton.get()
            logger.info(f"Connected to shared embedder: {self.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to access shared embedder: {e}")
            raise

    def _load_reranker(self):
        """M11: Lazy-load the cross-encoder reranker."""
        if self._reranker is not None:
            return self._reranker
        try:
            from ..vector_store.reranker import Reranker
            self._reranker = Reranker()
            logger.info("[RERANKER] Cross-encoder reranker loaded")
        except Exception as e:
            logger.warning(f"[RERANKER] Failed to load reranker: {e} — disabled")
            self.ENABLE_RERANKER = False
        return self._reranker
    
    def _batch_search(self, query_embeddings: np.ndarray, top_k: int) -> tuple:
        """Run multiple FAISS searches in a single call."""
        t_search = time.perf_counter()
        
        if hasattr(self.index, 'nlist'):
            self.index.nprobe = min(64, max(8, int(self.index.nlist * 0.05)))
        
        # FAISS search on matrix [num_queries, d]
        all_scores, all_indices = self.index.search(query_embeddings, top_k)
        
        elapsed = (time.perf_counter() - t_search) * 1000
        logger.info(
            f"[RETRIEVAL_BATCH] queries={len(query_embeddings)} top_k={top_k} "
            f"nprobe={getattr(self.index, 'nprobe', 'N/A')} "
            f"index_size={getattr(self.index, 'ntotal', 0)} total_latency={elapsed:.2f}ms"
        )
        
        return all_scores, all_indices

    def _single_search(self, query_embedding: np.ndarray, top_k: int) -> tuple:
        """Run a single FAISS search with consistent nprobe scaling."""
        scores_raw, indices_raw = self._batch_search(query_embedding, top_k)
        return scores_raw[0].tolist(), indices_raw[0].tolist()

    def _build_results(self, scores: list, indices: list) -> List[Dict[str, Any]]:
        """Map FAISS score/index pairs to result dicts."""
        results = []
        for score, idx in zip(scores, indices):
            if idx < 0:
                continue

            doc_data = {}
            if self._is_sqlite_meta:
                cursor = self._meta_conn.cursor()
                cursor.execute("SELECT text, json_meta FROM metadata WHERE id = ?", (int(idx),))
                match = cursor.fetchone()
                if match:
                    text, json_str = match
                    metadata = json.loads(json_str)
                    doc_data = {
                        'id': int(idx),
                        'text': text,
                        'score': float(score),
                        'metadata': metadata,
                        'source': metadata.get('source', 'fdc')
                    }
            else:
                doc = self.id_to_doc.get(idx, {})
                doc_data = {
                    'id': idx,
                    'text': doc.get('text', ''),
                    'score': float(score),
                    'metadata': doc.get('metadata', {}),
                    'source': doc.get('source', 'unknown')
                }

            if doc_data:
                results.append(doc_data)
        return results


    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.45,
        metadata_filter: Optional[Dict[str, Any]] = None,
        tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents with ontology-aware query decomposition.

        Phase 3 Pipeline:
            query → decompose (tier-aware) → embed each subquery → FAISS search
            → per-query normalize → merge → dedup (DocID + Semantic) → pool limit
            → cross-encoder rerank → taste tag/boost → sort → fallback → return
        """
        # ── TYPE GUARDS ──────────────────────────────────────────────────────────
        if isinstance(query, list):
            raise TypeError(f"Retriever received list query. Got: {query}")

        self.ensure_loaded()
        top_k = normalize_top_k(top_k)
        t_start = time.perf_counter()

        # ── 1. ONTOLOGY DECOMPOSITION ─────────────────────────────────────────
        subqueries = decompose_query(query, tier=tier)
        logger.info(f"[QUERY_DECOMP] subqueries={len(subqueries)} for: {query[:80]}")

        # ── 2. BATCH EMBEDDING & SEARCH ───────────────────────────────────────
        if self._embedder is None:
            self._load_embedder()
        
        # Batch embed all subqueries at once (Request 11 Optimization)
        sq_embs = self._embedder.embed_queries(subqueries)
        sq_embs = sq_embs.astype('float32')
        faiss.normalize_L2(sq_embs)

        all_scores, all_indices = self._batch_search(sq_embs, top_k)
        
        match_counts: Dict[int, int] = {}   # doc_id → count
        merged: Dict[int, Dict[str, Any]] = {}  # doc_id → best result dict

        for i, sq in enumerate(subqueries):
            scores = all_scores[i].tolist()
            indices = all_indices[i].tolist()
            partial = self._build_results(scores, indices)

            if partial:
                sq_max = max(r['score'] for r in partial)
                if sq_max > 0:
                    for r in partial:
                        r['score'] = r['score'] / sq_max

            for r in partial:
                doc_id = r['id']
                match_counts[doc_id] = match_counts.get(doc_id, 0) + 1
                if doc_id not in merged or r['score'] > merged[doc_id]['score']:
                    merged[doc_id] = r

        # ── 3. INITIAL RESULTS & BOOST ────────────────────────────────────────
        MULTI_MATCH_BOOST = 0.05
        all_results = []
        for doc_id, r in merged.items():
            extra = match_counts.get(doc_id, 1) - 1
            r['match_count'] = match_counts.get(doc_id, 1)
            r['original_score'] = r['score']
            r['score'] = r['score'] + MULTI_MATCH_BOOST * extra
            all_results.append(r)

        chunks_before_dedup = len(all_results)
        
        # ── 4. SEMANTIC DEDUPLICATION (Incremental) ───────────────────────────
        all_results.sort(key=lambda x: x['score'], reverse=True)
        all_results = self._semantic_dedup(all_results)
        chunks_after_dedup = len(all_results)

        # ── 5. POOL LIMIT ────────────────────────────────────────────────────
        all_results = all_results[:self.MAX_RESULT_POOL]
        t_faiss_done = time.perf_counter()

        # ── 6. CROSS-ENCODER RERANKING ────────────────────────────────────────
        rerank_applied = False
        if self.ENABLE_RERANKER and len(all_results) > 1:
            try:
                reranker = self._load_reranker()
                if reranker:
                    rerank_pool_size = min(len(all_results), self.MAX_RERANK_POOL)
                    reranked = reranker.rerank(query, all_results[:rerank_pool_size], top_n=rerank_pool_size)
                    for r in reranked:
                        r['reranker_score'] = r.get('rerank_score', r.get('score', 0.0))
                    all_results = reranked
                    rerank_applied = True
            except Exception as e:
                logger.warning(f"[RERANKER] Reranking failed: {e}")

        t_rerank_done = time.perf_counter()

        # ── 7. TASTE TAGGING & BOOSTING ───────────────────────────────────────
        for r in all_results:
            text_lower = r.get('text', '').lower()
            for compound, taste in self.CHEMICAL_TASTE_MAP.items():
                if re.search(r"\b" + re.escape(compound) + r"(s)?\b", text_lower):
                    r['taste_tag'] = taste
                    break
            
            taste_boost = self.TASTE_BONUS if r.get('taste_tag') else 0.0
            match_boost = MULTI_MATCH_BOOST * (r.get('match_count', 1) - 1)
            total_boost = min(taste_boost + match_boost, self.MAX_TOTAL_BOOST)
            
            base_score = r.get('reranker_score', r['score'])
            r['normalized_score'] = base_score + total_boost

        # ── 8. FALLBACK & SORT ────────────────────────────────────────────────
        all_results.sort(key=lambda x: x.get('normalized_score', x['score']), reverse=True)
        for r in all_results:
            r['strength'] = 'strong' if r['original_score'] >= min_score else 'weak'

        results = [r for r in all_results if r['strength'] == 'strong'][:top_k]

        if not results and all_results:
            logger.warning("[SAFEGUARD] Fallback to top 5 results after empty filter.")
            results = all_results[:5]

        # ── 9. TELEMETRY ─────────────────────────────────────────────────────
        t_end = time.perf_counter()
        logger.info(
            "[RETRIEVAL_LATENCY]",
            extra={
                "query": query[:80],
                "faiss_ms": round((t_faiss_done - t_start) * 1000, 1),
                "rerank_ms": round((t_rerank_done - t_faiss_done) * 1000, 1),
                "total_ms": round((t_end - t_start) * 1000, 1),
                "chunks": f"{chunks_before_dedup}->{chunks_after_dedup}->{len(results)}"
            }
        )
        return safe_retrieve(results)

    def _semantic_dedup(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Phase 3: Incremental semantic de-duplication."""
        if not chunks:
            return []
            
        filtered = []
        for c in chunks:
            c_emb = self._get_cached_embedding(c['text'])
            is_redundant = False
            for f in filtered:
                f_emb = self._get_cached_embedding(f['text'])
                sim = np.dot(c_emb, f_emb)
                if sim > self.SIM_THRESHOLD:
                    is_redundant = True
                    break
            
            if not is_redundant:
                filtered.append(c)
        return filtered

    def get_metadata(self) -> Dict[str, Any]:
        """Return index metadata."""
        self.ensure_loaded()
        return {
            'index_path': str(self.index_path),
            'index_size': self.index.ntotal if self.index else 0,
            'embedding_dim': self.index.d if self.index else 0,
            'embedding_model': self.embedding_model,
            'document_count': len(self.id_to_doc),
            **self.metadata
        }

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "not loaded"
        return f"FaissRetriever({self.index_path.name}, {status})"

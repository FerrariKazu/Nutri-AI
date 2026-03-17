"""
Hybrid Retriever — Nutri Phase 4

Orchestrates dual-retrieval (FAISS + BM25) with RRF fusion,
reusing Phase 3 dedup, reranking, and taste boosting.
"""

import re
import time
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import lru_cache

from .bm25_index import BM25Index
from .fusion import rrf_merge

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Phase 4 hybrid retrieval pipeline.

    Pipeline:
        Query → Decomposition → FAISS + BM25
        → Pre-RRF dedup → RRF Fusion → Docstore lookup
        → Semantic Dedup → Pool limit (25) → Reranker
        → Taste Boost → Return
    """

    # Phase 3 constants (preserved)
    MAX_RESULT_POOL = 25
    MAX_RERANK_POOL = 30
    MAX_TOTAL_BOOST = 0.10
    TASTE_BONUS = 0.05
    ENABLE_RERANKER = True
    SIM_THRESHOLD = 0.92

    CHEMICAL_TASTE_MAP = {
        "alkaloid": "bitter", "tannin": "bitter", "polyphenol": "bitter",
        "citric acid": "sour", "malic acid": "sour", "lactic acid": "sour",
        "glutamate": "umami", "inosinate": "umami",
        "sucrose": "sweet", "glucose": "sweet", "fructose": "sweet",
    }

    def __init__(
        self,
        faiss_retriever,
        bm25_index: BM25Index,
        docstore=None,
    ):
        """
        Args:
            faiss_retriever: Loaded FaissRetriever instance.
            bm25_index: Loaded BM25Index instance.
            docstore: Optional DocStore for chunk text lookup.
        """
        self.faiss = faiss_retriever
        self.bm25 = bm25_index
        self.docstore = docstore
        self._reranker = None

    def _load_reranker(self):
        if self._reranker is not None:
            return self._reranker
        try:
            from backend.vector_store.reranker import Reranker
            self._reranker = Reranker()
            logger.info("[HYBRID] Cross-encoder reranker loaded")
        except Exception as e:
            logger.warning(f"[HYBRID] Reranker load failed: {e} — disabled")
            self.ENABLE_RERANKER = False
        return self._reranker

    def _get_embedding(self, text: str):
        """Get cached embedding from FAISS retriever."""
        return self.faiss._get_cached_embedding(text)

    def _semantic_dedup(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Incremental semantic deduplication (Phase 3 logic)."""
        if not chunks:
            return []

        filtered = []
        for c in chunks:
            c_emb = self._get_embedding(c.get("text", ""))
            is_redundant = False
            for f in filtered:
                f_emb = self._get_embedding(f.get("text", ""))
                sim = float(np.dot(c_emb, f_emb))
                if sim > self.SIM_THRESHOLD:
                    is_redundant = True
                    break
            if not is_redundant:
                filtered.append(c)
        return filtered

    def _apply_taste_boost(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Phase 3 taste tagging and boost application."""
        for r in results:
            text_lower = r.get("text", "").lower()
            for compound, taste in self.CHEMICAL_TASTE_MAP.items():
                if re.search(r"\b" + re.escape(compound) + r"(s)?\b", text_lower):
                    r["taste_tag"] = taste
                    break

            taste_boost = self.TASTE_BONUS if r.get("taste_tag") else 0.0
            total_boost = min(taste_boost, self.MAX_TOTAL_BOOST)

            base_score = r.get("reranker_score", r.get("score", 0.0))
            r["normalized_score"] = base_score + total_boost
        return results

    def _lookup_texts(self, fused: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve chunk_ids to full text via docstore or FAISS id_to_doc."""
        enriched = []
        for item in fused:
            cid = item["chunk_id"]
            text = ""

            if self.docstore:
                meta = self.docstore.get_metadata(cid)
                if meta:
                    text = meta.get("text", "")
            elif hasattr(self.faiss, "id_to_doc"):
                doc = self.faiss.id_to_doc.get(cid, {})
                text = doc.get("text", "")

            enriched.append({
                "id": cid,
                "chunk_id": cid,
                "text": text,
                "score": item["score"],
                "source": item["source"],
            })
        return enriched

    def search(
        self,
        query: str,
        top_k: int = 8,
        k_vector: int = 20,
        k_bm25: int = 20,
        min_score: float = 0.45,
        tier: Optional[str] = None,
        enable_taste_boost: bool = True,
        enable_semantic_dedup: bool = True,
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval: FAISS + BM25 → RRF → Dedup → Rerank → Taste → Return.

        Returns:
            Dict with 'results', 'telemetry' keys.
        """
        t_start = time.perf_counter()

        # ── 1. FAISS VECTOR SEARCH ───────────────────────────────────────
        t_faiss_start = time.perf_counter()
        vector_results = []
        try:
            self.faiss.ensure_loaded()
            from backend.retriever.retrieval_utils import decompose_query
            import faiss as faiss_lib

            subqueries = decompose_query(query, tier=tier)
            for sq in subqueries:
                sq_emb = self._get_embedding(sq)
                sq_emb = sq_emb.reshape(1, -1).astype("float32")
                faiss_lib.normalize_L2(sq_emb)
                scores, indices = self.faiss._single_search(sq_emb, k_vector)
                for score, idx in zip(scores, indices):
                    if idx >= 0:
                        vector_results.append({
                            "chunk_id": int(idx),
                            "score": float(score),
                            "source": "vector",
                        })
        except Exception as e:
            logger.warning(f"[HYBRID] FAISS search failed: {e}")

        t_faiss = (time.perf_counter() - t_faiss_start) * 1000

        # ── 2. BM25 KEYWORD SEARCH ───────────────────────────────────────
        t_bm25_start = time.perf_counter()
        keyword_results = self.bm25.search(query, k=k_bm25)
        t_bm25 = (time.perf_counter() - t_bm25_start) * 1000

        # ── 3. RRF FUSION ────────────────────────────────────────────────
        t_fusion_start = time.perf_counter()
        fused, rrf_overlap = rrf_merge(vector_results, keyword_results, k=60)
        t_fusion = (time.perf_counter() - t_fusion_start) * 1000

        # ── 4. DOCSTORE LOOKUP ───────────────────────────────────────────
        enriched = self._lookup_texts(fused)
        chunks_before_dedup = len(enriched)

        # ── 5. SEMANTIC DEDUP ────────────────────────────────────────────
        if enable_semantic_dedup:
            enriched = self._semantic_dedup(enriched)
        chunks_after_dedup = len(enriched)

        # ── 6. POOL LIMIT ───────────────────────────────────────────────
        enriched = enriched[: self.MAX_RESULT_POOL]

        # ── 7. CROSS-ENCODER RERANKER ────────────────────────────────────
        t_rerank_start = time.perf_counter()
        if self.ENABLE_RERANKER and len(enriched) > 1:
            try:
                reranker = self._load_reranker()
                if reranker:
                    pool = min(len(enriched), self.MAX_RERANK_POOL)
                    reranked = reranker.rerank(query, enriched[:pool], top_n=pool)
                    for r in reranked:
                        r["reranker_score"] = r.get("rerank_score", r.get("score", 0.0))
                    enriched = reranked
            except Exception as e:
                logger.warning(f"[HYBRID] Reranking failed: {e}")
        t_rerank = (time.perf_counter() - t_rerank_start) * 1000

        # ── 8. TASTE BOOST ───────────────────────────────────────────────
        if enable_taste_boost:
            enriched = self._apply_taste_boost(enriched)

        # ── 9. FINAL SORT + FILTER ───────────────────────────────────────
        enriched.sort(
            key=lambda x: x.get("normalized_score", x.get("score", 0)), reverse=True
        )
        for r in enriched:
            r["strength"] = "strong" if r.get("score", 0) >= min_score else "weak"

        results = [r for r in enriched if r["strength"] == "strong"][:top_k]
        if not results and enriched:
            logger.warning("[HYBRID] Fallback to top 5 after empty filter.")
            results = enriched[:5]

        # ── 10. TELEMETRY ────────────────────────────────────────────────
        t_total = (time.perf_counter() - t_start) * 1000
        telemetry = {
            "faiss_ms": round(t_faiss, 1),
            "bm25_ms": round(t_bm25, 1),
            "fusion_ms": round(t_fusion, 1),
            "rerank_ms": round(t_rerank, 1),
            "total_ms": round(t_total, 1),
            "rrf_overlap_count": rrf_overlap,
            "chunks_before_dedup": chunks_before_dedup,
            "chunks_after_dedup": chunks_after_dedup,
            "final_chunks": len(results),
        }
        logger.info(f"[HYBRID_TELEMETRY] {telemetry}")

        return {"results": results, "telemetry": telemetry}

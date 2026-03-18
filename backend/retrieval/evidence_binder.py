"""
Evidence Binder — Forces alignment between generated claims and retrieved evidence.

Converts raw retrieved chunks into a structured context with trackable chunk_ids,
enabling citation-based claim verification.
"""

import logging
import hashlib
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EvidenceBinder:
    """
    Binds retrieved chunks to a structured evidence context.
    Ensures every chunk has a unique, stable chunk_id for citation tracking.
    """

    def bind(self, query: str, retrieved_chunks: List[Any]) -> Dict[str, Any]:
        """
        Forces alignment between generated claims and retrieved evidence.

        Args:
            query: The user query.
            retrieved_chunks: List of retrieved document objects or dicts.

        Returns:
            Dict with mode ("retrieval" or "fallback"), context string, and tagged chunks.
        """
        if not retrieved_chunks:
            logger.warning("[EVIDENCE_BINDER] No retrieved chunks — entering fallback mode.")
            return {
                "mode": "fallback",
                "context": "",
                "chunks": [],
                "evidence_count": 0,
                "claims": []
            }

        tagged_chunks = []
        for i, chunk in enumerate(retrieved_chunks):
            text = self._extract_text(chunk)
            source = self._extract_source(chunk)
            score = self._extract_score(chunk)
            chunk_id = self._generate_chunk_id(text, i)

            tagged_chunks.append({
                "chunk_id": chunk_id,
                "text": text,
                "source": source,
                "score": score,
                "index": i
            })

        context = "\n\n".join([
            f"[{c['chunk_id']}] {c['text']}"
            for c in tagged_chunks
        ])

        evidence_strength = self._compute_evidence_strength(tagged_chunks)

        logger.info(
            f"[EVIDENCE_BINDER] Bound {len(tagged_chunks)} chunks | "
            f"strength={evidence_strength:.2f} | mode=retrieval"
        )

        return {
            "mode": "retrieval",
            "context": context,
            "chunks": tagged_chunks,
            "evidence_count": len(tagged_chunks),
            "evidence_strength": evidence_strength
        }

    def _extract_text(self, chunk: Any) -> str:
        if isinstance(chunk, dict):
            return chunk.get("text", str(chunk))
        return getattr(chunk, "text", str(chunk))

    def _extract_source(self, chunk: Any) -> str:
        if isinstance(chunk, dict):
            return chunk.get("source", "unknown")
        return getattr(chunk, "source", "unknown")

    def _extract_score(self, chunk: Any) -> float:
        if isinstance(chunk, dict):
            return float(chunk.get("score", 0.0))
        return float(getattr(chunk, "score", 0.0))

    def _generate_chunk_id(self, text: str, index: int) -> str:
        """Stable hash-based chunk_id."""
        h = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()[:6]
        return f"CHK-{index:02d}-{h}"

    def _compute_evidence_strength(self, chunks: List[Dict]) -> float:
        """
        Compute evidence strength from chunk scores.
        Returns 0.0-1.0 based on average relevance score.
        """
        if not chunks:
            return 0.0
        scores = [c.get("score", 0.0) for c in chunks]
        avg = sum(scores) / len(scores)
        return min(1.0, max(0.0, avg))

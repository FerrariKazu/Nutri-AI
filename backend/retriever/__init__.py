"""
FAISS-Only Retriever Module

This module provides a clean, unified interface for semantic search
using FAISS indexes. No HNSW, no fallback, no magic paths.
"""

from .base import BaseRetriever
from .faiss_retriever import FaissRetriever
from .router import RetrievalRouter

__all__ = [
    "BaseRetriever",
    "FaissRetriever", 
    "RetrievalRouter",
]

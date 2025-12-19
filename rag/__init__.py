"""RAG Package - PDF-Based Retrieval-Augmented Generation"""

__version__ = "1.0.0"

from .retriever import FAISSRetriever
from .agent import ScienceAgent

__all__ = ["FAISSRetriever", "ScienceAgent"]

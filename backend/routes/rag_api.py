
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from rag.retriever import FAISSRetriever
from rag.agent import ScienceAgent

router = APIRouter()
logger = logging.getLogger(__name__)

_retriever: Optional[FAISSRetriever] = None
_agent: Optional[ScienceAgent] = None


def get_retriever() -> FAISSRetriever:
    """Get or initialize retriever."""
    global _retriever
    if _retriever is None:
        logger.info("Initializing FAISS Retriever...")
        _retriever = FAISSRetriever()
    return _retriever


def get_agent() -> ScienceAgent:
    """Get or initialize agent."""
    global _agent
    if _agent is None:
        logger.info("Initializing Science Agent...")
        _agent = ScienceAgent()
    return _agent


# Request/Response Models
class AskScienceRequest(BaseModel):
    """Request for asking a scientific question."""
    question: str
    top_k: int = 10
    rerank: bool = False
    use_llm: bool = False  # Set to True when LLM is configured
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Why does browning increase flavor?",
                "top_k": 10,
                "rerank": False
            }
        }


class SourceInfo(BaseModel):
    """Source citation information."""
    source: str
    filename: str
    max_score: float
    chunk_count: int


class AskScienceResponse(BaseModel):
    """Response from scientific question."""
    success: bool
    answer: str
    sources: List[SourceInfo]
    confidence: str
    method: str
    retrieved_chunks: int


class RAGStatsResponse(BaseModel):
    """RAG system statistics."""
    total_chunks: int
    total_sources: int
    index_dimension: int
    index_type: str


# Endpoints

@router.post("/ask_science", response_model=AskScienceResponse)
async def ask_science(request: AskScienceRequest):
    """
    Ask a scientific question using PDF knowledge base.
    
    Pipeline:
    1. Retrieve relevant chunks from FAISS
    2. Optional reranking
    3. Agent synthesis with source citations
    
    Returns structured answer with sources.
    """
    try:
        retriever = get_retriever()
        agent = get_agent()
        
        # Retrieve relevant chunks
        logger.info(f"Retrieving chunks for: {request.question}")
        chunks = retriever.retrieve(
            query=request.question,
            top_k=request.top_k
        )
        
        # Optional reranking
        if request.rerank:
            chunks = retriever.rerank(
                query=request.question,
                chunks=chunks,
                top_n=min(5, len(chunks))
            )
        
        # Synthesize answer
        logger.info(f"Synthesizing answer from {len(chunks)} chunks")
        response = agent.synthesize(
            question=request.question,
            chunks=chunks,
            use_llm=request.use_llm
        )
        
        return AskScienceResponse(
            success=True,
            answer=response["answer"],
            sources=[SourceInfo(**src) for src in response["sources"]],
            confidence=response["confidence"],
            method=response["method"],
            retrieved_chunks=len(chunks)
        )
    
    except Exception as e:
        logger.error(f"Error in ask_science: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/stats", response_model=RAGStatsResponse)
async def get_rag_stats():
    """
    Get RAG system statistics.
    
    Returns information about indexed chunks and sources.
    """
    try:
        retriever = get_retriever()
        
        # Count unique sources
        unique_sources = set()
        for chunk_data in retriever.metadata.values():
            unique_sources.add(chunk_data["source"])
        
        return RAGStatsResponse(
            total_chunks=retriever.index.ntotal,
            total_sources=len(unique_sources),
            index_dimension=retriever.index.d,
            index_type="IndexFlatIP (cosine similarity)"
        )
    
    except Exception as e:
        logger.error(f"Error in get_rag_stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/health")
async def health_check():
    """Simple health check for RAG system."""
    try:
        retriever = get_retriever()
        return {
            "status": "healthy",
            "index_loaded": retriever.index is not None,
            "total_vectors": retriever.index.ntotal
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

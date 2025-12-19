"""
FastAPI endpoints for food search and retrieval.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging

from backend.vector_store_food import search as food_search
from backend.utils.api_response import create_success_response, create_error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/food", tags=["food"])


class FoodSearchRequest(BaseModel):
    """Request for food search."""
    query: str = Field(..., description="Search query")
    k: int = Field(5, ge=1, le=20, description="Number of results")


class FoodDetailRequest(BaseModel):
    """Request for food detail."""
    id: str = Field(..., description="UUID or native_id")


@router.post("/search", response_model=dict)
async def search_foods(req: FoodSearchRequest) -> dict:
    """
    Search for food items using semantic search.

    Example:
        POST /api/food/search
        {
            "query": "sweet potato casserole",
            "k": 5
        }
    """
    try:
        # Ensure index is loaded
        if not food_search.is_ready():
            food_search.load()

        # Perform search
        results = food_search.semantic_search(req.query, k=req.k)

        return create_success_response({'results': results, 'count': len(results)})

    except Exception as e:
        logger.error(f"Food search failed: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))


@router.post("/detail", response_model=dict)
async def get_food_detail(req: FoodDetailRequest) -> dict:
    """
    Get detailed information about a specific food item.

    Example:
        POST /api/food/detail
        {
            "id": "abc-123-uuid"
        }
    """
    try:
        # Ensure index is loaded
        if not food_search.is_ready():
            food_search.load()

        # Get from metadata
        if food_search._metadata and req.id in food_search._metadata:
            return create_success_response(food_search._metadata[req.id])

        # Try searching by native_id
        for uuid, meta in (food_search._metadata or {}).items():
            if meta.get('native_id') == req.id:
                return create_success_response(meta)

        return create_error_response('NOT_FOUND', f"Food item not found: {req.id}")

    except Exception as e:
        logger.error(f"Failed to get food detail: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))


@router.get("/stats", response_model=dict)
async def get_stats() -> dict:
    """Get statistics about the food index."""
    try:
        if not food_search.is_ready():
            food_search.load()

        data = {
            "total_items": len(food_search._ids) if food_search._ids else 0,
            "index_loaded": food_search.is_ready(),
            "embedding_dim": 384
        }
        return create_success_response(data)

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))

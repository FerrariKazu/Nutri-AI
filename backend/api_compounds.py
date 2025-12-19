"""
FastAPI endpoints for compound search and retrieval.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging

from backend.vector_store_compound import search as compound_search
from backend.compound_loader import pubchem_client, datastore as compound_datastore
from backend.utils.api_response import create_success_response, create_error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compound", tags=["compound"])


class CompoundSearchRequest(BaseModel):
    """Request for compound search."""
    query: str = Field(..., description="Search query (name, formula, property)")
    k: int = Field(5, ge=1, le=20, description="Number of results")


class CompoundDetailRequest(BaseModel):
    """Request for compound detail."""
    id: str = Field(..., description="UUID, CID, or compound name")
    auto_enrich: bool = Field(True, description="Fetch from PubChem if not cached")


@router.post("/search", response_model=dict)
async def search_compounds(req: CompoundSearchRequest) -> dict:
    """
    Semantic search for chemical compounds.

    Example:
        POST /api/compound/search
        {
            "query": "lycopene antioxidant",
            "k": 5
        }
    """
    try:
        # Ensure index is loaded
        if not compound_search.is_ready():
            compound_search.load()

        # Perform search
        results = compound_search.semantic_search(req.query, k=req.k)

        return create_success_response({'results': results, 'count': len(results)})

    except Exception as e:
        logger.error(f"Compound search failed: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))


@router.post("/detail", response_model=dict)
async def get_compound_detail(req: CompoundDetailRequest) -> dict:
    """
    Get detailed information about a compound.

    Auto-enrichment: If compound not in local DB and auto_enrich=True,
    fetches from PubChem and caches result.

    Example:
        POST /api/compound/detail
        {
            "id": "2519",  // PubChem CID for caffeine
            "auto_enrich": true
        }
    """
    try:
        datastore = compound_datastore.get_datastore()

        # Try to parse as CID
        try:
            cid = int(req.id)
            cached = datastore.get_by_cid(cid)

            if cached:
                return create_success_response(cached['data'])

            # Auto-enrich from PubChem
            if req.auto_enrich:
                logger.info(f"Auto-enriching CID {cid} from PubChem")
                pubchem_data = pubchem_client.fetch_compound_summary(cid)

                if pubchem_data:
                    # Save to cache
                    name = pubchem_data.get('iupac_name') or f"compound_{cid}"
                    datastore.save_compound(name, cid, pubchem_data)

                    return create_success_response(pubchem_data)

                return create_error_response('NOT_FOUND', f"Compound CID {cid} not found in PubChem")

        except ValueError:
            # Not a CID, try as name
            pass

        # Try as name
        cached = datastore.get_by_name(req.id)
        if cached:
            return create_success_response(cached['data'])

        # Check if it's a UUID in compound index
        if compound_search.is_ready():
            if compound_search._metadata and req.id in compound_search._metadata:
                return create_success_response(compound_search._metadata[req.id])

        # Auto-enrich by name
        if req.auto_enrich:
            logger.info(f"Auto-enriching compound '{req.id}' from PubChem")
            pubchem_data = pubchem_client.fetch_compound_by_name(req.id)

            if pubchem_data:
                cid = pubchem_data.get('cid', 0)
                datastore.save_compound(req.id, cid, pubchem_data)
                return create_success_response(pubchem_data)

        return create_error_response('NOT_FOUND', f"Compound not found: {req.id}")

    except Exception as e:
        logger.error(f"Failed to get compound detail: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))


@router.get("/stats", response_model=dict)
async def get_compound_stats() -> dict:
    """Get statistics about the compound index."""
    try:
        datastore = compound_datastore.get_datastore()

        stats = {
            "cached_compounds": datastore.count(),
            "index_loaded": compound_search.is_ready()
        }

        if compound_search.is_ready():
            stats["total_items"] = len(compound_search._ids) if compound_search._ids else 0

        return create_success_response(stats)

    except Exception as e:
        logger.error(f"Failed to get compound stats: {e}")
        return create_error_response('INTERNAL_ERROR', str(e))

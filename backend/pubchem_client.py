"""
PubChem API Client for Nutri

Provides strict, verifiable compound resolution with:
- Hard timeouts (2s per request)
- Structured error types
- Response caching
- Schema validation

Zero hallucination tolerance: every compound must trace to PubChem.
"""

import logging
import hashlib
import time
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

# ============================================================================
# EXCEPTIONS
# ============================================================================

class PubChemError(Exception):
    """Base exception for PubChem operations"""
    pass

class PubChemNotFound(PubChemError):
    """Compound not found in PubChem database"""
    pass

class PubChemTimeout(PubChemError):
    """PubChem API request timed out"""
    pass

class PubChemRateLimited(PubChemError):
    """PubChem API rate limit exceeded"""
    pass

# ============================================================================
# SCHEMAS
# ============================================================================

class CompoundProperties(BaseModel):
    """Validated PubChem compound properties"""
    cid: int = Field(..., description="PubChem Compound ID")
    molecular_formula: Optional[str] = Field(None, alias="MolecularFormula")
    molecular_weight: Optional[float] = Field(None, alias="MolecularWeight")
    iupac_name: Optional[str] = Field(None, alias="IUPACName")
    canonical_smiles: Optional[str] = Field(None, alias="CanonicalSMILES")
    
    class Config:
        populate_by_name = True

class CompoundSearchResult(BaseModel):
    """Search result from PubChem"""
    cid: int
    name: str

# ============================================================================
# CACHE
# ============================================================================

@dataclass
class CacheEntry:
    """Cached compound data with TTL"""
    data: Any
    timestamp: datetime
    ttl_hours: int = 24
    
    def is_expired(self) -> bool:
        """Check if cache entry is stale"""
        expiry = self.timestamp + timedelta(hours=self.ttl_hours)
        return datetime.now() > expiry
    
    def freshness_weight(self) -> float:
        """Calculate freshness weight for confidence scoring"""
        age_hours = (datetime.now() - self.timestamp).total_seconds() / 3600
        if age_hours < 1:
            return 1.0
        elif age_hours < 24:
            return 0.95
        elif age_hours < 72:
            return 0.8
        else:
            return 0.6

class CompoundCache:
    """In-memory cache for PubChem responses"""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Retrieve cached entry if not expired"""
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            self._hits += 1
            logger.debug(f"[PUBCHEM_CACHE] HIT: {key}")
            return entry
        elif entry:
            # Expired entry
            del self._cache[key]
        self._misses += 1
        return None
    
    def set(self, key: str, data: Any, ttl_hours: int = 24):
        """Store data in cache"""
        self._cache[key] = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            ttl_hours=ttl_hours
        )
        logger.debug(f"[PUBCHEM_CACHE] SET: {key}")
    
    def stats(self) -> Dict[str, int]:
        """Return cache statistics"""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0
        }

# ============================================================================
# CLIENT
# ============================================================================

class PubChemClient:
    """
    Strict PubChem API client with hard timeouts and comprehensive error handling.
    
    Design principles:
    - Hard 2s timeout per request
    - Mandatory caching to reduce API load
    - Explicit error types for each failure mode
    - Zero silent fallbacks
    """
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    TIMEOUT = 2.0  # Hard timeout in seconds
    
    def __init__(self, cache_ttl_hours: int = 72):
        self.cache = CompoundCache()
        self.cache_ttl = cache_ttl_hours
        self._client = httpx.Client(timeout=self.TIMEOUT)
        logger.info(f"✅ [PUBCHEM] Client initialized (timeout={self.TIMEOUT}s, cache_ttl={cache_ttl_hours}h)")
    
    def search_compound(self, name: str) -> int:
        """
        Search for compound by name and return CID.
        
        Args:
            name: Compound name (e.g., "lycopene", "vitamin C")
            
        Returns:
            PubChem Compound ID (CID)
            
        Raises:
            PubChemNotFound: Compound not in database
            PubChemTimeout: Request exceeded 2s timeout
            PubChemRateLimited: API quota exceeded
        """
        cache_key = f"search:{name.lower()}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"[PUBCHEM] Search cache hit: {name} → CID {cached.data}")
            return cached.data
        
        url = f"{self.BASE_URL}/compound/name/{name}/cids/JSON"
        
        try:
            start_time = time.time()
            response = self._client.get(url)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 404:
                logger.warning(f"❌ [PUBCHEM] Not found: {name}")
                raise PubChemNotFound(f"Compound '{name}' not found in PubChem")
            
            if response.status_code == 429:
                logger.error(f"❌ [PUBCHEM] Rate limited for: {name}")
                raise PubChemRateLimited("PubChem API rate limit exceeded")
            
            response.raise_for_status()
            data = response.json()
            
            cid = data["IdentifierList"]["CID"][0]
            self.cache.set(cache_key, cid, self.cache_ttl)
            
            logger.info(f"✅ [PUBCHEM] Resolved: {name} → CID {cid} ({elapsed_ms}ms)")
            return cid
            
        except httpx.TimeoutException:
            logger.error(f"⏱️ [PUBCHEM] Timeout searching: {name}")
            raise PubChemTimeout(f"PubChem search timed out for '{name}' (>{self.TIMEOUT}s)")
        except httpx.HTTPError as e:
            logger.error(f"❌ [PUBCHEM] HTTP error: {e}")
            raise PubChemError(f"PubChem API error: {e}")
    
    def get_compound_properties(self, cid: int) -> CompoundProperties:
        """
        Retrieve compound properties by CID.
        
        Args:
            cid: PubChem Compound ID
            
        Returns:
            Validated compound properties
            
        Raises:
            PubChemNotFound: Invalid CID
            PubChemTimeout: Request exceeded timeout
        """
        cache_key = f"props:{cid}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"[PUBCHEM] Properties cache hit: CID {cid}")
            return cached.data
        
        url = f"{self.BASE_URL}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES/JSON"
        
        try:
            start_time = time.time()
            response = self._client.get(url)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 404:
                logger.warning(f"❌ [PUBCHEM] Invalid CID: {cid}")
                raise PubChemNotFound(f"CID {cid} not found")
            
            response.raise_for_status()
            data = response.json()
            
            props_data = data["PropertyTable"]["Properties"][0]
            props_data["cid"] = cid
            
            props = CompoundProperties(**props_data)
            self.cache.set(cache_key, props, self.cache_ttl)
            
            logger.info(f"✅ [PUBCHEM] Properties retrieved: CID {cid} ({elapsed_ms}ms)")
            return props
            
        except httpx.TimeoutException:
            logger.error(f"⏱️ [PUBCHEM] Timeout getting properties: CID {cid}")
            raise PubChemTimeout(f"PubChem properties request timed out for CID {cid}")
        except httpx.HTTPError as e:
            logger.error(f"❌ [PUBCHEM] HTTP error: {e}")
            raise PubChemError(f"PubChem API error: {e}")
    
    def resolve_compound(self, name: str) -> tuple[int, CompoundProperties]:
        """
        Convenience method: search + get properties in one call.
        
        Returns:
            (CID, CompoundProperties)
        """
        cid = self.search_compound(name)
        props = self.get_compound_properties(cid)
        return cid, props
    
    def health_check(self) -> bool:
        """
        Verify PubChem API connectivity.
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Try to resolve a common compound
            self.search_compound("water")
            logger.info("✅ [PUBCHEM] Health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ [PUBCHEM] Health check failed: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics for monitoring"""
        return self.cache.stats()
    
    def __del__(self):
        """Cleanup client on deletion"""
        try:
            self._client.close()
        except:
            pass


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_pubchem_client: Optional[PubChemClient] = None

def get_pubchem_client() -> PubChemClient:
    """Get or create global PubChem client instance"""
    global _pubchem_client
    if _pubchem_client is None:
        _pubchem_client = PubChemClient()
    return _pubchem_client


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Quick verification
    print("Testing PubChem Client...")
    
    client = get_pubchem_client()
    
    # Test 1: Search common compound
    try:
        cid = client.search_compound("lycopene")
        print(f"✅ Lycopene CID: {cid}")
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    # Test 2: Get properties
    try:
        props = client.get_compound_properties(446925)  # Lycopene CID
        print(f"✅ Lycopene formula: {props.molecular_formula}")
    except Exception as e:
        print(f"❌ Properties failed: {e}")
    
    # Test 3: Not found
    try:
        client.search_compound("nonexistent_compound_xyz_123")
    except PubChemNotFound as e:
        print(f"✅ Not found handled correctly: {e}")
    
    # Cache stats
    print(f"📊 Cache stats: {client.get_cache_stats()}")

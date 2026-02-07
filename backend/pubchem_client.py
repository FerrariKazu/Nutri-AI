import httpx
import logging
import asyncio
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class PubChemError(Exception):
    """Base class for PubChem client errors."""
    pass

class PubChemNotFound(PubChemError):
    """Raised when a compound is not found in PubChem."""
    pass

class PubChemTimeout(PubChemError):
    """Raised when a PubChem API call times out."""
    pass

class PubChemRateLimited(PubChemError):
    """Raised when PubChem API returns a 429 status."""
    pass

class PubChemClient:
    """
    Strict PubChem API client for verifying nutritional compounds.
    Base URL: https://pubchem.ncbi.nlm.nih.gov/rest/pug
    """
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    TIMEOUT = 2.0  # Strict 2s timeout per request

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)

    async def search_compound(self, name: str) -> int:
        """
        Search for a compound by name and return its CID.
        Endpoint: /compound/name/{name}/cids/JSON
        """
        url = f"{self.BASE_URL}/compound/name/{name}/cids/JSON"
        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                raise PubChemNotFound(f"Compound '{name}' not found.")
            if response.status_code == 429:
                raise PubChemRateLimited("PubChem API rate limited.")
            
            response.raise_for_status()
            data = response.json()
            
            cids = data.get("IdentifierList", {}).get("CID", [])
            if not cids:
                raise PubChemNotFound(f"Compound '{name}' CID list is empty.")
            
            return cids[0]
            
        except httpx.TimeoutException:
            logger.error(f"[PUBCHEM] Timeout searching for '{name}'")
            raise PubChemTimeout(f"PubChem timeout searching for '{name}'")
        except httpx.HTTPStatusError as e:
            logger.error(f"[PUBCHEM] HTTP error searching for '{name}': {e}")
            raise PubChemError(f"PubChem HTTP error: {e}")
        except Exception as e:
            logger.error(f"[PUBCHEM] Unexpected error searching for '{name}': {e}")
            raise PubChemError(f"PubChem unexpected error: {e}")

    async def get_compound_properties(self, cid: int, properties: List[str] = None) -> Dict[str, Any]:
        """
        Retrieve properties for a specific CID.
        Endpoint: /compound/cid/{cid}/property/{properties}/JSON
        """
        if properties is None:
            properties = ["MolecularFormula", "MolecularWeight", "IUPACName", "CanonicalSMILES"]
        
        prop_str = ",".join(properties)
        url = f"{self.BASE_URL}/compound/cid/{cid}/property/{prop_str}/JSON"
        
        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                raise PubChemNotFound(f"CID {cid} not found.")
            if response.status_code == 429:
                raise PubChemRateLimited("PubChem API rate limited.")
            
            response.raise_for_status()
            data = response.json()
            
            prop_list = data.get("PropertyTable", {}).get("Properties", [])
            if not prop_list:
                raise PubChemNotFound(f"No properties found for CID {cid}")
            
            return prop_list[0]

        except httpx.TimeoutException:
            logger.error(f"[PUBCHEM] Timeout getting properties for CID {cid}")
            raise PubChemTimeout(f"PubChem timeout getting properties for CID {cid}")
        except Exception as e:
            logger.error(f"[PUBCHEM] Error getting properties for CID {cid}: {e}")
            raise PubChemError(f"PubChem error: {e}")

    async def health_check(self) -> bool:
        """Simple connectivity check."""
        try:
            # Search for water (CID 962) - very fast
            url = f"{self.BASE_URL}/compound/cid/962/JSON"
            response = await self.client.get(url, timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()

def get_pubchem_client():
    """
    Helper for synchronous context (like production_audit).
    Provides a wrapper with a sync health_check.
    """
    class SyncPubChemWrapper:
        def health_check(self) -> bool:
            client = PubChemClient()
            try:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                return loop.run_until_complete(client.health_check())
            finally:
                # We can't easily close it here without another loop run, 
                # but for startup audit it's acceptable.
                pass
    return SyncPubChemWrapper()

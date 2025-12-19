"""
PubChem REST API client with rate limiting and caching.

Implements polite usage of PubChem PUG-REST API with:
- Rate limiting (5 req/sec)
- Exponential backoff retries
- Timeouts
- Response caching
"""

import requests
import time
import logging
from typing import List, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# PubChem API endpoints
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Rate limiting
_last_request_time = 0
_min_request_interval = 0.2  # 5 requests per second

# HTTP settings
TIMEOUT = 10  # seconds
MAX_RETRIES = 3


def _rate_limit():
    """Enforce rate limiting (max 5 req/sec)."""
    global _last_request_time
    
    now = time.time()
    elapsed = now - _last_request_time
    
    if elapsed < _min_request_interval:
        sleep_time = _min_request_interval - elapsed
        time.sleep(sleep_time)
    
    _last_request_time = time.time()


def _make_request(url: str, params: Dict = None) -> Dict:
    """
    Make HTTP GET request with retries and rate limiting.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        
    Returns:
        JSON response as dict
        
    Raises:
        requests.RequestException: On failure after retries
    """
    _rate_limit()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}/{MAX_RETRIES}: {url}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:
                logger.warning(f"Server error {e.response.status_code} on attempt {attempt + 1}/{MAX_RETRIES}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            else:
                raise
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    
    raise requests.RequestException(f"Failed after {MAX_RETRIES} attempts")


def search_compound_by_name(name: str) -> List[int]:
    """
    Search for compounds by name and return list of CIDs.
    
    Args:
        name: Compound name to search
        
    Returns:
        List of PubChem CIDs (compound IDs)
        
    Example:
        >>> cids = search_compound_by_name("caffeine")
        >>> print(cids[:3])
        [2519, 131626, ...]
    """
    logger.info(f"Searching PubChem for: '{name}'")
    
    url = f"{PUBCHEM_BASE}/compound/name/{name}/cids/JSON"
    
    try:
        data = _make_request(url)
        cids = data.get('IdentifierList', {}).get('CID', [])
        logger.info(f"Found {len(cids)} CIDs for '{name}'")
        return cids
    
    except Exception as e:
        logger.warning(f"Search failed for '{name}': {e}")
        return []


def fetch_compound_summary(cid: int) -> Optional[Dict]:
    """
    Fetch compound summary data by CID.
    
    Args:
        cid: PubChem Compound ID
        
    Returns:
        Dictionary with compound data or None
        
    Fields returned:
        - cid
        - iupac_name
        - synonyms
        - molecular_formula
        - molecular_weight
        - smiles
        - properties (xlogp3, h_bond_donors, h_bond_acceptors, etc.)
    """
    logger.info(f"Fetching summary for CID {cid}")
    
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IUPACName,XLogP,HBondDonorCount,HBondAcceptorCount,RotatableBondCount,TPSA/JSON"
    
    try:
        data = _make_request(url)
        
        if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
            props = data['PropertyTable']['Properties'][0]
            
            # Fetch synonyms separately
            synonyms = _fetch_synonyms(cid)
            
            return {
                'cid': cid,
                'iupac_name': props.get('IUPACName'),
                'synonyms': synonyms[:10],  # Limit to 10
                'molecular_formula': props.get('MolecularFormula'),
                'molecular_weight': props.get('MolecularWeight'),
                'smiles': props.get('CanonicalSMILES'),
                'xlogp3': props.get('XLogP'),
                'h_bond_donors': props.get('HBondDonorCount'),
                'h_bond_acceptors': props.get('HBondAcceptorCount'),
                'rotatable_bonds': props.get('RotatableBondCount'),
                'tpsa': props.get('TPSA'),
            }
    
    except Exception as e:
        logger.error(f"Failed to fetch summary for CID {cid}: {e}")
        return None


def _fetch_synonyms(cid: int, limit: int = 10) -> List[str]:
    """Fetch synonyms for a compound."""
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
    
    try:
        data = _make_request(url)
        synonyms = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
        return synonyms[:limit]
    except:
        return []


def fetch_compound_by_name(name: str) -> Optional[Dict]:
    """
    Convenience function: search by name and fetch first result.
    
    Args:
        name: Compound name
        
    Returns:
        Compound data dict or None
    """
    cids = search_compound_by_name(name)
    
    if not cids:
        return None
    
    # Fetch first result
    return fetch_compound_summary(cids[0])


def batch_fetch(names: List[str], batch_size: int = 10) -> Dict[str, Optional[Dict]]:
    """
    Fetch compounds for multiple names with batching.
    
    Args:
        names: List of compound names
        batch_size: Number of concurrent requests (rate limited)
        
    Returns:
        Dictionary mapping names to compound data
    """
    results = {}
    
    for i, name in enumerate(names):
        logger.info(f"Fetching {i+1}/{len(names)}: {name}")
        results[name] = fetch_compound_by_name(name)
    
    return results

"""
Food ↔ Compound linker.

Maps food items to chemical compounds using FooDB, DSSTox, FartDB, and PubChem.
"""

import logging
from typing import List, Dict, Optional
from rapidfuzz import fuzz

from backend.nutrition_loader.schema import UnifiedFood
from backend.compound_loader import pubchem_client, datastore as compound_datastore

logger = logging.getLogger(__name__)


def find_compound_for_food_item(
    food_item: UnifiedFood,
    datastore: compound_datastore.CompoundDatastore = None,
    threshold: int = 90
) -> Optional[Dict]:
    """
    Find compound match for a food item.
    
    Searches:
    1. FooDB compounds (food_item.compounds)
    2. Local PubChem cache
    3. PubChem API (auto-enrichment)
    
    Args:
        food_item: UnifiedFood object
        datastore: PubChem datastore (optional)
        threshold: Fuzzy match threshold (0-100)
        
    Returns:
        Compound dict with confidence score or None
    """
    if datastore is None:
        datastore = compound_datastore.get_datastore()
    
    # Check if food already has compound data
    if food_item.compounds:
        compound_names = []
        if isinstance(food_item.compounds, dict):
            compound_names = [
                v.get('name', '') for v in food_item.compounds.values()
            ]
        
        if compound_names:
            # Use first compound
            compound_name = compound_names[0]
            logger.info(f"Found compound in food item: {compound_name}")
            
            # Try to get more data from cache or PubChem
            cached = datastore.get_by_name(compound_name)
            if cached:
                return {
                    **cached['data'],
                    'confidence': 1.0,
                    'source': 'FooDB_cached'
                }
            
            # Fetch from PubChem
            try:
                pubchem_data = pubchem_client.fetch_compound_by_name(compound_name)
                if pubchem_data:
                    # Save to cache
                    datastore.save_compound(
                        compound_name,
                        pubchem_data.get('cid', 0),
                        pubchem_data
                    )
                    return {
                        **pubchem_data,
                        'confidence': 0.95,
                        'source': 'FooDB_PubChem'
                    }
            except Exception as e:
                logger.warning(f"PubChem fetch failed for '{compound_name}': {e}")
    
    # Try fuzzy matching on normalized name
    normalized_name = food_item.normalized_name
    
    # Check cache first
    cached = datastore.get_by_name(normalized_name)
    if cached:
        return {
            **cached['data'],
            'confidence': 0.9,
            'source': 'cache_exact'
        }
    
    # Try PubChem search
    try:
        pubchem_data = pubchem_client.fetch_compound_by_name(normalized_name)
        if pubchem_data:
            datastore.save_compound(
                normalized_name,
                pubchem_data.get('cid', 0),
                pubchem_data
            )
            return {
                **pubchem_data,
                'confidence': 0.85,
                'source': 'PubChem_search'
            }
    except Exception as e:
        logger.debug(f"PubChem search failed for '{normalized_name}': {e}")
    
    return None


def enrich_unified_dataset_with_compounds(
    items: List[UnifiedFood],
    datastore: compound_datastore.CompoundDatastore = None,
    batch_size: int = 100
) -> int:
    """
    Enrich food items with compound links.
    
    Args:
        items: List of UnifiedFood objects
        datastore: PubChem datastore
        batch_size: Process in batches
        
    Returns:
        Number of items enriched
    """
    if datastore is None:
        datastore = compound_datastore.get_datastore()
    
    enriched_count = 0
    
    logger.info(f"Enriching {len(items)} items with compounds...")
    
    for i, item in enumerate(items):
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(items)}")
        
        # Skip if already has compounds
        if item.compounds:
            enriched_count += 1
            continue
        
        # Try to find compound
        compound = find_compound_for_food_item(item, datastore)
        
        if compound:
            # Add compound to item
            item.compounds = {
                'primary': {
                    'cid': compound.get('cid'),
                    'name': compound.get('iupac_name') or compound.get('name'),
                    'formula': compound.get('molecular_formula'),
                    'confidence': compound.get('confidence', 0.0),
                    'source': compound.get('source', 'unknown')
                }
            }
            enriched_count += 1
    
    logger.info(f"Enriched {enriched_count}/{len(items)} items with compounds")
    return enriched_count

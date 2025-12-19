"""
FooDB data loader for food compounds, flavors, and content.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Path to FooDB directory
FOODB_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "FoodDB"

# Cache for loaded data
_compound_cache = {}
_flavor_cache = {}
_food_cache = {}


def load_compounds() -> Dict[int, Dict]:
    """Load compound data from FooDB."""
    global _compound_cache
    
    if _compound_cache:
        return _compound_cache
    
    try:
        compound_file = FOODB_PATH / "Compound.csv"
        with open(compound_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                compound_id = int(row['id'])
                _compound_cache[compound_id] = {
                    'id': compound_id,
                    'name': row.get('name', ''),
                    'public_id': row.get('public_id', ''),
                    'moldb_smiles': row.get('moldb_smiles', ''),
                    'state': row.get('state', ''),
                    'description': row.get('description', ''),
                }
        
        logger.info(f"Loaded {len(_compound_cache)} compounds from FooDB")
        return _compound_cache
        
    except Exception as e:
        logger.error(f"Error loading FooDB compounds: {e}")
        return {}


def load_flavors() -> Dict[int, Dict]:
    """Load flavor data from FooDB."""
    global _flavor_cache
    
    if _flavor_cache:
        return _flavor_cache
    
    try:
        flavor_file = FOODB_PATH / "Flavor.csv"
        with open(flavor_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                flavor_id = int(row['id'])
                _flavor_cache[flavor_id] = {
                    'id': flavor_id,
                    'name': row.get('name', ''),
                    'flavor_group': row.get('flavor_group', ''),
                }
        
        logger.info(f"Loaded {len(_flavor_cache)} flavors from FooDB")
        return _flavor_cache
        
    except Exception as e:
        logger.error(f"Error loading FooDB flavors: {e}")
        return {}


def search_compound(name: str) -> Optional[Dict[str, Any]]:
    """
    Search for a compound by name in FooDB.
    
    Args:
        name: Compound name to search for
        
    Returns:
        Dict with compound data or None if not found
    """
    compounds = load_compounds()
    name_lower = name.lower()
    
    # Search by name
    for compound in compounds.values():
        if name_lower in compound['name'].lower():
            return compound
    
    return None


def get_compound_flavors(compound_id: int) -> List[str]:
    """
    Get flavors associated with a compound.
    
    Args:
        compound_id: FooDB compound ID
        
    Returns:
        List of flavor names
    """
    try:
        flavors_file = FOODB_PATH / "CompoundsFlavor.csv"
        flavor_data = load_flavors()
        compound_flavors = []
        
        with open(flavors_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row['compound_id']) == compound_id:
                    flavor_id = int(row['flavor_id'])
                    if flavor_id in flavor_data:
                        compound_flavors.append(flavor_data[flavor_id]['name'])
        
        return compound_flavors
        
    except Exception as e:
        logger.error(f"Error getting compound flavors: {e}")
        return []


def get_food_compounds(food_name: str) -> List[Dict]:
    """
    Get compounds found in a specific food.
    
    Args:
        food_name: Name of the food
        
    Returns:
        List of compound dictionaries
    """
    try:
        # Load foods
        food_file = FOODB_PATH / "Food.csv"
        food_id = None
        
        with open(food_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if food_name.lower() in row.get('name', '').lower():
                    food_id = int(row['id'])
                    break
        
        if not food_id:
            return []
        
        # Get compounds for this food
        content_file = FOODB_PATH / "Content.csv"
        compounds = load_compounds()
        food_compounds = []
        
        with open(content_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row.get('food_id', 0)) == food_id:
                    compound_id = int(row.get('source_id', 0))
                    if compound_id in compounds:
                        food_compounds.append(compounds[compound_id])
        
        return food_compounds[:20]  # Limit to 20 compounds
        
    except Exception as e:
        logger.error(f"Error getting food compounds: {e}")
        return []

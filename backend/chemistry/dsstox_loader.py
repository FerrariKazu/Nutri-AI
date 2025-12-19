"""
DSSTox data loader for toxicology and safety information.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import openpyxl

logger = logging.getLogger(__name__)

# Path to DSSTox directory
DSSTOX_PATH = Path(__file__).parent.parent.parent / "DSSTox"

# Cache for loaded data
_compound_cache = {}


def load_dsstox_file(file_num: int = 1) -> List[Dict]:
    """
    Load a DSSTox Excel file.
    
    Args:
        file_num: File number (1-13)
        
    Returns:
        List of compound dictionaries
    """
    try:
        file_path = DSSTOX_PATH / f"DSSToxDump{file_num}.xlsx"
        
        if not file_path.exists():
            logger.warning(f"DSSTox file not found: {file_path}")
            return []
        
        workbook = openpyxl.load_workbook(file_path, read_only=True)
        sheet = workbook.active
        
        # Get headers from first row
        headers = [cell.value for cell in sheet[1]]
        
        compounds = []
        for row in sheet.iter_rows(min_row=2, max_row=1000, values_only=True):  # Limit to 1000 rows
            compound = {}
            for i, value in enumerate(row):
                if i < len(headers) and headers[i]:
                    compound[headers[i]] = value
            
            if compound:
                compounds.append(compound)
        
        logger.info(f"Loaded {len(compounds)} compounds from DSSToxDump{file_num}.xlsx")
        return compounds
        
    except Exception as e:
        logger.error(f"Error loading DSSTox file {file_num}: {e}")
        return []


def search_compound(name: str) -> Optional[Dict]:
    """
    Search for a compound in DSSTox data.
    
    Args:
        name: Compound name
        
    Returns:
        Dict with compound data or None
    """
    # Try loading first file (can be extended to search all files)
    compounds = load_dsstox_file(1)
    
    name_lower = name.lower()
    
    for compound in compounds:
        compound_name = str(compound.get('Preferred Name', '')).lower()
        if name_lower in compound_name:
            return compound
    
    return None


def get_safety_data(compound_name: str) -> Dict[str, Any]:
    """
    Get safety and toxicology data for a compound.
    
    Args:
        compound_name: Name of the compound
        
    Returns:
        Dict with safety data
    """
    compound = search_compound(compound_name)
    
    if not compound:
        return {
            'found': False,
            'message': f'No safety data found for {compound_name}'
        }
    
    return {
        'found': True,
        'compound': compound_name,
        'preferred_name': compound.get('Preferred Name', ''),
        'casrn': compound.get('CASRN', ''),
        'dtxsid': compound.get('DTXSID', ''),
        'molecular_formula': compound.get('Molecular Formula', ''),
        'molecular_weight': compound.get('Molecular Weight', ''),
    }

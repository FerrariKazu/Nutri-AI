"""
DSSTox loader - Toxicity database.

Loads DSSTox Excel files containing chemical toxicity and bioactivity data.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List
from uuid import uuid4

from .schema import UnifiedFood
from .normalizer import normalize_ingredient_name

logger = logging.getLogger(__name__)


def load_dsstox(folder_path: str, limit: int = None) -> List[UnifiedFood]:
    """
    Load DSSTox database from Excel files.
    
    DSSTox contains toxicity metrics and chemical safety information.
    
    Args:
        folder_path: Path to DSSTox folder
        limit: Optional limit on number of records
        
    Returns:
        List of UnifiedFood objects with toxicity data
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"DSSTox folder not found: {folder_path}")
    
    logger.info(f"Loading DSSTox from {folder_path}")
    
    # Find Excel files
    excel_files = list(folder.glob("*.xlsx")) + list(folder.glob("*.xls"))
    
    if not excel_files:
        logger.warning(f"No Excel files found in {folder_path}")
        return []
    
    all_foods = []
    
    for excel_file in excel_files:
        try:
            logger.info(f"Reading {excel_file.name}")
            
            # Read Excel with openpyxl engine
            df = pd.read_excel(excel_file, engine='openpyxl')
            
            for idx, row in df.iterrows():
                if limit and len(all_foods) >= limit:
                    break
                
                try:
                    food = _parse_dsstox_row(row)
                    if food:
                        all_foods.append(food)
                except Exception as e:
                    logger.debug(f"Skipping row {idx}: {e}")
            
            if limit and len(all_foods) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error reading {excel_file.name}: {e}")
    
    logger.info(f"Loaded {len(all_foods)} DSSTox records")
    return all_foods


def _parse_dsstox_row(row: pd.Series) -> UnifiedFood:
    """Parse DSSTox row into UnifiedFood with toxicity data."""
    
    # Extract ID
    native_id = None
    for id_col in ['dsstox_substance_id', 'dtxsid', 'casrn', 'id']:
        if id_col in row and pd.notna(row[id_col]):
            native_id = str(row[id_col])
            break
    
    # Extract name
    name = None
    for name_col in ['preferred_name', 'substance_name', 'chemical_name', 'name']:
        if name_col in row and pd.notna(row[name_col]):
            name = str(row[name_col])
            break
    
    if not name:
        return None
    
    normalized = normalize_ingredient_name(name)
    
    # Extract synonyms
    synonyms = []
    if 'substance_synonyms' in row and pd.notna(row['substance_synonyms']):
        syn_str = str(row['substance_synonyms'])
        synonyms = [s.strip() for s in syn_str.split('|') if s.strip()]
    
    # Extract toxicity data
    toxicity = {}
    
    tox_fields = {
        'oral_ld50': 'Oral LD50',
        'dermal_ld50': 'Dermal LD50',
        'inhalation_lc50': 'Inhalation LC50',
        'carcinogenicity': 'Carcinogenicity',
        'mutagenicity': 'Mutagenicity',
        'reproductive_toxicity': 'Reproductive Toxicity',
        'acute_toxicity': 'Acute Toxicity'
    }
    
    for field, label in tox_fields.items():
        if field in row and pd.notna(row[field]):
            toxicity[label] = str(row[field])
    
    # Generic toxicity score if available
    if 'hazard_score' in row and pd.notna(row['hazard_score']):
        try:
            toxicity['hazard_score'] = float(row['hazard_score'])
        except (ValueError, TypeError):
            pass
    
    # Create UnifiedFood
    food = UnifiedFood(
        uuid=uuid4(),
        native_id=native_id,
        source="DSSTox",
        name=name,
        normalized_name=normalized,
        synonyms=synonyms,
        nutrients={},
        compounds={},
        toxicity=toxicity,
        description=row.get('description') if 'description' in row else None,
        raw=row.to_dict()
    )
    
    return food

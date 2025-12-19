"""
FooDB loader - Food compound database.

Loads FooDB CSV files containing food compounds, nutrients, and phytochemicals.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict
from uuid import uuid4

from .schema import UnifiedFood
from .normalizer import normalize_ingredient_name

logger = logging.getLogger(__name__)


def load_foodb(folder_path: str, limit: int = None) -> List[UnifiedFood]:
    """
    Load FooDB database.
    
    FooDB contains detailed compound information for foods.
    
    Args:
        folder_path: Path to FooDB folder
        limit: Optional limit on number of records
        
    Returns:
        List of UnifiedFood objects with compound data
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"FooDB folder not found: {folder_path}")
    
    logger.info(f"Loading FooDB from {folder_path}")
    
    # Find relevant CSV files
    food_files = list(folder.glob("*food*.csv")) + list(folder.glob("*Food*.csv"))
    compound_files = list(folder.glob("*compound*.csv")) + list(folder.glob("*Compound*.csv"))
    
    if not food_files and not compound_files:
        logger.warning(f"No FooDB CSV files found in {folder_path}")
        return []
    
    all_foods = []
    
    # Load foods with compounds
    for csv_file in food_files + compound_files:
        try:
            logger.info(f"Reading {csv_file.name}")
            
            df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
            
            for idx, row in df.iterrows():
                if limit and len(all_foods) >= limit:
                    break
                
                try:
                    food = _parse_foodb_row(row)
                    if food:
                        all_foods.append(food)
                except Exception as e:
                    logger.debug(f"Skipping row {idx}: {e}")
            
            if limit and len(all_foods) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error reading {csv_file.name}: {e}")
    
    logger.info(f"Loaded {len(all_foods)} FooDB records")
    return all_foods


def _parse_foodb_row(row: pd.Series) -> UnifiedFood:
    """Parse FooDB row into UnifiedFood with compound data."""
    
    # Extract ID
    native_id = None
    for id_col in ['id', 'food_id', 'public_id']:
        if id_col in row and pd.notna(row[id_col]):
            native_id = str(row[id_col])
            break
    
    # Extract name
    name = None
    for name_col in ['name', 'food_name', 'description']:
        if name_col in row and pd.notna(row[name_col]):
            name = str(row[name_col])
            break
    
    if not name:
        return None
    
    normalized = normalize_ingredient_name(name)
    
    # Extract compounds
    compounds = {}
    
    # Look for compound-related columns
    compound_fields = ['compound_name', 'compound_id', 'cas_number', 'inchikey']
    for field in compound_fields:
        if field in row and pd.notna(row[field]):
            compound_name = str(row.get('compound_name', row[field]))
            compounds[compound_name] = {
                'name': compound_name,
                'cas': str(row.get('cas_number', '')),
                'inchikey': str(row.get('inchikey', '')),
                'amount': row.get('amount') or row.get('concentration'),
                'unit': row.get('unit', 'unknown')
            }
    
    # Create UnifiedFood
    food = UnifiedFood(
        uuid=uuid4(),
        native_id=native_id,
        source="FooDB",
        name=name,
        normalized_name=normalized,
        synonyms=[],
        nutrients={},
        compounds=compounds,
        description=row.get('description') if 'description' in row else None,
        raw=row.to_dict()
    )
    
    return food

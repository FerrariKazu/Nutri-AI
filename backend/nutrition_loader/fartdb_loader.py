"""
FartDB loader - Gas composition database.

Loads FartDB parquet file containing compound/gas composition data.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List
from uuid import uuid4

from .schema import UnifiedFood
from .normalizer import normalize_ingredient_name

logger = logging.getLogger(__name__)


def load_fartdb(parquet_path: str, limit: int = None) -> List[UnifiedFood]:
    """
    Load FartDB from parquet file.
    
    FartDB contains gas composition and volatile compound data.
    
    Args:
        parquet_path: Path to fartdb.parquet file
        limit: Optional limit on number of records
        
    Returns:
        List of UnifiedFood objects
    """
    path = Path(parquet_path)
    if not path.exists():
        raise FileNotFoundError(f"FartDB file not found: {parquet_path}")
    
    logger.info(f"Loading FartDB from {parquet_path}")
    
    try:
        # Read parquet
        df = pd.read_parquet(path)
        logger.info(f"Read {len(df)} rows from FartDB")
        
        all_foods = []
        
        for idx, row in df.iterrows():
            if limit and len(all_foods) >= limit:
                break
            
            try:
                food = _parse_fartdb_row(row)
                if food:
                    all_foods.append(food)
            except Exception as e:
                logger.debug(f"Skipping row {idx}: {e}")
        
        logger.info(f"Loaded {len(all_foods)} FartDB records")
        return all_foods
        
    except Exception as e:
        logger.error(f"Error loading FartDB: {e}")
        return []


def _parse_fartdb_row(row: pd.Series) -> UnifiedFood:
    """Parse FartDB row into UnifiedFood."""
    
    # Extract ID
    native_id = str(row.get('id', row.name))
    
    # Extract name
    name = row.get('name') or row.get('food_name') or row.get('description')
    if not name or pd.isna(name):
        return None
    
    name = str(name)
    normalized = normalize_ingredient_name(name)
    
    # Extract gas/compound composition
    compounds = {}
    
    # Common gas components
    gas_components = ['methane', 'hydrogen', 'co2', 'h2s', 'nitrogen']
    
    for component in gas_components:
        if component in row and pd.notna(row[component]):
            try:
                value = float(row[component])
                compounds[component] = {
                    'name': component,
                    'amount': value,
                    'unit': row.get(f'{component}_unit', 'ppm')
                }
            except (ValueError, TypeError):
                pass
    
    # Also check for generic 'compounds' column
    if 'compounds' in row and pd.notna(row['compounds']):
        try:
            compounds_str = str(row['compounds'])
            # Try parsing as JSON or comma-separated
            import json
            compounds.update(json.loads(compounds_str))
        except:
            pass
    
    # Create UnifiedFood
    food = UnifiedFood(
        uuid=uuid4(),
        native_id=native_id,
        source="FartDB",
        name=name,
        normalized_name=normalized,
        synonyms=[],
        nutrients={},
        compounds=compounds,
        description=f"Gas composition data for {name}",
        raw=row.to_dict()
    )
    
    return food

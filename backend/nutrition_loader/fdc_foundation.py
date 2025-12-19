"""
FDC Foundation Foods loader.

Loads USDA FoodData Central Foundation Foods dataset into UnifiedFood schema.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List
from uuid import uuid4

from .schema import UnifiedFood
from .normalizer import normalize_ingredient_name

logger = logging.getLogger(__name__)


def load_foundation(folder_path: str, limit: int = None) -> List[UnifiedFood]:
    """
    Load FDC Foundation Foods from CSV files.
    
    Args:
        folder_path: Path to FoundationFoods folder
        limit: Optional limit on number of records
        
    Returns:
        List of UnifiedFood objects
        
    Raises:
        FileNotFoundError: If folder doesn't exist
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Foundation Foods folder not found: {folder_path}")
    
    logger.info(f"Loading Foundation Foods from {folder_path}")
    
    # Find relevant CSV files
    food_files = list(folder.glob("*food*.csv")) + list(folder.glob("*Food*.csv"))
    
    if not food_files:
        logger.warning(f"No food CSV files found in {folder_path}")
        return []
    
    all_foods = []
    
    for csv_file in food_files:
        try:
            logger.info(f"Reading {csv_file.name}")
            
            # Read CSV with flexible encoding
            try:
                df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(csv_file, encoding='latin-1', low_memory=False)
            
            # Process rows
            for idx, row in df.iterrows():
                if limit and len(all_foods) >= limit:
                    break
                
                try:
                    food = _parse_foundation_row(row, csv_file.name)
                    if food:
                        all_foods.append(food)
                except Exception as e:
                    logger.debug(f"Skipping row {idx} in {csv_file.name}: {e}")
            
            if limit and len(all_foods) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error reading {csv_file.name}: {e}")
    
    logger.info(f"Loaded {len(all_foods)} Foundation Foods records")
    return all_foods


def _parse_foundation_row(row: pd.Series, source_file: str) -> UnifiedFood:
    """Parse a Foundation Foods row into UnifiedFood."""
    
    # Extract ID (try common column names)
    native_id = None
    for id_col in ['fdc_id', 'FDC_ID', 'id', 'ID', 'food_id']:
        if id_col in row and pd.notna(row[id_col]):
            native_id = str(row[id_col])
            break
    
    # Extract name
    name = None
    for name_col in ['description', 'Description', 'food_name', 'name', 'Name']:
        if name_col in row and pd.notna(row[name_col]):
            name = str(row[name_col])
            break
    
    if not name:
        return None
    
    # Normalize name
    normalized = normalize_ingredient_name(name)
    
    # Extract nutrients (look for common nutrient columns)
    nutrients = {}
    
    # Common nutrient mappings
    nutrient_mappings = {
        'Energy': 'calories',
        'energy': 'calories',
        'Protein': 'protein_g',
        'protein': 'protein_g',
        'Total lipid (fat)': 'fat_g',
        'fat': 'fat_g',
        'Carbohydrate, by difference': 'carbs_g',
        'carbohydrate': 'carbs_g',
        'Fiber, total dietary': 'fiber_g',
        'fiber': 'fiber_g',
        'Sugars, total': 'sugar_g',
        'sugar': 'sugar_g',
        'Sodium, Na': 'sodium_mg',
        'sodium': 'sodium_mg',
    }
    
    for col in row.index:
        col_lower = str(col).lower()
        val = row[col]
        
        # Try to match nutrients
        for pattern, key in nutrient_mappings.items():
            if pattern.lower() in col_lower and pd.notna(val):
                try:
                    nutrients[key] = float(val)
                except (ValueError, TypeError):
                    pass
    
    # Create UnifiedFood
    food = UnifiedFood(
        uuid=uuid4(),
        native_id=native_id,
        source="FDC_Foundation",
        name=name,
        normalized_name=normalized,
        synonyms=[],
        nutrients=nutrients,
        compounds={},
        toxicity={},
        description=None,
        category=row.get('food_category', None) if 'food_category' in row else None,
        raw=row.to_dict()
    )
    
    return food

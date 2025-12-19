"""
FDC Branded Foods loader.

Loads USDA FoodData Central Branded Foods dataset into UnifiedFood schema.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List
from uuid import uuid4

from .schema import UnifiedFood
from .normalizer import normalize_ingredient_name

logger = logging.getLogger(__name__)


def load_branded(folder_path: str, limit: int = None) -> List[UnifiedFood]:
    """
    Load FDC Branded Foods from CSV files.
    
    Branded foods include serving sizes and brand information.
    
    Args:
        folder_path: Path to BrandedFoods folder
        limit: Optional limit on number of records
        
    Returns:
        List of UnifiedFood objects
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Branded Foods folder not found: {folder_path}")
    
    logger.info(f"Loading Branded Foods from {folder_path}")
    
    # Find CSV files
    food_files = list(folder.glob("*branded*.csv")) + list(folder.glob("*Branded*.csv"))
    
    if not food_files:
        logger.warning(f"No branded food CSV files found in {folder_path}")
        return []
    
    all_foods = []
    
    for csv_file in food_files:
        try:
            logger.info(f"Reading {csv_file.name}")
            
            # Read with encoding detection
            try:
                df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(csv_file, encoding='latin-1', low_memory=False)
            
            # Process rows
            for idx, row in df.iterrows():
                if limit and len(all_foods) >= limit:
                    break
                
                try:
                    food = _parse_branded_row(row, csv_file.name)
                    if food:
                        all_foods.append(food)
                except Exception as e:
                    logger.debug(f"Skipping row {idx}: {e}")
            
            if limit and len(all_foods) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error reading {csv_file.name}: {e}")
    
    logger.info(f"Loaded {len(all_foods)} Branded Foods records")
    return all_foods


def _parse_branded_row(row: pd.Series, source_file: str) -> UnifiedFood:
    """Parse a Branded Foods row into UnifiedFood."""
    
    # Extract ID
    native_id = None
    for id_col in ['fdc_id', 'FDC_ID', 'id', 'gtin_upc']:
        if id_col in row and pd.notna(row[id_col]):
            native_id = str(row[id_col])
            break
    
    # Extract name
    name = None
    for name_col in ['description', 'branded_food_category', 'brand_name']:
        if name_col in row and pd.notna(row[name_col]):
            name = str(row[name_col])
            break
    
    if not name:
        return None
    
    # Add brand if available
    brand = row.get('brand_owner') or row.get('brand_name')
    if brand and pd.notna(brand):
        name = f"{brand} {name}"
    
    # Normalize
    normalized = normalize_ingredient_name(name)
    
    # Extract serving size
    serving_size = None
    for serving_col in ['serving_size', 'household_serving_fulltext']:
        if serving_col in row and pd.notna(row[serving_col]):
            serving_size = str(row[serving_col])
            break
    
    # Extract nutrients
    nutrients = {}
    nutrient_cols = {
        'energy': 'calories',
        'protein': 'protein_g',
        'fat': 'fat_g',
        'carbohydrate': 'carbs_g',
        'fiber': 'fiber_g',
        'sugars': 'sugar_g',
        'sodium': 'sodium_mg',
    }
    
    for col in row.index:
        col_lower = str(col).lower()
        for pattern, key in nutrient_cols.items():
            if pattern in col_lower and pd.notna(row[col]):
                try:
                    nutrients[key] = float(row[col])
                except (ValueError, TypeError):
                    pass
    
    # Create UnifiedFood
    food = UnifiedFood(
        uuid=uuid4(),
        native_id=native_id,
        source="FDC_Branded",
        name=name,
        normalized_name=normalized,
        synonyms=[],
        nutrients=nutrients,
        serving_size=serving_size,
        category=row.get('branded_food_category') if 'branded_food_category' in row else None,
        raw=row.to_dict()
    )
    
    return food

"""
Master loader for all nutrition datasets.

Coordinates loading from all sources and produces unified dataset.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

from .schema import UnifiedFood
from .fdc_foundation import load_foundation

logger = logging.getLogger(__name__)


def load_all(root_paths: Dict[str, str], limit_per_source: int = None) -> List[UnifiedFood]:
    """
    Load and combine all nutrition datasets.
    
    Args:
        root_paths: Dictionary mapping source names to paths:
            {
                "fdc_foundation": "FoodData_Central/FoundationFoods",
                "fdc_branded": "FoodData_Central/BrandedFoods",
                "foodb": "FooDB",
                "fartdb": "FartDB/fartdb.parquet",
                "dsstox": "DSSTox"
            }
        limit_per_source: Optional limit per data source
        
    Returns:
        Combined list of UnifiedFood objects
        
    Example:
        >>> paths = {
        ...     "fdc_foundation": "FoodData_Central/FoundationFoods",
        ...     "fdc_branded": "FoodData_Central/BrandedFoods"
        ... }
        >>> foods = load_all(paths, limit_per_source=1000)
    """
    all_foods = []
    
    # Import loaders lazily to avoid circular imports
    from .fdc_branded import load_branded
    from .foodb_loader import load_foodb
    from .fartdb_loader import load_fartdb
    from .dsstox_loader import load_dsstox
    
    # Load FDC Foundation (primary source)
    if "fdc_foundation" in root_paths:
        logger.info("Loading FDC Foundation Foods...")
        try:
            foundation_foods = load_foundation(
                root_paths["fdc_foundation"],
                limit=limit_per_source
            )
            all_foods.extend(foundation_foods)
            logger.info(f"Added {len(foundation_foods)} Foundation Foods")
        except Exception as e:
            logger.error(f"Failed to load Foundation Foods: {e}")
    
    # Load FDC Branded
    if "fdc_branded" in root_paths:
        logger.info("Loading FDC Branded Foods...")
        try:
            branded_foods = load_branded(
                root_paths["fdc_branded"],
                limit=limit_per_source
            )
            all_foods.extend(branded_foods)
            logger.info(f"Added {len(branded_foods)} Branded Foods")
        except Exception as e:
            logger.error(f"Failed to load Branded Foods: {e}")
    
    # Load FooDB
    if "foodb" in root_paths:
        logger.info("Loading FooDB...")
        try:
            foodb_foods = load_foodb(
                root_paths["foodb"],
                limit=limit_per_source
            )
            all_foods.extend(foodb_foods)
            logger.info(f"Added {len(foodb_foods)} FooDB entries")
        except Exception as e:
            logger.error(f"Failed to load FooDB: {e}")
    
    # Load FartDB
    if "fartdb" in root_paths:
        logger.info("Loading FartDB...")
        try:
            fartdb_foods = load_fartdb(
                root_paths["fartdb"],
                limit=limit_per_source
            )
            all_foods.extend(fartdb_foods)
            logger.info(f"Added {len(fartdb_foods)} FartDB entries")
        except Exception as e:
            logger.error(f"Failed to load FartDB: {e}")
    
    # Load DSSTox
    if "dsstox" in root_paths:
        logger.info("Loading DSSTox...")
        try:
            dsstox_foods = load_dsstox(
                root_paths["dsstox"],
                limit=limit_per_source
            )
            all_foods.extend(dsstox_foods)
            logger.info(f"Added {len(dsstox_foods)} DSSTox entries")
        except Exception as e:
            logger.error(f"Failed to load DSSTox: {e}")
    
    # Deduplicate
    logger.info(f"Deduplicating {len(all_foods)} records...")
    deduplicated = _deduplicate_foods(all_foods)
    
    # Print statistics
    print_dataset_stats(deduplicated)
    
    return deduplicated


def _deduplicate_foods(foods: List[UnifiedFood]) -> List[UnifiedFood]:
    """
    Deduplicate foods based on normalized_name and native_id.
    
    Keep first occurrence.
    """
    seen = set()
    unique = []
    
    for food in foods:
        # Create key from normalized name + source + native_id
        key = f"{food.normalized_name}|{food.source}|{food.native_id}"
        
        if key not in seen:
            seen.add(key)
            unique.append(food)
    
    logger.info(f"Deduplicated: {len(foods)} → {len(unique)} records")
    return unique


def save_unified_dataset(items: List[UnifiedFood], out_path: str) -> None:
    """
    Save unified dataset as NDJSON (newline-delimited JSON).
    
    Args:
        items: List of UnifiedFood objects
        out_path: Output file path (.jsonl recommended)
    """
    logger.info(f"Saving {len(items)} items to {out_path}")
    
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_file, 'w', encoding='utf-8') as f:
        for item in tqdm(items, desc="Saving"):
            # Serialize to JSON
            json_str = json.dumps(item.dict(), default=str, ensure_ascii=False)
            f.write(json_str + '\n')
    
    logger.info(f"Saved to {out_path}")


def load_unified_dataset(path: str) -> List[UnifiedFood]:
    """
    Load unified dataset from NDJSON file.
    
    Args:
        path: Path to .jsonl file
        
    Returns:
        List of UnifiedFood objects
    """
    logger.info(f"Loading unified dataset from {path}")
    
    items = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Loading"):
            if line.strip():
                data = json.loads(line)
                item = UnifiedFood(**data)
                items.append(item)
    
    logger.info(f"Loaded {len(items)} items")
    return items


def print_dataset_stats(foods: List[UnifiedFood]) -> None:
    """Print summary statistics about the dataset."""
    
    print("\n" + "="*60)
    print("DATASET STATISTICS")
    print("="*60)
    
    # Total count
    print(f"Total records: {len(foods)}")
    
    # By source
    sources = {}
    for food in foods:
        sources[food.source] = sources.get(food.source, 0) + 1
    
    print("\nBy source:")
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count}")
    
    # With nutrients
    with_nutrients = sum(1 for f in foods if f.nutrients)
    print(f"\nWith nutrients: {with_nutrients} ({with_nutrients/len(foods)*100:.1f}%)")
    
    # With compounds
    with_compounds = sum(1 for f in foods if f.compounds)
    print(f"With compounds: {with_compounds} ({with_compounds/len(foods)*100:.1f}%)")
    
    # Average nutrients per item
    total_nutrients = sum(len(f.nutrients) for f in foods)
    avg_nutrients = total_nutrients / len(foods) if foods else 0
    print(f"Avg nutrients per item: {avg_nutrients:.1f}")
    
    print("="*60 + "\n")

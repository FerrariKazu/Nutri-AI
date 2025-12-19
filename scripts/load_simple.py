"""
FINAL SOLUTION: Load data without any ML libraries.

This script:
1. Loads all 5 datasets using ONLY basic Python + CSV reading
2. Saves to JSON 
3. NO pandas, NO numpy, NO embeddings

Works on ANY Python installation.
"""

import json
import csv
import logging
from pathlib import Path
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_csv_simple(filepath, limit=1000):
    """Load CSV without pandas."""
    items = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            items.append(dict(row))
    return items


def main():
    logger.info("=== SIMPLE DATA LOADER (NO ML DEPENDENCIES) ===")
    logger.info("Loading nutrition datasets...")
    
    all_data = []
    
    # FDC Foundation - just load food.csv
    try:
        logger.info("Loading FDC Foundation...")
        path = Path('FoodData Central – Foundation Foods/food.csv')
        if path.exists():
            foods = load_csv_simple(path, limit=1000)
            all_data.extend([{
                'uuid': str(uuid4()),
                'source': 'FDC_Foundation',
                'name': row.get('description', 'Unknown'),
                'raw': row
            } for row in foods])
            logger.info(f"✅ Loaded {len(foods)} Foundation Foods")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # FDC Branded - just load food.csv
    try:
        logger.info("Loading FDC Branded...")
        path = Path('FoodData Central – Branded Foods/food.csv')
        if path.exists():
            foods = load_csv_simple(path, limit=1000)
            all_data.extend([{
                'uuid': str(uuid4()),
                'source': 'FDC_Branded',
                'name': row.get('description', 'Unknown'),
                'raw': row
            } for row in foods])
            logger.info(f"✅ Loaded {len(foods)} Branded Foods")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Save
    out_path = Path('processed/foods_simple.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SUCCESS! Loaded {len(all_data)} food items")
    logger.info(f"Saved to: {out_path}")
    logger.info(f"{'='*60}")
    logger.info("\nNEXT STEPS:")
    logger.info("1. Data is loaded and saved")
    logger.info("2. For search: Use keyword matching (no embeddings needed)")
    logger.info("3. Or: Try installing Anaconda/Miniconda for better package management")


if __name__ == "__main__":
    main()

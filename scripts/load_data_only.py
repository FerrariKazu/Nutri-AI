"""
Simple data loader for Nutri RAG system.

This script ONLY loads and saves nutrition data.
NO embeddings, NO FAISS, NO problematic dependencies.
"""

import logging
import sys
from pathlib import Path

print("DEBUG: Script started", flush=True)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print("DEBUG: Importing basic dependencies...", flush=True)
import json
from backend.nutrition_loader.schema import UnifiedFood
from backend.nutrition_loader import fdc_foundation, fdc_branded, foodb_loader, fartdb_loader, dsstox_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Nutri RAG Data Loader ===")
    logger.info("Loading datasets (limit: 1000 per source for testing)")
    
    all_foods = []
    
    # Load FDC Foundation
    try:
        logger.info("Loading FDC Foundation Foods...")
        foods = fdc_foundation.load_foundation('FoodData Central – Foundation Foods', limit=1000)
        all_foods.extend(foods)
        logger.info(f"✅ Added {len(foods)} Foundation Foods")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Load FDC Branded
    try:
        logger.info("Loading FDC Branded Foods...")
        foods = fdc_branded.load_branded('FoodData Central – Branded Foods', limit=1000)
        all_foods.extend(foods)
        logger.info(f"✅ Added {len(foods)} Branded Foods")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Load FooDB
    try:
        logger.info("Loading FooDB...")
        foods = foodb_loader.load_foodb('FoodDB', limit=1000)
        all_foods.extend(foods)
        logger.info(f"✅ Added {len(foods)} FooDB entries")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Load FartDB
    try:
        logger.info("Loading FartDB...")
        foods = fartdb_loader.load_fartdb('FartDB.parquet', limit=1000)
        all_foods.extend(foods)
        logger.info(f"✅ Added {len(foods)} FartDB entries")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Load DSSTox
    try:
        logger.info("Loading DSSTox...")
        foods = dsstox_loader.load_dsstox('DSSTox', limit=1000)
        all_foods.extend(foods)
        logger.info(f"✅ Added {len(foods)} DSSTox entries")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Save as JSON
    logger.info(f"\nSaving {len(all_foods)} total records...")
    out_path = Path('processed/unified_foods.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump([f.dict() for f in all_foods], f, indent=2, default=str)
    
    logger.info(f"✅ Saved to {out_path}")
    logger.info(f"\n{'='*60}")
    logger.info("SUCCESS! Data loaded and saved.")
    logger.info(f"{'='*60}")
    logger.info("\nNext: We'll add FAISS indexing in a separate step")
    logger.info("once we resolve the embedding library issues.")


if __name__ == "__main__":
    main()

import logging
import sys
import time
from pathlib import Path

print("DEBUG: Script started", flush=True)

print("DEBUG: Importing numpy...", flush=True)
import numpy
print("DEBUG: Numpy imported", flush=True)

print("DEBUG: Importing pandas...", flush=True)
import pandas
print("DEBUG: Pandas imported", flush=True)

print("DEBUG: Importing inflect...", flush=True)
import inflect
print("DEBUG: Inflect imported", flush=True)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print("DEBUG: Importing loader...", flush=True)
from backend.nutrition_loader import loader
print("DEBUG: Loader imported", flush=True)

print("DEBUG: Importing faiss...", flush=True)
import faiss
print("DEBUG: Faiss imported", flush=True)

print("DEBUG: Importing torch...", flush=True)
import torch
print("DEBUG: Torch imported", flush=True)

print("DEBUG: Importing sentence_transformers...", flush=True)
from sentence_transformers import SentenceTransformer
print("DEBUG: Sentence Transformers imported", flush=True)

print("DEBUG: Importing food index builder...", flush=True)
from backend.vector_store_food import index_builder as food_index
print("DEBUG: Food index builder imported", flush=True)

print("DEBUG: Importing compound index builder...", flush=True)
from backend.vector_store_compound import index_builder as compound_index
print("DEBUG: Compound index builder imported", flush=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting reindexing process...")
    
    # Define dataset paths
    # Using raw strings to avoid escape issues
    paths = {
        'fdc_foundation': 'FoodData Central – Foundation Foods',
        'fdc_branded': 'FoodData Central – Branded Foods',
        'foodb': 'FoodDB',
        'fartdb': 'FartDB.parquet',
        'dsstox': 'DSSTox'
    }
    
    # 1. Load Datasets
    logger.info("Step 1: Loading nutrition datasets...")
    try:
        # Use limit for testing (remove or increase for production)
        foods = loader.load_all(paths, limit_per_source=1000)
        
        # Save unified dataset
        out_path = 'processed/unified_foods.jsonl'
        loader.save_unified_dataset(foods, out_path)
        logger.info(f"✅ Saved {len(foods)} food items to {out_path}")
        
    except Exception as e:
        logger.error(f"Failed to load datasets: {e}")
        sys.exit(1)
    
    # 2. Build Food Index
    logger.info("\nStep 2: Building food FAISS index...")
    try:
        food_index.build_index(foods, batch_size=64)
        logger.info("✅ Food index built successfully")
    except Exception as e:
        logger.error(f"Failed to build food index: {e}")
    
    # 3. Build Compound Index
    logger.info("\nStep 3: Building compound FAISS index...")
    try:
        # Filter items with compound data
        compounds = [
            f for f in foods 
            if f.compounds or f.toxicity or f.source in ['FooDB', 'DSSTox', 'FartDB']
        ]
        
        logger.info(f"Found {len(compounds)} items with compound data")
        
        if compounds:
            compound_index.build_index(compounds, batch_size=64)
            logger.info("✅ Compound index built successfully")
        else:
            logger.warning("⚠️ No compounds found, skipping compound index")
            
    except Exception as e:
        logger.error(f"Failed to build compound index: {e}")
    
    logger.info("\n==============================================")
    logger.info("✅ Reindexing complete!")
    logger.info("==============================================")


if __name__ == "__main__":
    main()

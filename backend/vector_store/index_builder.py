"""
FAISS index builder for recipe semantic search.

Creates and saves a FAISS index from processed recipes.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import logging

try:
    import faiss
except ImportError:
    faiss = None

from backend.data_loader import get_all_recipes
from backend.vector_store.embedder import embed_batch, load_model as load_embedding_model

logger = logging.getLogger(__name__)

# Paths for saving index
INDEX_DIR = Path("backend/vector_store")
INDEX_PATH = INDEX_DIR / "faiss_index.bin"
IDS_PATH = INDEX_DIR / "recipe_ids.json"


def prepare_recipe_text(recipe: Dict[str, Any]) -> str:
    """
    Combine recipe fields into a single searchable text.
    
    Args:
        recipe: Recipe dictionary
        
    Returns:
        Combined text string
    """
    title = recipe.get('title', '')
    
    # Get normalized ingredient names
    ingredients = recipe.get('ingredients', [])
    ingredient_names = [
        ing.get('normalized', ing.get('raw', ''))
        for ing in ingredients
    ]
    ingredients_text = " ".join(ingredient_names)
    
    # Get dietary tags
    tags = recipe.get('diet_tags', [])
    tags_text = " ".join(tags)
    
    # Combine all
    combined = f"{title}. Ingredients: {ingredients_text}. {tags_text}"
    
    return combined.strip()


def build_index(force_rebuild: bool = False) -> bool:
    """
    Build FAISS index from loaded recipes.
    
    Args:
        force_rebuild: Force rebuild even if index exists
        
    Returns:
        True if successful, False otherwise
    """
    if faiss is None:
        logger.error("FAISS not installed. Run: pip install faiss-cpu")
        return False
    
    # Check if index already exists
    if INDEX_PATH.exists() and IDS_PATH.exists() and not force_rebuild:
        logger.info("FAISS index already exists. Use force_rebuild=True to rebuild.")
        return True
    
    logger.info("Building FAISS index...")
    
    # Ensure embedding model is loaded
    load_embedding_model()
    
    # Get all recipes
    recipes = get_all_recipes()
    if not recipes:
        logger.error("No recipes loaded. Cannot build index.")
        return False
    
    logger.info(f"Processing {len(recipes)} recipes...")
    
    # Prepare texts
    recipe_texts = []
    recipe_ids = []
    
    for idx, recipe in enumerate(recipes):
        text = prepare_recipe_text(recipe)
        recipe_texts.append(text)
        recipe_ids.append(idx)
    
    # Generate embeddings
    logger.info("Generating embeddings...")
    embeddings = embed_batch(recipe_texts, batch_size=64, show_progress=True)
    
    logger.info(f"Generated embeddings shape: {embeddings.shape}")
    
    # Build FAISS index (L2 distance, which approximates cosine similarity for normalized vectors)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    
    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Add to index
    index.add(embeddings.astype('float32'))
    
    logger.info(f"FAISS index built with {index.ntotal} vectors")
    
    # Save index and IDs
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    faiss.write_index(index, str(INDEX_PATH))
    logger.info(f"Saved FAISS index to {INDEX_PATH}")
    
    with open(IDS_PATH, 'w') as f:
        json.dump(recipe_ids, f)
    logger.info(f"Saved recipe IDs to {IDS_PATH}")
    
    logger.info("✅ FAISS index ready!")
    return True


def index_exists() -> bool:
    """Check if FAISS index files exist."""
    return INDEX_PATH.exists() and IDS_PATH.exists()

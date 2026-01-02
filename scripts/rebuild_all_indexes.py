#!/usr/bin/env python3
"""
Rebuild All FAISS Indexes

Single entrypoint for building all FAISS indexes from raw data sources.
This script:
1. Validates raw data exists
2. Chunks text consistently
3. Embeds using BGE-M3
4. Builds FAISS IndexFlatIP
5. Writes .faiss and _meta.json files
6. Logs sizes and counts

Usage:
    python scripts/rebuild_all_indexes.py [--index TYPE] [--force]
    
Examples:
    python scripts/rebuild_all_indexes.py          # Build all indexes
    python scripts/rebuild_all_indexes.py --index recipes  # Build only recipes
    python scripts/rebuild_all_indexes.py --force  # Force rebuild even if exists
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import faiss

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class IndexConfig:
    """Configuration for a single index."""
    name: str
    source_paths: List[str]  # Relative to data_sources/
    output_name: str         # e.g., "recipes" -> recipes.faiss
    chunk_size: int = 1000
    chunk_overlap: int = 200
    file_types: List[str] = None  # e.g., ['csv', 'json']
    text_builder: str = 'default'  # Function to build searchable text


INDEX_CONFIGS = {
    'recipes': IndexConfig(
        name='Recipes',
        source_paths=['recipes/13k-recipes.csv'],
        output_name='recipes',
        chunk_size=1500,
        file_types=['csv']
    ),
    'nutrition': IndexConfig(
        name='Nutrition',
        source_paths=[
            'nutrition/opennutrition_foods.tsv',
            'nutrition/branded_foods/',
            'nutrition/foundation_foods/'
        ],
        output_name='nutrition',
        chunk_size=1200,
        file_types=['tsv', 'csv']
    ),
    'chemistry': IndexConfig(
        name='Chemistry',
        source_paths=[
            'chemistry/FoodDB/',
            'chemistry/DSSTox/',
            'chemistry/FartDB.parquet'
        ],
        output_name='chemistry',
        chunk_size=900,
        file_types=['csv', 'xlsx', 'parquet']
    ),
    'science': IndexConfig(
        name='Science',
        source_paths=['science/'],
        output_name='science',
        chunk_size=1000,
        file_types=['pdf', 'txt']
    ),
}

DATA_SOURCES_DIR = PROJECT_ROOT / 'data_sources'
OUTPUT_DIR = PROJECT_ROOT / 'backend' / 'indexes'
EMBEDDING_MODEL = 'BAAI/bge-m3'
EMBEDDING_DIM = 1024


# ============================================================================
# Data Loading
# ============================================================================

def validate_data_sources() -> Dict[str, bool]:
    """Check which data sources exist."""
    results = {}
    for name, config in INDEX_CONFIGS.items():
        exists = False
        for path in config.source_paths:
            full_path = DATA_SOURCES_DIR / path
            if full_path.exists():
                exists = True
                break
        results[name] = exists
        status = "✓" if exists else "✗"
        logger.info(f"  {status} {name}: {config.source_paths}")
    return results


def load_csv_data(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load data from CSV/TSV file."""
    import csv
    
    delimiter = '\t' if path.suffix == '.tsv' else ','
    
    items = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            items.append(dict(row))
    
    logger.info(f"Loaded {len(items)} items from {path.name}")
    return items


def load_parquet_data(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load data from Parquet file."""
    import pandas as pd
    
    df = pd.read_parquet(path)
    if limit:
        df = df.head(limit)
    
    items = df.to_dict('records')
    logger.info(f"Loaded {len(items)} items from {path.name}")
    return items


def load_excel_data(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load data from Excel file."""
    import pandas as pd
    
    try:
        df = pd.read_excel(path)
        if limit:
            df = df.head(limit)
        
        items = df.to_dict('records')
        logger.info(f"Loaded {len(items)} items from {path.name}")
        return items
    except Exception as e:
        logger.error(f"Error loading Excel {path.name}: {e}")
        return []


def load_pdf_data(path: Path) -> List[Dict[str, Any]]:
    """Extract text chunks from PDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning(f"PyMuPDF not installed, skipping PDF: {path.name}")
        return []
    
    doc = fitz.open(path)
    chunks = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            chunks.append({
                'text': text,
                'source': path.name,
                'page': page_num + 1
            })
    
    doc.close()
    logger.info(f"Extracted {len(chunks)} pages from {path.name}")
    return chunks


def load_directory_data(
    dir_path: Path,
    file_types: List[str],
    limit_per_file: Optional[int] = 5000
) -> List[Dict[str, Any]]:
    """Load all files from a directory."""
    all_items = []
    
    for ext in file_types:
        for file_path in dir_path.glob(f'**/*.{ext}'):
            if ext in ['csv', 'tsv']:
                items = load_csv_data(file_path, limit=limit_per_file)
            elif ext == 'parquet':
                items = load_parquet_data(file_path, limit=limit_per_file)
            elif ext == 'pdf':
                items = load_pdf_data(file_path)
            elif ext in ['xlsx', 'xls']:
                items = load_excel_data(file_path, limit=limit_per_file)
            else:
                continue
            
            # Tag with source
            for item in items:
                item['_source_file'] = file_path.name
            
            all_items.extend(items)
    
    return all_items


# ============================================================================
# Text Building
# ============================================================================

def build_recipe_text(item: Dict[str, Any]) -> str:
    """Build searchable text from recipe data."""
    parts = []
    
    # Title
    title = item.get('title') or item.get('name') or item.get('Title') or ''
    if title:
        parts.append(title)
    
    # Ingredients
    ingredients = item.get('ingredients') or item.get('Ingredients') or ''
    if isinstance(ingredients, str):
        parts.append(f"Ingredients: {ingredients}")
    elif isinstance(ingredients, list):
        parts.append(f"Ingredients: {', '.join(ingredients)}")
    
    # Instructions
    instructions = item.get('instructions') or item.get('directions') or ''
    if instructions:
        parts.append(instructions[:500])  # Truncate long instructions
    
    return ' '.join(parts)


def build_nutrition_text(item: Dict[str, Any]) -> str:
    """Build searchable text from nutrition data."""
    parts = []
    
    # Food name
    name = (
        item.get('description') or 
        item.get('name') or 
        item.get('food_name') or
        item.get('brandedFoodCategory') or
        ''
    )
    if name:
        parts.append(name)
    
    # Brand
    brand = item.get('brand_owner') or item.get('brand')
    if brand:
        parts.append(f"Brand: {brand}")
    
    # Category
    category = item.get('food_category') or item.get('category')
    if category:
        parts.append(f"Category: {category}")
    
    return ' '.join(parts)


def build_chemistry_text(item: Dict[str, Any]) -> str:
    """Build searchable text from chemistry data."""
    parts = []
    
    # Compound name
    name = item.get('name') or item.get('compound_name') or ''
    if name:
        parts.append(name)
    
    # Description
    desc = item.get('description') or ''
    if desc:
        parts.append(desc[:500])
    
    # Formula
    formula = item.get('moldb_smiles') or item.get('formula') or ''
    if formula:
        parts.append(f"Formula: {formula[:100]}")
    
    return ' '.join(parts)


def build_science_text(item: Dict[str, Any]) -> str:
    """Build searchable text from PDF/science data."""
    text = item.get('text', '')
    source = item.get('source', '')
    page = item.get('page', '')
    
    return f"[{source} p{page}] {text}"


def build_text(item: Dict[str, Any], index_type: str) -> str:
    """Build searchable text based on index type."""
    builders = {
        'recipes': build_recipe_text,
        'nutrition': build_nutrition_text,
        'chemistry': build_chemistry_text,
        'science': build_science_text,
    }
    
    builder = builders.get(index_type, lambda x: str(x))
    text = builder(item)
    
    # Clean and normalize
    text = ' '.join(text.split())  # Normalize whitespace
    return text[:4000]  # Limit length for embedding


# ============================================================================
# Chunking
# ============================================================================

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size // 2:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


# ============================================================================
# Embedding
# ============================================================================

_embedder = None

def get_embedder():
    """Get or create embedder singleton."""
    global _embedder
    if _embedder is None:
        from backend.embedder_bge import EmbedderBGE
        _embedder = EmbedderBGE(model_name=EMBEDDING_MODEL)
        logger.info(f"Loaded embedder: {EMBEDDING_MODEL}")
    return _embedder


def embed_texts(texts: List[str], batch_size: int = 32) -> np.ndarray:
    """Embed a list of texts."""
    embedder = get_embedder()
    
    logger.info(f"Embedding {len(texts)} texts (batch_size={batch_size})...")
    
    embeddings = embedder.embed_texts(texts, batch_size=batch_size)
    
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    
    return embeddings.astype('float32')


# ============================================================================
# Index Building
# ============================================================================

def build_index(
    index_type: str,
    force: bool = False
) -> bool:
    """Build a single FAISS index."""
    config = INDEX_CONFIGS.get(index_type)
    if not config:
        logger.error(f"Unknown index type: {index_type}")
        return False
    
    output_path = OUTPUT_DIR / f"{config.output_name}.faiss"
    meta_path = OUTPUT_DIR / f"{config.output_name}_meta.json"
    
    # Check if already exists
    if output_path.exists() and not force:
        logger.info(f"Index already exists: {output_path}")
        logger.info("Use --force to rebuild")
        return True
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Building index: {config.name}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Load data
    all_items = []
    for source_path in config.source_paths:
        full_path = DATA_SOURCES_DIR / source_path
        
        if not full_path.exists():
            logger.warning(f"Source not found: {full_path}")
            continue
        
        if full_path.is_dir():
            items = load_directory_data(full_path, config.file_types or [])
        elif full_path.suffix == '.csv' or full_path.suffix == '.tsv':
            items = load_csv_data(full_path)
        elif full_path.suffix == '.parquet':
            items = load_parquet_data(full_path)
        elif full_path.suffix == '.pdf':
            items = load_pdf_data(full_path)
        else:
            logger.warning(f"Unsupported file type: {full_path}")
            continue
        
        all_items.extend(items)
    
    if not all_items:
        logger.error(f"No data loaded for {index_type}")
        return False
    
    logger.info(f"Loaded {len(all_items)} items")
    
    # Build texts
    texts = []
    doc_map = {}
    
    for i, item in enumerate(all_items):
        text = build_text(item, index_type)
        if not text.strip():
            continue
        
        # Chunk if needed
        chunks = chunk_text(text, config.chunk_size, config.chunk_overlap)
        
        for chunk in chunks:
            idx = len(texts)
            texts.append(chunk)
            doc_map[idx] = {
                'text': chunk[:500],  # Store preview
                'source': item.get('_source_file', 'unknown'),
                'metadata': {k: v for k, v in item.items() if not k.startswith('_')}
            }
    
    logger.info(f"Generated {len(texts)} text chunks")
    
    if not texts:
        logger.error("No texts to embed")
        return False
    
    # Embed
    embeddings = embed_texts(texts)
    
    # Build FAISS index
    logger.info("Building FAISS index...")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product for cosine similarity
    index.add(embeddings)
    
    logger.info(f"Index contains {index.ntotal} vectors")
    
    # Save index
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(output_path))
    logger.info(f"Saved index: {output_path}")
    
    # Save metadata
    metadata = {
        'index_info': {
            'name': config.name,
            'build_date': datetime.now().isoformat(),
            'vector_count': index.ntotal,
            'embedding_model': EMBEDDING_MODEL,
            'embedding_dim': EMBEDDING_DIM,
            'chunk_size': config.chunk_size,
            'source_paths': config.source_paths,
        },
        'documents': doc_map
    }
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"Saved metadata: {meta_path}")
    
    elapsed = time.time() - start_time
    logger.info(f"✅ Built {config.name} index in {elapsed:.1f}s")
    
    return True


def build_all_indexes(force: bool = False) -> Dict[str, bool]:
    """Build all indexes."""
    results = {}
    
    logger.info("\n" + "="*60)
    logger.info("FAISS Index Builder")
    logger.info("="*60 + "\n")
    
    # Validate data sources
    logger.info("Checking data sources...")
    available = validate_data_sources()
    
    # Build each index
    for index_type in INDEX_CONFIGS.keys():
        if not available.get(index_type):
            logger.warning(f"Skipping {index_type}: no data sources found")
            results[index_type] = False
            continue
        
        try:
            results[index_type] = build_index(index_type, force=force)
        except Exception as e:
            logger.error(f"Failed to build {index_type}: {e}")
            results[index_type] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Build Summary")
    logger.info("="*60)
    
    for index_type, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"  {status} {index_type}")
    
    return results


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Rebuild FAISS indexes from data sources'
    )
    parser.add_argument(
        '--index', '-i',
        choices=list(INDEX_CONFIGS.keys()),
        help='Build only this index'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force rebuild even if index exists'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available indexes and exit'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available indexes:")
        for name, config in INDEX_CONFIGS.items():
            print(f"  {name}: {config.name}")
            for path in config.source_paths:
                print(f"    - {path}")
        return
    
    if args.index:
        success = build_index(args.index, force=args.force)
        sys.exit(0 if success else 1)
    else:
        results = build_all_indexes(force=args.force)
        success = all(results.values())
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

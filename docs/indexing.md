# Indexing Guide

This document explains how FAISS indexes are built and how to rebuild them.

## Index Locations

All FAISS indexes are stored in:

```
backend/indexes/
├── recipes.faiss         # Recipe search index
├── recipes_meta.json     # Recipe metadata
├── nutrition.faiss       # Nutrition database index
├── nutrition_meta.json
├── chemistry.faiss       # Chemistry/compound index
├── chemistry_meta.json
├── science.faiss         # Science/PDF knowledge index
└── science_meta.json
```

## The Mandated Ingestion Script

The primary script for building indexes is [scripts/ingest_isolated.py](file:///home/ferrarikazu/nutri-ai/scripts/ingest_isolated.py). This script ensures strict isolation between datasets.

### Basic Usage

```bash
# Build a specific index
python3 scripts/ingest_isolated.py --dataset recipes

# Build all indexes sequentially (Max Stability)
python3 scripts/ingest_isolated.py --dataset all
```

### Supported Datasets

- `usda_branded`: USDA Branded Foods (~1.9M records)
- `usda_foundation`: USDA Foundation Foods
- `open_nutrition`: OpenNutrition Database (~320k records)
- `recipes`: Nutri-AI Curated Recipes (13k)
- `chemistry`: FoodDB, PubChem, DSSTox
- `science`: Scientific PDFs

## What the Script Does

1. **Validates** raw data exists in `data_sources/`
2. **Loads** data from CSV, TSV, Parquet, and PDF files
3. **Chunks** text with configurable size and overlap
4. **Embeds** using BGE-M3 (1024 dimensions)
5. **Builds** FAISS IndexFlatIP (cosine similarity)
6. **Saves** `.faiss` index and `_meta.json` metadata
7. **Logs** sizes and counts for verification

## Index Configuration

Each index has its own configuration in `rebuild_all_indexes.py`:

| Index | Chunk Size | Source Paths |
|-------|------------|--------------|
| recipes | 1500 | recipes/13k-recipes.csv |
| nutrition | 1200 | nutrition/*.tsv, branded_foods/, foundation_foods/ |
| chemistry | 900 | FoodDB/, DSSTox/, FartDB.parquet |
| science | 1000 | science/*.pdf |

## Embedding Model

- **Model**: `BAAI/bge-m3`
- **Dimensions**: 1024
- **Normalization**: L2 (for cosine similarity via inner product)

## High-Volume Metadata (SQLite)

For datasets exceeding 100k records (like FDC Nutrition), Nutri-AI uses **SQLite-backed metadata** instead of JSON.

- **Index File**: `backend/indexes/nutrition.faiss`
- **Metadata File**: `backend/indexes/nutrition.meta.sqlite`

This ensures that the retriever does not need to load millions of records into RAM simultaneously. Instead, it queries the SQLite database on-demand for the specific results returned by FAISS.

## Artifacts and Structure

Each indexing run produces the following artifacts in `vector_store/[dataset]/`:

1.  `index.faiss`: The vector index file.
2.  `index.meta.sqlite`: (High-volume) SQLite database containing text and metadata.
3.  `index.meta.json`: (Low-volume) JSON file containing text and metadata.
4.  `index_report.txt`: Automated report with vector counts and build time.

## Verification

After ingestion, run the validation script to ensure retrieval integrity:

```bash
python3 scripts/validate_fdc_ingestion.py
```
This script samples 20 random IDs from the newly built indexes and verifies successful retrieval from the FAISS store.

## Ingestion Report

Every full build produces a report in `backend/indexes/ingestion_report.txt`. This report contains:
- Total raw rows read
- Total documents created
- Final vector count (must match raw rows)
- Build time and disk usage

Verification is performed via:
```bash
python3 scripts/validate_fdc_ingestion.py
```

## Troubleshooting

### "Index not found" error
Run the rebuild script:
```bash
python3 scripts/rebuild_all_indexes.py --force
```

### "No data sources found"
Check that `data_sources/` contains the expected files:
```bash
find data_sources -type f | wc -l
```

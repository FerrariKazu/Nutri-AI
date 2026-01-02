# Data Pipeline

This document explains where raw data lives and how to add new datasets to Nutri-AI.

## Canonical Data Root

All raw data lives in:

```
/home/ferrarikazu/nutri-ai/data_sources/
```

This is the **single source of truth**. Indexes are derived from this directory.

## Directory Structure

```
data_sources/
├── recipes/
│   └── 13k-recipes.csv          # Recipe dataset
├── nutrition/
│   ├── opennutrition_foods.tsv  # OpenNutrition database
│   ├── branded_foods/           # FoodData Central (Branded)
│   └── foundation_foods/        # FoodData Central (Foundation)
├── chemistry/
│   ├── FoodDB/                  # FoodDB compound data (29 CSVs)
│   ├── DSSTox/                  # EPA toxicity database
│   ├── FartDB.parquet           # Volatile compound database
│   └── composition-data.xlsx    # Food composition data
└── science/
    ├── *.pdf                    # RAG2 science PDFs (7 files)
    └── herbal-pdrsmall.pdf      # Herbal PDR reference
```

## Adding New Datasets

1. **Place raw files** in the appropriate subdirectory
2. **Update** `scripts/rebuild_all_indexes.py`:
   - Add source path to the appropriate `IndexConfig`
   - Add any custom text builder if needed
3. **Rebuild** the affected index:
   ```bash
   python scripts/rebuild_all_indexes.py --index <type> --force
   ```

## Data Recovery

If data is lost, it can be recovered from:
- **Windows backup**: `F:\KitchenMind\`
- **Copy command**:
  ```bash
  rsync -av /mnt/f/KitchenMind/<SOURCE>/ ~/nutri-ai/data_sources/<TARGET>/
  ```

## Completeness Policy (Mandatory)

Nutri-AI follows a **Total Ingestion Policy**. Partial ingestion, sampling, or filtering of raw data is strictly prohibited.

1. **Why Completeness Matters**: For an agentic RAG system, "missing data is missing knowledge." An agent cannot reason about a compound or nutrient relationship if it was filtered out to save disk space.
2. **Branded Foods**: 100% of the USDA Branded Foods dataset (~1.9M+ entries) is ingested.
3. **Relationships**: All nutrient and portion relationships are preserved and attached to the food record before embedding.
4. **No Deduplication**: Every unique entry remains retrievable to preserve data nuances from different sources.

## Data Ingestion Verification

After every major reindex, a machine-verifiable report is generated in `backend/indexes/ingestion_report.txt`. Use `scripts/validate_fdc_ingestion.py` to prove retrieval success.

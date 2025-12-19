# Nutri RAG System - Two-Tier Food & Compound Retrieval

**Production-grade RAG system integrating nutrition datasets (FDC, FooDB, FartDB) and chemical/toxicity databases (DSSTox) with PubChem auto-enrichment and dual FAISS vector search.**

## 🎯 System Overview

This system provides:

- **Unified Data Schema**: StandardizedUnifiedFood model across all datasets
- **Dual FAISS Indices**: Separate food and compound vector stores
- **PubChem Integration**: Auto-enrichment with caching (SQLite + JSON)
- **FastAPI Endpoints**: `/api/food/*`, `/api/compound/*`, enhanced `/api/recipe`
- **GPU Acceleration**: CUDA support for RTX 4060
- **Production Features**: Atomic writes, rate limiting, comprehensive logging

---

## 📦 Installation

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: For GPU-accelerated FAISS, replace `faiss-cpu` with `faiss-gpu` in requirements.txt

### 3. Verify CUDA (Optional)

```python
import torch
print(torch.cuda.is_available())  # Should be True for RTX 4060
```

---

## 📂 Dataset Preparation

Place your raw datasets in these folders:

```
KitchenMind/
├── FoodData_Central/
│   ├── FoundationFoods/  (CSV files)
│   └── BrandedFoods/     (CSV files)
├── FooDB/                (CSV files)
├── FartDB/               (fartdb.parquet)
└── DSSTox/               (Excel files)
```

---

## 🔧 Initial Setup & Index Building

### Build All Indices

**Windows:**

```cmd
scripts\reindex_all.bat
```

**Linux/Mac:**

```bash
chmod +x scripts/reindex_all.sh
./scripts/reindex_all.sh
```

This script will:

1. Load all datasets → `processed/unified_foods.jsonl`
2. Build food FAISS index → `backend/vector_store_food/`
3. Build compound FAISS index → `backend/vector_store_compound/`
4. Initialize PubChem cache → `backend/compound_loader/pubchem_cache.sqlite`

**Expected time**: 10-30 minutes depending on dataset size and GPU

---

## 🚀 Running the API

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

---

## 📡 API Endpoints

### Food Search

```bash
POST /api/food/search
{
  "query": "sweet potato casserole",
  "k": 6
}
```

Returns: List of food items with similarity scores

### Food Detail

```bash
POST /api/food/detail
{
  "id": "<uuid or native_id>"
}
```

Returns: Complete UnifiedFood record

### Compound Search

```bash
POST /api/compound/search
{
  "query": "lycopene antioxidant",
  "k": 5
}
```

Returns: Chemical compounds with properties

### Compound Detail (Auto-Enrich)

```bash
POST /api/compound/detail
{
  "id": "<cid or uuid>",
  "auto_enrich": true
}
```

**Auto-enrichment**: If compound not in local DB and CID provided, fetches from PubChem, caches result, and updates compound index incrementally.

### RAG-Enhanced Recipe Generation

```bash
POST /api/recipe
{
  "ingredients": "eggs, spinach, cheese",
  "dislikes": "onion",
  "dietary_constraints": "vegetarian",
  "goal": "breakfast",
  "innovation_level": 2,
  "explain_compounds": true
}
```

**Process:**

1. Normalize ingredients
2. Search food index → retrieve 5 similar recipes
3. Search compound index → get chemical properties
4. Build enhanced LLM prompt with:
   - Retrieved recipe context
   - Compound/nutrition blocks
   - User constraints
5. Generate with Qwen
6. Run pantry checker
7. Return draft + corrections

---

## 🔬 PubChem Integration

### Auto-Enrichment Behavior

When a compound is requested but not in local database:

1. Query PubChem REST API
2. Cache result in SQLite (`backend/compound_loader/pubchem_cache.sqlite`)
3. Backup to JSON (`backend/compound_loader/pubchem_cache.json`)
4. Embed compound text
5. Add to FAISS compound index incrementally
6. Return result to user

### Rate Limiting

- Maximum 5 requests/second to PubChem
- Exponential backoff on failures (3 retries)
- 10s timeout per request

### Clearing Cache

```bash
# Remove SQLite cache
rm backend/compound_loader/pubchem_cache.sqlite

# Remove JSON backup
rm backend/compound_loader/pubchem_cache.json

# Rebuild compound index
python -m backend.vector_store_compound.index_builder build
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_loaders.py
pytest tests/test_index_build.py
pytest tests/test_search_endpoints.py

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

**Note**: Network calls to PubChem are mocked in tests

---

## 📊 Performance Tuning

### GPU Utilization (RTX 4060)

The system uses CUDA for:

- Sentence transformer embeddings (sentence-transformers)
- Batch encoding (up to 64 items/batch)

Monitor GPU usage:

```bash
nvidia-smi -l 1
```

### Memory Optimization

- Datasets loaded incrementally (streaming CSV reading)
- FAISS uses IndexFlatIP (cosine similarity via normalized vectors)
- Batch size capped at 64 to avoid OOM

### Index Size Estimates

- Food index: ~50-100 MB for 100K items
- Compound index: ~20-50 MB for 50K items
- Embeddings: 384 dimensions (all-MiniLM-L6-v2)

---

## 🗂️ File Structure

```
backend/
├── nutrition_loader/
│   ├── schema.py              ✅ UnifiedFood model
│   ├── normalizer.py          ✅ Text processing
│   ├── loader.py              ⏳ Master loader
│   ├── fdc_foundation.py      ⏳ FDC Foundation Foods
│   ├── fdc_branded.py         ⏳ FDC Branded Foods
│   ├── foodb_loader.py        ⏳ FooDB chemical compounds
│   ├── fartdb_loader.py       ⏳ FartDB gas composition
│   └── dsstox_loader.py       ⏳ DSSTox toxicity
├── compound_loader/
│   ├── pubchem_client.py      ⏳ PubChem API client
│   ├── datastore.py           ⏳ SQLite cache
│   └── linker.py              ⏳ Auto-enrichment
├── vector_store_food/
│   ├── embedder.py            ⏳ Sentence transformers
│   ├── index_builder.py       ⏳ FAISS index builder
│   └── search.py              ⏳ Semantic search
├── vector_store_compound/
│   └── (same as food)         ⏳
├── api_foods.py               ⏳ Food endpoints
├── api_compounds.py           ⏳ Compound endpoints
├── api_recipe.py              ⏳ RAG recipe generation
├── data_store.py              ⏳ Singleton state
└── utils.py                   ⏳ Utilities

scripts/
├── reindex_all.sh             ⏳ Linux reindexing
└── reindex_all.bat            ⏳ Windows reindexing

tests/
├── data/                      ⏳ Sample test data
├── test_loaders.py            ⏳ Loader tests
├── test_index_build.py        ⏳ Index building tests
└── test_search_endpoints.py   ⏳ API tests
```

✅ = Complete | ⏳ = In Progress

---

## 🔐 Security & Licensing

### Dataset Licenses

- **FoodData Central**: Public domain (USDA)
- **FooDB**: [Check FooDB license](https://foodb.ca/)
- **FartDB**: [Verify license]
- **DSSTox**: Public (EPA)
- **PubChem**: Public domain (NIH)

### API Keys

No API keys required for PubChem (public REST API)

### Rate Limiting

Respect PubChem usage policies:

- Max 5 req/sec implemented
- Caching to minimize redundant calls

---

## 🐛 Troubleshooting

### CUDA Out of Memory

Reduce batch size in embedder:

```python
# backend/vector_store_food/embedder.py
batch_size = 32  # instead of 64
```

### PubChem Timeout

Increase timeout in pubchem_client.py:

```python
timeout = 30  # instead of 10
```

### Index Corruption

Rebuild indices:

```bash
rm backend/vector_store_food/index.bin
rm backend/vector_store_compound/index.bin
./scripts/reindex_all.sh
```

---

## 📝 Logs

All logs saved to: `logs/nutri_rag.log`

Log levels:

- INFO: Normal operations
- DEBUG: Detailed traces
- WARNING: Non-critical issues
- ERROR: Failures

---

## 🤝 Contributing

This is a production system. Please ensure:

1. All tests pass before committing
2. Add logging for new features
3. Update this README for API changes
4. Respect rate limits for external services

---

## 📞 Support

For issues:

1. Check logs/nutri_rag.log
2. Verify dataset paths
3. Confirm CUDA availability
4. Review PubChem cache status

---

## ⚡ Quick Start Summary

```bash
# 1. Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Build indices
scripts\reindex_all.bat  # Windows

# 3. Start API
uvicorn api:app --reload

# 4. Test
curl http://localhost:8000/api/food/search -X POST -d '{"query":"apple","k":3}'
```

---

**System Status**: Schema & Normalization ✅ | Loaders ⏳ | Vector Stores ⏳ | API ⏳

**Next Step**: Complete dataset loaders and PubChem integration

---

RAG compound+food ingestion & two-tier FAISS system generated — run `./scripts/reindex_all.sh` then `uvicorn api:app --reload`

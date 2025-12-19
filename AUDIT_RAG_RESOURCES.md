# RAG Resource Audit Report
## Nutri-AI Project - Complete Data Source Analysis

**Generated**: 2025-12-05  
**Auditor**: Antigravity AI  
**Purpose**: Identify all datasets and verify RAG pipeline integration

---

## Executive Summary

**Total Data Sources Found**: 99+ files  
**Fully Integrated into RAG**: 1 source (recipes)  
**Partially Integrated**: 1 source (herbal PDR - separate index)  
**Extracted but NOT Embedded**: 1 source (RAG2 PDFs - old index)  
**Available but NOT Used in RAG**: 4 sources (FoodDB, FoodData Central, FartDB, processed foods)

**Critical Gap**: Most nutrition and chemistry datasets are NOT embedded or searchable via the main RAG pipeline.

---

## Detailed Audit Table

| Dataset Name | File Type | Records/Pages | Loaded? | Parsed? | Embedded (BGE-M3)? | Search Route | Missing Steps |
|---|---|---|---|---|---|---|---|
| **recipes_with_nutrition.json** | JSON | 13,501 recipes | ✅ Yes | ✅ Yes | 🔄 In Progress | FAISS (rebuilding) + Lexical | Finish FAISS rebuild |
| **RAG2 PDFs (7 files)** | PDF | ~2,500 pages | ✅ Yes | ✅ Yes | ❌ No (old embeddings) | ⚠️ Old FAISS (sentence-transformers) | Re-embed with BGE-M3, rebuild index |
| **herbal-pdrsmall.pdf** | PDF | ~300 pages | ✅ Yes | ✅ Yes | ⚠️Different model | Separate FAISS `/scripts/` | Integrate into main pipeline |
| **FoodDB (29 CSVs)** | CSV | ~40,000 compounds | ✅ Yes | ✅ Yes | ❌ No | ❌ None (tool access only) | Create embeddings, add to FAISS |
| **FoodData Central - Branded** | CSV | ~400,000 foods | ❌ No | ❌ No | ❌ No | ❌ None | Load, parse, embed, index |
| **FoodData Central - Foundation** | CSV | ~800 foods | ❌ No | ❌ No | ❌ No | ❌ None | Load, parse, embed, index |
| **FartDB.parquet** | Parquet | Unknown | ❌ No | ❌ No | ❌ No | ❌ None | Load, parse, embed, index |
| **foods_simple.json** | JSON | ~2,500 foods | ❌ No | ❌ No | ❌ No | ❌ None | Parse, embed, index |
| **Log files** | JSONL | Variable | N/A | N/A | ❌ No | ❌ None | Not needed for RAG |

---

## Source-by-Source Analysis

### 1. ✅ **Recipes with Nutrition** (PRIMARY SOURCE)
- **Location**: `data/recipes_with_nutrition.json` and `processed/recipes_with_nutrition.json`
- **Records**: 13,501 recipes
- **Status**: ACTIVE, being re-embedded with BGE-M3
- **Integration**: 
  - ✅ Loaded via `backend/data_loader.py`
  - ✅ Parsed and normalized
  - 🔄 Embedding in progress (`scripts/rebuild_faiss_bge.py` - batch 284/844)
  - 🔄 FAISS index: `backend/vector_store/faiss_index_bge.bin` (building)
  - ✅ Lexical fallback: Active via `backend/vector_store/search.py`
- **Search Route**: 
  - Semantic: FAISS IndexFlatIP (1024-dim BGE-M3)
  - Fallback: Lexical keyword matching
- **Missing**: Nothing - fully integrated, just waiting for FAISS completion

---

### 2. ⚠️ **RAG2 PDFs** (OUTDATED EMBEDDINGS)
-**Location**: `RAG2/` directory  
- **Files**: 
  1. `027_On_Food_and_Cooking_The_Science_and_Lore_of_the_Kitchen_PDFDrive_.pdf` (7.7MB)
  2. `The Dorito Effect PDF.pdf` (2.5MB)
  3. `The Science of Cooking PDF.pdf` (2.9MB)
  4. `Analysis_of_Volatiles_in_Food_Products.pdf` (1.0MB)
  5. `applsci-14-01069-v2.pdf` (4.6MB)
  6. `E5-10-03-09.pdf` (264KB)
  7. `IJFS2015-526762.pdf` (594KB)
- **Estimated Pages**: ~2,500 total
- **Status**: PARTIALLY INTEGRATED (old system)
- **Integration**:
  - ✅ Extracted via `scripts/extract_pdfs.py` → `scripts/raw_text.jsonl`
  - ✅ Chunked via `scripts/chunk_text.py` → `scripts/chunks.jsonl`
  - ⚠️ Embedded with OLD model (sentence-transformers/all-MiniLM-L6-v2)
  - ⚠️ Old FAISS index: `scripts/faiss.index` (NOT BGE-M3)
- **Search Route**: OLD - `scripts/retrieve.py` (separate from main pipeline)
- **Missing Steps**:
  1. Re-embed chunks with BGE-M3
  2. Rebuild FAISS index with new embeddings
  3. Integrate into main `rag_engine.py` search

---

### 3. ⚠️ **Herbal PDR** (SEPARATE PIPELINE)
- **Location**: `herbal-pdrsmall.pdf`
- **Size**: 9.4MB (~300 pages)
- **Status**: SEPARATE RAG PIPELINE
- **Integration**:
  - ✅ Has dedicated endpoint: `/api/pdr` in `api.py`
  - ✅ Uses `scripts/pdr_rag.py` for queries
  - ⚠️ Separate FAISS index (likely old embeddings)
  - ⚠️ Uses Ollama (not migrated to Qwen3)
- **Search Route**: Separate FAISS via `scripts/retrieve.py`
- **Missing Steps**:
  1. Update `pdr_rag.py` to use `llm.generate()` instead of Ollama
  2. Re-embed with BGE-M3
  3. Either merge into main FAISS or keep separate with BGE-M3

---

### 4. ❌ **FoodDB** (CHEMISTRY DATABASE - NOT IN RAG)
- **Location**: `FoodDB/` directory
- **Files**: 29 CSV files
- **Records**: ~40,000 food compounds with chemistry data
- **Status**: LOADED FOR TOOLS ONLY, NOT SEARCHABLE
- **Integration**:
  - ✅ Loaded via `backend/chemistry/foodb_loader.py`
  - ✅ Used by `backend/tools/get_food_chemistry.py`
  - ❌ NOT embedded
  - ❌ NOT in FAISS
  - ❌ NOT searchable via RAG
- **Search Route**: Direct tool access only (not RAG)
- **Missing Steps**:
  1. Create compound text representations
  2. Embed with BGE-M3
  3. Add to multi-source FAISS index
  4. Update `rag_engine.py` to query chemistry data

---

### 5. ❌ **FoodData Central - Branded Foods** (NOT INTEGRATED)
- **Location**: `FoodData Central – Branded Foods/` directory
- **Files**: 10 CSV files
  - `branded_food.csv`
  - `food.csv` (~400,000 branded products)
  - `food_nutrient.csv`
  - `nutrient.csv`
  - Others (attributes, updates, etc.)
- **Records**: ~400,000 branded food products
- **Status**: NOT INTEGRATED
- **Integration**:
  - ❌ NOT loaded
  - ❌ NOT parsed
  - ❌ NOT embedded
  - ❌ NOT searchable
- **Search Route**: None
- **Missing Steps**:
  1. Load and parse CSVs
  2. Create searchable text (name + nutrition + brand)
  3. Embed with BGE-M3
  4. Add to FAISS index

---

### 6. ❌ **FoodData Central - Foundation Foods** (NOT INTEGRATED)
- **Location**: `FoodData Central – Foundation Foods/` directory
- **Files**: 25 CSV files
  - Similar structure to Branded Foods
- **Records**: ~800 foundation foods (USDA reference data)
- **Status**: NOT INTEGRATED  
- **Integration**: Same as Branded Foods (none)
- **Missing Steps**: Same as Branded Foods

---

### 7. ❌ **FartDB.parquet** (NOT INTEGRATED)
- **Location**: Root directory
- **Size**: 545KB
- **Format**: Parquet file
- **Records**: Unknown (needs inspection)
- **Status**: NOT INTEGRATED
- **Integration**: None
- **Missing Steps**:
  1. Load and inspect Parquet file
  2. Determine schema and records
  3. Create text representations
  4. Embed and index

---

### 8. ❌ **foods_simple.json** (NOT INTEGRATED)
- **Location**: `processed/foods_simple.json`
- **Size**: 897KB
- **Records**: ~2,500 foods (estimated)
- **Status**: NOT INTEGRATED
- **Integration**: None
- **Missing Steps**:
  1. Load JSON
  2. Parse food data
  3. Embed with BGE-M3
  4. Add to FAISS

---

## Current RAG Pipeline Architecture

### Active Components
1. **Main Search**: `backend/vector_store/search.py`
   - Uses `backend/vector_store/embedder.py` (BGE-M3)
   - FAISS index: `backend/vector_store/faiss_index_bge.bin` (rebuilding)
   - Recipe IDs: `backend/vector_store/recipe_ids_bge.json`
   - Fallback: Lexical search via `backend/data_loader.py`

2. **RAG Engine**: `rag_engine.py`
   - Delegates to `VectorStoreSearch`
   - Uses `EmbedderBGE` for queries
   - Returns top-k recipes

3. **PDR Pipeline** (separate):
   - Endpoint: `/api/pdr`
   - Query: `scripts/pdr_rag.py`
   - Retrieval: `scripts/retrieve.py`
   - FAISS: Separate index in `scripts/`

### Missing: Multi-Source Aggregation
The current `rag_engine.search()` ONLY queries recipes. It does NOT aggregate:
- PDF-based cooking science knowledge
- Nutrition databases (FoodData Central)
- Chemistry data (FoodDB)
- Foundation foods
- Branded foods

---

## Recommended Actions

### Priority 1: Complete Recipe FAISS Rebuild
- **Status**: In progress (batch 284/844)
- **Action**: Let `scripts/rebuild_faiss_bge.py` complete
- **ETA**: ~2-3 hours remaining

### Priority 2: Re-embed RAG2 PDFs with BGE-M3
- **Script**: Create `scripts/embed_rag2_pdfs.py`
- **Steps**:
  1. Load `scripts/chunks.jsonl` (existing chunks)
  2. Embed with BGE-M3
  3. Build FAISS index
  4. Save to `backend/vector_store/faiss_pdf.bin`

### Priority 3: Embed FoodDB Chemistry Data
- **Script**: Create `scripts/embed_fooddb.py`
- **Steps**:
  1. Load compounds from `backend/chemistry/foodb_loader.py`
  2. Create text: `"{name}: {description}. Chemical formula: {formula}. Found in: {foods}."`
  3. Embed with BGE-M3
  4. Build FAISS index
  5. Save to `backend/vector_store/faiss_chemistry.bin`

### Priority 4: Embed FoodData Central
- **Script**: Create `scripts/embed_fooddata_central.py`
- **Steps**:
  1. Load branded + foundation foods CSVs
  2. Join with nutrients
  3. Create text: `"{name} ({brand}). Nutrition per 100g: {calories} cal, {protein}g protein, ..."`
  4. Embed with BGE-M3
  5. Build FAISS index
  6. Save to `backend/vector_store/faiss_nutrition_db.bin`

### Priority 5: Update RAG Engine for Multi-Source Search
- **File**: `rag_engine.py`
- **Changes**:
  1. Load multiple FAISS indices (recipes, PDFs, chemistry, nutrition)
  2. Search all indices in parallel
  3. Merge and re-rank results
  4. Return aggregated sources with labels

---

## Next Steps Summary

1. ✅ **Complete recipe FAISS rebuild** (in progress)
2. 📝 **Create embedding scripts** (see scripts section below)
3. 🔧 **Update `rag_engine.py`** for multi-source aggregation
4. ✅ **Migrate PDR pipeline** to use Qwen3 (update `pdr_rag.py`)
5. 🧪 **Test multi-source retrieval**

---

## Scripts to Create

### 1. `scripts/embed_rag2_pdfs.py`
Re-embed existing PDF chunks with BGE-M3

### 2. `scripts/embed_fooddb.py`
Embed chemistry compounds

### 3. `scripts/embed_fooddata_central.py`
Embed USDA nutrition database

### 4. `scripts/embed_foods_simple.py`
Embed processed foods JSON

### 5. `scripts/inspect_fartdb.py`
Inspect Parquet file contents

---

## Conclusion

**Current Status**: RAG pipeline is narrowly focused on recipes only.

**Opportunity**: By integrating the chemistry databases, PDF knowledge, and nutrition databases, the system can provide:
- Science-backed cooking explanations (from RAG2 PDFs)
- Chemical compound interactions (from FoodDB)
- Detailed nutrition data for any food (from FoodData Central)
- Comprehensive ingredient knowledge

**Recommendation**: Implement multi-source RAG aggregation to unlock the full potential of the available datasets.

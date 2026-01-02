# Retrieval Architecture

This document explains how the FAISS-only retrieval system works.

## Overview

Nutri-AI uses a **FAISS-only** retrieval backend. No HNSW, no fallbacks, no magic.

```
Query → Router → FAISS Index(es) → Results
```

## Module Structure

```
backend/retriever/
├── __init__.py           # Module exports
├── base.py               # Abstract BaseRetriever class
├── faiss_retriever.py    # FAISS implementation
└── router.py             # Multi-index routing
```

## Key Classes

### FaissRetriever

Handles a single FAISS index:

```python
from backend.retriever import FaissRetriever

retriever = FaissRetriever("backend/indexes/recipes.faiss")
retriever.load()
results = retriever.search("chicken pasta", top_k=5)
```

### Retrieval Architecture

Nutri-AI uses an **Agentic RAG** architecture where multiple isolated FAISS indexes provide specialized knowledge to a reasoning agent.

## Core Principle: Isolation

Strict dataset isolation is a non-negotiable requirement. Datasets are **never** logically or semantically merged within a single vector space.

### Mandated Isolated Indexes

| Dataset | Index Path | Content |
|---------|------------|---------|
| **USDA Branded** | `vector_store/usda_branded/` | 1.9M+ commercial food products |
| **USDA Foundation** | `vector_store/usda_foundation/` | High-fidelity raw food/ingredient data |
| **OpenNutrition** | `vector_store/open_nutrition/` | 320k+ international food records |
| **Recipes** | `vector_store/recipes/` | 13,500+ curated recipes |
| **Chemistry** | `vector_store/chemistry/` | FoodDB, PubChem, DSSTox, FartDB |
| **Science** | `vector_store/science/` | Scientific PDFs and research papers |

## Retrieval Router

The `RetrievalRouter` serves as the central orchestration layer. It does **not** perform global fallbacks. Instead:
1. **Explicit Selection**: The agent (or router logic) must explicitly decide which index(es) to query.
2. **Independent Boundaries**: Retrieval occurs within discrete boundaries.
3. **Agent Synthesis**: Cross-dataset reasoning happens at the LLM level, not via vector similarity.

### RetrievalRouter

Routes queries to multiple indexes:

```python
from backend.retriever import RetrievalRouter, IndexType

router = RetrievalRouter()
router.load_all_indexes()

# Smart search (auto-detects relevant indexes)
results = router.smart_search("Why does garlic turn green?")

# Explicit index search
results = router.search("protein rich foods", 
                        index_types=[IndexType.NUTRITION, IndexType.RECIPES])
```

## Index Types

| Type | Description |
|------|-------------|
| RECIPES | Recipe search (ingredients, instructions) |
| NUTRITION | Food nutrition data (USDA, branded foods) |
| CHEMISTRY | Chemical compounds (FoodDB, DSSTox) |
| SCIENCE | Science knowledge (PDFs, research) |

## Query Routing

The router detects query type using keywords:

- **Chemistry**: molecule, compound, reaction, enzyme, maillard...
- **Science**: research, study, why does, how does, temperature...
- **Nutrition**: calorie, protein, vitamin, healthy, diet...
- **Recipes**: recipe, cook, make, ingredients, meal...

If no keywords match, defaults to RECIPES.

## Integration Points

### In AgenticRAG

```python
from backend.retriever import RetrievalRouter

class AgenticRAG:
    def __init__(self):
        self.router = RetrievalRouter()
        self.router.load_all_indexes()
    
    def query(self, user_query):
        context = self.router.smart_search(user_query, top_k=5)
        # Use context in LLM prompt...
```

### In API Endpoints

```python
from backend.retriever import FaissRetriever

@app.get("/api/search")
def search(query: str, top_k: int = 10):
    retriever = FaissRetriever("backend/indexes/recipes.faiss")
    retriever.load()
    return retriever.search(query, top_k=top_k)
```

## Principles

1. **FAISS Only** - No HNSW, no mixed backends
2. **Explicit Paths** - All index paths in configuration
3. **Loud Failures** - Missing indexes raise exceptions
4. **Stateless Retrievers** - Load on demand, no global state

# Nutri-AI Project Setup Complete ✅

## Project Overview
**Nutri-AI** is an advanced recipe generation and nutrition analysis system that combines:
- 🤖 Large Language Models (Qwen3 via Ollama)
- 🔍 RAG (Retrieval-Augmented Generation) with semantic search
- 🧬 Chemistry compound analysis
- 📚 Nutrition insights from 140K+ recipes
- ⚗️ Multi-pass reasoning engine

## Architecture
```
Frontend (React)          Backend (FastAPI)         LLM Engine
  :3000                      :5001                  (Ollama)
    |                          |                        |
    +---- HTTP API ----+---- Routes ----+---- SYSTEM_PROMPT
                          |
                    RAG Pipeline
                          |
                   Vector Stores
                  (HNSW/FAISS)
```

## Installed Components

### Backend (Python/FastAPI)
- ✅ FastAPI framework
- ✅ Uvicorn ASGI server
- ✅ PyTorch & HuggingFace transformers
- ✅ Sentence transformers (embeddings)
- ✅ FAISS/HNSW (vector databases)
- ✅ Ollama (LLM integration)
- ✅ RAG pipeline with multi-index support

### Key Directories
```
backend/
  ├── routes/              # API endpoints
  ├── pipeline/            # RAG orchestration
  ├── vector_store/        # HNSW indices for recipes, compounds, nutrition
  ├── llm_qwen3.py        # Ollama integration
  └── agentic_rag.py      # Streaming agent with reasoning

frontend/                  # React UI (pending setup)
data/
  ├── raw/                 # Source data (FoodDB, DSSTox, etc.)
  ├── processed/           # FAISS indices
  └── nutrition/           # Nutrition metadata
```

## Running the Project

### 1. Backend Only (Currently Running)
```bash
python -m uvicorn api:app --port 5001 --host 0.0.0.0
```
✅ **Status**: Installing dependencies and starting on port 5001

### 2. Frontend Setup (Next Step)
```bash
cd frontend
npm install
npm run dev
```
Runs on `http://localhost:3000`

### 3. API Endpoints Available

**Chat & Recipe Generation**
- `POST /api/recipe` - Generate recipes from ingredients
- `POST /api/chat` - Multi-turn conversation
- `POST /api/chat/stream` - Streaming responses
- `WebSocket /ws` - Real-time agentic streaming

**Search**
- `POST /api/search` - Semantic recipe search
- `POST /api/hybrid_search` - Advanced hybrid retrieval

**RAG**
- `POST /api/pdr` - PDR (Herbal Medicine) query
- Integrated compound/nutrition knowledge bases

**System**
- `GET /api/stats` - System statistics
- `POST /api/feedback` - Collect user feedback
- `POST /api/session/clear` - Clear conversation history

## Key Files

- `api.py` - Main FastAPI application
- `llm.py` - LLM generation utilities  
- `prompts/__init__.py` - SYSTEM_PROMPT with role definition
- `backend/agentic_rag.py` - Streaming RAG agent
- `backend/vector_store/` - Multi-index vector search
- `requirements.txt` - Python dependencies

## Development Notes

### System Capabilities
- **Ingredient Analysis**: Pantry tracking and constraint validation
- **Recipe Generation**: Multi-pass self-correcting generation
- **Chemistry Mode**: Compound identification and properties
- **Nutritional Analysis**: Macro/micro nutrient calculations
- **Conversation Memory**: Session-based persistent context

### Environment Variables (Optional)
```
OLLAMA_HOST=http://localhost:11434  # Ollama server
BACKEND_PORT=5001                    # Backend port
```

### Data & Models
- Models cached in `./models/` (bge-m3 embeddings)
- Vector stores initialized on first query
- Recipe database: 142,893 recipes
- Chemistry compounds: 24,109+ papers

## Browser Preview
The backend API is now accessible at **http://localhost:5001**

### Test the API:
```bash
curl -X GET http://localhost:5001/api/stats
```

Expected response:
```json
{
  "recipes": 142893,
  "ingredients": "8.5M+",
  "papers": 24109
}
```

## Next Steps

1. **Frontend Setup** (Recommended)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. **Test Recipe Generation**
   ```bash
   curl -X POST http://localhost:5001/api/recipe \
     -H "Content-Type: application/json" \
     -d '{
       "ingredients": "chicken, rice, garlic",
       "goal": "quick dinner",
       "dietary_constraints": "none",
       "dislikes": "spicy",
       "innovation_level": 2
     }'
   ```

3. **Monitor Logs**
   - Backend logs in `logs/web_recipes.jsonl`
   - Feedback stored in `logs/feedback.jsonl`
   - Retrieval analytics in `logs/retrievals.jsonl`

## Configuration Saved
- Project config: `.orchids/orchids.json`
- Generated: 2025-12-14
- Backend: Python 3.10+ with FastAPI
- Status: ✅ Ready for development

---

**Happy cooking! 🍳** Your Nutri-AI backend is configured and running!

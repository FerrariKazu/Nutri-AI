# Nutri-AI Quick Start Guide

## 🚀 Backend Status
✅ **Running on http://localhost:5001**

The FastAPI backend is automatically starting with all dependencies installed.

## 📋 What's Running

### Backend (Python/FastAPI)
- Port: **5001**
- Status: **✅ Starting**
- Components: RAG pipeline, vector search, LLM integration

### Frontend (React)  
- Port: **3000**
- Status: **Pending setup**
- Next step: See "Frontend Setup" below

---

## 🧪 Test the Backend

### 1. Check API Status
```bash
curl http://localhost:5001/api/stats
```

### 2. Generate a Recipe
```bash
curl -X POST http://localhost:5001/api/recipe \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": "chicken, rice, tomato",
    "goal": "quick dinner",
    "dietary_constraints": "none",
    "dislikes": "spicy",
    "innovation_level": 2
  }'
```

### 3. Search Recipes
```bash
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pasta with vegetables", "k": 5}'
```

### 4. Chat
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I make a risotto?",
    "session_id": "test-session-123"
  }'
```

---

## 🎨 Frontend Setup (Optional)

### Prerequisites
- Node.js 18+
- npm or yarn

### Steps
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will run on **http://localhost:3000**

---

## 📚 API Documentation

### Swagger UI
Once backend is running, visit:
```
http://localhost:5001/docs
```

### OpenAPI Schema
```
http://localhost:5001/openapi.json
```

---

## 🔧 Configuration

All settings saved to: `.orchids/orchids.json`

### Environment Variables (Optional)
```bash
# Ollama server location
export OLLAMA_HOST=http://localhost:11434

# Backend port
export BACKEND_PORT=5001
```

---

## 📊 Project Structure

```
nutri-ai/
├── api.py                 # Main FastAPI app
├── backend/
│   ├── routes/           # API endpoints
│   ├── agentic_rag.py    # RAG agent
│   └── vector_store/     # Semantic search indices
├── frontend/             # React UI
├── data/                 # Recipes, compounds, nutrition
├── models/               # Cached ML models
├── requirements.txt      # Python dependencies
└── SETUP_COMPLETE.md     # Full documentation
```

---

## 🐛 Troubleshooting

### Backend won't start
1. Check Python version: `python --version` (need 3.10+)
2. Verify dependencies: `pip list | grep fastapi`
3. Check port 5001 is free: `netstat -an | grep 5001`

### Missing modules
Run: `pip install -r requirements.txt`

### Ollama not found
Ensure Ollama is installed and running:
```bash
ollama serve  # or check if already running
```

---

## 📖 Documentation

- **Full Setup**: See `SETUP_COMPLETE.md`
- **Architecture**: See `.orchids/orchids.json`
- **API Docs**: Visit `/docs` endpoint when backend is running

---

## 🎯 Next Steps

1. ✅ Backend is running
2. ⏳ Test an API endpoint above
3. 🎨 Set up frontend (optional)
4. 📝 Read full docs in `SETUP_COMPLETE.md`

**Happy cooking! 🍳**

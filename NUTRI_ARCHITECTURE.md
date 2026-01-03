# Nutri AI - Production Architecture

## Overview
Nutri is a scientifically grounded, agentic food intelligence system that performs **13 distinct reasoning phases** to provide sensory-aware, chemically validated culinary guidance.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER (Vercel Frontend)                      │
│                   React + Vite + TailwindCSS                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTPS (Cloudflare Tunnel)
                            │ chatdps.dpdns.org
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              LOCAL BACKEND (FastAPI + Python)                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  POST /api/chat  (Unified Endpoint)                       │ │
│  │  - Session-scoped memory (SQLite)                         │ │
│  │  - Typed SSE streaming (token, reasoning, final, error)   │ │
│  │  - Preference-aware orchestration                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼─────────────────────────────────┐ │
│  │         NutriOrchestrator (13 Phases)                     │ │
│  │  1. Intent Extraction                                     │ │
│  │  2. Knowledge Retrieval (RAG)                             │ │
│  │  3. Synthesis & Verification                              │ │
│  │  4. Sensory Modeling                                      │ │
│  │  5-6. Counterfactuals & Trade-offs                        │ │
│  │  7-10. Multi-Objective Optimization                       │ │
│  │  11-13. Final Compilation & Explanation                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼─────────────────────────────────┐ │
│  │  NutriPipeline Components:                                │ │
│  │  - LLMQwen3 (Ollama qwen3:8b)                             │ │
│  │  - FAISS Vector Store (bge-m3 embeddings)                 │ │
│  │  - Sensory Prediction Engine                              │ │
│  │  - Chemistry Validator                                    │ │
│  │  - Pareto Frontier Generator                              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼─────────────────────────────────┐ │
│  │  SessionMemoryStore (SQLite)                              │ │
│  │  - Table: sessions (session_id, created_at)               │ │
│  │  - Table: messages (id, session_id, role, content, ts)    │ │
│  │  - Context injection into Phase 1                         │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13 Scientific Reasoning Phases

### Phase 1: Intent & Constraint Extraction
- **Purpose**: Parse user input into structured culinary intent
- **Streaming**: Yes (token-by-token via LLM)
- **Output**: `IntentResult` with goals, constraints, dietary restrictions

### Phase 2: Domain Feasibility Check
- **Purpose**: Retrieve scientific evidence from vector store
- **Method**: FAISS semantic search on 50k+ documents
- **Output**: Top-k relevant scientific documents

### Phase 3: Culinary/Nutrition Synthesis
- **Purpose**: Generate baseline recipe with chemical grounding
- **Streaming**: Yes
- **Verification**: Rule-based chemistry validator
- **Output**: Baseline recipe + verification report

### Phase 4: Sensory Dimension Modeling
- **Purpose**: Predict physical/sensory properties
- **Properties**: Texture, aroma, flavor, mouthfeel, visual
- **Output**: `SensoryProfile` object

### Phase 5-6: Counterfactual Reasoning & Trade-offs
- **Purpose**: Simulate recipe variations to explain sensory impacts
- **Method**: Parameter perturbation (e.g., salt ±10%)
- **Calibration**: Audience-aware explanations (scientific, casual, etc.)
- **Output**: Explanation text

### Phase 7-10: Multi-Objective Optimization
- **Purpose**: Balance nutrition, sensory appeal, and user preferences
- **Method**: Pareto frontier construction
- **Selection**: Preference projection onto optimal variants
- **Output**: Selected optimal variant

### Phase 11-13: Final Compilation
- **Purpose**: Package final recipe, sensory profile, and explanations
- **Format**: Structured JSON with:
  - `recipe`: Final culinary output
  - `sensory_profile`: Predicted properties
  - `explanation`: Audience-calibrated reasoning
  - `verification_report`: Chemistry claims

---

## Streaming Protocol (SSE)

### Event Types
```
event: reasoning
data: <status message>

event: token
data: <single LLM token>

event: final
data: {"content": {...}}

event: error
data: <error message>
```

### Backend Implementation
- **Generator**: `orchestrator.execute_streamed()` yields `Dict[str, Any]`
- **Wrapper**: `server.py` wraps dicts into typed SSE events
- **Headers**:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`

### Frontend Implementation
- **Transport**: `fetch` + `ReadableStream` with `POST /api/chat`
- **Parser**: Line-based SSE parser tracking `currentEvent`
- **Callbacks**:
  - `onReasoning(message)` → Update UI phase status
  - `onToken(token)` → Append to streaming text
  - `onComplete(result)` → Finalize display
  - `onError(err)` → Show error UI

---

## Session Memory

### Architecture
- **Storage**: SQLite (`nutri_sessions.db`)
- **Scope**: Per-session (not global)
- **Lifetime**: Persistent across browser refreshes via `localStorage`

### Tables
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT CHECK(role IN ('user', 'assistant')),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
```

### Context Injection
- **Where**: Phase 1 (Intent Extraction)
- **Method**: `get_context_string(session_id, limit=5)` fetches last N messages
- **Format**:
  ```
  Previous Interaction Context:
  USER: <last user message>
  ASSISTANT: <last assistant summary>
  ...
  USER: <current message>
  ```

---

## Cloudflare Tunnel Setup

### Configuration (`cloudflared/config.yml`)
```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: chatdps.dpdns.org
    service: http://localhost:8000
  - service: http_status:404
```

### Setup Script (`setup_tunnel.sh`)
```bash
#!/bin/bash
# 1. Login to Cloudflare
cloudflared tunnel login

# 2. Create named tunnel
cloudflared tunnel create nutri-backend

# 3. Route DNS
cloudflared tunnel route dns nutri-backend chatdps.dpdns.org

# 4. Run tunnel
cloudflared tunnel --config cloudflared/config.yml run
```

### Security
- No exposed ports
- HTTPS enforced
- No temporary URLs (ngrok replacement)

---

## Deployment Workflow

### Backend (Local Machine)
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Start Ollama**: `ollama serve` (ensure `qwen3:8b` model pulled)
3. **Setup tunnel**: `./setup_tunnel.sh`
4. **Run backend**: `uvicorn backend.server:app --host 0.0.0.0 --port 8000`

### Frontend (Vercel)
1. **Build**: `cd frontend && npm run build`
2. **Deploy**: `vercel --prod`
3. **Environment Variable**: Set `VITE_API_URL=https://chatdps.dpdns.org`

### Unified Launch (Development)
```bash
./full_launch.sh
```
This starts Ollama, backend, frontend, and tunnel in separate terminals.

---

## Operating Principles

1. **Deterministic where possible**: Use rules for chemistry, ML only for synthesis
2. **Preserve scientific uncertainty**: Never hallucinate data
3. **No recipe retrieval**: Pure synthesis from first principles
4. **Stream all outputs**: Never block on long-running LLM calls
5. **Favor stability over cleverness**: Production-grade error handling

---

## Technology Stack

### Backend
- **Framework**: FastAPI (async)
- **LLM**: Ollama (`qwen3:8b`)
- **Embeddings**: BAAI/bge-m3
- **Vector Store**: FAISS
- **Database**: SQLite
- **Streaming**: Server-Sent Events (SSE)

### Frontend
- **Framework**: React 18 + Vite
- **Styling**: TailwindCSS
- **State**: React hooks (no Redux)
- **API**: Native `fetch` + `ReadableStream`

### Infrastructure
- **Tunnel**: Cloudflare Tunnel
- **Domain**: `chatdps.dpdns.org`
- **Frontend Hosting**: Vercel
- **Backend Hosting**: Local machine (high RAM/VRAM required)

---

## Error Handling

### Backend
- **Exceptions**: Caught in `orchestrator.execute_streamed()`, yielded as `{"type": "error"}`
- **Timeouts**: None (streaming keeps connection alive)
- **Retry Logic**: Not needed (streaming is stateless)

### Frontend
- **Network Errors**: Caught and passed to `onError` callback
- **Parse Errors**: Logged to console, stream continues
- **Abort**: User can cancel via returned abort function

---

## Future Enhancements

1. **Multi-user support**: Add authentication layer
2. **Advanced preferences**: More granular optimization goals
3. **Recipe export**: PDF/JSON download
4. **Image generation**: Visual plating suggestions (Stable Diffusion)
5. **Voice input**: Speech-to-text for culinary queries

---

**End of Architecture Document**

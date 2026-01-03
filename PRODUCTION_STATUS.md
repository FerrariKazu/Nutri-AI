# ✅ Production System - LIVE

## System Status

**Status**: 🟢 **OPERATIONAL**  
**Public Endpoint**: https://chatdps.dpdns.org  
**Last Verified**: 2026-01-03 22:27 UTC+2

---

## Active Services

### 1. Backend (FastAPI)
- **Status**: ✅ Running
- **Port**: 8000
- **Health**: `{"status":"healthy","service":"nutri-backend","version":"1.1.0"}`

### 2. Ollama (LLM Server) 
- **Status**: ✅ Running
- **Port**: 11434
- **Model**: qwen3:8b

### 3. Cloudflare Tunnel
- **Status**: ✅ Connected
- **Tunnel ID**: 39b45e5b-ddda-4560-a59c-f958e7d5c057
- **Domain**: chatdps.dpdns.org → localhost:8000
- **Edges**: 3 active connections (mrs04, mrs05, 2xmrs06)
- **DNS**: Resolves to 188.114.96.6, 188.114.97.6 ✅
- **TLS**: Valid Cloudflare certificate ✅

---

## Production URLs

### Public API (External)
```
https://chatdps.dpdns.org/api/chat      # Main endpoint
https://chatdps.dpdns.org/health        # Health check
```

### Local Backend (Internal)
```
http://localhost:8000/api/chat
http://localhost:8000/health
```

---

## Frontend Deployment to Vercel

### Step 1: Set Environment Variable
In your Vercel project settings:
```
VITE_API_URL=https://chatdps.dpdns.org
```

### Step 2: Deploy
```bash
cd frontend
npm run build
vercel --prod
```

### Step 3: Test
Once deployed, your frontend will automatically connect to `https://chatdps.dpdns.org`

---

## Test the Production API

### Simple Health Check
```bash
curl https://chatdps.dpdns.org/health
```

### Full Chat Request (SSE Stream)
```bash
curl -X POST https://chatdps.dpdns.org/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001",
    "message": "Create a low-glycemic, umami-rich pasta sauce",
    "preferences": {
      "audience_mode": "scientific",
      "optimization_goal": "comfort",
      "verbosity": "medium"
    }
  }'
```

Expected: Streaming SSE events with typed events (`reasoning`, `token`, `final`)

---

## Keep Services Running

### Current Setup (Manual)
You need **3 terminals** open:
1. **Terminal 1**: `ollama serve`
2. **Terminal 2**: `uvicorn backend.server:app --host 0.0.0.0 --port 8000`
3. **Terminal 3**: `./run_tunnel.sh`

### Recommended: Use screen/tmux
```bash
# Start all services in background
screen -dmS nutri-ollama bash -c "cd /home/ferrarikazu/nutri-ai && ollama serve"
screen -dmS nutri-backend bash -c "cd /home/ferrarikazu/nutri-ai && source venv/bin/activate && uvicorn backend.server:app --host 0.0.0.0 --port 8000"
screen -dmS nutri-tunnel bash -c "cd /home/ferrarikazu/nutri-ai && ./run_tunnel.sh"

# Check status
screen -ls

# Attach to view logs
screen -r nutri-backend  # Ctrl+A, D to detach
screen -r nutri-tunnel
```

---

## Architecture Overview

```
USER (Browser)
    ↓ HTTPS
Vercel Frontend (nutri-ai.vercel.app)
    ↓ POST /api/chat
Cloudflare Tunnel (chatdps.dpdns.org)
    ↓ Encrypted tunnel
WSL2 Backend (localhost:8000)
    ↓ HTTP
FastAPI + NutriOrchestrator
    ↓ Native API calls
Ollama (localhost:11434) → qwen3:8b
```

---

## ✅ Production Checklist

- [x] WSL2 DNS fixed (Cloudflare 1.1.1.1)
- [x] Cloudflare Tunnel created and running
- [x] DNS CNAME routed (chatdps.dpdns.org)
- [x] Backend healthy (localhost:8000)
- [x] Ollama running (qwen3:8b loaded)
- [x] Public HTTPS endpoint verified
- [x] TLS certificate valid
- [ ] Frontend deployed to Vercel (NEXT STEP)
- [ ] End-to-end test from Vercel UI

---

**Next Step**: Deploy your frontend to Vercel with `VITE_API_URL=https://chatdps.dpdns.org`

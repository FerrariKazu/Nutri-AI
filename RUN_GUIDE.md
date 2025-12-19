# 🚀 Nutri-AI Run Guide

Complete guide to running the optimized Nutri-AI system with qwen3:8b.

---

## ⚡ Quick Start (Copy-Paste Commands)

### 1. Stop Everything First
```bash
# Kill any existing processes
pkill -9 uvicorn
pkill -9 ollama
sleep 2
```

### 2. Start Ollama (WSL Optimized)
```bash
# We have a dedicated script for WSL that handles ports and models
./start_ollama_wsl.sh

# This will:
# 1. Kill old Ollama instances
# 2. Start WSL Ollama on port 11435
# 3. Check/Pull qwen3:8b model automatically
```

**Expected Output:**
```
✅ WSL Ollama running on port 11435
✅ qwen3:8b model found
✨ WSL Ollama Ready!
```

**Expected Output:**
```
qwen3:8b    500a1f067a9f    5.2 GB    ...
```

---

### 3. Start Backend
```bash
cd /home/ferrarikazu/nutri-ai

# Activate virtual environment
source venv/bin/activate

# Start backend (uses port 8000)
./start_backend.sh
```

**Expected Output:**
```
INFO - api - ✅ Model qwen3:8b found in Ollama
INFO - api - ✨ Nutri API Ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### 4. Start Frontend (New Terminal)
```bash
cd /home/ferrarikazu/nutri-ai/frontend

# Start Vite dev server (uses port 5173)
npm run dev
```

**Expected Output:**
```
VITE v... ready in ...ms
➜  Local:   http://localhost:5173/
```

---

### 5. Open Browser
```
http://localhost:5173
```

---

## 🔧 Troubleshooting

### ❌ OOM Error (GGML_ASSERT failed)

**Cause:** Ollama ran out of VRAM (8GB RTX 4060 is tight)

**Solution 1: Free VRAM**
```bash
# Kill Ollama
pkill -9 ollama
sleep 2

# Clear GPU memory
nvidia-smi --gpu-reset

# Restart with memory limits
OLLAMA_HOST=0.0.0.0:11435 \
OLLAMA_MAX_LOADED_MODELS=1 \
OLLAMA_NUM_PARALLEL=1 \
OLLAMA_MAX_QUEUE=4 \
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

**Solution 2: Unload Unused Models**
```bash
# Check what's loaded
ollama ps

# If other models are loaded, unload them
# (They auto-unload after 5 minutes of inactivity)
```

**Solution 3: Switch to Smaller Model (Last Resort)**
```bash
# Use the 7B model instead
ollama pull qwen2.5:7b-instruct-q4_K_M

# Update backend/agentic_rag.py line 47:
# Change: model_name: str = "qwen3:8b"
# To:     model_name: str = "qwen2.5:7b-instruct-q4_K_M"
```

---

### ❌ WebSocket Connection Failed

**Cause:** Backend not running or ports blocked

**Solution:**
```bash
# Check if backend is running
ss -tlnp | grep :8000

# If not running, start it
cd /home/ferrarikazu/nutri-ai
./start_backend.sh

# Check WebSocket logs
tail -f logs/server.log
```

---

### ❌ Model Not Found (404)

**Cause:** Ollama on wrong port

**Solution:**
```bash
# Check which port Ollama is on
ss -tlnp | grep 11435

# Should show port 11435
# If not running:
./start_ollama_wsl.sh
```

---

### ❌ Slow Responses

**Symptoms:** Queries take 60-90 seconds

**Diagnosis:**
```bash
# Monitor VRAM usage while running
watch -n 1 nvidia-smi

# Check if CPU offloading is happening
# (shown as "CPU layers" in nvidia-smi)
```

**Solutions:**
1. Close other GPU programs (browsers with hardware acceleration, etc.)
2. Reduce `max_iterations` further (edit `backend/agentic_rag.py` line 49)
3. Use smaller model

---

## 📊 System Requirements Check

### Verify Your Setup
```bash
# 1. Check VRAM
nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv

# 2. Check Python version (need 3.11+)
python3 --version

# 3. Check Node version (need 18+)
node --version

# 4. Check Ollama
ollama --version

# 5. Check if ports are free
ss -tlnp | grep -E ':(8000|5173|11435)'
```

**Expected:**
- VRAM: 8GB total, ~5-6GB free when idle
- Python: 3.11.x
- Node: 18.x or 20.x
- Ollama: 0.1.x or newer
- Ports: Only Ollama on 11435 (nothing on 8000 or 5173)

---

## 🎯 Performance Monitoring

### Check Response Speed
```bash
# Time a simple query
time curl -s http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is protein?", "mode": "standard"}'
```

**Expected:** 20-30 seconds for simple queries

### Monitor GPU Usage
```bash
# Live GPU monitoring
watch -n 1 nvidia-smi

# Log GPU usage to file
nvidia-smi dmon -s u -c 100 > gpu_usage.log
```

**Expected:**
- GPU Util: 80-100% during query
- Memory: 5-6GB used
- Temp: <80°C

---

## 🛑 Clean Shutdown

### Stop All Services Cleanly
```bash
# 1. Stop frontend (Ctrl+C in its terminal)

# 2. Stop backend
pkill -SIGTERM uvicorn
sleep 2

# 3. Stop Ollama
pkill -SIGTERM ollama
sleep 2

# 4. Verify everything stopped
ps aux | grep -E 'ollama|uvicorn|vite' | grep -v grep
```

---

## 📝 Configuration Files Modified

All optimizations are already applied in these files:

### Backend
- `backend/agentic_rag.py` - Model: qwen3:8b, Port: 11434
- `backend/llm_qwen3.py` - Model: qwen3:8b
- `backend/prompts/prompt_templates.py` - 84% smaller prompts
- `start_backend.sh` - Ollama port 11434

### Frontend
- `frontend/tailwind.config.js` - Dark mode enabled
- `frontend/src/styles/kitchen-theme.css` - Dark mode styles
- `frontend/src/components/Chat.jsx` - WebSocket streaming

---

## 🚨 Emergency Reset

If everything is broken:

```bash
#!/bin/bash
# emergency_reset.sh

echo "🚨 Emergency Reset - Killing Everything"

# Kill all processes
pkill -9 uvicorn
pkill -9 ollama
pkill -9 node

sleep 3

# Clear GPU
nvidia-smi --gpu-reset

sleep 2

echo "✅ All processes killed"
echo "📋 Now run the Quick Start commands from the top of this file"
```

---

## ✨ Expected Performance (After Optimizations)

| Metric | Value |
|--------|-------|
| Startup Time | ~16 seconds |
| Simple Query ("Make cookies") | 20-30s |
| Complex Query ("Why does bread rise?") | 30-45s |
| Token Generation Speed | 20-30 tok/s |
| VRAM Usage | 5-6GB |
| First Query (lazy load) | +30s (one-time) |

---

## 📞 Quick Reference

```bash
# Check backend status
curl -s http://localhost:8000/ | jq

# Check Ollama status  
curl -s http://localhost:11435/api/tags | jq '.models[].name'

# Check frontend status
curl -s http://localhost:5173/

# View backend logs
tail -f /home/ferrarikazu/nutri-ai/logs/server.log

# View Ollama logs
tail -f /tmp/ollama.log

# Monitor VRAM
watch -n 1 nvidia-smi
```

---

## 🎉 Success Checklist

Before asking a query, verify:
- [ ] Ollama running on port 11435
- [ ] `ollama list` shows `qwen3:8b`
- [ ] Backend shows "✨ Nutri API Ready!"
- [ ] Frontend accessible at localhost:5173
- [ ] GPU Util at 0-5% (idle)
- [ ] VRAM shows ~2-3GB used (embeddings loaded)

If all checked, **you're ready to go!** 🚀

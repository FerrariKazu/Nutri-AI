# Production Deployment Guide

## ✅ DNS Fix Applied (Permanent)

The WSL2 DNS issue has been resolved with the following changes:

### What Was Fixed
1. **Updated `/etc/wsl.conf`** to disable auto-generation of `resolv.conf`
2. **Configured `/etc/resolv.conf`** with production-grade DNS:
   - Primary: Cloudflare DNS (1.1.1.1, 1.0.0.1)
   - Backup: Google DNS (8.8.8.8, 8.8.4.4)
3. **Made immutable** with `chattr +i` to prevent WSL from overwriting

### Verification
```bash
# DNS now resolves Cloudflare servers:
nslookup region1.v2.argotunnel.com
# Server: 1.1.1.1
# Address: 198.41.192.77 (and 19 more IPs)
```

---

## 🚀 Production Deployment Workflow

### Step 1: Start Backend (Terminal 1)
```bash
cd /home/ferrarikazu/nutri-ai
source venv/bin/activate
uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 2: Start Cloudflare Tunnel (Terminal 2)
```bash
cd /home/ferrarikazu/nutri-ai
./run_tunnel.sh
```

Expected output:
```
🚀 Starting Cloudflare Tunnel: nutri-backend
📍 Domain: chatdps.dpdns.org → http://localhost:8000

2026-01-03T21:36:18Z INF Starting tunnel tunnelID=39b45e5b-ddda-4560-a59c-f958e7d5c057
2026-01-03T21:36:19Z INF Connection registered connIndex=0 ip=198.41.192.77
2026-01-03T21:36:19Z INF Connection registered connIndex=1 ip=198.41.192.37
...
```

### Step 3: Verify Tunnel is Live
```bash
# From any machine with internet:
curl https://chatdps.dpdns.org/health

# Expected: {"status":"healthy","service":"nutri-backend","version":"1.1.0"}
```

### Step 4: Deploy Frontend to Vercel
1. **Set Environment Variable** in Vercel dashboard:
   ```
   VITE_API_URL=https://chatdps.dpdns.org
   ```

2. **Deploy**:
   ```bash
   cd frontend
   npm run build
   vercel --prod
   ```

3. **Access**: Your Vercel URL (e.g., `nutri-ai.vercel.app`)

---

## ⚠️ Important Notes

### Keep Terminals Open
Both the backend AND tunnel must remain running:
- **Terminal 1**: Backend (Python/FastAPI)
- **Terminal 2**: Cloudflare Tunnel

If you close either terminal, the service will stop.

### For Long-Running Production
Use a process manager like `systemd` or `screen`:

#### Option A: Using screen (Simple)
```bash
# Start backend
screen -dmS nutri-backend bash -c "cd /home/ferrarikazu/nutri-ai && source venv/bin/activate && uvicorn backend.server:app --host 0.0.0.0 --port 8000"

# Start tunnel
screen -dmS nutri-tunnel bash -c "cd /home/ferrarikazu/nutri-ai && ./run_tunnel.sh"

# Check status
screen -ls

# Attach to see logs
screen -r nutri-backend  # Ctrl+A, D to detach
screen -r nutri-tunnel   # Ctrl+A, D to detach
```

#### Option B: Create systemd services (Recommended for production)
See `SYSTEMD_SETUP.md` for complete guide.

---

## 🔧 Troubleshooting

### Tunnel won't start
```bash
# Check DNS resolution
nslookup region1.v2.argotunnel.com

# Should show: Server: 1.1.1.1
# If it shows 10.255.255.254, the DNS fix didn't persist
# Re-run the DNS fix commands
```

### Backend not accessible via tunnel
```bash
# 1. Verify backend is running
curl http://localhost:8000/health

# 2. Check tunnel logs
tail -f /var/log/cloudflared.log

# 3. Verify tunnel config
cat /home/ferrarikazu/nutri-ai/cloudflared/config.yml
```

### Frontend can't connect
- **Check VITE_API_URL** in Vercel environment variables
- **Test directly**: `curl https://chatdps.dpdns.org/health`
- **Check CORS** in `backend/server.py` (should allow your Vercel domain)

---

## 📊 Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│  USER BROWSER (anywhere)                                │
│  https://nutri-ai.vercel.app                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ HTTPS
                      ↓
┌─────────────────────────────────────────────────────────┐
│  VERCEL (Frontend Hosting)                              │
│  - React + Vite                                         │
│  - Env: VITE_API_URL=https://chatdps.dpdns.org         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ API Requests
                      ↓
┌─────────────────────────────────────────────────────────┐
│  CLOUDFLARE TUNNEL                                      │
│  chatdps.dpdns.org → localhost:8000                     │
│  - Named tunnel: nutri-backend                          │
│  - No exposed ports                                     │
│  - HTTPS enforced                                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ Tunnel (encrypted)
                      ↓
┌─────────────────────────────────────────────────────────┐
│  LOCAL MACHINE (WSL2)                                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │  FastAPI Backend (localhost:8000)                  │ │
│  │  - 13-Phase Orchestration                          │ │
│  │  - SQLite Session Memory                           │ │
│  │  - FAISS Vector Store                              │ │
│  │  - Ollama (qwen3:8b)                               │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Deployment Checklist

- [x] WSL2 DNS fixed (permanent)
- [x] Cloudflare Tunnel created (`nutri-backend`)
- [x] Domain routed (`chatdps.dpdns.org`)
- [ ] Backend running on localhost:8000
- [ ] Tunnel running (`./run_tunnel.sh`)
- [ ] Tunnel verified (`curl https://chatdps.dpdns.org/health`)
- [ ] Vercel env variable set (`VITE_API_URL`)
- [ ] Frontend deployed to Vercel
- [ ] End-to-end test successful

---

**Next**: Start both services and verify the tunnel is accessible!

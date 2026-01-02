#!/bin/bash

# ==============================================================================
# Nutri-AI Persistent Launch Script (Serveo/WSL Friendly)
# Starts: Ollama -> Backend (API) -> Frontend (Vite) -> Tunnel (Serveo)
# ==============================================================================

# Ensure we are in the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load Environment Variables
if [ -f "nutri_env.sh" ]; then
    source nutri_env.sh
else
    echo "⚠️ nutri_env.sh not found. Using defaults."
    export BACKEND_PORT=8000
    export FRONTEND_PORT=5173
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}🚀 Nutri-AI Launch System (High Reliability)${NC}"
echo -e "${BLUE}====================================================${NC}"

# Cleanup function
kill_services() {
    pkill -f "backend.server" || true
    pkill -f "server.py" || true
    pkill -f "ngrok" || true
    pkill -f "vite" || true
    pkill -f "ollama serve" || true
    pkill -f "lt --port" || true
    pkill -f "ssh -R" || true
}

cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping all background services...${NC}"
    kill_services
    echo -e "${GREEN}✅ Services stopped.${NC}"
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${YELLOW}🧹 Cleaning up old sessions...${NC}"
kill_services > /dev/null 2>&1 || true
sleep 2

echo -e "${YELLOW}⚙️  Starting services in background...${NC}"

# 1. Ollama (Only if not running)
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    nohup ollama serve > ollama.log 2>&1 &
    echo -e "${GREEN}🤖 Ollama started (logs: ollama.log)${NC}"
else
    echo -e "${GREEN}🤖 Ollama is already running.${NC}"
fi

# 2. Backend
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
nohup python -u backend/server.py > api.log 2>&1 &
echo -e "${GREEN}⚙️  Backend started (logs: api.log)${NC}"

# 3. Frontend
cd frontend && nohup npm run dev > frontend.log 2>&1 &
echo -e "${GREEN}🌐 Frontend started (logs: frontend.log)${NC}"
cd ..

# 4. Tunneling (Using Serveo - most reliable fallback for WSL)
echo -e "${YELLOW}🚀 Starting tunnel (Serveo)...${NC}"
# We start SSH in background and log output to find the URL
nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:localhost:8000 serveo.net > serveo.log 2>&1 &

# 5. Detect URL
echo -ne "${YELLOW}⏳ Waiting for tunnel endpoint...${NC}"
TUNNEL_URL=""
for i in {1..20}; do
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.serveo\.net' serveo.log | head -n 1)
    if [ -n "$TUNNEL_URL" ]; then break; fi
    echo -ne "."
    sleep 1
done
echo ""

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${YELLOW}⚠️ Serveo slow. Trying Ngrok as fallback...${NC}"
    nohup ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
    for i in {1..15}; do
        TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.app' | head -n 1)
        if [ -n "$TUNNEL_URL" ]; then break; fi
        echo -ne "."
        sleep 1
    done
fi

if [ -n "$TUNNEL_URL" ]; then
    echo -e "${GREEN}====================================================${NC}"
    echo -e "${GREEN}✨ Nutri-AI is ONLINE!${NC}"
    echo -e "🌍 Public URL: ${NC}${YELLOW}$TUNNEL_URL${NC}"
    echo -e "⚙️  Local API: ${NC}http://localhost:8000"
    echo -e "${GREEN}====================================================${NC}"
    echo -e "${BLUE}INSTRUCTIONS FOR VERCEL:${NC}"
    echo -e "Update ${YELLOW}VITE_API_URL${NC} to: ${CYAN}$TUNNEL_URL${NC}"
    echo -e "${BLUE}====================================================${NC}"
else
    echo -e "${RED}❌ Failed to establish any tunnel. Check serveo.log and ngrok.log${NC}"
fi

# Keep script running
wait

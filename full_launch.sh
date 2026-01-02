#!/bin/bash

# ==============================================================================
# Nutri-AI Robust Launch Script (WSL/Remote Friendly)
# Starts: Ollama -> Backend (API) -> Frontend (Vite) -> Tunnel (lt/ngrok)
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
echo -e "${BLUE}🚀 Nutri-AI Launch System (Robust Mode)${NC}"
echo -e "${BLUE}====================================================${NC}"

# Function to kill all related processes
kill_services() {
    pkill -f "backend.server" || true
    pkill -f "server.py" || true
    pkill -f "ngrok" || true
    pkill -f "vite" || true
    pkill -f "ollama serve" || true
    pkill -f "lt --port" || true
}

# Cleanup function for signals
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

# 1. Ollama
nohup ollama serve > ollama.log 2>&1 &
echo -e "${GREEN}🤖 Ollama started (logs: ollama.log)${NC}"

# 2. Backend
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
nohup python -u backend/server.py > api.log 2>&1 &
echo -e "${GREEN}⚙️  Backend started (logs: api.log)${NC}"

# 3. Frontend
cd frontend && nohup npm run dev > frontend.log 2>&1 &
echo -e "${GREEN}🌐 Frontend started (logs: frontend.log)${NC}"
cd ..

# 4. Tunneling (Try LocalTunnel first as Ngrok is failing in this environment)
echo -e "${YELLOW}🚀 Starting tunnel (LocalTunnel)...${NC}"
nohup lt --port 8000 > lt.log 2>&1 &

# 5. Detect URL
echo -ne "${YELLOW}⏳ Waiting for tunnel endpoint...${NC}"
TUNNEL_URL=""
for i in {1..20}; do
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.loca\.lt' lt.log | head -n 1)
    if [ -n "$TUNNEL_URL" ]; then break; fi
    echo -ne "."
    sleep 1
done
echo ""

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${YELLOW}⚠️ LocalTunnel failed or slow. Trying Ngrok as fallback...${NC}"
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
    echo -e "1. Go to: ${WHITE}https://vercel.com/dashboard${NC}"
    echo -e "2. Update ${YELLOW}VITE_API_URL${NC} to: ${CYAN}$TUNNEL_URL${NC}"
    echo -e "3. Save and Redeploy if necessary."
    echo -e "${BLUE}====================================================${NC}"
else
    echo -e "${RED}❌ Failed to establish any tunnel. Check lt.log and ngrok.log${NC}"
fi

# Keep script running
wait

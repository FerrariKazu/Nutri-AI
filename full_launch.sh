#!/bin/bash

# ==============================================================================
# Nutri-AI Bulletproof Launch Script (Serveo/Localtunnel/WSL)
# Starts: Ollama -> Backend (API) -> Frontend (Vite) -> Tunnel
# ==============================================================================

# Ensure we are in the script's directory (Project Root)
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
WHITE='\033[1;37m'
CYAN='\033[0;36m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}🚀 Nutri-AI Launch System (Zero-Zombie Mode)${NC}"
echo -e "${BLUE}====================================================${NC}"

# Cleanup function
kill_services() {
    echo -e "${YELLOW}🧹 Aggressively recovering ports...${NC}"
    # Force kill anything on our ports (solves 502/CORS issues)
    fuser -k 8000/tcp > /dev/null 2>&1 || true
    fuser -k 5173/tcp > /dev/null 2>&1 || true
    
    # Kill by name as backup
    pkill -f "backend.server" || true
    pkill -f "server.py" || true
    pkill -f "ngrok" || true
    pkill -f "vite" || true
    pkill -f "ollama serve" || true
    pkill -f "lt --port" || true
    pkill -f "ssh -o ServerAliveInterval=60 -R" || true
    pkill -f "ssh -R 80:localhost:8000" || true
}

cleanup() {
    echo -e "\n${RED}🛑 Stopping all background services...${NC}"
    kill_services
    echo -e "${GREEN}✅ Services stopped cleanly.${NC}"
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${YELLOW}🧹 Cleaning up old sessions...${NC}"
kill_services > /dev/null 2>&1 || true
sleep 3

echo -e "${YELLOW}⚙️  Starting services in background...${NC}"

# 1. Ollama (Only if not running)
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    nohup ollama serve > "$SCRIPT_DIR/ollama.log" 2>&1 &
    echo -e "${GREEN}🤖 Ollama started (logs: ollama.log)${NC}"
else
    echo -e "${GREEN}🤖 Ollama is already running.${NC}"
fi

# 2. Backend
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}❌ Virtual environment (venv) not found!${NC}"
    exit 1
fi
export PYTHONPATH=$PYTHONPATH:.
nohup python -u backend/server.py > "$SCRIPT_DIR/api.log" 2>&1 &
echo -e "${GREEN}⚙️  Backend started (logs: api.log)${NC}"

# 3. Frontend
if [ -d "frontend" ]; then
    cd frontend
    nohup npm run dev > "$SCRIPT_DIR/frontend.log" 2>&1 &
    echo -e "${GREEN}🌐 Frontend started (logs: frontend.log)${NC}"
    cd ..
else
    echo -e "${RED}❌ Frontend directory not found!${NC}"
fi

# 4. Tunneling (Cloudflare Tunnel)
echo -e "${YELLOW}🚀 Starting Cloudflare Tunnel (chatdps.dpdns.org)...${NC}"
nohup ./run_tunnel.sh > "$SCRIPT_DIR/tunnel.log" 2>&1 &

# 5. Detect and Verify Health
echo -ne "${YELLOW}⏳ Verifying System Health...${NC}"
TUNNEL_URL="https://chatdps.dpdns.org"

for i in {1..30}; do
    if curl -s "http://localhost:8000/health" | grep -q "healthy"; then
        if curl -s "$TUNNEL_URL/health" | grep -q "healthy"; then
            echo -e "\n${GREEN}✨ Nutri-AI is ONLINE!${NC}"
            echo -e "🌍 Public URL: ${NC}${YELLOW}$TUNNEL_URL${NC}"
            echo -e "⚙️  Local API: ${NC}http://localhost:8000"
            echo -e "${GREEN}====================================================${NC}"
            echo -e "${BLUE}INSTRUCTIONS FOR VERCEL:${NC}"
            echo -e "1. Update ${YELLOW}VITE_API_URL${NC} to: ${CYAN}$TUNNEL_URL${NC}"
            echo -e "2. Save and Redeploy."
            echo -e "${BLUE}====================================================${NC}"
            break
        fi
    fi
    echo -ne "."
    sleep 2
done

if [ $i -eq 30 ]; then
    echo -e "\n${RED}❌ System health check timed out. Check api.log and tunnel.log${NC}"
fi

echo -e "${WHITE}⚠️  KEEP THIS TERMINAL OPEN TO MAINTAIN THE CONNECTION.${NC}"
echo -e "${WHITE}Press ${CYAN}Ctrl+C${WHITE} to stop all services and exit.${NC}"

# Keep alive loop
while true; do
    sleep 60
done

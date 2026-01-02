#!/bin/bash

# ==============================================================================
# Nutri-AI Extreme Debugging Launch Script
# Starts: Ollama -> Backend (API) -> Frontend (Vite) -> Ngrok Tunnel
# ==============================================================================

# Ensure we are in the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load Environment Variables
if [ -f "nutri_env.sh" ]; then
    source nutri_env.sh
else
    echo "⚠️ nutri_env.sh not found. Using defaults."
    export NGROK_AUTHTOKEN="3751t7SGjFTSuVk1pHjCefca6xZ_HFscRBC65pq2darzgMkZ"
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
echo -e "${BLUE}🚀 Nutri-AI Launch System${NC}"
echo -e "${BLUE}====================================================${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping all background services...${NC}"
    pkill -f "backend.server" || true
    pkill -f "server.py" || true
    pkill -f "ngrok" || true
    pkill -f "vite" || true
    pkill -f "ollama serve" || true
    echo -e "${GREEN}✅ Services stopped.${NC}"
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${YELLOW}🧹 Cleaning up old sessions...${NC}"
pkill -f "backend.server" || true
pkill -f "server.py" || true
pkill -f "ngrok" || true
pkill -f "vite" || true
pkill -f "ollama serve" || true
sleep 2

# Force background mode if requested or if xterm is known to be problematic
FORCE_BG=true # Default to background for stability in WSL

if [ "$FORCE_BG" = "true" ]; then
    echo -e "${YELLOW}⚙️  Running in background mode (most stable for WSL/Remote)...${NC}"
    
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
    
    # 4. Ngrok
    nohup ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
    echo -e "${GREEN}🚀 Ngrok started (logs: ngrok.log)${NC}"
    
    # 5. Detect URL
    echo -ne "${YELLOW}⏳ Waiting for ngrok endpoint...${NC}"
    NGROK_URL=""
    for i in {1..30}; do
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.app' | head -n 1)
        if [ -n "$NGROK_URL" ]; then break; fi
        echo -ne "."
        sleep 1
    done
    echo ""
    
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}====================================================${NC}"
        echo -e "${GREEN}✨ Nutri-AI is ONLINE!${NC}"
        echo -e "🌍 Public URL: ${NC}${YELLOW}$NGROK_URL${NC}"
        echo -e "⚙️  Local API: ${NC}http://localhost:8000"
        echo -e "${GREEN}====================================================${NC}"
        echo -e "${BLUE}IMPORTANT FOR VERCEL:${NC}"
        echo -e "Update your Vercel VITE_API_URL to: ${YELLOW}$NGROK_URL${NC}"
        echo -e "${BLUE}====================================================${NC}"
    else
        echo -e "${RED}❌ Timeout waiting for ngrok. Check ngrok.log${NC}"
    fi

else
    # Legacy GUI Terminal block (skipped by default now)
    echo "GUI Terminal mode skipped. Running in background mode is recommended."
fi

# Keep script running
wait

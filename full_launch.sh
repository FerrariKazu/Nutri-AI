#!/bin/bash

# ==============================================================================
# Nutri-AI Extreme Debugging Launch Script
# Starts: Ollama -> Backend (API) -> Frontend (Vite) -> Ngrok Tunnel
# Each service opens in its own terminal for live log viewing.
# ==============================================================================

# Load Environment Variables
if [ -f "nutri_env.sh" ]; then
    source nutri_env.sh
else
    echo "⚠️ nutri_env.sh not found. Using defaults."
    export NGROK_AUTHTOKEN="3751t7SGjFTSuVk1pHjCefca6xZ_HFscRBC65pq2darzgMkZ"
    export BACKEND_PORT=8000
    export FRONTEND_PORT=5173
fi

# Colors for better output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}🚀 Starting Nutri-AI Extreme Debugging Mode${NC}"
echo -e "${BLUE}====================================================${NC}"

# Detect available terminal emulator
get_terminal() {
    if command -v xterm &> /dev/null; then
        echo "xterm"
    elif command -v gnome-terminal &> /dev/null; then
        echo "gnome-terminal"
    elif command -v x-terminal-emulator &> /dev/null; then
        echo "x-terminal-emulator"
    elif [ -n "$WT_SESSION" ]; then # Windows Terminal detection (WSL)
        echo "wt"
    else
        echo "none"
    fi
}

TERMINAL=$(get_terminal)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Configure Ngrok
if [ -n "$NGROK_AUTHTOKEN" ]; then
    echo -e "${YELLOW}🔑 Configuring ngrok...${NC}"
    ngrok config add-authtoken "$NGROK_AUTHTOKEN" > /dev/null 2>&1
fi

if [ "$TERMINAL" != "none" ] && [ -n "$DISPLAY" ]; then
    echo -e "${GREEN}🖥️  Launching separate terminals for logs...${NC}"
    
    # 1. Ollama Terminal
    if [ "$TERMINAL" = "gnome-terminal" ]; then
        dbus-run-session -- gnome-terminal --title="Nutri Ollama" -- bash -c "echo '🤖 NUTRI OLLAMA LOGS'; ollama serve; exec bash"
    elif [ "$TERMINAL" = "xterm" ]; then
        xterm -title "Nutri Ollama" -e bash -c "echo '🤖 NUTRI OLLAMA LOGS'; ollama serve; exec bash" &
    else
        x-terminal-emulator -T "Nutri Ollama" -e bash -c "echo '🤖 NUTRI OLLAMA LOGS'; ollama serve; exec bash" &
    fi
    
    sleep 2

    # 2. Backend Terminal
    # Added PYTHONPATH to ensure 'backend' module is found
    BACKEND_CMD="echo '⚙️ NUTRI BACKEND LOGS'; cd '$SCRIPT_DIR'; source venv/bin/activate; export PYTHONPATH=\$PYTHONPATH:. ; python -u backend/server.py; exec bash"
    if [ "$TERMINAL" = "gnome-terminal" ]; then
        dbus-run-session -- gnome-terminal --title="Nutri Backend" -- bash -c "$BACKEND_CMD"
    elif [ "$TERMINAL" = "xterm" ]; then
        xterm -title "Nutri Backend" -e bash -c "$BACKEND_CMD" &
    else
        x-terminal-emulator -T "Nutri Backend" -e bash -c "$BACKEND_CMD" &
    fi

    sleep 5

    # 3. Frontend Terminal
    FRONTEND_CMD="echo '🌐 NUTRI FRONTEND LOGS'; cd '$SCRIPT_DIR/frontend'; npm run dev; exec bash"
    if [ "$TERMINAL" = "gnome-terminal" ]; then
        dbus-run-session -- gnome-terminal --title="Nutri Frontend" -- bash -c "$FRONTEND_CMD"
    elif [ "$TERMINAL" = "xterm" ]; then
        xterm -title "Nutri Frontend" -e bash -c "$FRONTEND_CMD" &
    else
        x-terminal-emulator -T "Nutri Frontend" -e bash -c "$FRONTEND_CMD" &
    fi

    # 4. Ngrok & Summary (Stay in this terminal)
    echo -e "${YELLOW}🚀 Starting ngrok tunnel...${NC}"
    ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
    
    # Wait for Ngrok to generate URL
    echo -e "${YELLOW}⏳ Waiting for ngrok endpoint...${NC}"
    NGROK_URL=""
    for i in {1..20}; do
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.app' | head -n 1)
        if [ -n "$NGROK_URL" ]; then break; fi
        sleep 1
    done
    
    if [ -z "$NGROK_URL" ]; then
        echo -e "${RED}❌ Failed to detect ngrok URL. Check ngrok.log${NC}"
    fi
    
    echo -e "${GREEN}====================================================${NC}"
    echo -e "${GREEN}✨ Nutri-AI is now ONLINE in EXTREME DEBUG MODE!${NC}"
    echo -e "🌍 Public URL: ${NC}${YELLOW}$NGROK_URL${NC}"
    echo -e "⚙️  Backend: ${NC}http://localhost:8000"
    echo -e "🌐 Frontend: ${NC}http://localhost:5173"
    echo -e "${GREEN}====================================================${NC}"
    echo -e "${BLUE}Check separate terminal windows if they opened.${NC}"
    echo -e "${BLUE}If using Vercel, update VITE_API_URL to: $NGROK_URL${NC}"
    
else
    echo -e "${RED}⚠️ No GUI terminal detected (or no DISPLAY). Running in background mode...${NC}"
    
    # Fallback to original background behavior but with explicit logging
    pkill -f "ollama serve" || true
    nohup ollama serve > ollama.log 2>&1 &
    echo -e "${YELLOW}🤖 Ollama started in background (logs: ollama.log)${NC}"
    
    source venv/bin/activate
    export PYTHONPATH=$PYTHONPATH:.
    nohup python -u backend/server.py > api.log 2>&1 &
    echo -e "${YELLOW}⚙️  Backend started in background (logs: api.log)${NC}"
    
    cd frontend && nohup npm run dev > frontend.log 2>&1 &
    echo -e "${YELLOW}🌐 Frontend started in background (logs: frontend.log)${NC}"
    cd ..
    
    nohup ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
    echo -e "${YELLOW}🚀 Ngrok started in background (logs: ngrok.log)${NC}"
    
    echo -e "${YELLOW}⏳ Waiting for ngrok endpoint...${NC}"
    NGROK_URL=""
    for i in {1..20}; do
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.app' | head -n 1)
        if [ -n "$NGROK_URL" ]; then break; fi
        sleep 1
    done
    
    echo -e "${GREEN}====================================================${NC}"
    echo -e "${GREEN}✨ Nutri-AI is ONLINE!${NC}"
    echo -e "🌍 Public URL: ${NC}${YELLOW}$NGROK_URL${NC}"
    echo -e "${GREEN}====================================================${NC}"
    echo -e "Use 'tail -f *.log' to see live logs in this environment."
    echo -e "${BLUE}If using Vercel, update VITE_API_URL to: $NGROK_URL${NC}"
fi

# Keep script running
wait

#!/bin/bash

# 0. Cleanup existing processes
echo "🧹 Cleaning up old sessions..."
pkill -f ngrok || true
pkill -f api.py || true
sleep 2

# 1. Start Backend
echo "⚙️  Starting Backend (api.py)..."
# Load venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# Use python3 as fallback if python is not found
PY_CMD=$(command -v python3 || command -v python)
nohup $PY_CMD -u api.py > api.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# 2. Start Ngrok
NGROK_TOKEN="3751t7SGjFTSuVk1pHjCefca6xZ_HFscRBC65pq2darzgMkZ"
echo "🔑 Configuring ngrok..."
ngrok config add-authtoken $NGROK_TOKEN

echo "🚀 Starting ngrok tunnel..."
ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!

echo "⏳ Waiting for initialization (25s)..."
sleep 25

# Extract the URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.app' | head -n 1)

if [ -z "$NGROK_URL" ]; then
    # Retry with .dev domain search if .app fails
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.dev' | head -n 1)
fi

if [ -n "$NGROK_URL" ]; then
    echo "----------------------------------------------------"
    echo "🌍 Public URL: $NGROK_URL"
    echo "⚙️  VITE_API_URL: $NGROK_URL"
    echo "----------------------------------------------------"
else
    echo "❌ Failed to get ngrok URL. Checking logs..."
    tail -n 10 ngrok.log
fi

# Prevent script from exiting
wait $NGROK_PID

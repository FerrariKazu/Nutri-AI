#!/bin/bash

# User's ngrok Authtoken
NGROK_TOKEN="3751t7SGjFTSuVk1pHjCefca6xZ_HFscRBC65pq2darzgMkZ"

echo "🔑 Configuring ngrok authtoken..."
ngrok config add-authtoken $NGROK_TOKEN

echo "🚀 Starting ngrok tunnel on port 8000..."
# Run ngrok in the background. 
# We use --log=stdout to help extract the URL if needed, 
# but usually checking the API is better.
ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!

echo "⏳ Waiting for ngrok URL..."
sleep 5

# Extract the public URL from the local ngrok API
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-zA-Z0-9.-]*\.ngrok-free.app' | head -n 1)

if [ -z "$NGROK_URL" ]; then
    # Try alternate pattern just in case
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://.*\.ngrok\.io' | head -n 1)
fi

if [ ! -z "$NGROK_URL" ]; then
    echo "=================================================="
    echo "✅ SUCCESS! Your Backend is now public at:"
    echo "🔗 $NGROK_URL"
    echo "=================================================="
    echo ""
    echo "👉 Copy this URL and paste it as VITE_API_URL in Vercel."
    echo ""
    echo "ℹ️  Keep this script running to maintain the connection."
else
    echo "❌ Failed to extract ngrok URL."
    echo "Check ngrok.log for details."
    kill $NGROK_PID
fi

# Keep script running
wait $NGROK_PID

#!/bin/bash

# Configuration
RAILWAY_SERVICE_NAME="Nutri-AI"

echo "🔄 Starting Nutri-AI Auto-Connector..."

# 1. Start Tunnel (using Cloudflare for stability)
# If cloudflared is not found, fallback to localhost.run
if command -v cloudflared &> /dev/null; then
    echo "☁️  Starting Cloudflare Tunnel..."
    # Start cloudflared in background and log to temp file
    cloudflared tunnel --url http://localhost:8000 > /tmp/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    
    echo "⏳ Waiting for tunnel URL..."
    
    # Loop to wait for URL (up to 30s)
    for i in {1..30}; do
        TUNNEL_URL=$(grep -o 'https://.*\.trycloudflare.com' /tmp/tunnel.log | head -n 1)
        if [ ! -z "$TUNNEL_URL" ]; then
            break
        fi
        sleep 1
    done
else
    echo "🔗 Starting SSH Tunnel (localhost.run)..."
    ssh -R 80:localhost:8000 nokey@localhost.run > /tmp/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    
    echo "⏳ Waiting for tunnel URL..."
    sleep 5
    
    # Extract URL from log (localhost.run format might vary, usually in stdout or stderr)
    # This is trickier with ssh, so likely we need to rely on user or better parsing
    # For now, let's assume Cloudflare is preferred since it is installed.
    TUNNEL_URL=$(grep -o 'https://.*\.lhr.life' /tmp/tunnel.log | head -n 1)
fi

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Failed to get tunnel URL. Check /tmp/tunnel.log"
    cat /tmp/tunnel.log
    kill $TUNNEL_PID
    exit 1
fi

echo "✅ Tunnel Active: $TUNNEL_URL"

# 2. Update Railway
if command -v railway &> /dev/null; then
    echo "🚀 Updating Railway Variable..."
    # Use --set for variable update and quote the key=value pair
    railway variables --set "LLM_ENDPOINT=$TUNNEL_URL" --service $RAILWAY_SERVICE_NAME
    
    echo "🔄 Redeploying Gateway..."
    # Variable update usually triggers redeploy automatically, but we can force it if needed
    # railway up --service $RAILWAY_SERVICE_NAME 
    
    echo "✨ Done! Railway is updating to: $TUNNEL_URL"
else
    echo "⚠️  Railway CLI not found!"
    echo "👉 Please manually update LLM_ENDPOINT in Railway to: $TUNNEL_URL"
fi

# 3. Keep script running to keep tunnel alive
wait $TUNNEL_PID

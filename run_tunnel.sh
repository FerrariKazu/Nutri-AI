#!/bin/bash
# Cloudflare Tunnel Runner for Production

echo "🚀 Starting Cloudflare Tunnel: nutri-backend"
echo "📍 Domain: chatdps.dpdns.org → http://localhost:8000"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "⚠️  WARNING: Backend (localhost:8000) is not responding!"
    echo "   Start backend first with: uvicorn backend.server:app --host 0.0.0.0 --port 8000"
    echo ""
fi

# Start tunnel
cloudflared tunnel --config /home/ferrarikazu/nutri-ai/cloudflared/config.yml run

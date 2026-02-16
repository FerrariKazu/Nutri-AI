#!/bin/bash
echo "🚀 Starting Frontend Auto-Sync (Watch Mode)..."
echo "   - Interval: 30s"
echo "   - Max File Size: 50MB"
echo "   - Directory: frontend/"

# python3 scripts/sync_frontend.py
nohup python3 scripts/sync_frontend.py > frontend_sync.log 2>&1 &
PID=$!
echo "✅ Sync process started in background. PID: $PID"
echo "   Logs: frontend_sync.log"
echo "   Stop: kill $PID"

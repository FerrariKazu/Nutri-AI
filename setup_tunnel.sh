#!/bin/bash
# Nutri Cloudflare Tunnel Setup Helper

echo "🚀 Starting Nutri Tunnel Setup..."

# 1. Login if needed
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "🔑 Please log in to Cloudflare..."
    cloudflared tunnel login
fi

# 2. Create tunnel if it doesn't exist
TUNNEL_NAME="nutri-backend"
if ! cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo "⚙️ Creating tunnel: $TUNNEL_NAME..."
    cloudflared tunnel create $TUNNEL_NAME
else
    echo "✅ Tunnel $TUNNEL_NAME already exists."
fi

# 3. Get Tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo "🆔 Tunnel ID: $TUNNEL_ID"

# 4. Update config.yml
CONFIG_PATH="/home/ferrarikazu/nutri-ai/cloudflared/config.yml"
sed -i "s/<TUNNEL_ID>/$TUNNEL_ID/g" $CONFIG_PATH

# 5. Route DNS
echo "🌐 Routing chatdps.dpdns.org to tunnel..."
cloudflared tunnel route dns $TUNNEL_NAME chatdps.dpdns.org

echo "✅ Setup Complete!"
echo "Run 'cloudflared tunnel --config $CONFIG_PATH run' to start the tunnel."

#!/usr/bin/env bash
set -e

# Configuration
DOWNLOAD_DIR="${DOWNLOAD_DIR:-/content/drive/MyDrive/Downloads}"
ARIA2_PORT="${ARIA2_PORT:-6800}"
WEB_PORT="${PORT:-8000}"

echo "⚡ Starting Cloud Ultra Downloader..."
mkdir -p "$DOWNLOAD_DIR"

# 1. Start Aria2c RPC daemon if not running
if ! pgrep -x "aria2c" > /dev/null; then
    echo "🚀 Starting aria2c daemon (16 parallel connections)..."
    aria2c --enable-rpc \
           --rpc-listen-all=true \
           --rpc-listen-port="$ARIA2_PORT" \
           --max-connection-per-server=16 \
           --split=16 \
           --min-split-size=1M \
           --max-concurrent-downloads=5 \
           --continue=true \
           --dir="$DOWNLOAD_DIR" \
           --rpc-allow-origin-all=true \
           --daemon=true
    sleep 1
    echo "✓ Aria2c daemon running on port $ARIA2_PORT"
else
    echo "✓ Aria2c daemon is already running"
fi

# 2. Launch FastAPI web server
echo "🌐 Starting Web Server on port $WEB_PORT..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$WEB_PORT"

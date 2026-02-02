#!/bin/bash
# run_llama_server.sh
# Hardened launcher for Nutri's llama.cpp runtime (Qwen3-8B)
# Optimized for RTX 4060 (8GB VRAM)

DIST_DIR="./llm_runtime/llama_cpp/dist"
export LD_LIBRARY_PATH="$DIST_DIR/lib:$DIST_DIR:$LD_LIBRARY_PATH"

# 1. Resolve Binary
if [ -n "$LLAMA_BIN" ]; then
    BINARY="$LLAMA_BIN"
elif [ -f "$DIST_DIR/bin/llama-server" ]; then
    BINARY="$DIST_DIR/bin/llama-server"
elif [ -f "$DIST_DIR/llama-server" ]; then
    BINARY="$DIST_DIR/llama-server"
else
    echo "Error: llama-server binary not found in $DIST_DIR"
    exit 1
fi

# 2. Configuration (User Recommended Defaults)
MODEL_PATH=${MODEL_PATH:-"models/qwen3-4b-instruct-q4_k_m.gguf"}
PORT=${LLAMA_PORT:-8081}
HOST=${LLAMA_HOST:-"127.0.0.1"}

# Optimization Flags
N_CTX=${LLAMA_N_CTX:-8192}          # Increased from 4096 (4B is light)
NGL=${LLAMA_NGL:-99}                # Offload all layers for maximum performance
THREADS=${LLAMA_THREADS:-6}         # Physical cores reserved
BATCH_SIZE=${LLAMA_BATCH:-512}      # Batch size for processing

# 3. Model Check
if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file missing at $MODEL_PATH"
    echo "Please run ./setup_llama.sh to download Qwen3-8B."
    exit 1
fi

# 4. Pre-Flight CUDA Check
echo "----------------------------------------"
echo "Nutri Llama Runtime: GPU-Accelerated Mode"
echo "----------------------------------------"
echo "🔍 Verifying GPU availability..."

# Check if nvidia-smi is available
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)
    echo "✅ GPU Detected: $GPU_NAME ($GPU_VRAM)"
else
    echo "⚠️  WARNING: nvidia-smi not found. GPU may not be available."
fi

# Check if binary supports CUDA
if "$BINARY" --help 2>&1 | grep -qi "cuda\|gpu"; then
    echo "✅ CUDA support confirmed in llama-server binary"
else
    echo "⚠️  WARNING: CUDA support not detected in binary!"
    echo "   This will run in CPU-only mode."
fi

echo "----------------------------------------"
echo "Binary: $BINARY"
echo "Model:  $MODEL_PATH"
echo "Config: NGL=$NGL CTX=$N_CTX Batch=$BATCH_SIZE"
echo "----------------------------------------"

# 5. Launch with GPU Offload
echo "🚀 Launching llama-server with GPU acceleration..."
echo "⏳ Model will load in background. This takes 30-90 seconds."
echo "   Watch for 'main: server is listening' message below."
echo ""

# Launch server in foreground (logs will appear in this terminal)
"$BINARY" \
  -m "$MODEL_PATH" \
  -c "$N_CTX" \
  -ngl "$NGL" \
  -b "$BATCH_SIZE" \
  --port "$PORT" \
  --host "$HOST" \
  --threads "$THREADS" \
  --mlock \
  --parallel 1 &

SERVER_PID=$!

# Monitor GPU usage after 30 seconds (give model time to load)
(
  sleep 30
  if command -v nvidia-smi &> /dev/null; then
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
    echo "----------------------------------------"
    echo "📊 GPU Status After Model Load:"
    echo "   VRAM Used: ${VRAM_USED} MB (Expected: 4000-6000 MB)"
    echo "   GPU Utilization: ${GPU_UTIL}%"
    echo "----------------------------------------"
  fi
) &

# Wait for server process
wait $SERVER_PID
EXIT_CODE=$?

# If GPU launch fails (e.g., OOM or CUDA missing), try CPU fallback
if [ $EXIT_CODE -ne 0 ]; then
    echo "⚠️  GPU Launch Failed (Code $EXIT_CODE). Falling back to CPU/Safe Mode..."
    
    # Safe Mode: No GPU, reduced context
    SAFE_CTX=2048
    "$BINARY" \
      -m "$MODEL_PATH" \
      -c "$SAFE_CTX" \
      -ngl 0 \
      -b 256 \
      --port "$PORT" \
      --host "$HOST" \
      --threads "$THREADS" 
fi

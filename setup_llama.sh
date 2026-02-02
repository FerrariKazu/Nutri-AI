#!/bin/bash
# setup_llama.sh
# Automates downloading llama-server and the Qwen3-4B model
# Robust Version: Extracts full runtime including shared libraries

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Nutri Llama.cpp Setup (Complete Runtime)...${NC}"

# 1. Download llama-server (CUDA 12.4 Enabled)
# Using specific stable release b7836 for Ubuntu x64 with CUDA support
BINARY_URL="https://github.com/ggml-org/llama.cpp/releases/download/b7836/llama-b7836-bin-ubuntu-x64-cu124.tar.gz"
DIST_DIR="llm_runtime/llama_cpp/dist"

echo "Downloading CUDA-enabled llama.cpp binary from: $BINARY_URL"
wget -O llama.tar.gz "$BINARY_URL" || { echo -e "${RED}Binary download failed.${NC}"; exit 1; }

echo "Extracting to $DIST_DIR..."
mkdir -p "$DIST_DIR"
tar -xzf llama.tar.gz -C "$DIST_DIR" --strip-components=1
# Note: --strip-components=1 assumes the tarball has a root folder. 
# If it's flat, this might strip files. Let's check structure safe way:
# Actually, b7836 usually has "build" or similar. 
# Safer: extract to temp, then move.

rm -rf llama_temp
mkdir -p llama_temp
tar -xzf llama.tar.gz -C llama_temp

# Move contents to DIST_DIR
# We want bin/* and lib/* if they exist, or just everything
cp -r llama_temp/* "$DIST_DIR/"

rm -rf llama.tar.gz llama_temp
echo -e "${GREEN}✅ Runtime installed to $DIST_DIR.${NC}"

# 1b. Verify CUDA Support
echo "Verifying CUDA backend support..."
if "$DIST_DIR/llama-server" --help 2>&1 | grep -qi "cuda\|gpu"; then
    echo -e "${GREEN}✅ CUDA/GPU support detected in binary${NC}"
else
    echo -e "${RED}⚠️  WARNING: CUDA support not detected. Binary may be CPU-only.${NC}"
    echo "This will still work but won't use your RTX 4060 GPU."
fi

# 2. Download Model (Qwen3-4B-Instruct Q4_K_M)
MODEL_DIR="models"
mkdir -p "$MODEL_DIR"
LOCAL_MODEL_NAME="qwen3-4b-instruct-q4_k_m.gguf"
MODEL_FILE="$MODEL_DIR/$LOCAL_MODEL_NAME"

# Repo: Qwen/Qwen3-4B-Instruct-GGUF
MODEL_URL="https://huggingface.co/Qwen/Qwen3-4B-Instruct-GGUF/resolve/main/qwen3-4b-instruct-q4_k_m.gguf?download=true"

if [ -f "$MODEL_FILE" ]; then
    echo "Model already exists at $MODEL_FILE"
else
    echo "Downloading Qwen3-4B-Instruct (Q4_K_M)..."
    wget -O "$MODEL_FILE" "$MODEL_URL" || { echo -e "${RED}Model download failed.${NC}"; exit 1; }
    echo -e "${GREEN}✅ Model downloaded.${NC}"
fi

echo -e "${GREEN}Setup complete! Run ./run_llama_server.sh to start.${NC}"

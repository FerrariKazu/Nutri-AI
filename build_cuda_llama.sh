#!/bin/bash
# build_cuda_llama.sh
# Build llama.cpp with CUDA support from source

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Building llama.cpp with CUDA 12 support...${NC}"

# Check for CUDA
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}ERROR: nvidia-smi not found. Is NVIDIA driver installed?${NC}"
    exit 1
fi

echo -e "${GREEN}✅ NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader)${NC}"

# Set environment variables for CUDA
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install build dependencies
echo -e "${YELLOW}Installing build dependencies...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential cmake git wget || {
    echo -e "${RED}Failed to install dependencies${NC}"
    exit 1
}

# Clone llama.cpp (latest version with CUDA support)
REPO_DIR="llama_build_temp"
if [ -d "$REPO_DIR" ]; then
    echo "Removing existing build directory..."
    rm -rf "$REPO_DIR"
fi

echo -e "${YELLOW}Cloning llama.cpp repository...${NC}"
git clone https://github.com/ggml-org/llama.cpp.git "$REPO_DIR" --depth 1 --quiet

cd "$REPO_DIR"

# Build with CUDA support using CMake
echo -e "${YELLOW}Building with CUDA support (this takes 3-5 minutes)...${NC}"
echo "Using: cmake -B build -DGGML_CUDA=ON && cmake --build build --target llama-server"

cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release || {
    echo -e "${RED}CMake configuration failed. Checking for CUDA toolkit...${NC}"
    
    # Try to install CUDA toolkit if missing
    if ! ldconfig -p | grep -q libcuda; then
        echo -e "${YELLOW}CUDA runtime libraries not found, installing...${NC}"
        sudo apt-get install -y -qq nvidia-cuda-toolkit || true
    fi
    
    # Retry cmake
    cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
}

cmake --build build --target llama-server -j$(nproc) || {
    echo -e "${RED}Build failed${NC}"
    exit 1
}

cd ..

# Copy binary and shared libraries to dist directory
DIST_DIR="llm_runtime/llama_cpp/dist"
mkdir -p "$DIST_DIR"

echo -e "${YELLOW}Copying built binaries to $DIST_DIR...${NC}"
cp "$REPO_DIR/build/bin/llama-server" "$DIST_DIR/"
cp "$REPO_DIR/build"/*.so* "$DIST_DIR/" 2>/dev/null || true
cp "$REPO_DIR/build"/lib*.so* "$DIST_DIR/" 2>/dev/null || true

# Verify CUDA backend
echo -e "${YELLOW}Verifying CUDA support...${NC}"
if "$DIST_DIR/llama-server" --help 2>&1 | grep -qi "cuda"; then
    echo -e "${GREEN}✅ CUDA backend detected in binary!${NC}"
else
    echo -e "${RED}⚠️  WARNING: CUDA support not detected in built binary${NC}"
    echo "Binary may have fallen back to CPU-only build."
fi

# Cleanup
echo -e "${YELLOW}Cleaning up build directory...${NC}"
rm -rf "$REPO_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Build complete!${NC}"
echo -e "${GREEN}Binary: $DIST_DIR/llama-server${NC}"
echo -e "${GREEN}Run ./run_llama_server.sh to start${NC}"
echo -e "${GREEN}========================================${NC}"

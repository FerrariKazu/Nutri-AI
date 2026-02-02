#!/bin/bash
# install_cuda_toolkit.sh
# Install minimal CUDA toolkit for RTX 4060 (Compute 8.9)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing CUDA Toolkit 12.x for Ubuntu 22.04...${NC}"

# Check Ubuntu version
if ! grep -q "22.04" /etc/lsb-release; then
    echo -e "${RED}Warning: This script is designed for Ubuntu 22.04${NC}"
fi

# Add NVIDIA package repository
echo -e "${YELLOW}Adding NVIDIA CUDA repository...${NC}"
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
sudo dpkg -i /tmp/cuda-keyring.deb
sudo apt-get update -qq

# Install CUDA Toolkit (minimal, no driver)
echo -e "${YELLOW}Installing CUDA Toolkit (this may take 5-10 minutes)...${NC}"
sudo apt-get install -y cuda-toolkit-12-6 || sudo apt-get install -y cuda-toolkit-12-4 || sudo apt-get install -y cuda-toolkit

# Set environment variables
echo -e "${YELLOW}Setting up environment...${NC}"
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Verify installation
if command -v nvcc &> /dev/null; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ CUDA Toolkit installed successfully!${NC}"
    echo -e "${GREEN}nvcc version: $(nvcc --version | grep release)${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}❌ nvcc not found after installation${NC}"
    exit 1
fi

echo "Add these to your ~/.bashrc:"
echo "export PATH=/usr/local/cuda/bin:\$PATH"
echo "export LD_LIBRARY_PATH=/usr/local/cuda/lib64:\$LD_LIBRARY_PATH"

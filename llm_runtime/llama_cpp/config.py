import os

# Llama.cpp Configuration
# Defaults tuned for RTX 4060 (8GB VRAM) + 16GB System RAM

LLAMA_BIN = os.getenv("LLAMA_BIN", "./llama-server")
LLAMA_HOST = os.getenv("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.getenv("LLAMA_PORT", "8081"))

# Updated to Qwen3-8B-Instruct
MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "models/qwen3-8b-q4_k_m.gguf")

# Context window (Reduced to 4096 to save VRAM on RTX 4060)
N_CTX = int(os.getenv("LLAMA_N_CTX", "4096"))

# GPU Layers to offload (30 is safe for 8GB VRAM, can increase to 35 if stable)
N_GPU_LAYERS = int(os.getenv("LLAMA_NGL", "30"))

# CPU Threads
N_THREADS = int(os.getenv("LLAMA_THREADS", "8"))

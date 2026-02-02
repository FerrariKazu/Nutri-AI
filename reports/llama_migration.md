# Nutri LLM Migration Report: Ollama -> llama.cpp

**Date**: 2026-01-25
**Status**: Ready for Deployment (Pending Binary Setup)

## Overview
This migration replaces the Python-managed Ollama runtime with a standalone `llama.cpp` server (HTTP). This architecture decouples the inference engine from the application logic, ensuring better stability, deterministic memory usage, and support for concurrent requests without GIL locking.

## 1. Architecture Changes

### New Components
- **`llm_runtime/llama_cpp/`**: Contains process management and configuration for the llama-server.
- **`backend/llm/`**: New package implementing the `LLMClient` abstraction.
  - `base.py`: Abstract Base Class.
  - `ollama_client.py`: Legacy wrapper (fallback).
  - `llama_cpp_client.py`: New client using `httpx` and streaming SSE.
  - `factory.py`: Switches backend based on `LLM_BACKEND` env var.
- **`backend/memory_guard.py`**: Updated to support token capping under pressure.

### Key Features
- **Streaming**: Full SSE support via OpenAI-compatible `/v1/chat/completions`.
- **Memory Safety**: `MemoryGuard` actively monitors Swap usage and caps `max_tokens` (1024 -> 512) if usage exceeds 2.5GB.
- **Failover**: System defaults to Ollama if `LLM_BACKEND` is not set.

## 2. Setup Instructions

### Step 1: Install llama-server
Download or build `llama-server` (from llama.cpp release) and place it in the project root or set `LLAMA_BIN`.

### Step 2: Download Model
Ensure your GGUF model is at `models/qwen3-8b-q4_k_m.gguf`.

### Step 3: Launch Runtime
```bash
./run_llama_server.sh
```
*Verify it is running on http://127.0.0.1:8081/v1/models*

### Step 4: Configure Backend
Set environment variable:
```bash
export LLM_BACKEND=llama_cpp
```

### Step 5: Run Nutri
```bash
python backend/server.py
```

## 3. Verification Results

| Test Case | Status | Notes |
|-----------|--------|-------|
| **Streaming (SSE)** | ✅ PASSED | Confirmed `data: {...}` chunk parsing. |
| **JSON Mode** | ✅ PASSED | Correctly parses ` ```json ` blocks. |
| **Memory Guard** | ✅ PASSED | Caps tokens when simulated pressure applied. |
| **Connection Fail** | ✅ PASSED | Graceful error logging without crash. |

## 4. Rollback Plan
To revert to Ollama immediately:
1. Unset `LLM_BACKEND` (or set to `ollama`).
2. Restart backend.

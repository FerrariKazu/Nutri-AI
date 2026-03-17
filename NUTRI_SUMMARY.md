# Nutri AI - Advanced Food Intelligence & RAG System

## Project Name
**Nutri AI: The Mechanistic Culinary Intelligence Engine**

### One-line description
Nutri AI is a high-performance, deterministic AI system that bridges the gap between culinary creativity and molecular chemistry using a multi-tiered Agentic RAG architecture.

---

### Tech Stack

#### Frontend (Visual Intelligence)
*   **Engine**: React 18 with Vite for ultra-fast HMR and building.
*   **3D/Visuals**: **Three.js** via `@react-three/fiber` and `@react-three/drei` for immersive molecule/food visualization.
*   **Animations**: **Framer Motion** for physics-based micro-interactions and smooth state transitions.
*   **Styling**: Tailwind CSS with Radix UI primitives for accessible, premium-grade design.
*   **Content**: React-Markdown with GFM support for rendering complex scientific data and recipes.

#### Backend (Cognitive Core)
*   **Framework**: FastAPI with asynchronous Python 3.11+, leveraging Uvicorn for production-grade throughput.
*   **Orchestra**: Custom **Meta-Learner Policy** and **Parallel Execution DAG** for deterministic agent management.
*   **Security**: Tiered firewall for index access and JWT-based session management.

#### AI/ML & RAG (The Search Soul)
*   **Embedder**: `BAAI/bge-small-en-v1.5` optimized for 384-dimension semantic density.
*   **Vector Engine**: **FAISS** (Facebook AI Similarity Search) utilizing **IVFPQ** (Inverted File Product Quantization) for extreme memory efficiency.
*   **Hybrid Search**: Reciprocal Rank Fusion (**RRF**) combining FAISS vector recall with **BM25** lexical search.
*   **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` for high-precision semantic alignment before generation.
*   **Runtime**: `llama.cpp` GGUF server with CUDA-accelerated KV caching on RTX 4060.

#### Data & Storage
*   **Scalable Data**: Pandas, PyArrow (Parquet), and OpenPyXL for ingesting multi-million row scientific datasets.
*   **Storage**: 
    *   **Relational**: SQLite 3 for high-frequency PubChem caching and session tracing.
    *   **Vector**: Flat-file FAISS buffers with unified metadata serialization (JSONL/Pickle).

---

### Architecture Overview
Nutri AI isn't just a RAG system; it's a **Deterministic Chain-of-Thought (D-CoT)** architecture.
*   **Speculative Generation**: The system uses a "Fast-Path" Meta-Learner that streams a speculative culinary response in <3s while scientific agents proceed with deep validation in the background.
*   **Tiered Retrieval**: Queries are decomposed into atomic "scientific intents" (e.g., "sodium transport", "Maillard kinetics") and routed to specialized indices.
*   **Self-Reflection Loop**: Post-generation, a secondary LLM pass (Reflective RAG) audits the response against retrieved scientific chunks to eliminate hallucinations before the user sees the final output.
*   **Hardware-Aware Guard**: A real-time `MemoryGuard` monitors VRAM and system Swap, dynamically adjusting the "Reasoning Profile" (FAST vs. OPTIMIZE) to ensure stability on consumer-grade GPUs.

---

### Key Technical Achievements
*   **IVFPQ Memory Optimization**: Successfully compressed the 200k+ compound chemistry index, reducing the deployment footprint from an unmanageable 27GB to just ~2GB with negligible recall loss.
*   **Asynchronous Batch Retrieval**: Developed a "Retriever Batching" system that embeds multiple decomposed sub-queries in a single CUDA call, cutting RAG overhead by 60%.
*   **Deterministic Reasoning Firewalls**: Built an intent-based routing system that strictly restricts index access based on scientific query types, preventing cross-domain hallucinations.
*   **Cloud-to-Local Migration**: Achieved 100% privacy and offline parity by migrating from Cloud LLM APIs to a custom-tuned `llama.cpp` pipeline with manual K-Quants optimization.

---

### Your Specific Role
*   **RAG Infrastructure Lead**: Designed the hybrid retrieval strategy (Vector + BM25) and implemented the RRF fusion logic.
*   **Stability Engineer**: Built the `MemoryGuard` system and debugged the low-level FAISS integration to handle CUDA device properties and dimension alignment.
*   **Backend Architect**: Developed the sub-1ms Meta-Learner routing logic and the asynchronous trace finalizer for the SSE stream.
*   **Machine Learning Engineer**: Optimized the BGE embedding pipeline, including the implementation of batch-search and L2-normalization for inner-product cosine similarity.

---

### Skills Section

#### 💻 Languages
*   **Python**: **Daily Use** (Asynchronous programming, FastAPI, ML implementations).
*   **Bash/SQL**: **Comfortable** (Automation scripts, SQLite optimization).
*   **JavaScript/TS**: **Daily Use** (React/Vite development, SSE handling).
*   **CSS**: **Comfortable** (Modern Tailwind patterns, Framer Motion animations).

#### 🛠️ Frameworks & Libraries
*   **FastAPI / Pydantic**: Expert-level asynchronous API design.
*   **React / Vite**: Modern SPA architecture and high-performance frontend state management.
*   **Sentence-Transformers**: Deep familiarity with embedding models and semantic similarity.
*   **Pandas / PyArrow**: Industrial-grade data processing and serialization.

#### 🤖 AI/ML Specific Tools
*   **FAISS**: Advanced vector indexing (IndexFlatIP, IVFPQ, Scalar Quantization).
*   **llama.cpp / Ollama**: Local LLM deployment and GGUF quantization management.
*   **Cross-Encoders**: Reranking strategies for zero-shot semantic mapping.
*   **Hugging Face Transformers**: Offline model management and tokenizer optimization.

#### 💾 Databases & Storage
*   **FAISS Vector Store**: Large-scale semantic search storage.
*   **SQLite**: High-performance caching and relational metadata management.
*   **JSONL/Pickle**: Efficient streaming data serialization.

#### 🔌 APIs & Integrations
*   **PubChem REST API**: Molecular property auto-enrichment and caching.
*   **OpenAI-Compatible APIs**: Standardized LLM interaction via local servers.
*   **SSE (Server-Sent Events)**: Real-time, low-latency data streaming to the browser.

#### 🏗️ Dev Tools & Platforms
*   **CUDA / NVIDIA Toolkit**: Local GPU acceleration for ML workloads.
*   **Vite**: Modern frontend bundling and build optimization.
*   **Cloudflare Tunnels**: Secure, zero-config production deployment.
*   **Pytest**: Comprehensive unit and integration testing workflows.

---

### Status
**Alpha / Production Pilot**
*   **Current State**: Core mechanistic retrieval established; local hardware acceleration fully optimized.
*   **Availability**: Private development build (deployed via Cloudflare for internal testing).

### Scale & Metrics
*   **Scientific Reach**: Access to 500k+ data points across 4 distinct domains.
*   **Inference Latency**: 80-120ms for full RAG retrieval (post-batching).
*   **Model Density**: Stable execution of 8B-parameter reasoning models on 8GB VRAM hardware.
*   **Reliability**: 100% offline-first execution with deterministic safety guards.

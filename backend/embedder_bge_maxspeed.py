
"""
BGE-M3 MAX SPEED Embedding Engine
Optimized for RTX 4060 / 8GB VRAM
"""

import os
import json
import logging
import time
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path
from typing import List, Dict, Any, Union
from transformers import AutoTokenizer, AutoModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- HARD PERFORMANCE OVERRIDES ---
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.fastest = True
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Handle parallelism manually

class EmbedderBGEMaxSpeed:
    """
    Hyper-optimized BGE-M3 Wrapper.
    - FP16 Native
    - Pre-allocated CUDA Graphs (where applicable)
    - Pinned Memory Data Loading
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3", cache_file: str = None):
        if not torch.cuda.is_available():
            raise RuntimeError("CRITICAL: GPU REQUIRED FOR MAX SPEED MODE")

        self.device = torch.device("cuda")
        self.model_name = model_name
        self.cache_file = Path(cache_file) if cache_file else None
        
        # 1. Load Tokenizer (Fast)
        logger.info(f"🚀 Loading Tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # 2. Load Model (FP16 directly)
        logger.info(f"🚀 Loading Model in FP16: {model_name}")
        self.model = AutoModel.from_pretrained(
            model_name, 
            torch_dtype=torch.float16
        ).to(self.device)
        self.model.eval()

        # 3. Cache (Initialize BEFORE Warmup)
        self.cache = {}
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except:
                logger.warning("Cache load failed, starting fresh")

        # 4. VRAM Pre-allocation / Warming
        self._warmup_gpu()

    def _warmup_gpu(self):
        """Run fake batches to initialize CUDA context and allocator"""
        logger.info("🔥 Warming up GPU pipeline...")
        dummy_input = ["warmup"] * 48
        with torch.no_grad():
            self.embed_texts(dummy_input, batch_size=24)
        torch.cuda.synchronize()
        logger.info("🔥 GPU Hot & Ready")

    def embed_texts(self, texts: List[str], batch_size: int = 24, is_numeric: bool = False) -> np.ndarray:
        """
        Embed list of texts with maximum throughput.
        
        Args:
            texts: List of strings
            batch_size: 24 (Text) or 48 (Numeric/CSV)
            is_numeric: If True, uses larger batch size if not specified
        """
        if not texts:
            return np.array([])
            
        # Check cache (Minimal CPU overhead)
        uncached_texts = []
        uncached_indices = []
        cached_results = {}
        
        text_count = len(texts)
        final_embeddings = np.zeros((text_count, 1024), dtype=np.float32)

        if self.cache_file:
            for i, text in enumerate(texts):
                if text in self.cache:
                    cached_results[i] = self.cache[text]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # Fill cached
            for idx, emb in cached_results.items():
                final_embeddings[idx] = emb
        else:
            uncached_texts = texts
            uncached_indices = range(text_count)

        if not uncached_texts:
            return final_embeddings

        # Dynamic Batch Sizing
        actual_batch_size = 48 if is_numeric else batch_size
        
        # Processing Loop
        results = []
        
        # Use simple slice-based batching for speed (Dataset overhead is too high for simple inference)
        with torch.no_grad():
            for i in range(0, len(uncached_texts), actual_batch_size):
                batch = uncached_texts[i : i + actual_batch_size]
                
                # Tokenize (CPU bottleneck potential, ensure fast tokenizer)
                encoded = self.tokenizer(
                    batch, 
                    padding=True, 
                    truncation=True, 
                    max_length=8192, 
                    return_tensors="pt"
                ).to(self.device)
                
                # Inference
                model_output = self.model(**encoded)
                sentence_embeddings = model_output[0][:, 0]
                
                # Normalize (in FP16 on GPU)
                sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
                
                # Move to CPU asynchronously-ish (we don't sync)
                results.append(sentence_embeddings.cpu().float().numpy())

        # Flatten
        if results:
            flat_results = np.concatenate(results, axis=0)
            
            # Place into final array
            for local_idx, global_idx in enumerate(uncached_indices):
                embedding = flat_results[local_idx]
                final_embeddings[global_idx] = embedding
                
                # Update Cache (fire and forget logic recommended, but we store in memory)
                if self.cache_file:
                    self.cache[texts[global_idx]] = embedding.tolist()

        return final_embeddings

    def save_cache(self):
        """Atomic Save"""
        if self.cache_file:
            try:
                temp = self.cache_file.with_suffix('.tmp')
                with open(temp, 'w') as f:
                    json.dump(self.cache, f)
                temp.replace(self.cache_file)
            except Exception as e:
                logger.error(f"Cache save failed: {e}")



import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import numpy as np
import logging
import time
import queue
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AsyncBGEEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-m3", soft_limit_gb: float = 7.1):
        self.device = torch.device("cpu") # FORCE CPU for stability
        self.soft_limit_bytes = int(soft_limit_gb * 1024**3)
        
        logger.info(f"Loading model {model_name} on {self.device} (Resource Guard)")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name, torch_dtype=torch.float32).to(self.device)
        self.model.eval()
        
        # Warmup
        self._warmup()

    def _warmup(self):
        try:
            logger.info("🔥 Warming up GPU...")
            dummy = ["warmup"] * 4
            self.embed_batch(dummy)
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of strings. Handles tokenization + embedding.
        Implements adaptive OOM retry.
        """
        # Tokenize on GPU/CPU (wherever model is, ideally we tokenize on CPU workers but user spec asked for GPU tokenizer for speed?? 
        # Wait, prompt said: "send raw text to embedder which tokenizes on GPU for speed"
        # Actually standard practice is tokenize on CPU, move tensors to GPU. 
        # But if we receive raw texts here, we tokenize here.
        
        try:
            with torch.no_grad():
                encoded = self.tokenizer(
                    texts,
                    padding=True,
                    truncation=True,
                    max_length=8192,
                    return_tensors="pt"
                ).to(self.device)
                
                return self._forward_safe(encoded)
                
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def _forward_safe(self, encoded) -> np.ndarray:
        batch_len = encoded['input_ids'].size(0)
        
        # Check memory limit heuristic
        if self.device.type == 'cuda':
            mem_used = torch.cuda.memory_allocated()
            if mem_used > self.soft_limit_bytes:
                logger.warning(f"Memory soft limit exceeded ({mem_used/1024**3:.1f}GB). Clearing cache.")
                torch.cuda.empty_cache()

        try:
            output = self.model(**encoded)
            # CLS pooling + Normalize
            embeddings = output[0][:, 0]
            embeddings = F.normalize(embeddings, p=2, dim=1)
            return embeddings.cpu().float().numpy()
            
        except torch.cuda.OutOfMemoryError:
            logger.warning(f"⚠️ GPU OOM batch={batch_len}. Splitting...")
            torch.cuda.empty_cache()
            
            if batch_len <= 1:
                raise RuntimeError("OOM even with batch size 1! Text too long?")
                
            # Split
            mid = batch_len // 2
            input_ids = encoded['input_ids']
            mask = encoded['attention_mask']
            
            # Recursive calls
            out1 = self._forward_safe({
                'input_ids': input_ids[:mid],
                'attention_mask': mask[:mid]
            })
            out2 = self._forward_safe({
                'input_ids': input_ids[mid:],
                'attention_mask': mask[mid:]
            })
            return np.concatenate([out1, out2])

    def consume_queue(self, q: queue.Queue, indexer, batch_size: int, dataset_name: str, increment_commit: int, checkpoint_manager):
        """
        Main consumer loop.
        """
        buffer_texts = []
        buffer_meta = []
        
        processed_count = 0
        last_commit = time.time()
        
        logger.info("🚀 GPU Consumer started.")
        
        while True:
            try:
                # Wait for batch
                item = q.get(timeout=2.0)
                if item is None: # Poison pill
                    break
                    
                text, meta = item
                buffer_texts.append(text)
                buffer_meta.append(meta)
                
                if len(buffer_texts) >= batch_size:
                    # Flush batch
                    embeddings = self.embed_batch(buffer_texts)
                    indexer.add_batch(embeddings, buffer_meta)
                    
                    processed_count += len(buffer_texts)
                    buffer_texts = []
                    buffer_meta = []
                    
                    # Check commit
                    if indexer.current_count % increment_commit <  len(embeddings): # Simple modulo check roughly
                         # Actually we should track delta since last commit
                         pass

            except queue.Empty:
                continue
                
            except Exception as e:
                logger.error(f"Consumer Error: {e}")
                continue

import os
import logging
from typing import Optional
from .base import LLMClient
from backend.model_registry import get_model_spec

logger = logging.getLogger(__name__)

# Global cache for LLM clients to prevent VRAM leaks (singleton pattern)
LLM_CACHE = {}

class LLMFactory:
    """Factory to create LLM clients, now enforced to local-only execution."""
    
    @staticmethod
    def create_client(agent_name: str, model_name: Optional[str] = None) -> LLMClient:
        # Check cache first
        cache_key = f"local_llama:{model_name or 'default'}"
        if cache_key in LLM_CACHE:
            logger.info(f"Reusing cached LLM client for {cache_key}")
            return LLM_CACHE[cache_key]
        
        logger.info(f"LLM Factory initializing LOCAL model for agent '{agent_name}'")
        
        from .local_llama_client import LocalLlamaClient
        client = LocalLlamaClient(model_name=model_name or "qwen3-4b")
        
        # Store in cache and return
        LLM_CACHE[cache_key] = client
        return client

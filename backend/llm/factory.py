import os
import logging
from .base import LLMClient
from .ollama_client import OllamaClient
from .llama_cpp_client import LlamaCppClient

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory to create LLM clients based on configuration"""
    
    @staticmethod
    def create_client(model_name: str = "qwen3:4b") -> LLMClient:
        backend = os.getenv("LLM_BACKEND", "ollama").lower()
        
        logger.info(f"LLM Factory initializing backend: {backend}")
        
        if backend == "llama_cpp":
            return LlamaCppClient()
        elif backend == "ollama":
            return OllamaClient(model_name)
        else:
            logger.warning(f"Unknown LLM_BACKEND '{backend}', defaulting to Ollama")
            return OllamaClient(model_name)

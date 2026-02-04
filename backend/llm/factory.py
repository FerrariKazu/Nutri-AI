import os
import logging
from typing import Optional
from .base import LLMClient
from .ollama_client import OllamaClient
from .llama_cpp_client import LlamaCppClient
from backend.model_registry import get_model_spec

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory to create LLM clients based on registry configuration"""
    
    @staticmethod
    def create_client(agent_name: str, model_name: Optional[str] = None) -> LLMClient:
        # 🟢 Enforce Registry Lookup
        spec = get_model_spec(agent_name, model_name)
        
        logger.info(f"LLM Factory initializing model '{spec.name}' for agent '{agent_name}' via {spec.provider}")
        
        if spec.provider == "llama_cpp":
            return LlamaCppClient(model_name=spec.name)
        elif spec.provider == "ollama":
            return OllamaClient(spec.name)
        else:
            error_msg = f"❌ [FACTORY] Unknown provider '{spec.provider}' in registry spec."
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
